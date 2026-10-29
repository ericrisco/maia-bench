#!/usr/bin/env python3
"""Puntua les respostes d'un model i n'escriu el resum.

Ús:  python3 tools/puntua.py resultats/<nom> [--jutge vertex:google/gemini-3.8-flash] [--fils 2]

- Tests: automàtic (1 si la lletra és la correcta, 0 si no).
- Obertes i trampes: el jutge dona 0, 1 o 2 amb la resposta de referència, els fets clau i els errors a penalitzar
  (es normalitza a 0, 0,5 o 1).
Escriu puntuacions.jsonl (reprenible) i resum.json, amb un interval de confiança del 95 % per bootstrap.
"""
import argparse
import collections
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from executa import preguntes  # noqa: E402
from proveidors import ErrorModel, crida  # noqa: E402

JUTGE = "vertex:google/gemini-3.8-flash"
VERSIO_JUTGE = "j1"

SISTEMA_JUTGE = (
    "Ets el jutge d'un benchmark sobre Andorra. Compares la resposta d'un model amb la informació de referència i "
    "puntues només si és correcta i completa segons aquesta referència. No premies l'estil ni la llargada. "
    "Respon únicament amb un objecte JSON."
)

RUBRICA = """Puntua la RESPOSTA DEL MODEL:
- 2: correcta i completa. Conté els fets clau essencials i cap afirmació falsa. Si és una pregunta trampa, rebutja
  explícitament la premissa falsa i diu què és cert.
- 1: parcialment correcta. Encerta part dels fets clau sense cap error greu, o bé (trampa) rebutja la premissa però no
  diu què és cert.
- 0: incorrecta, inventada, evasiva o sense resposta; o conté algun dels ERRORS A PENALITZAR o una altra afirmació falsa
  rellevant; o (trampa) accepta la premissa falsa.
Respon amb aquest JSON exacte: {"nota": 0|1|2, "motiu": "una frase"}"""


def lletra(text):
    t = text.strip()
    m = re.match(r"^\W*([ABCD])\b", t)
    if m:
        return m.group(1)
    trobades = set(re.findall(r"\b([ABCD])\)", t)) or set(re.findall(r"\b([ABCD])\b", t))
    return trobades.pop() if len(trobades) == 1 else None


def prompt_jutge(p, resposta):
    ref = {"pregunta": p["pregunta"], "context": p["context"], "resposta_de_referencia": p["resposta"],
           "fets_clau": p.get("fets_clau", []), "errors_a_penalitzar": p.get("errors_a_penalitzar", [])}
    if p["tipus"] == "trampa":
        ref["premissa_falsa"] = p.get("premissa_falsa", "")
        ref["tipus"] = "trampa: la pregunta dona per bona una premissa falsa"
    return [{"role": "system", "content": SISTEMA_JUTGE},
            {"role": "user", "content": f"REFERÈNCIA:\n{json.dumps(ref, ensure_ascii=False, indent=1)}\n\n"
                                        f"RESPOSTA DEL MODEL:\n{resposta or '(buida)'}\n\n{RUBRICA}"}]


def jutja(jutge, p, resposta):
    if not resposta.strip():
        return {"nota": 0, "motiu": "resposta buida"}
    d = crida(jutge, prompt_jutge(p, resposta), temperatura=0, max_tokens=4000)
    m = re.search(r"\{.*\}", d["text"], re.S)
    if not m:
        raise ErrorModel(f"el jutge no ha retornat JSON: {d['text'][:120]!r}")
    v = json.loads(m.group(0))
    if v.get("nota") not in (0, 1, 2):
        raise ErrorModel(f"nota invàlida: {v!r}")
    return {"nota": v["nota"], "motiu": v.get("motiu", "")}


def bootstrap(valors, n=1000, llavor=7):
    if not valors:
        return None, None
    rnd = random.Random(llavor)
    k = len(valors)
    mitjanes = sorted(sum(rnd.choice(valors) for _ in range(k)) / k for _ in range(n))
    return round(mitjanes[int(0.025 * n)], 4), round(mitjanes[int(0.975 * n) - 1], 4)


