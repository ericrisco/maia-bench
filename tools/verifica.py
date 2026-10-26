#!/usr/bin/env python3
"""Verificació independent del dataset de coneixement.

Un model d'una altra família (per defecte Gemini 3.8 Flash a Vertex AI, pel endpoint compatible
amb OpenAI) comprova cada entrada **contra l'article original**, no contra el context que n'ha
escrit l'autor. Detecta respostes no sostingudes, contextos amb afegits, tests sense una única
opció correcta, trampes amb una premissa que no queda demostrada i preguntes ambigües.

Ús:  python3 tools/verifica.py coneixement/<fitxer>.jsonl [...] --maia <arrel de maia> --sortida <fitxer.jsonl>

Requereix `gcloud` autenticat i accés a Vertex AI al projecte GCP_PROJECT (per defecte maia-andorra).
Es pot reprendre: les entrades que ja són a --sortida s'ometen.
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

PROJECTE = os.environ.get("GCP_PROJECT", "maia-andorra")
MODEL = os.environ.get("JUDGE_MODEL", "google/gemini-3.8-flash")
URL = (
    f"https://aiplatform.googleapis.com/v1/projects/{PROJECTE}"
    "/locations/global/endpoints/openapi/chat/completions"
)
MAX_PARAULES_ARTICLE = 9000

_tok = {"v": None, "t": 0}
_lock = threading.Lock()


def token():
    with _lock:
        if not _tok["v"] or time.time() - _tok["t"] > 2400:
            r = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
            _tok["v"], _tok["t"] = r.stdout.strip(), time.time()
        return _tok["v"]


SISTEMA = (
    "Ets un verificador estricte d'un benchmark sobre Andorra. Et donen el text d'un o més ARTICLES font i una "
    "ENTRADA del benchmark (pregunta, context, resposta, etc.). Comproves l'entrada NOMÉS contra els articles: "
    "no facis servir coneixement extern. Respon únicament amb un objecte JSON."
)

INSTRUCCIO = """Comprova l'entrada contra els articles i respon amb aquest JSON exacte:
{
 "resposta_suportada": true|false,   // la resposta és certa segons els articles
 "context_suportat": true|false,     // tot el que afirma el context surt dels articles, sense afegits ni errors
 "unica_correcta": true|false|null,  // només per a tests: l'opció marcada és correcta i cap altra ho és també
 "premissa_demostrada_falsa": true|false|null, // només per a trampes: els articles demostren que la premissa és falsa (no només que no hi consti)
 "ambigua": true|false,              // la pregunta admet més d'una resposta raonable o depèn d'un context que no diu
 "problemes": ["..."]                // frases curtes; buit si tot és correcte
}"""


def llegeix_articles(entrada, maia):
    out = []
    for d in entrada["documents"]:
        p = os.path.join(maia, d)
        try:
            t = open(p, encoding="utf-8").read()
        except OSError:
            t = "(article no trobat)"
        w = t.split()
        if len(w) > MAX_PARAULES_ARTICLE:
            t = " ".join(w[:MAX_PARAULES_ARTICLE]) + " …(tallat)"
        out.append(f"=== ARTICLE: {d} ===\n{t}")
    return "\n\n".join(out)


def entrada_text(e):
    camps = {k: e[k] for k in ("tipus", "pregunta", "opcions", "correcta", "context", "resposta",
                                "fets_clau", "errors_a_penalitzar", "premissa_falsa") if k in e}
    return json.dumps(camps, ensure_ascii=False, indent=1)


def crida(missatges):
    cos = json.dumps({"model": MODEL, "temperature": 0, "max_tokens": 6000,
                      "response_format": {"type": "json_object"}, "messages": missatges}).encode()
    for intent in range(5):
        req = urllib.request.Request(URL, data=cos, headers={
            "Authorization": f"Bearer {token()}", "Content-Type": "application/json",
            "x-goog-user-project": PROJECTE})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and intent < 4:
                time.sleep(2 ** intent * 3)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]!r}")
        except (urllib.error.URLError, TimeoutError):
            if intent < 4:
                time.sleep(2 ** intent * 3)
                continue
            raise
    raise RuntimeError("sense resposta")


def verifica(e, maia):
    msg = [{"role": "system", "content": SISTEMA},
           {"role": "user", "content": f"{llegeix_articles(e, maia)}\n\n=== ENTRADA ===\n{entrada_text(e)}\n\n{INSTRUCCIO}"}]
    d = crida(msg)
    res = json.loads(d["choices"][0]["message"]["content"])
    u = d.get("usage", {})
    p = res.get("problemes") or []
    ok = (res.get("resposta_suportada") is True and res.get("context_suportat") is True
          and not res.get("ambigua") and not p)
    if e["tipus"] == "test" and res.get("unica_correcta") is not True:
        ok = False
    if e["tipus"] == "trampa" and res.get("premissa_demostrada_falsa") is not True:
        ok = False
    return {"id": e["id"], "ok": ok, **res, "tokens": u.get("total_tokens", 0), "model": MODEL}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fitxers", nargs="+")
    ap.add_argument("--maia", required=True)
    ap.add_argument("--sortida", required=True)
    ap.add_argument("--fils", type=int, default=8)
    a = ap.parse_args()

    fets = set()
    if os.path.exists(a.sortida):
        fets = {json.loads(l)["id"] for l in open(a.sortida, encoding="utf-8") if l.strip()}
    pendents = []
    for f in a.fitxers:
        for l in open(f, encoding="utf-8"):
            if l.strip():
                e = json.loads(l)
                if e["id"] not in fets:
                    pendents.append(e)
    print(f"{len(pendents)} entrades per verificar ({len(fets)} ja fetes)", file=sys.stderr)

    escriu = threading.Lock()
    tokens = ok = mal = err = 0
    with cf.ThreadPoolExecutor(a.fils) as ex, open(a.sortida, "a", encoding="utf-8") as out:
        futs = {ex.submit(verifica, e, a.maia): e for e in pendents}
        for fu in cf.as_completed(futs):
            e = futs[fu]
            try:
                r = fu.result()
            except Exception as x:
                err += 1
                print(f"ERROR {e['id']}: {x}", file=sys.stderr)
                continue
            with escriu:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush()
            tokens += r["tokens"]
            if r["ok"]:
                ok += 1
            else:
                mal += 1
                print(f"REVISAR {r['id']}: {r.get('problemes')}")
    print(f"OK {ok} · a revisar {mal} · errors {err} · tokens {tokens}")


if __name__ == "__main__":
    main()
