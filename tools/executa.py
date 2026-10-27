#!/usr/bin/env python3
"""Passa les preguntes de coneixement a un model i en desa les respostes.

Ús:  python3 tools/executa.py --model ollama:gemma4:e4b [--limit N] [--fils 4] [--nom etiqueta] [--origen text]

El model només rep la pregunta (i les opcions als tests): mai el context ni la resposta de referència.
Les respostes van a resultats/<nom>/respostes.jsonl. Es pot reprendre: les preguntes ja respostes s'ometen.
Després, puntua amb tools/puntua.py.
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
from proveidors import ErrorModel, crida, separa  # noqa: E402

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIO_PROMPT = "p1"

SISTEMA = "Respon en català les preguntes sobre Andorra que et facin."
INSTR_TEST = "Respon només amb la lletra de l'opció correcta (A, B, C o D)."
INSTR_OBERTA = "Respon de manera breu i precisa, en un màxim de tres frases."


def preguntes():
    out = []
    for f in sorted(glob.glob(os.path.join(ARREL, "coneixement", "*.jsonl"))):
        for linia in open(f, encoding="utf-8"):
            if linia.strip():
                out.append(json.loads(linia))
    return out


def empremta_dataset(rows):
    h = hashlib.sha256()
    for r in sorted(rows, key=lambda r: r["id"]):
        h.update(json.dumps(r, ensure_ascii=False, sort_keys=True).encode())
    return h.hexdigest()[:12]


def missatges(r):
    if r["tipus"] == "test":
        ops = "\n".join(f"{k}) {r['opcions'][k]}" for k in "ABCD")
        usuari = f"{r['pregunta']}\n\n{ops}\n\n{INSTR_TEST}"
    else:
        usuari = f"{r['pregunta']}\n\n{INSTR_OBERTA}"
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": usuari}]


def nom_carpeta(model):
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", model).strip("_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="proveidor:model, p. ex. ollama:gemma4:e4b")
    ap.add_argument("--nom", help="nom de la carpeta de resultats (per defecte, derivat del model)")
    ap.add_argument("--origen", default="", help="p. ex. 'Andorra · model del projecte'")
    ap.add_argument("--limit", type=int, help="només les N primeres preguntes (proves)")
    ap.add_argument("--fils", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=4000)
    a = ap.parse_args()
    separa(a.model)

    rows = preguntes()
    total = len(rows)
    if a.limit:
        rows = rows[: a.limit]
    carpeta = os.path.join(ARREL, "resultats", a.nom or nom_carpeta(a.model))
    os.makedirs(carpeta, exist_ok=True)
    fitxer = os.path.join(carpeta, "respostes.jsonl")

    meta_path = os.path.join(carpeta, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ARREL, capture_output=True, text=True).stdout.strip()
    meta.update({"model": a.model, "origen": a.origen or meta.get("origen", ""), "prompt": VERSIO_PROMPT,
                 "sistema": SISTEMA, "temperatura": 0, "max_tokens": a.max_tokens,
                 "dataset": empremta_dataset(preguntes()), "preguntes_dataset": total, "commit": git})
    meta.setdefault("inici", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)

    fets = set()
    if os.path.exists(fitxer):
        for l in open(fitxer, encoding="utf-8"):
            r = json.loads(l)
            if not r.get("error"):
                fets.add(r["id"])
    pendents = [r for r in rows if r["id"] not in fets]
    print(f"{a.model}: {len(pendents)} preguntes per respondre ({len(fets)} ja fetes)", file=sys.stderr)

    lock = threading.Lock()
    errors = 0

    def una(r):
        t0 = time.time()
        try:
            res = crida(a.model, missatges(r), temperatura=0, max_tokens=a.max_tokens)
            return {"id": r["id"], "resposta": res["text"].strip(), "tokens_entrada": res["tokens_entrada"],
                    "tokens_sortida": res["tokens_sortida"], "segons": round(time.time() - t0, 2)}
        except ErrorModel as e:
            return {"id": r["id"], "error": str(e)}

    with cf.ThreadPoolExecutor(a.fils) as ex, open(fitxer, "a", encoding="utf-8") as out:
        for i, res in enumerate(ex.map(una, pendents), 1):
            with lock:
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
            if res.get("error"):
                errors += 1
                print(f"ERROR {res['id']}: {res['error']}", file=sys.stderr)
            if i % 25 == 0:
                print(f"  {i}/{len(pendents)}", file=sys.stderr)

    meta["fi"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    print(f"fet: {len(pendents) - errors} respostes, {errors} errors -> {fitxer}")


if __name__ == "__main__":
    main()