def bloc(valors):
    if not valors:
        return {"n": 0}
    lo, hi = bootstrap(valors)
    return {"n": len(valors), "nota": round(sum(valors) / len(valors), 4), "ic95": [lo, hi]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--jutge", default=JUTGE)
    ap.add_argument("--fils", type=int, default=2)
    ap.add_argument("--sense-jutge", action="store_true", help="només els tests; obertes i trampes queden pendents")
    a = ap.parse_args()

    dataset = {p["id"]: p for p in preguntes()}
    respostes = {}
    for l in open(os.path.join(a.carpeta, "respostes.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        if not r.get("error"):
            respostes[r["id"]] = r["resposta"]
    # empremta de la resposta puntuada: si el model l'ha tornada a fer (p. ex. --refes-buides), es repuntua
    emp = {i: hashlib.sha1(t.encode("utf-8")).hexdigest()[:12] for i, t in respostes.items()}

    fitxer = os.path.join(a.carpeta, "puntuacions.jsonl")
    fetes = {}
    if os.path.exists(fitxer):
        for l in open(fitxer, encoding="utf-8"):
            r = json.loads(l)
            if r.get("jutge") in (None, a.jutge) and r["id"] in respostes and r.get("h", emp[r["id"]]) == emp[r["id"]]:
                fetes[r["id"]] = r

    noves, per_jutjar = [], []
    for i, resp in respostes.items():
        if i not in dataset:
            continue
        p = dataset[i]
        if p["tipus"] == "test":
            l = lletra(resp)
            if i in fetes and fetes[i].get("lletra") == l:
                continue
            noves.append({"id": i, "tipus": "test", "lletra": l, "punts": 1.0 if l == p["correcta"] else 0.0,
                          "h": emp[i]})
        elif i in fetes:
            continue
        elif not a.sense_jutge:
            per_jutjar.append(i)
    print(f"tests nous: {len(noves)} · per al jutge: {len(per_jutjar)} · ja puntuades: {len(fetes)}", file=sys.stderr)

    errors = 0
    with open(fitxer, "a", encoding="utf-8") as out:
        for r in noves:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            fetes[r["id"]] = r

        def una(i):
            try:
                v = jutja(a.jutge, dataset[i], respostes[i])
                return {"id": i, "tipus": dataset[i]["tipus"], "nota": v["nota"], "punts": v["nota"] / 2,
                        "motiu": v["motiu"], "jutge": a.jutge, "h": emp[i]}
            except (ErrorModel, json.JSONDecodeError) as e:
                return {"id": i, "error": str(e)}

        with cf.ThreadPoolExecutor(a.fils) as ex:
            for res in ex.map(una, per_jutjar):
                if res.get("error"):
                    errors += 1
                    print(f"ERROR {res['id']}: {res['error']}", file=sys.stderr)
                    continue
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
                fetes[res["id"]] = res

    meta = json.load(open(os.path.join(a.carpeta, "meta.json")))
    punts = {i: r["punts"] for i, r in fetes.items()}
    per_tipus, per_domini = collections.defaultdict(list), collections.defaultdict(list)
    no_vistes, vistes = [], []
    for i, v in punts.items():
        p = dataset[i]
        per_tipus[p["tipus"]].append(v)
        per_domini[p["domini"]].append(v)
        (no_vistes if p.get("no_vista") else vistes).append(v)

    resum = {
        "model": meta["model"], "origen": meta.get("origen", ""), "dataset": meta.get("dataset"),
        "preguntes_dataset": len(dataset), "respostes": len(respostes), "puntuades": len(punts),
        "complet": len(punts) == len(dataset),
        "nomes_tests": not any(dataset[i]["tipus"] != "test" for i in punts),
        "jutge": a.jutge, "versio_jutge": VERSIO_JUTGE, "prompt": meta.get("prompt"), "temperatura": 0,
        "mateix_model_que_jutge": meta["model"] == a.jutge,
        "data": datetime.date.today().isoformat(),
        "coneixement": bloc(list(punts.values())),
        "per_tipus": {k: bloc(v) for k, v in sorted(per_tipus.items())},
        "vistes": bloc(vistes), "no_vistes": bloc(no_vistes),
        "per_domini": {k: bloc(v) for k, v in sorted(per_domini.items())},
    }
    json.dump(resum, open(os.path.join(a.carpeta, "resum.json"), "w"), ensure_ascii=False, indent=1)
    c = resum["coneixement"]
    print(f"{meta['model']}: coneixement {c.get('nota')} IC95 {c.get('ic95')} sobre {c['n']} preguntes "
          f"({errors} errors del jutge)")


if __name__ == "__main__":
    main()
