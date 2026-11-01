#!/usr/bin/env bash
# Runs the benchmark on Ollama models served by a private Cloud Run service with a GPU (see docs/cloudrun.md).
#
# Usage:  tools/cloudrun.sh <service-url> <model> [<model> ...]
#         e.g. tools/cloudrun.sh https://maia-bench-ollama-...run.app gemma4:e2b gemma4:e4b
#
# For each model: pulls it into the service, runs the benchmark in 50-minute slices (the identity token expires
# after an hour and run.py resumes on its own), repeats until no errors are left, scores multiple choice and deletes
# the model from the service. It does not delete the service: do that by hand when done (gcloud run services delete).
set -uo pipefail
URL="$1"; shift
cd "$(dirname "$0")/.."
export OLLAMA_HOST="$URL"
TOTAL=$(python3 -c 'import sys; sys.path.insert(0, "tools"); from run import load_questions; print(len(load_questions()))')

answered() {  # answers without error for a model
  python3 - "$1" <<'EOF'
import json, os, sys
f = os.path.join("results", sys.argv[1], "answers.jsonl")
ok = set()
if os.path.exists(f):
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        if not r.get("error"):
            ok.add(r["id"])
print(len(ok))
EOF
}

for MODEL in "$@"; do
  FOLDER="ollama_${MODEL//[:\/]/_}"
  echo "== $MODEL ($(date +%H:%M))"
  export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
  if ! curl -sf -m 1800 "$URL/api/pull" -H "Authorization: Bearer $OLLAMA_TOKEN" \
       -d "{\"model\":\"$MODEL\",\"stream\":false}" >/dev/null; then
    echo "   could not pull it; skipping"; continue
  fi
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
    perl -e 'alarm shift; exec @ARGV' 3000 python3 tools/run.py --model "ollama:$MODEL" --threads 4 >/dev/null 2>&1
    N=$(answered "$FOLDER")
    echo "   slice $attempt: $N of $TOTAL"
    [ "$N" -ge "$TOTAL" ] && break
  done
  python3 tools/score.py "results/$FOLDER" --no-judge 2>/dev/null
  export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
  curl -s -m 120 -X DELETE "$URL/api/delete" -H "Authorization: Bearer $OLLAMA_TOKEN" -d "{\"model\":\"$MODEL\"}" >/dev/null
done
echo "END ($(date +%H:%M))"
