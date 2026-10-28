#!/usr/bin/env python3
"""Genera la pàgina pública de resultats a partir de resultats/*/resum.json, en tres idiomes:
web/index.html (anglès, per defecte), web/ca.html i web/es.html. Els textos de la plantilla són a web/textos.json;
els que es munten aquí, a TXT. Les preguntes del dataset es mostren sempre en català.

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
IDIOMES = {"en": "index.html", "ca": "ca.html", "es": "es.html"}
NOM_IDIOMA = {"en": "EN", "ca": "CA", "es": "ES"}
IDIOMA = "en"  # el que s'està generant; el fixa main()

TXT = {
    "complet": {"en": "Complete", "ca": "Complet", "es": "Completo"},
    "tests": {"en": "Tests", "ca": "Tests", "es": "Tests"},
    "en_curs": {"en": "In progress", "ca": "En curs", "es": "En curso"},
    "t_test": {"en": "Multiple choice", "ca": "Tests", "es": "Tests"},
    "t_oberta": {"en": "Open", "ca": "Obertes", "es": "Abiertas"},
    "t_trampa": {"en": "Traps", "ca": "Trampes", "es": "Trampas"},
    "jutge_pendent": {"en": "judge pending", "ca": "jutge pendent", "es": "juez pendiente"},
    "es_jutge": {"en": "also the judge", "ca": "també és el jutge", "es": "también es el juez"},
    "no_comparable": {"en": "not comparable yet", "ca": "encara no comparable", "es": "aún no comparable"},
    "cap_model": {"en": "No model scored yet.", "ca": "Encara no hi ha cap model puntuat.", "es": "Aún no hay ningún modelo puntuado."},
    "interval": {"en": "interval", "ca": "interval", "es": "intervalo"},
    "en_curs_min": {"en": "in progress", "ca": "en curs", "es": "en curso"},
    "sense_dades": {"en": "no data", "ca": "sense dades", "es": "sin datos"},
    "millor": {"en": "Best", "ca": "Millor", "es": "Mejor"},
    "preguntes": {"en": "questions", "ca": "preguntes", "es": "preguntas"},
    "obert": {"en": "open", "ca": "obert", "es": "abierto"},
    "tancat": {"en": "closed", "ca": "tancat", "es": "cerrado"},
    "fotos": {"en": "Photographs", "ca": "Fotografies", "es": "Fotografías"},
    "avis": {
        "en": "{n} models evaluated; {c} have every multiple-choice question scored and {k} all {t} questions. "
              "“Tests only” scores count the four-option questions; open and trap questions will be added once the "
              "judge scores them. A run “in progress” is not yet comparable with complete ones.",
        "ca": "{n} models avaluats; {c} ja tenen tots els tests puntuats i {k} les {t} preguntes. Les notes «només tests» "
              "compten les preguntes de quatre opcions; les obertes i les trampes s'hi afegiran quan les puntuï el jutge. "
              "Una execució «en curs» encara no és comparable amb les completes.",
        "es": "{n} modelos evaluados; {c} ya tienen todos los tests puntuados y {k} las {t} preguntas. Las notas «solo tests» "
              "cuentan las preguntas de cuatro opciones; las abiertas y las trampas se añadirán cuando las puntúe el juez. "
              "Una ejecución «en curso» aún no es comparable con las completas.",
    },
    # textos que fa servir el JavaScript de la pàgina
    "js": {
        "en": {"test": "Multiple choice · four options", "oberta": "Open question", "trampa": "Trap question",
               "ok": "Correct", "mig": "Partly", "ko": "Wrong", "sense": "Not scored", "ref": "Reference answer",
               "preguntes": "questions", "cap": "No scored answers yet.", "cap_tipus": "No scored questions of this type yet.",
               "ca": "Questions are in Catalan, the benchmark's language."},
        "ca": {"test": "Test · quatre opcions", "oberta": "Pregunta oberta", "trampa": "Pregunta trampa",
               "ok": "Correcta", "mig": "A mitges", "ko": "Incorrecta", "sense": "Sense puntuar", "ref": "Resposta de referència",
               "preguntes": "preguntes", "cap": "Encara no hi ha respostes puntuades.",
               "cap_tipus": "Encara no hi ha preguntes d'aquest tipus puntuades.", "ca": ""},
        "es": {"test": "Test · cuatro opciones", "oberta": "Pregunta abierta", "trampa": "Pregunta trampa",
               "ok": "Correcta", "mig": "A medias", "ko": "Incorrecta", "sense": "Sin puntuar", "ref": "Respuesta de referencia",
               "preguntes": "preguntas", "cap": "Aún no hay respuestas puntuadas.",
               "cap_tipus": "Aún no hay preguntas de este tipo puntuadas.", "ca": "Las preguntas están en catalán, la lengua del benchmark."},
    },
}

NOM_DOMINI = {
    "en": {"historia": "History", "institucions": "Institutions", "societat": "Society", "llengua": "Language",
           "economia": "Economy", "cultura": "Culture", "esports": "Sport", "territori": "Territory",
           "costums": "Customs", "politica": "Politics", "gastronomia": "Food", "vida-quotidiana": "Daily life",
           "persones": "People"},
    "es": {"historia": "Historia", "institucions": "Instituciones", "societat": "Sociedad", "llengua": "Lengua",
           "economia": "Economía", "cultura": "Cultura", "esports": "Deportes", "territori": "Territorio",
           "costums": "Costumbres", "politica": "Política", "gastronomia": "Gastronomía",
           "vida-quotidiana": "Vida cotidiana", "persones": "Personas"},
}


def tr(clau):
    return TXT[clau][IDIOMA]


def nom_domini(d, nom_ca):
    return NOM_DOMINI.get(IDIOMA, {}).get(d, nom_ca)

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
        nom, sub = NOMS[model]
    else:
        prov, _, nom = model.partition(":")
        sub = "obert · Ollama Cloud" if prov == "ollamacloud" else prov
    return nom, sub.replace("obert", tr("obert")).replace("tancat", tr("tancat"))


def pct(v):
    x = f"{v * 100:.1f}"
    return (x if IDIOMA == "en" else x.replace(".", ",")) + "\u00a0%"


def metres(v):
    x = f"{round(v * CIM):,}"
    return (x if IDIOMA == "en" else x.replace(",", ".")) + " m"


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


def estat(m, total):
    """Paraula d'estat de la fila i la seva classe: complet, només tests o en curs."""
    if m["complet"]:
        return tr("complet"), "e-ok"
    if m["comparable"]:
        return tr("tests"), "e-tests"
    return f"{tr('en_curs')} · {m['puntuades']}", "e-curs"


