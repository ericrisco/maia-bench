#!/usr/bin/env python3
"""Genera la pàgina pública de resultats: web/index.html a partir de resultats/*/resum.json.

Ús:  python3 tools/web.py

La taula es pinta aquí (es veu sense JavaScript); els dominis i «Prova-ho» es dibuixen al navegador amb les dades
incrustades a la mateixa pàgina, que funciona com a fitxer local i a GitHub Pages.
"""
import datetime
import glob
import html
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from executa import empremta_dataset, preguntes  # noqa: E402
from puntua import JUTGE  # noqa: E402

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIM = 2942  # metres del Coma Pedrosa: el 100 %
MOSTRA = 80

DOMINIS = [("historia", "Història"), ("institucions", "Institucions"), ("societat", "Societat"), ("llengua", "Llengua"),
           ("economia", "Economia"), ("cultura", "Cultura"), ("esports", "Esports"), ("territori", "Territori"),
           ("costums", "Costums"), ("politica", "Política"), ("gastronomia", "Gastronomia"),
           ("vida-quotidiana", "Vida quotidiana"), ("persones", "Persones")]

NOMS = {
    "ollama:gemma4:e4b": ("Gemma 4 E4B", "Google · obert · local"),
    "ollama:gemma4:e2b": ("Gemma 4 E2B", "Google · obert · local"),
    "ollama:gemma4:12b": ("Gemma 4 12B", "Google · obert · local"),
    "ollama:gemma3:12b": ("Gemma 3 12B", "Google · obert · local"),
    "ollama:qwen2.5:3b-instruct": ("Qwen 2.5 3B", "Alibaba · obert · local"),
    "ollama:ministral-3:latest": ("Ministral 3", "Mistral · obert · local"),
    "ollama:gpt-oss:20b": ("gpt-oss 20B", "OpenAI · obert · local"),
    "vertex:google/gemini-3.8-flash": ("Gemini 3.8 Flash", "Google · tancat · API"),
    "vertex:google/gemma-4-26b-a4b-it-maas": ("Gemma 4 26B-A4B", "Google · obert · Vertex"),
    "ollamacloud:gemma4:31b": ("Gemma 4 31B", "Google · obert · Ollama Cloud"),
    "ollamacloud:gpt-oss:20b": ("gpt-oss 20B", "OpenAI · obert · Ollama Cloud"),
    "ollamacloud:gpt-oss:120b": ("gpt-oss 120B", "OpenAI · obert · Ollama Cloud"),
    "ollamacloud:deepseek-v4.1-flash": ("DeepSeek V4.1 Flash", "DeepSeek · obert · Ollama Cloud"),
    "ollamacloud:kimi-k3": ("Kimi K3", "Moonshot · obert · Ollama Cloud"),
    "ollamacloud:mistral-large-4": ("Mistral Large 4", "Mistral · obert · Ollama Cloud"),
    "ollamacloud:glm-5.3": ("GLM 5.3", "Z.ai · obert · Ollama Cloud"),
    "ollamacloud:minimax-m3": ("MiniMax M3", "MiniMax · obert · Ollama Cloud"),
    "ollamacloud:nemotron-3-super": ("Nemotron 3 Super", "NVIDIA · obert · Ollama Cloud"),
    "ollamacloud:nemotron-3-ultra": ("Nemotron 3 Ultra", "NVIDIA · obert · Ollama Cloud"),
    "ollamacloud:glm-5.2": ("GLM 5.2", "Z.ai · obert · Ollama Cloud"),
    "ollamacloud:glm-5.3-flash": ("GLM 5.3 Flash", "Z.ai · obert · Ollama Cloud"),
    "ollamacloud:minimax-m3.1-flash": ("MiniMax M3.1 Flash", "MiniMax · obert · Ollama Cloud"),
    "ollamacloud:deepseek-v4-pro:0813": ("DeepSeek V4 Pro", "DeepSeek · obert · Ollama Cloud"),
    "ollamacloud:deepseek-v4.1-flash:1017": ("DeepSeek V4.1 Flash 1017", "DeepSeek · obert · Ollama Cloud"),
    "ollamacloud:beam": ("Beam", "obert · Ollama Cloud"),
}


