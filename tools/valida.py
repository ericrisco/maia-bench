#!/usr/bin/env python3
"""Valida els fitxers del dataset de coneixement de maia-bench.

Ús:  python3 tools/valida.py coneixement/<fitxer>.jsonl [...] [--maia <arrel de maia>]

Només dona error per als fitxers indicats, però per detectar ids i preguntes duplicades
carrega sempre tots els `coneixement/*.jsonl`. Codi de sortida 1 si hi ha errors.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

PROHIBIDES = re.compile(
    r"\bcorpus\b|\bfitxa\b|segons (el|l')\s*(text|article|document)|\bdocs/|\.md\b", re.I
)
CADUCA = re.compile(
    r"\b(actualment|avui dia|a dia d'avui|vigent|ministre actual|cap de govern actual)\b", re.I
)
TIPUS = {"test", "oberta", "trampa"}
BASE = {"id", "tipus", "domini", "subtema", "nivell", "pregunta", "context", "resposta", "documents"}
CAMPS_TEXT = ("pregunta", "context", "resposta", "premissa_falsa")


def norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


def textos(r):
    for k in CAMPS_TEXT:
        if isinstance(r.get(k), str):
            yield k, r[k]
    for k in ("fets_clau", "errors_a_penalitzar"):
        for i, v in enumerate(r.get(k) or []):
            if isinstance(v, str):
                yield f"{k}[{i}]", v
    for k, v in (r.get("opcions") or {}).items():
        if isinstance(v, str):
            yield f"opcions.{k}", v


def valida_entrada(r, reservades, maia, errs):
    falta = BASE - set(r)
    if falta:
        errs.append(f"falten claus: {sorted(falta)}")
        return
    if r["tipus"] not in TIPUS:
        errs.append(f"tipus invàlid: {r['tipus']!r}")
    if r["nivell"] not in (1, 2, 3):
        errs.append(f"nivell invàlid: {r['nivell']!r}")
    if not re.fullmatch(r"[a-z0-9-]+/\d{3}", r["id"]):
        errs.append(f"id amb format incorrecte: {r['id']!r}")
    elif r.get("no_vista"):
        if not r["id"].startswith("nv-"):
            errs.append("una entrada no_vista ha de tenir id 'nv-<lot>/NNN'")
    elif r["id"].split("/")[0] != r["subtema"]:
        errs.append(f"l'id ha de començar pel subtema ({r['subtema']})")

    if r["tipus"] == "test":
        op = r.get("opcions")
        if not isinstance(op, dict) or sorted(op) != ["A", "B", "C", "D"]:
            errs.append("test: cal opcions A, B, C i D")
        else:
            vals = [str(v).strip() for v in op.values()]
            if any(not v for v in vals) or len({norm(v) for v in vals}) != 4:
                errs.append("test: les 4 opcions han de ser no buides i diferents")
            if r.get("correcta") not in op:
                errs.append("test: 'correcta' ha de ser A, B, C o D")
    else:
        if "opcions" in r or "correcta" in r:
            errs.append(f"{r['tipus']}: no pot tenir opcions ni correcta")
        for k in ("fets_clau", "errors_a_penalitzar"):
            v = r.get(k)
            if not isinstance(v, list) or not v or not all(isinstance(x, str) and x.strip() for x in v):
                errs.append(f"{r['tipus']}: cal '{k}' (llista no buida de textos)")
    if r["tipus"] == "trampa" and not str(r.get("premissa_falsa", "")).strip():
        errs.append("trampa: cal 'premissa_falsa'")

    n = len(str(r["context"]).split())
    if not 40 <= n <= 400:
        errs.append(f"context de {n} paraules (ha de ser de 40 a 400)")
    minim = 1 if r["tipus"] == "test" else 3
    if len(str(r["resposta"]).split()) < minim:
        errs.append("resposta massa curta")
    if not str(r["pregunta"]).strip().endswith("?"):
        errs.append("la pregunta ha d'acabar amb '?'")

    for camp, txt in textos(r):
        m = PROHIBIDES.search(txt)
        if m:
            errs.append(f"{camp}: expressió prohibida {m.group(0)!r}")

    docs = r["documents"]
    if not isinstance(docs, list) or not docs or not all(isinstance(d, str) and d.endswith(".md") for d in docs):
        errs.append("documents: llista no buida de rutes .md")
        return
    es_res = [d in reservades for d in docs] if reservades else []
    if reservades:
        if r.get("no_vista") and not all(es_res):
            errs.append("no_vista: tots els documents han de ser fitxes reservades")
        if not r.get("no_vista") and any(es_res):
            errs.append("una entrada normal no pot citar una fitxa reservada")
    if maia:
        for d in docs:
            if not os.path.exists(os.path.join(maia, d)):
                errs.append(f"el document no existeix: {d}")


def avisos(r, warns):
    for camp, txt in textos(r):
        m = CADUCA.search(txt)
        if m:
            warns.append(f"{camp}: possible dada que caduca ({m.group(0)!r})")
    if r.get("tipus") == "test" and isinstance(r.get("opcions"), dict) and r.get("correcta") in r["opcions"]:
        if norm(r["opcions"][r["correcta"]]) not in norm(r.get("resposta", "")):
            warns.append("la resposta no conté el text de l'opció correcta")


def llegeix(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for i, linia in enumerate(f, 1):
            if not linia.strip():
                continue
            try:
                out.append((i, json.loads(linia)))
            except json.JSONDecodeError as e:
                out.append((i, e))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fitxers", nargs="+")
    ap.add_argument("--maia", default=os.environ.get("MAIA_ROOT"))
    ap.add_argument("--reserva", default=None)
    a = ap.parse_args()

    arrel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rf = a.reserva or os.path.join(arrel, "reserva", "fitxes.txt")
    reservades = set(open(rf).read().split()) if os.path.exists(rf) else set()
    if not a.maia:
        print("avís: sense --maia / MAIA_ROOT no es comprova que els documents existeixin", file=sys.stderr)

    ids, preguntes = collections.defaultdict(list), collections.defaultdict(list)
    for p in glob.glob(os.path.join(arrel, "coneixement", "*.jsonl")):
        for i, r in llegeix(p):
            if isinstance(r, dict) and "id" in r:
                ids[r["id"]].append(os.path.basename(p))
                preguntes[norm(str(r.get("pregunta", "")))].append(r["id"])

    errors, warns, recompte = [], [], collections.Counter()
    for fitxer in a.fitxers:
        p = fitxer if os.path.isabs(fitxer) else os.path.join(arrel, fitxer)
        tests = collections.Counter()
        for i, r in llegeix(p):
            ref = f"{os.path.basename(p)}:{i}"
            if isinstance(r, Exception):
                errors.append(f"{ref}: JSON invàlid ({r})")
                continue
            e = []
            valida_entrada(r, reservades, a.maia, e)
            if len(ids.get(r.get("id"), [])) > 1:
                e.append("id repetit")
            if len(preguntes.get(norm(str(r.get("pregunta", ""))), [])) > 1:
                e.append("pregunta repetida")
            errors += [f"{ref} ({r.get('id')}): {x}" for x in e]
            w = []
            avisos(r, w)
            warns += [f"{ref} ({r.get('id')}): {x}" for x in w]
            recompte[r.get("tipus")] += 1
            if r.get("tipus") == "test" and r.get("correcta"):
                tests[r["correcta"]] += 1
        if sum(tests.values()) >= 4 and max(tests.values()) / sum(tests.values()) > 0.5:
            warns.append(f"{os.path.basename(p)}: la lletra correcta està desequilibrada {dict(tests)}")

    for w in warns:
        print("AVÍS ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{sum(recompte.values())} entrades {dict(recompte)}: {len(errors)} errors, {len(warns)} avisos")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