def files_tauler(models, total):
    """La taula completa com un tauler de files; cada fila s'obre amb el detall per tipus."""
    out = []
    for i, m in enumerate(models):
        nom, sub = nom_model(m["model"])
        c = m["coneixement"]
        if not c.get("n"):
            continue
        lo, hi = c["ic95"]
        paraula, cls = estat(m, total)
        tipus = []
        for t in ("test", "oberta", "trampa"):
            etiqueta = tr("t_" + t)
            b = m["per_tipus"].get(t) or {}
            tipus.append(f"{etiqueta} {pct(b['nota'])} ({b['n']})" if b.get("n") else f"{etiqueta}: {tr('jutge_pendent')}")
        avisos = [sub]
        if m.get("origen"):
            avisos.append(m["origen"])
        if m.get("mateix_model_que_jutge"):
            avisos.append(tr("es_jutge"))
        if not m["comparable"]:
            avisos.append(tr("no_comparable"))
        obert = " open" if i == 0 else ""
        out.append(
            f'<details class="fila" name="taula"{obert}><summary>'
            f'<span class="f-nom">{html.escape(nom)}</span>'
            f'<span class="f-n num">{pct(c["nota"])}</span>'
            f'<span class="f-ic num hide-m">{pct(lo)} – {pct(hi)}</span>'
            f'<span class="f-m num hide-m">{metres(c["nota"])}</span>'
            f'<span class="f-e {cls}">{html.escape(paraula)}</span></summary>'
            f'<div class="f-det"><p>{html.escape(" · ".join(avisos))}</p>'
            f'<p>{html.escape(" · ".join(tipus))}</p></div></details>')
    return "\n".join(out) or f'<p>{tr("cap_model")}</p>'


