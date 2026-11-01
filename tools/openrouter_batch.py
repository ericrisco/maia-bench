#!/usr/bin/env python3
"""Runs the knowledge questions on one OpenRouter model through the Batch API (half price) and saves the answers.

Usage:  python3 tools/openrouter_batch.py --model anthropic/claude-haiku-5.5 [--limit 20] [--effort low]
        then: python3 tools/judge_batch.py resultats/openrouter_<model>   and   python3 tools/puntua.py ... --sense-jutge

Same prompt and system message as executa.py; only the transport changes. Answers go to
resultats/openrouter_<model>/respostes.jsonl in executa.py's format, so judge_batch.py, puntua.py and the page read
them unchanged. Only questions without a non-empty answer are sent, so a rerun fills the gaps (and --limit makes a
cheap pilot). The batch id is kept in the folder while it runs: rerunning the command resumes waiting for it instead
of paying for a second batch. Needs OPENROUTER_API_KEY (01-TOOLS/OPENROUTER/.env).
"""
import argparse
import base64
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from executa import ARREL, SISTEMA, VERSIO_PROMPT, empremta_dataset, missatges, nom_carpeta, preguntes  # noqa: E402

API = "https://openrouter.ai/api/v1/batches"
FINAL = ("completed", "failed", "expired", "cancelled")


def api(url, body=None, method=None, missing_ok=False):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("needs OPENROUTER_API_KEY (01-TOOLS/OPENROUTER/.env)")
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if missing_ok and e.code == 404:  # a new batch can take a moment to become readable
            return None
        sys.exit(f"HTTP {e.code}: {e.read()[:500].decode(errors='replace')}")


def to_custom_id(qid):
    # some providers (Anthropic) only take [A-Za-z0-9_-] in custom_id; question ids have "/"
    return base64.urlsafe_b64encode(qid.encode()).decode().rstrip("=")


def from_custom_id(cid):
    return base64.urlsafe_b64decode(cid + "=" * (-len(cid) % 4)).decode()


def answered(path):
    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if not r.get("error") and r.get("resposta", "").strip():
                done.add(r["id"])
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="OpenRouter slug, e.g. anthropic/claude-haiku-5.5")
    ap.add_argument("--limit", type=int, help="only the first N pending questions (pilot)")
    ap.add_argument("--effort", default="low", help="reasoning effort (low keeps reasoning from eating the answer)")
    ap.add_argument("--max-tokens", type=int, default=8000)
    a = ap.parse_args()

    model = f"openrouter:{a.model}"
    folder = os.path.join(ARREL, "resultats", nom_carpeta(model))
    os.makedirs(folder, exist_ok=True)
    answers_path = os.path.join(folder, "respostes.jsonl")
    pending_path = os.path.join(folder, ".batch_id")
    rows = preguntes()

    meta_path = os.path.join(folder, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ARREL, capture_output=True, text=True).stdout.strip()
    meta.update({"model": model, "origen": meta.get("origen", ""), "prompt": VERSIO_PROMPT, "sistema": SISTEMA,
                 "temperatura": 0, "max_tokens": a.max_tokens, "raonament": a.effort, "transport": "openrouter-batch",
                 "dataset": empremta_dataset(rows), "preguntes_dataset": len(rows), "commit": git})
    meta.setdefault("inici", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)

    if os.path.exists(pending_path):
        batch_id = open(pending_path).read().strip()
        print(f"{model}: resuming batch {batch_id}", file=sys.stderr)
    else:
        done = answered(answers_path)
        todo = [r for r in rows if r["id"] not in done][: a.limit]
        print(f"{model}: {len(todo)} questions to send ({len(done)} already answered)", file=sys.stderr)
        if not todo:
            return
        # endpoint and model go before requests: OpenRouter reads the body as a stream
        batch = api(API, {"endpoint": "/v1/chat/completions", "model": a.model,
                          "requests": [{"custom_id": to_custom_id(r["id"]),
                                        "body": {"messages": missatges(r), "temperature": 0,
                                                 "max_tokens": a.max_tokens, "reasoning": {"effort": a.effort}}}
                                       for r in todo]})
        batch_id = batch["id"]
        open(pending_path, "w").write(batch_id)
        print(f"batch {batch_id} on {batch.get('provider')} ({len(todo)} requests)", file=sys.stderr)

    while True:
        batch = api(f"{API}/{batch_id}", missing_ok=True)
        if batch and batch["status"] in FINAL:
            break
        time.sleep(60)
    print(f"status {batch['status']} {batch.get('request_counts')} {batch.get('error') or ''}", file=sys.stderr)

    written = empty = errors = 0
    with open(answers_path, "a", encoding="utf-8") as out:
        for r in batch.get("results") or []:
            qid = from_custom_id(r["custom_id"])
            body = (r.get("response") or {}).get("body") or {}
            if r.get("error") or not body.get("choices"):
                row = {"id": qid, "error": json.dumps(r.get("error") or body.get("error") or "no choices")[:300]}
                errors += 1
            else:
                usage = body.get("usage") or {}
                text = (body["choices"][0]["message"].get("content") or "").strip()
                row = {"id": qid, "resposta": text, "tokens_entrada": usage.get("prompt_tokens", 0),
                       "tokens_sortida": usage.get("completion_tokens", 0), "raonament": a.effort}
                empty += not text
                written += 1
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.remove(pending_path)
    meta["fi"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    meta["cost_usd"] = round(meta.get("cost_usd", 0) + ((batch.get("usage") or {}).get("cost") or 0), 4)
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    print(f"done: {written} answers ({empty} empty), {errors} errors, batch cost {batch.get('usage', {}) and batch['usage'].get('cost')} $,"
          f" total {meta['cost_usd']} $ -> {answers_path}")


if __name__ == "__main__":
    main()