def nom_model(model):
    if model in NOMS:
        return NOMS[model]
    prov, _, nom = model.partition(":")
    if prov == "ollamacloud":
        return nom, "obert · Ollama Cloud"
    return nom, prov


def pct(v):
    return f"{v * 100:.1f}".replace(".", ",") + " %"


def metres(v):
    return f"{round(v * CIM):,}".replace(",", ".") + " m"


def carrega():
    models = []
    for f in sorted(glob.glob(os.path.join(ARREL, "resultats", "*", "resum.json"))):
        r = json.load(open(f, encoding="utf-8"))
        r["carpeta"] = os.path.dirname(f)
        models.append(r)
    # Comparable: puntuat sobre gairebé les mateixes preguntes que el model més avançat (els tests, de moment).
    maxim = max((r["coneixement"].get("n") or 0 for r in models), default=0)
    for r in models:
        r["comparable"] = (r["coneixement"].get("n") or 0) >= 0.95 * maxim
    models.sort(key=lambda r: (not r["complet"], not r["comparable"], -(r["coneixement"].get("nota") or 0)))
    return models


def files_taula(models, total):
    out = []
    for i, m in enumerate(models):
        nom, sub = nom_model(m["model"])
        c = m["coneixement"]
        if not c.get("n"):
            continue
        lo, hi = c["ic95"]
        avisos = []
        if m.get("origen"):
            avisos.append(html.escape(m["origen"]))
        if m.get("nomes_tests") and not m["comparable"]:
            avisos.append(f"en curs: {m['puntuades']} tests, encara no comparable")
        elif m.get("nomes_tests"):
            avisos.append(f"només tests ({m['puntuades']}), jutge pendent")
        elif not m["complet"]:
            avisos.append(f"en curs: {m['puntuades']} de {total}")
        if m.get("mateix_model_que_jutge"):
            avisos.append("també és el jutge")
        sep = ' class="sep"' if i and i % 4 == 0 else ""
        cls = ' class="maia"' if "maia" in m["model"].lower() else ""
        out.append(
            f'<tr{sep or cls}><td><span class="nm">{html.escape(nom)}</span>'
            f'<span class="sub">{html.escape(sub)}{" · " if avisos else ""}{" · ".join(avisos)}</span>'
            f'<div class="barra" aria-hidden="true" style="--i:{i}"><s style="left:{lo * 100:.1f}%;width:{(hi - lo) * 100:.1f}%"></s>'
            f'<i style="width:{c["nota"] * 100:.1f}%"></i></div></td>'
            f'<td class="num"><span class="nota">{pct(c["nota"])}</span>'
            f'<span class="sub">{pct(lo)} – {pct(hi)}</span></td>'
            f'<td class="num hide-m alt">{metres(c["nota"])}</td></tr>')
    return "\n".join(out) or '<tr><td colspan="3">Encara no hi ha cap model puntuat.</td></tr>'


def mostra_preguntes(models, dataset):
    complets = [m for m in models if m["coneixement"].get("n") and m["comparable"]]
    per_model = {}
    for m in complets:
        resp, punts = {}, {}
        for l in open(os.path.join(m["carpeta"], "respostes.jsonl"), encoding="utf-8"):
            r = json.loads(l)
            if not r.get("error"):
                resp[r["id"]] = r["resposta"]
        pf = os.path.join(m["carpeta"], "puntuacions.jsonl")
        if os.path.exists(pf):
            for l in open(pf, encoding="utf-8"):
                r = json.loads(l)
                punts[r["id"]] = r
        per_model[m["model"]] = (resp, punts)
    comuns = [i for i in dataset if all(i in p for _, p in per_model.values())] if per_model else []
    rnd = random.Random(20261027)
    # Primer les preguntes on els models no coincideixen: són les que expliquen més.
    def desacord(i):
        vals = {per_model[m][1][i]["punts"] for m in per_model}
        return len(vals) > 1
    rnd.shuffle(comuns)
    comuns.sort(key=lambda i: not desacord(i))
    out = []
    for i in comuns[:MOSTRA]:
        p = dataset[i]
        dom = dict(DOMINIS).get(p["domini"], p["domini"])
        e = {"id": i, "tipus": p["tipus"], "domini": dom, "pregunta": p["pregunta"],
             "referencia": p["resposta"] if p["tipus"] != "test" else f"{p['correcta']}) {p['opcions'][p['correcta']]}",
             "respostes": []}
        if p["tipus"] == "test":
            e["opcions"] = p["opcions"]
        for m, (resp, punts) in per_model.items():
            pu = punts[i]
            e["respostes"].append({"model": m, "text": resp.get(i, "")[:700], "punts": pu["punts"],
                                   "motiu": pu.get("motiu", "")})
        out.append(e)
    return out


