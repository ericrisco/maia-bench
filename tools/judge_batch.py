#!/usr/bin/env python3
"""Judges pending open and trap answers with Vertex AI Batch and appends the scores to puntuacions.jsonl.

Usage:  python3 tools/judge_batch.py resultats/<name> [resultats/<name2> ...] [--model gemini-3.8-flash]
        then: python3 tools/puntua.py resultats/<name>   (scores the tests and writes resum.json)

Same prompt, rubric and judge as puntua.py; only the transport changes (one batch job instead of online calls),
which is not affected by the project's block on online Gemini calls. Rows are tagged with puntua.py's judge id so
puntua.py treats them as done. Field names (nota, punts, motiu, jutge, tipus) are puntua.py's data schema.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from executa import preguntes  # noqa: E402
from puntua import JUTGE, prompt_jutge  # noqa: E402

PROJECT = os.environ.get("GCP_PROJECT", "maia-andorra")
ACCOUNT = os.environ.get("GCP_ACCOUNT", "ericriscodelatorre@gmail.com")
BUCKET = os.environ.get("BATCH_BUCKET", "gs://maia-andorra-entrenaments/jutge-batch")
API = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/batchPredictionJobs"
FINAL_STATES = ("JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED",
                "JOB_STATE_PARTIALLY_SUCCEEDED")


def gcloud(*args):
    return subprocess.run(["gcloud", *args, f"--project={PROJECT}", f"--account={ACCOUNT}"],
                          check=True, capture_output=True, text=True).stdout


def access_token():
    return subprocess.run(["gcloud", "auth", "print-access-token", f"--account={ACCOUNT}"],
                          check=True, capture_output=True, text=True).stdout.strip()


def api(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {access_token()}",
                                          "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def to_request(messages):
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    user = "\n".join(m["content"] for m in messages if m["role"] == "user")
    return {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 4000}}


def pending(folder, dataset):
    answers = {}
    for line in open(os.path.join(folder, "respostes.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if not r.get("error"):
            answers[r["id"]] = r["resposta"]
    done = set()
    scores = os.path.join(folder, "puntuacions.jsonl")
    if os.path.exists(scores):
        for line in open(scores, encoding="utf-8"):
            r = json.loads(line)
            if r.get("jutge") in (None, JUTGE):
                done.add(r["id"])
    return {i: a for i, a in answers.items() if i in dataset and dataset[i]["tipus"] != "test" and i not in done}


def append_score(folder, row):
    with open(os.path.join(folder, "puntuacions.jsonl"), "a", encoding="utf-8") as out:
        out.write(json.dumps(row, ensure_ascii=False) + "\n")


def score_row(dataset, qid, nota, motiu):
    return {"id": qid, "tipus": dataset[qid]["tipus"], "nota": nota, "punts": nota / 2, "motiu": motiu,
            "jutge": JUTGE, "transport": "batch"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--model", default=JUTGE.split("/")[-1])
    args = ap.parse_args()

    dataset = {p["id"]: p for p in preguntes()}
    rows, empty = [], []
    for folder in args.folders:
        for qid, answer in pending(folder, dataset).items():
            if not answer.strip():
                empty.append((folder, qid))
            else:
                rows.append({"key": f"{folder}|{qid}", "request": to_request(prompt_jutge(dataset[qid], answer))})
    print(f"to judge: {len(rows)} · empty: {len(empty)}", file=sys.stderr)

    for folder, qid in empty:
        append_score(folder, score_row(dataset, qid, 0, "resposta buida"))
    if not rows:
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    local = os.path.join(args.folders[0], f".batch-{stamp}.jsonl")
    with open(local, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    source = f"{BUCKET}/{stamp}/input.jsonl"
    gcloud("storage", "cp", local, source)
    os.remove(local)
    job = api(API, {"displayName": f"judge-{stamp}", "model": f"publishers/google/models/{args.model}",
                    "inputConfig": {"instancesFormat": "jsonl", "gcsSource": {"uris": [source]}},
                    "outputConfig": {"predictionsFormat": "jsonl",
                                     "gcsDestination": {"outputUriPrefix": f"{BUCKET}/{stamp}/out"}}})
    job_id = job["name"].split("/")[-1]
    print(f"job {job_id} ({len(rows)} requests)", file=sys.stderr)
    while True:
        job = api(f"{API}/{job_id}")
        if job["state"] in FINAL_STATES:
            break
        time.sleep(60)
    print(f"state {job['state']} {job.get('completionStats', '')} {job.get('error', '')}", file=sys.stderr)

    errors = 0
    for path in gcloud("storage", "ls", "-r", f"{BUCKET}/{stamp}/out/").split():
        if not path.endswith(".jsonl"):
            continue
        for line in gcloud("storage", "cat", path).splitlines():
            r = json.loads(line)
            folder, _, qid = r["key"].partition("|")
            try:
                parts = r["response"]["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                verdict = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
                if verdict.get("nota") not in (0, 1, 2):
                    raise ValueError(f"invalid score: {verdict!r}")
            except (KeyError, IndexError, AttributeError, ValueError) as e:
                errors += 1
                print(f"ERROR {qid}: {r.get('status') or e}", file=sys.stderr)
                continue
            append_score(folder, score_row(dataset, qid, verdict["nota"], verdict.get("motiu", "")))
    print(f"done ({errors} errors; rerun the same command to resubmit them)", file=sys.stderr)


if __name__ == "__main__":
    main()
