#!/usr/bin/env bash
# Passa el benchmark a models d'Ollama servits per un Cloud Run privat amb GPU (vegeu docs/cloudrun.md).
#
# Ús:  tools/cloudrun.sh <url-del-servei> <model> [<model> ...]
#      p. ex. tools/cloudrun.sh https://maia-bench-ollama-...run.app gemma4:e2b gemma4:e4b
#
# Per a cada model: el descarrega al servei, executa el benchmark en trams de 50 minuts (el token d'identitat
# caduca a l'hora i executa.py es reprèn sol), repeteix fins que no queden errors, puntua els tests i esborra el
# model del servei. No esborra el servei: això es fa a mà quan s'acaba (gcloud run services delete).
set -uo pipefail
URL="$1"; shift
cd "$(dirname "$0")/.."
export OLLAMA_HOST="$URL"
TOTAL=$(python3 -c 'import sys; sys.path.insert(0, "tools"); from executa import preguntes; print(len(preguntes()))')

fetes() {  # respostes sense error d'un model
  python3 - "$1" <<'EOF'
import json, os, sys
f = os.path.join("resultats", sys.argv[1], "respostes.jsonl")
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
  CARPETA="ollama_${MODEL//[:\/]/_}"
  echo "== $MODEL ($(date +%H:%M))"
  export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
  if ! curl -sf -m 1800 "$URL/api/pull" -H "Authorization: Bearer $OLLAMA_TOKEN" \
       -d "{\"model\":\"$MODEL\",\"stream\":false}" >/dev/null; then
    echo "   no s'ha pogut descarregar; el salto"; continue
  fi
  for intent in 1 2 3 4 5 6 7 8 9 10; do
    export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
    perl -e 'alarm shift; exec @ARGV' 3000 python3 tools/executa.py --model "ollama:$MODEL" --fils 4 >/dev/null 2>&1
    N=$(fetes "$CARPETA")
    echo "   tram $intent: $N de $TOTAL"
    [ "$N" -ge "$TOTAL" ] && break
  done
  python3 tools/puntua.py "resultats/$CARPETA" --sense-jutge 2>/dev/null
  export OLLAMA_TOKEN=$(gcloud auth print-identity-token)
  curl -s -m 120 -X DELETE "$URL/api/delete" -H "Authorization: Bearer $OLLAMA_TOKEN" -d "{\"model\":\"$MODEL\"}" >/dev/null
done
echo "FI ($(date +%H:%M))"