def barres_cim(models):
    """El gràfic principal: una barra per model que s'aixeca des de baix; el 100 % és el cim del Coma Pedrosa."""
    out = []
    for i, m in enumerate(m for m in models if m["coneixement"].get("n")):
        nom, _ = nom_model(m["model"])
        c = m["coneixement"]
        lo, hi = c["ic95"]
        cls = "b" + (" lider" if i == 0 else "") + ("" if m["comparable"] else " curs")
        etiqueta = f'{html.escape(nom)}: {pct(c["nota"])}, {tr("interval")} {pct(lo)} – {pct(hi)}' + (
            "" if m["comparable"] else f', {tr("en_curs_min")}')
        valor = f'<b class="bv num">{pct(c["nota"])}</b>' if i < 3 else f'<span class="bi num">{pct(c["nota"])}</span>'
        out.append(
            f'<div class="{cls}" style="--v:{c["nota"]:.4f};--lo:{lo:.4f};--hi:{hi:.4f}" tabindex="0" '
            f'aria-label="{etiqueta}" data-tip="{etiqueta}">{valor}<i class="ic"></i>'
            f'<span class="bn">{html.escape(nom)}</span></div>')
    return "\n".join(out)


def hero_barres(models, n=8):
    """Les columnes de la primera pantalla: el fons de cada columna és el cim (100 %), la barra és la nota."""
    out = []
    for i, m in enumerate([m for m in models if m["comparable"]][:n]):
        nom, _ = nom_model(m["model"])
        c = m["coneixement"]
        out.append(f'<li style="--v:{c["nota"]:.4f};--i:{i}"><b class="num">{pct(c["nota"])}</b>'
                   f'<span class="hb"><i></i></span><span class="hn">{html.escape(nom)}<span class="hv"> · {pct(c["nota"])}</span></span></li>')
    return "\n".join(out)