def main():
    rows = preguntes()
    dataset = {r["id"]: r for r in rows}
    models = carrega()
    plantilla = open(os.path.join(ARREL, "web", "plantilla.html"), encoding="utf-8").read()
    credits = json.load(open(os.path.join(ARREL, "web", "assets", "credits.json"), encoding="utf-8"))

    peces = []
    for c in credits if isinstance(credits, list) else credits.values():
        titol = html.escape(c.get("title", ""))
        autor = c.get("creator") or c.get("author")
        lic = c.get("licence") or c.get("license") or ""
        peces.append(f'<a href="{html.escape(c.get("page") or c.get("source", ""))}">«{titol}»</a>'
                     + (f", {html.escape(autor)}" if autor else "") + (f", {html.escape(lic)}" if lic else ""))
    credits_html = "Fotografies: " + "; ".join(peces) + ", via Wikimedia Commons."

    dades = {
        "models": [{"id": m["model"], "nom": nom_model(m["model"])[0], "nota": m["coneixement"].get("nota", 0),
                    "n": m["coneixement"].get("n", 0), "complet": m["complet"],
                    "per_domini": m["per_domini"], "per_tipus": m["per_tipus"]} for m in models],
        "dominis": [{"id": d, "nom": n} for d, n in DOMINIS],
        "mostra": mostra_preguntes(models, dataset),
    }
    versio = f"v1-esborrany ({empremta_dataset(rows)})"
    tipus = {t: sum(1 for r in rows if r["tipus"] == t) for t in ("test", "oberta", "trampa")}
    complets = sum(1 for m in models if m["complet"])
    comparables = sum(1 for m in models if m["comparable"])
    avis = (f"{len(models)} models avaluats; {comparables} ja tenen tots els tests puntuats i {complets} les {len(rows)} preguntes. "
            "Les notes «només tests» "
            "compten les preguntes de quatre opcions; les obertes i les trampes s'hi afegiran quan les puntuï el jutge. "
            "Una execució «en curs» encara no és comparable amb les completes.")
    jutge = nom_model(JUTGE)[0]
    subst = {
        "__FILES__": files_taula(models, len(rows)),
        "__VERSIO__": html.escape(versio), "__AVIS__": html.escape(avis), "__JUTGE__": html.escape(jutge),
        "__DATA__": datetime.date.today().strftime("%d/%m/%Y"),
        "__N_TEST__": str(tipus["test"]), "__N_OBERTA__": str(tipus["oberta"]), "__N_TRAMPA__": str(tipus["trampa"]),
        "__N_TOTAL__": str(len(rows)),
        "__N_ARTICLES__": f"{len({d for r in rows for d in r['documents']})}",
        "__N_NOVISTES__": str(sum(1 for r in rows if r.get("no_vista"))),
        "__N_FITXES__": str(len(open(os.path.join(ARREL, "reserva", "fitxes.txt")).read().split())),
        "__CREDITS__": credits_html,
        "__DADES__": json.dumps(dades, ensure_ascii=False).replace("</", "<\\/"),
    }
    for k, v in subst.items():
        plantilla = plantilla.replace(k, v)
    sortida = os.path.join(ARREL, "web", "index.html")
    open(sortida, "w", encoding="utf-8").write(plantilla)
    print(f"{sortida}: {len(models)} models, {len(dades['mostra'])} preguntes a «Prova-ho»")


if __name__ == "__main__":
    main()
