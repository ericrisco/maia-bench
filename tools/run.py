#!/usr/bin/env python3
"""Sends the knowledge questions to a model and saves its answers.

Usage:  python3 tools/run.py --model ollama:gemma4:e4b [--limit N] [--threads 4] [--name label] [--origin text]

The model only gets the question (and the options for multiple choice): never the context or the reference answer.
Answers go to results/<name>/answers.jsonl. It resumes: questions already answered are skipped.
Then score them with tools/score.py.
"""
import argparse
import concurrent.futures as cf
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from providers import ModelError, call, split_model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_VERSION = "p1"

# The prompts are part of the benchmark data: the models are evaluated in Catalan.
SYSTEM = "Respon en català les preguntes sobre Andorra que et facin."
INSTR_MULTIPLE_CHOICE = "Respon només amb la lletra de l'opció correcta (A, B, C o D)."
INSTR_OPEN = "Respon de manera breu i precisa, en un màxim de tres frases."


def load_questions():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "knowledge", "*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                out.append(json.loads(line))
    return out


def dataset_fingerprint(rows):
    h = hashlib.sha256()
    for r in sorted(rows, key=lambda r: r["id"]):
        h.update(json.dumps(r, ensure_ascii=False, sort_keys=True).encode())
    return h.hexdigest()[:12]


def messages(q):
    if q["type"] == "multiple_choice":
        options = "\n".join(f"{k}) {q['options'][k]}" for k in "ABCD")
        user = f"{q['question']}\n\n{options}\n\n{INSTR_MULTIPLE_CHOICE}"
    else:
        user = f"{q['question']}\n\n{INSTR_OPEN}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def folder_name(model):
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", model).strip("_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="provider:model, e.g. ollama:gemma4:e4b")
    ap.add_argument("--name", help="results folder name (default: derived from the model)")
    ap.add_argument("--origin", default="", help="e.g. 'Andorra · project model'")
    ap.add_argument("--limit", type=int, help="only the first N questions (tests)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--retry-empty", action="store_true",
                    help="ask the empty answers again (models that spend every token reasoning)")
    ap.add_argument("--reasoning",
                    help="reasoning effort: low|medium|high, or a number (reasoning token cap, OpenRouter only); "
                         "with --retry-empty, only for the empty answers")
    a = ap.parse_args()
    split_model(a.model)

    rows = load_questions()
    total = len(rows)
    if a.limit:
        rows = rows[: a.limit]
    folder = os.path.join(ROOT, "results", a.name or folder_name(a.model))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "answers.jsonl")

    meta_path = os.path.join(folder, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    meta.update({"model": a.model, "origin": a.origin or meta.get("origin", ""), "prompt": PROMPT_VERSION,
                 "system": SYSTEM, "temperature": 0,
                 "dataset": dataset_fingerprint(load_questions()), "dataset_questions": total, "commit": git})
    if a.retry_empty:
        meta["max_tokens_empty_retry"] = a.max_tokens
        meta["reasoning_empty_retry"] = a.reasoning
    else:
        meta["max_tokens"] = a.max_tokens
        meta["reasoning"] = a.reasoning
    meta.setdefault("started", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)

    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if not r.get("error") and (r.get("answer") or not a.retry_empty):
                done.add(r["id"])
    pending = [r for r in rows if r["id"] not in done]
    print(f"{a.model}: {len(pending)} questions to answer ({len(done)} already done)", file=sys.stderr)

    lock = threading.Lock()
    errors = 0

    def one(q):
        t0 = time.time()
        try:
            res = call(a.model, messages(q), temperature=0, max_tokens=a.max_tokens, reasoning=a.reasoning)
            row = {"id": q["id"], "answer": res["text"].strip(), "input_tokens": res["input_tokens"],
                   "output_tokens": res["output_tokens"], "seconds": round(time.time() - t0, 2)}
            if a.reasoning:
                row["reasoning"] = a.reasoning
            return row
        except ModelError as e:
            return {"id": q["id"], "error": str(e)}

    with cf.ThreadPoolExecutor(a.threads) as ex, open(path, "a", encoding="utf-8") as out:
        for i, res in enumerate(ex.map(one, pending), 1):
            with lock:
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
            if res.get("error"):
                errors += 1
                print(f"ERROR {res['id']}: {res['error']}", file=sys.stderr)
            if i % 25 == 0:
                print(f"  {i}/{len(pending)}", file=sys.stderr)

    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    print(f"done: {len(pending) - errors} answers, {errors} errors -> {path}")


if __name__ == "__main__":
    main()
