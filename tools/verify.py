#!/usr/bin/env python3
"""Independent verification of the knowledge dataset.

A model from another family (by default Gemini 3.8 Flash on Vertex AI, through the OpenAI-compatible endpoint)
checks each entry **against the original article**, not against the context its author wrote. It catches
unsupported answers, contexts with additions, multiple-choice questions without a single correct option, traps whose
premise is not shown to be false, and ambiguous questions.

Usage:  python3 tools/verify.py knowledge/<file>.jsonl [...] --maia <maia root> --output <file.jsonl>

Needs an authenticated `gcloud` and Vertex AI access in GCP_PROJECT (default maia-andorra).
It resumes: entries already in --output are skipped.
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

PROJECT = os.environ.get("GCP_PROJECT", "maia-andorra")
MODEL = os.environ.get("JUDGE_MODEL", "google/gemini-3.8-flash")
URL = (
    f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}"
    "/locations/global/endpoints/openapi/chat/completions"
)
MAX_ARTICLE_WORDS = 9000

_token = {"value": None, "at": 0}
_lock = threading.Lock()


def token():
    with _lock:
        if not _token["value"] or time.time() - _token["at"] > 2400:
            r = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
            _token["value"], _token["at"] = r.stdout.strip(), time.time()
        return _token["value"]


# The verifier prompt works on Catalan content, so it is written in Catalan.
SYSTEM = (
    "Ets un verificador estricte d'un benchmark sobre Andorra. Et donen el text d'un o més ARTICLES font i una "
    "ENTRADA del benchmark (pregunta, context, resposta, etc.). Comproves l'entrada NOMÉS contra els articles: "
    "no facis servir coneixement extern. Respon únicament amb un objecte JSON."
)

INSTRUCTION = """Comprova l'entrada contra els articles i respon amb aquest JSON exacte:
{
 "resposta_suportada": true|false,   // la resposta és certa segons els articles
 "context_suportat": true|false,     // tot el que afirma el context surt dels articles, sense afegits ni errors
 "unica_correcta": true|false|null,  // només per a tests: l'opció marcada és correcta i cap altra ho és també
 "premissa_demostrada_falsa": true|false|null, // només per a trampes: els articles demostren que la premissa és falsa (no només que no hi consti)
 "ambigua": true|false,              // la pregunta admet més d'una resposta raonable o depèn d'un context que no diu
 "problemes": ["..."]                // frases curtes; buit si tot és correcte
}"""

# the entry is shown to the verifier with the Catalan field names its prompt refers to
PROMPT_FIELDS = {"type": "tipus", "question": "pregunta", "options": "opcions", "correct": "correcta",
                 "context": "context", "reference_answer": "resposta", "key_facts": "fets_clau",
                 "errors_to_penalise": "errors_a_penalitzar", "false_premise": "premissa_falsa"}
PROMPT_TYPES = {"multiple_choice": "test", "open": "oberta", "trap": "trampa"}


def read_articles(entry, maia):
    out = []
    for d in entry["documents"]:
        p = os.path.join(maia, d)
        try:
            t = open(p, encoding="utf-8").read()
        except OSError:
            t = "(article no trobat)"
        w = t.split()
        if len(w) > MAX_ARTICLE_WORDS:
            t = " ".join(w[:MAX_ARTICLE_WORDS]) + " …(tallat)"
        out.append(f"=== ARTICLE: {d} ===\n{t}")
    return "\n\n".join(out)


def entry_text(e):
    fields = {PROMPT_FIELDS[k]: (PROMPT_TYPES[e[k]] if k == "type" else e[k]) for k in PROMPT_FIELDS if k in e}
    return json.dumps(fields, ensure_ascii=False, indent=1)


def call(messages):
    body = json.dumps({"model": MODEL, "temperature": 0, "max_tokens": 6000,
                       "response_format": {"type": "json_object"}, "messages": messages}).encode()
    for attempt in range(5):
        req = urllib.request.Request(URL, data=body, headers={
            "Authorization": f"Bearer {token()}", "Content-Type": "application/json",
            "x-goog-user-project": PROJECT})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2 ** attempt * 3)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]!r}")
        except (urllib.error.URLError, TimeoutError):
            if attempt < 4:
                time.sleep(2 ** attempt * 3)
                continue
            raise
    raise RuntimeError("no answer")


def verify(e, maia):
    msg = [{"role": "system", "content": SYSTEM},
           {"role": "user", "content": f"{read_articles(e, maia)}\n\n=== ENTRADA ===\n{entry_text(e)}\n\n{INSTRUCTION}"}]
    d = call(msg)
    res = json.loads(d["choices"][0]["message"]["content"])
    u = d.get("usage", {})
    problems = res.get("problemes") or []
    ok = (res.get("resposta_suportada") is True and res.get("context_suportat") is True
          and not res.get("ambigua") and not problems)
    if e["type"] == "multiple_choice" and res.get("unica_correcta") is not True:
        ok = False
    if e["type"] == "trap" and res.get("premissa_demostrada_falsa") is not True:
        ok = False
    return {"id": e["id"], "ok": ok,
            "answer_supported": res.get("resposta_suportada"), "context_supported": res.get("context_suportat"),
            "single_correct": res.get("unica_correcta"), "premise_shown_false": res.get("premissa_demostrada_falsa"),
            "ambiguous": res.get("ambigua"), "problems": problems,
            "tokens": u.get("total_tokens", 0), "model": MODEL}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--maia", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()

    done = set()
    if os.path.exists(a.output):
        done = {json.loads(line)["id"] for line in open(a.output, encoding="utf-8") if line.strip()}
    pending = []
    for f in a.files:
        for line in open(f, encoding="utf-8"):
            if line.strip():
                e = json.loads(line)
                if e["id"] not in done:
                    pending.append(e)
    print(f"{len(pending)} entries to verify ({len(done)} already done)", file=sys.stderr)

    write = threading.Lock()
    tokens = ok = bad = err = 0
    with cf.ThreadPoolExecutor(a.threads) as ex, open(a.output, "a", encoding="utf-8") as out:
        futures = {ex.submit(verify, e, a.maia): e for e in pending}
        for fu in cf.as_completed(futures):
            e = futures[fu]
            try:
                r = fu.result()
            except Exception as x:
                err += 1
                print(f"ERROR {e['id']}: {x}", file=sys.stderr)
                continue
            with write:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush()
            tokens += r["tokens"]
            if r["ok"]:
                ok += 1
            else:
                bad += 1
                print(f"REVIEW {r['id']}: {r.get('problems')}")
    print(f"OK {ok} · to review {bad} · errors {err} · tokens {tokens}")


if __name__ == "__main__":
    main()