def tiles_dominis(models):
    comp = [m for m in models if m["comparable"]]
    if not comp:
        return ""
    sel = comp[0]["model"]
    out = []
    for d, nom in DOMINIS:
        nom = nom_domini(d, nom)
        vals = [(m["model"], (m["per_domini"].get(d) or {}).get("nota")) for m in comp]
        v = dict(vals).get(sel)
        mini = "".join(f'<i class="{"sel" if mid == sel else ""}" data-m="{html.escape(mid)}" '
                       f'title="{html.escape(nom_model(mid)[0])}: {pct(x) if x is not None else tr("sense_dades")}" '
                       f'style="--v:{(x or 0):.4f}"></i>' for mid, x in vals)
        nsel = (comp[0]["per_domini"].get(d) or {}).get("n", 0)
        millor = max((x for x in vals if x[1] is not None), key=lambda x: x[1], default=None)
        mtxt = (f"{tr('millor')}: {html.escape(nom_model(millor[0])[0])}, {pct(millor[1])}" if millor
                else tr("sense_dades").capitalize())
        out.append(f'<div class="dt" data-d="{d}"><h3>{nom}</h3><b class="dv num">{pct(v) if v is not None else "–"}</b>'
                   f'<div class="mini" data-ui aria-hidden="true">{mini}</div><p class="dn"><span class="dnn">{nsel} {tr("preguntes")}</span> · {mtxt}</p></div>')
    return "\n".join(out)


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
        dom = nom_domini(p["domini"], dict(DOMINIS).get(p["domini"], p["domini"]))
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
    global IDIOMA
    rows = preguntes()
    dataset = {r["id"]: r for r in rows}
    models = carrega()
    plantilla_base = open(os.path.join(ARREL, "web", "plantilla.html"), encoding="utf-8").read()
    textos = json.load(open(os.path.join(ARREL, "web", "textos.json"), encoding="utf-8"))
    credits = json.load(open(os.path.join(ARREL, "web", "assets", "credits.json"), encoding="utf-8"))
    versio = f"v1-esborrany ({empremta_dataset(rows)})"
    tipus = {t: sum(1 for r in rows if r["tipus"] == t) for t in ("test", "oberta", "trampa")}
    complets = sum(1 for m in models if m["complet"])
    comparables = sum(1 for m in models if m["comparable"])

    for idioma, fitxer in IDIOMES.items():
        IDIOMA = idioma
        peces = []
        for c in credits if isinstance(credits, list) else credits.values():
            titol = html.escape(c.get("title", ""))
            autor = c.get("creator") or c.get("author")
            lic = c.get("licence") or c.get("license") or ""
            peces.append(f'<a href="{html.escape(c.get("page") or c.get("source", ""))}">«{titol}»</a>'
                         + (f", {html.escape(autor)}" if autor else "") + (f", {html.escape(lic)}" if lic else ""))
        credits_html = f"{tr('fotos')}: " + "; ".join(peces) + ", via Wikimedia Commons."
        dades = {
            "models": [{"id": m["model"], "nom": nom_model(m["model"])[0], "nota": m["coneixement"].get("nota", 0),
                        "n": m["coneixement"].get("n", 0), "complet": m["complet"], "comparable": m["comparable"],
                        "per_domini": {d: (v.get("nota") if v.get("n") else None) for d, v in m["per_domini"].items()},
                        "per_domini_n": {d: v.get("n", 0) for d, v in m["per_domini"].items()}}
                       for m in models],
            "mostra": mostra_preguntes(models, dataset),
            "t": TXT["js"][idioma],
            "dec": "." if idioma == "en" else ",",
        }
        avis = tr("avis").format(n=len(models), c=comparables, k=complets, t=len(rows))
        idiomes = "".join(f'<a href="{f}" hreflang="{i}" lang="{i}"' + (' aria-current="page"' if i == idioma else "")
                          + f">{NOM_IDIOMA[i]}</a>" for i, f in IDIOMES.items())
        data = datetime.date.today()
        subst = {
            "__FILES__": files_tauler(models, len(rows)),
            "__BARRES__": barres_cim(models),
            "__HERO_BARRES__": hero_barres(models),
            "__DOMINIS__": tiles_dominis(models),
            "__IDIOMES__": idiomes,
            "__LANG__": idioma,
            "__N_MODELS__": str(len(models)),
            "__N_COMPARABLES__": str(comparables),
            "__MILLOR_NOM__": html.escape(nom_model(models[0]["model"])[0]) if models else "–",
            "__MILLOR_NOTA__": pct(models[0]["coneixement"]["nota"]) if models else "–",
            "__MILLOR_M__": metres(models[0]["coneixement"]["nota"]) if models else "–",
            "__AVIS__": html.escape(avis),
            "__DATA__": data.isoformat() if idioma == "en" else data.strftime("%d/%m/%Y"),
            "__CREDITS__": credits_html,
            "__DADES__": json.dumps(dades, ensure_ascii=False).replace("</", "<\\/"),
        }
        pagina = plantilla_base
        for clau, t in textos.items():
            pagina = pagina.replace(f"__T:{clau}__", t[idioma])
        # els textos traduïts poden portar marcadors de dades: se substitueixen després
        subst.update({
            "__VERSIO__": html.escape(versio), "__JUTGE__": html.escape(nom_model(JUTGE)[0]),
            "__N_TEST__": str(tipus["test"]), "__N_OBERTA__": str(tipus["oberta"]), "__N_TRAMPA__": str(tipus["trampa"]),
            "__N_TOTAL__": str(len(rows)),
            "__N_ARTICLES__": f"{len({d for r in rows for d in r['documents']})}",
            "__N_NOVISTES__": str(sum(1 for r in rows if r.get("no_vista"))),
            "__N_FITXES__": str(len(open(os.path.join(ARREL, "reserva", "fitxes.txt")).read().split())),
        })
        for k, v in subst.items():
            pagina = pagina.replace(k, v)
        sortida = os.path.join(ARREL, "web", fitxer)
        open(sortida, "w", encoding="utf-8").write(pagina)
        print(f"{sortida}: {len(models)} models, {len(dades['mostra'])} preguntes a «Prova-ho»")


if __name__ == "__main__":
    main()
