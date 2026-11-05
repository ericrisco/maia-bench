#!/usr/bin/env python3
"""Builds the public results page from results/*/summary.json, in three languages:
web/index.html (English, the default), web/ca.html and web/es.html. The template's strings live in web/strings.json;
the ones assembled here live in TXT. Dataset questions are always shown in Catalan.
It also builds web/training.html, training-ca.html and training-es.html (how maia was trained) from
web/training-template.html and web/training-strings.json, with the same styles.

Usage:  python3 tools/web.py

The table is rendered here (it shows without JavaScript); the domains and «Try it» are drawn in the
browser from the data embedded in the same page, which works as a local file and on GitHub Pages.
"""
import collections
import datetime
import glob
import html
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import dataset_fingerprint, load_questions  # noqa: E402
from score import JUDGE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMIT = 2942  # metres of Coma Pedrosa: the 100 %
SAMPLE_SIZE = 80
LANGS = {"en": "index.html", "ca": "ca.html", "es": "es.html"}
TRAINING = {"en": "training.html", "ca": "training-ca.html", "es": "training-es.html"}
SITE = "https://ericrisco.github.io/maia-bench/"
LANG_LABEL = {"en": "EN", "ca": "CA", "es": "ES"}
LANG = "en"  # the one being generated; set by main()
TYPES = ("multiple_choice", "open", "trap")

TXT = {
    "overall": {"en": "Overall", "ca": "General", "es": "General"},
    "topic_filter": {"en": "Rank by topic", "ca": "Classifica per tema", "es": "Clasifica por tema"},
    "complete": {"en": "Complete", "ca": "Complet", "es": "Completo"},
    "tests": {"en": "Tests", "ca": "Tests", "es": "Tests"},
    "in_progress": {"en": "In progress", "ca": "En curs", "es": "En curso"},
    "t_multiple_choice": {"en": "Multiple choice", "ca": "Tests", "es": "Tests"},
    "t_open": {"en": "Open", "ca": "Obertes", "es": "Abiertas"},
    "t_trap": {"en": "Traps", "ca": "Trampes", "es": "Trampas"},
    "judge_pending": {"en": "judge pending", "ca": "jutge pendent", "es": "juez pendiente"},
    "is_judge": {"en": "also the judge", "ca": "també és el jutge", "es": "también es el juez"},
    "not_comparable": {"en": "not comparable yet", "ca": "encara no comparable", "es": "aún no comparable"},
    "no_model": {"en": "No model scored yet.", "ca": "Encara no hi ha cap model puntuat.", "es": "Aún no hay ningún modelo puntuado."},
    "interval": {"en": "interval", "ca": "interval", "es": "intervalo"},
    "in_progress_lc": {"en": "in progress", "ca": "en curs", "es": "en curso"},
    "no_data": {"en": "no data", "ca": "sense dades", "es": "sin datos"},
    "best": {"en": "Best", "ca": "Millor", "es": "Mejor"},
    "questions": {"en": "questions", "ca": "preguntes", "es": "preguntas"},
    "open": {"en": "open", "ca": "obert", "es": "abierto"},
    "closed": {"en": "closed", "ca": "tancat", "es": "cerrado"},
    "photos": {"en": "Photographs", "ca": "Fotografies", "es": "Fotografías"},
    "notice": {
        "en": "{n} models evaluated, {k} with all {t} questions scored: multiple choice automatically, open and trap "
              "questions by the judge (Gemini 3.8 Flash, in batch). Gemini 3.8 Flash is also the judge, so its open and "
              "trap scores may be inflated. An empty answer counts as wrong.",
        "ca": "{n} models avaluats, {k} amb les {t} preguntes puntuades: els tests automàticament, les obertes i les "
              "trampes amb el jutge (Gemini 3.8 Flash, per lots). Gemini 3.8 Flash també és el jutge: la seva nota a les "
              "obertes i trampes pot estar inflada. Una resposta buida compta com a errada.",
        "es": "{n} modelos evaluados, {k} con las {t} preguntas puntuadas: los tests automáticamente, las abiertas y las "
              "trampas con el juez (Gemini 3.8 Flash, por lotes). Gemini 3.8 Flash también es el juez: su nota en las "
              "abiertas y trampas puede estar inflada. Una respuesta vacía cuenta como error.",
    },
    # strings used by the page's JavaScript
    "js": {
        "en": {"multiple_choice": "Multiple choice · four options", "open": "Open question", "trap": "Trap question",
               "ok": "Correct", "partial": "Partly", "ko": "Wrong", "unscored": "Not scored", "ref": "Reference answer",
               "questions": "questions", "none": "No scored answers yet.",
               "none_of_type": "No scored questions of this type yet.",
               "catalan_note": "Questions are in Catalan, the benchmark's language."},
        "ca": {"multiple_choice": "Test · quatre opcions", "open": "Pregunta oberta", "trap": "Pregunta trampa",
               "ok": "Correcta", "partial": "A mitges", "ko": "Incorrecta", "unscored": "Sense puntuar",
               "ref": "Resposta de referència", "questions": "preguntes", "none": "Encara no hi ha respostes puntuades.",
               "none_of_type": "Encara no hi ha preguntes d'aquest tipus puntuades.", "catalan_note": ""},
        "es": {"multiple_choice": "Test · cuatro opciones", "open": "Pregunta abierta", "trap": "Pregunta trampa",
               "ok": "Correcta", "partial": "A medias", "ko": "Incorrecta", "unscored": "Sin puntuar",
               "ref": "Respuesta de referencia", "questions": "preguntas", "none": "Aún no hay respuestas puntuadas.",
               "none_of_type": "Aún no hay preguntas de este tipo puntuadas.",
               "catalan_note": "Las preguntas están en catalán, la lengua del benchmark."},
    },
}

# Domain ids (as in the dataset and summary.json), in page order, with their display name per language.
DOMAINS = [
    ("history", {"en": "History", "ca": "Història", "es": "Historia"}),
    ("institutions", {"en": "Institutions", "ca": "Institucions", "es": "Instituciones"}),
    ("society", {"en": "Society", "ca": "Societat", "es": "Sociedad"}),
    ("language", {"en": "Language", "ca": "Llengua", "es": "Lengua"}),
    ("economy", {"en": "Economy", "ca": "Economia", "es": "Economía"}),
    ("culture", {"en": "Culture", "ca": "Cultura", "es": "Cultura"}),
    ("sports", {"en": "Sport", "ca": "Esports", "es": "Deportes"}),
    ("territory", {"en": "Territory", "ca": "Territori", "es": "Territorio"}),
    ("customs", {"en": "Customs", "ca": "Costums", "es": "Costumbres"}),
    ("politics", {"en": "Politics", "ca": "Política", "es": "Política"}),
    ("gastronomy", {"en": "Food", "ca": "Gastronomia", "es": "Gastronomía"}),
    ("daily-life", {"en": "Daily life", "ca": "Vida quotidiana", "es": "Vida cotidiana"}),
    ("people", {"en": "People", "ca": "Persones", "es": "Personas"}),
]
DOMAIN_NAMES = dict(DOMAINS)


def tr(key):
    return TXT[key][LANG]


def domain_name(d):
    return DOMAIN_NAMES.get(d, {}).get(LANG, d)


MODEL_NAMES = {
    "ollama:gemma4:e4b": ("Gemma 4 E4B", "Google · open · local"),
    "ollama:maia-e4b:20261102-1437": ("maia E4B", "maia project · open · Gemma 4 E4B fine-tuned on Andorra"),
    "ollama:maia-12b:20261104-0036": ("maia 12B", "maia project · open · Gemma 4 12B fine-tuned on Andorra"),
    "ollama:gemma4:e2b": ("Gemma 4 E2B", "Google · open · local"),
    "ollama:gemma4:12b": ("Gemma 4 12B", "Google · open · local"),
    "ollama:gemma3:12b": ("Gemma 3 12B", "Google · open · local"),
    "ollama:qwen2.5:3b-instruct": ("Qwen 2.5 3B", "Alibaba · open · local"),
    "ollama:ministral-3:latest": ("Ministral 3", "Mistral · open · local"),
    "ollama:gpt-oss:20b": ("gpt-oss 20B", "OpenAI · open · local"),
    "vertex:google/gemini-3.8-flash": ("Gemini 3.8 Flash", "Google · closed · API"),
    "vertex:google/gemini-4-argon": ("Gemini 4 Argon", "Google · closed · API"),
    "vertex:google/gemini-3.1-pro-preview": ("Gemini 3.1 Pro", "Google · closed · API"),
    "vertex:google/gemini-3.7-flash": ("Gemini 3.7 Flash", "Google · closed · API"),
    "vertex:google/gemini-3.6-flash": ("Gemini 3.6 Flash", "Google · closed · API"),
    "vertex:google/gemini-3.5-flash": ("Gemini 3.5 Flash", "Google · closed · API"),
    "vertex:google/gemini-3-flash-preview": ("Gemini 3 Flash", "Google · closed · API"),
    "vertex:google/gemini-3.5-flash-lite": ("Gemini 3.5 Flash-Lite", "Google · closed · API"),
    "vertex:google/gemini-3.1-flash-lite": ("Gemini 3.1 Flash-Lite", "Google · closed · API"),
    "vertex:xai/grok-4.20-non-reasoning": ("Grok 4.20", "xAI · closed · API"),
    "ollama:gemma3:4b": ("Gemma 3 4B", "Google · open · local"),
    "ollama:gemma3:27b": ("Gemma 3 27B", "Google · open · local"),
    "ollamacloud:kimi-k2.6": ("Kimi K2.6", "Moonshot · open · Ollama Cloud"),
    "openrouter:anthropic/claude-haiku-5.5": ("Claude Haiku 5.5", "Anthropic · closed · API"),
    "openrouter:anthropic/claude-sonnet-5.5": ("Claude Sonnet 5.5", "Anthropic · closed · API"),
    "openrouter:anthropic/claude-opus-5.5": ("Claude Opus 5.5", "Anthropic · closed · API"),
    "openrouter:openai/gpt-6-luna": ("GPT-6 Luna", "OpenAI · closed · API"),
    "openrouter:openai/gpt-6.1-terra": ("GPT-6.1 Terra", "OpenAI · closed · API"),
    "openrouter:openai/gpt-6.1-sol": ("GPT-6.1 Sol", "OpenAI · closed · API"),
    "openrouter:x-ai/grok-4.7": ("Grok 4.7", "xAI · closed · API"),
    "openrouter:qwen/qwen3.8-max-0902": ("Qwen 3.8 Max", "Alibaba · closed · API"),
    "openrouter:qwen/qwen3.8-flash": ("Qwen 3.8 Flash", "Alibaba · closed · API"),
    "openrouter:dots-studio/dots-3-note-preview:free": ("Dots 3", "Dots · open · API"),
    "vertex:google/gemma-4-26b-a4b-it-maas": ("Gemma 4 26B-A4B", "Google · open · Vertex"),
    "ollamacloud:gemma4:31b": ("Gemma 4 31B", "Google · open · Ollama Cloud"),
    "ollamacloud:gpt-oss:20b": ("gpt-oss 20B", "OpenAI · open · Ollama Cloud"),
    "ollamacloud:gpt-oss:120b": ("gpt-oss 120B", "OpenAI · open · Ollama Cloud"),
    "ollamacloud:deepseek-v4.1-flash": ("DeepSeek V4.1 Flash", "DeepSeek · open · Ollama Cloud"),
    "ollamacloud:kimi-k3": ("Kimi K3", "Moonshot · open · Ollama Cloud"),
    "ollamacloud:mistral-large-4": ("Mistral Large 4", "Mistral · open · Ollama Cloud"),
    "ollamacloud:glm-5.3": ("GLM 5.3", "Z.ai · open · Ollama Cloud"),
    "ollamacloud:minimax-m3": ("MiniMax M3", "MiniMax · open · Ollama Cloud"),
    "ollamacloud:nemotron-3-super": ("Nemotron 3 Super", "NVIDIA · open · Ollama Cloud"),
    "ollamacloud:nemotron-3-ultra": ("Nemotron 3 Ultra", "NVIDIA · open · Ollama Cloud"),
    "ollamacloud:glm-5.2": ("GLM 5.2", "Z.ai · open · Ollama Cloud"),
    "ollamacloud:glm-5.3-flash": ("GLM 5.3 Flash", "Z.ai · open · Ollama Cloud"),
    "ollamacloud:minimax-m3.1-flash": ("MiniMax M3.1 Flash", "MiniMax · open · Ollama Cloud"),
    "ollamacloud:deepseek-v4-pro:0813": ("DeepSeek V4 Pro", "DeepSeek · open · Ollama Cloud"),
    "ollamacloud:deepseek-v4.1-flash:1017": ("DeepSeek V4.1 Flash 1017", "DeepSeek · open · Ollama Cloud"),
    "ollamacloud:beam": ("Beam", "open · Ollama Cloud"),
}


def model_name(model):
    """Display name and subtitle of a model; the subtitle's open/closed tag is translated."""
    if model in MODEL_NAMES:
        name, sub = MODEL_NAMES[model]
    else:
        prov, _, name = model.partition(":")
        sub = "open · Ollama Cloud" if prov == "ollamacloud" else prov
    sub = " · ".join(tr(p) if p in ("open", "closed") else p for p in sub.split(" · "))
    return name, sub


def pct(v):
    x = f"{v * 100:.1f}"
    return (x if LANG == "en" else x.replace(".", ",")) + " %"


def metres(v):
    x = f"{round(v * SUMMIT):,}"
    return (x if LANG == "en" else x.replace(",", ".")) + " m"


def load_models():
    models = []
    for f in sorted(glob.glob(os.path.join(ROOT, "results", "*", "summary.json"))):
        r = json.load(open(f, encoding="utf-8"))
        r["folder"] = os.path.dirname(f)
        # Only models with every question answered go on the page.
        if r.get("answers", 0) < r.get("dataset_questions", 0):
            continue
        models.append(r)
    # Comparable: scored on nearly the same questions as the most advanced model (multiple choice, for now).
    top = max((r["knowledge"].get("n") or 0 for r in models), default=0)
    for r in models:
        r["comparable"] = (r["knowledge"].get("n") or 0) >= 0.95 * top
    models.sort(key=lambda r: (not r["complete"], not r["comparable"], -(r["knowledge"].get("score") or 0)))
    return models


def status(m, total):
    """The row's status word and its class: complete, multiple choice only or in progress."""
    if m["complete"]:
        return tr("complete"), "e-ok"
    if m["comparable"]:
        return tr("tests"), "e-tests"
    return f"{tr('in_progress')} · {m['scored']}", "e-pending"


def table_rows(models, total):
    """The full table as a board of rows; each row opens with the per-type detail."""
    out = []
    for i, m in enumerate(models):
        name, sub = model_name(m["model"])
        k = m["knowledge"]
        if not k.get("n"):
            continue
        lo, hi = k["ci95"]
        word, cls = status(m, total)
        types = []
        for t in TYPES:
            label = tr("t_" + t)
            b = m["by_type"].get(t) or {}
            types.append(f"{label} {pct(b['score'])} ({b['n']})" if b.get("n") else f"{label}: {tr('judge_pending')}")
        notes = [sub]
        if m.get("origin"):
            notes.append(m["origin"])
        if m.get("same_model_as_judge"):
            notes.append(tr("is_judge"))
        if not m["comparable"]:
            notes.append(tr("not_comparable"))
        opened = " open" if i == 0 else ""
        out.append(
            f'<details class="row" name="table"{opened}><summary>'
            f'<span class="f-name">{html.escape(name)}</span>'
            f'<span class="f-n num">{pct(k["score"])}</span>'
            f'<span class="f-ci num hide-m">{pct(lo)} – {pct(hi)}</span>'
            f'<span class="f-m num hide-m">{metres(k["score"])}</span>'
            f'<span class="f-e {cls}">{html.escape(word)}</span></summary>'
            f'<div class="f-det"><p>{html.escape(" · ".join(notes))}</p>'
            f'<p>{html.escape(" · ".join(types))}</p></div></details>')
    return "\n".join(out) or f'<p>{tr("no_model")}</p>'


def summit_bars(models):
    """The main chart: one bar per model rising from the bottom; 100 % is the summit of Coma Pedrosa."""
    out = []
    for i, m in enumerate(m for m in models if m["knowledge"].get("n")):
        name, _ = model_name(m["model"])
        k = m["knowledge"]
        lo, hi = k["ci95"]
        cls = "b" + (" leader" if i == 0 else "") + ("" if m["comparable"] else " pending")
        label = f'{html.escape(name)}: {pct(k["score"])}, {tr("interval")} {pct(lo)} – {pct(hi)}' + (
            "" if m["comparable"] else f', {tr("in_progress_lc")}')
        value = f'<b class="bv num">{pct(k["score"])}</b>' if i < 3 else f'<span class="bi num">{pct(k["score"])}</span>'
        # score and interval per topic, so the topic filter can reorder the bars without regenerating the page
        ds = {d: [round(b["score"], 4), *[round(x, 4) for x in b["ci95"]]]
              for d, b in m.get("by_domain", {}).items() if b.get("score") is not None}
        out.append(
            f'<div class="{cls}" style="--v:{k["score"]:.4f};--lo:{lo:.4f};--hi:{hi:.4f}" tabindex="0" '
            f'data-name="{html.escape(name)}" data-g="{k["score"]:.4f},{lo:.4f},{hi:.4f}" '
            f'data-ds="{html.escape(json.dumps(ds, separators=(",", ":")))}" '
            f'aria-label="{label}" data-tip="{label}">{value}<i class="ci"></i>'
            f'<span class="bn">{html.escape(name)}</span></div>')
    return "\n".join(out)


def topic_filter(models):
    """Buttons to rank by topic: Overall and one per domain, with the number of questions."""
    n = collections.Counter()
    for m in models[:1]:
        n.update({d: b.get("n", 0) for d, b in m.get("by_domain", {}).items()})
    buttons = [f'<div class="ctl filter" id="topic-filter" role="group" aria-label="{tr("topic_filter")}">',
               f'<button type="button" data-d="" aria-pressed="true">{tr("overall")}</button>']
    for d, _ in DOMAINS:
        buttons.append(f'<button type="button" data-d="{d}" aria-pressed="false">{html.escape(domain_name(d))}'
                       f' <span class="num">{n.get(d, 0)}</span></button>')
    return "\n".join(buttons + ["</div>"])


def hero_bars(models, n=8):
    """The first screen's columns: each column's background is the summit (100 %), the bar is the score."""
    out = []
    for i, m in enumerate([m for m in models if m["comparable"]][:n]):
        name, _ = model_name(m["model"])
        k = m["knowledge"]
        out.append(f'<li style="--v:{k["score"]:.4f};--i:{i}"><b class="num">{pct(k["score"])}</b>'
                   f'<span class="hb"><i></i></span><span class="hn">{html.escape(name)}<span class="hv"> · {pct(k["score"])}</span></span></li>')
    return "\n".join(out)


def domain_tiles(models):
    comp = [m for m in models if m["comparable"]]
    if not comp:
        return ""
    sel = comp[0]["model"]
    out = []
    for d, _ in DOMAINS:
        name = domain_name(d)
        vals = [(m["model"], (m["by_domain"].get(d) or {}).get("score")) for m in comp]
        v = dict(vals).get(sel)
        mini = "".join(f'<i class="{"sel" if mid == sel else ""}" data-m="{html.escape(mid)}" '
                       f'title="{html.escape(model_name(mid)[0])}: {pct(x) if x is not None else tr("no_data")}" '
                       f'style="--v:{(x or 0):.4f}"></i>' for mid, x in vals)
        nsel = (comp[0]["by_domain"].get(d) or {}).get("n", 0)
        best = max((x for x in vals if x[1] is not None), key=lambda x: x[1], default=None)
        btxt = (f"{tr('best')}: {html.escape(model_name(best[0])[0])}, {pct(best[1])}" if best
                else tr("no_data").capitalize())
        out.append(f'<div class="dt" data-d="{d}"><h3>{name}</h3><b class="dv num">{pct(v) if v is not None else "–"}</b>'
                   f'<div class="mini" data-ui aria-hidden="true">{mini}</div><p class="dn"><span class="dnn">{nsel} {tr("questions")}</span> · {btxt}</p></div>')
    return "\n".join(out)


# Success cases: the project's fine-tuned models against the base models they start from, by placeholder prefix.
CASES = {"CASE": ("ollama:maia-e4b:20261102-1437", "ollama:gemma4:e4b"),
         "CASE12": ("ollama:maia-12b:20261104-0036", "ollama:gemma4:12b")}


def case_numbers(models):
    """Base and maia knowledge scores and the difference in points, as page strings (empty without both)."""
    by_id = {m["model"]: m for m in models}
    out = {}
    for prefix, (model, base_model) in CASES.items():
        if model not in by_id or base_model not in by_id:
            out.update({f"__{prefix}_BASE__": "–", f"__{prefix}_MAIA__": "–", f"__{prefix}_DIFF__": "–"})
            continue
        base, maia = by_id[base_model]["knowledge"]["score"], by_id[model]["knowledge"]["score"]
        # From the rounded percentages on the page, so the three figures always agree.
        diff = f"{round(maia * 100, 1) - round(base * 100, 1):+.1f}"
        out.update({f"__{prefix}_BASE__": pct(base), f"__{prefix}_MAIA__": pct(maia),
                    f"__{prefix}_DIFF__": diff if LANG == "en" else diff.replace(".", ",")})
    return out


def social_tags(title, description, filename):
    """Open Graph and Twitter tags for a page, from its already translated title and description."""
    tags = {"og:type": "website", "og:site_name": "maia-bench", "og:title": title, "og:description": description,
            "og:url": SITE + ("" if filename == "index.html" else filename), "og:image": SITE + "assets/og.png",
            "og:image:width": "1200", "og:image:height": "630"}
    out = [f'<meta property="{k}" content="{html.escape(v)}">' for k, v in tags.items()]
    return "\n".join(out + ['<meta name="twitter:card" content="summary_large_image">'])


def training_page(lang, template, strings, train_template, train_strings, credits_html):
    """One language of the page that explains how maia was trained; it reuses the results page's styles."""
    page = train_template.replace("__STYLE__", re.search(r"<style>.*?</style>", template, re.S).group(0))
    page = page.replace("__BLOCKS__", re.search(r'<div class="blocks".*?</div>', template, re.S).group(0))
    for key, t in {**strings, **train_strings}.items():
        page = page.replace(f"__T:{key}__", t[lang])
    langs = "".join(f'<a href="{f}" hreflang="{i}" lang="{i}"' + (' aria-current="page"' if i == lang else "")
                    + f">{LANG_LABEL[i]}</a>" for i, f in TRAINING.items())
    title = re.sub(r"</?title>", "", train_strings["tr_title"][lang])
    subst = {"__LANG__": lang, "__HOME__": LANGS[lang], "__LANGS__": langs, "__CREDITS__": credits_html,
             "__SOCIAL__": social_tags(title, train_strings["tr_meta"][lang], TRAINING[lang])}
    for k, v in subst.items():
        page = page.replace(k, v)
    return page


def question_sample(models, dataset):
    complete = [m for m in models if m["knowledge"].get("n") and m["comparable"]]
    by_model = {}
    for m in complete:
        answers, scores = {}, {}
        for line in open(os.path.join(m["folder"], "answers.jsonl"), encoding="utf-8"):
            r = json.loads(line)
            if not r.get("error"):
                answers[r["id"]] = r["answer"]
        sf = os.path.join(m["folder"], "scores.jsonl")
        if os.path.exists(sf):
            for line in open(sf, encoding="utf-8"):
                r = json.loads(line)
                scores[r["id"]] = r
        by_model[m["model"]] = (answers, scores)
    shared = [i for i in dataset if all(i in s for _, s in by_model.values())] if by_model else []
    rnd = random.Random(20261027)

    # Questions where the models disagree come first: they explain the most.
    def disagree(i):
        vals = {by_model[m][1][i]["points"] for m in by_model}
        return len(vals) > 1
    rnd.shuffle(shared)
    shared.sort(key=lambda i: not disagree(i))
    out = []
    for i in shared[:SAMPLE_SIZE]:
        p = dataset[i]
        e = {"id": i, "type": p["type"], "domain": domain_name(p["domain"]), "question": p["question"],
             "reference": (p["reference_answer"] if p["type"] != "multiple_choice"
                           else f"{p['correct']}) {p['options'][p['correct']]}"),
             "answers": []}
        if p["type"] == "multiple_choice":
            e["options"] = p["options"]
        for m, (answers, scores) in by_model.items():
            s = scores[i]
            e["answers"].append({"model": m, "text": answers.get(i, "")[:700], "points": s["points"],
                                 "reason": s.get("reason", "")})
        out.append(e)
    return out


def main():
    global LANG
    rows = load_questions()
    dataset = {r["id"]: r for r in rows}
    models = load_models()
    template = open(os.path.join(ROOT, "web", "template.html"), encoding="utf-8").read()
    strings = json.load(open(os.path.join(ROOT, "web", "strings.json"), encoding="utf-8"))
    credits = json.load(open(os.path.join(ROOT, "web", "assets", "credits.json"), encoding="utf-8"))
    train_template = open(os.path.join(ROOT, "web", "training-template.html"), encoding="utf-8").read()
    train_strings = json.load(open(os.path.join(ROOT, "web", "training-strings.json"), encoding="utf-8"))
    version = f"v1-draft ({dataset_fingerprint(rows)})"
    type_counts = {t: sum(1 for r in rows if r["type"] == t) for t in TYPES}
    n_complete = sum(1 for m in models if m["complete"])
    n_comparable = sum(1 for m in models if m["comparable"])
    fact_sheets = open(os.path.join(ROOT, "holdout", "fact-sheets.txt"), encoding="utf-8").read().split()

    for lang, filename in LANGS.items():
        LANG = lang
        pieces = []
        for c in credits if isinstance(credits, list) else credits.values():
            title = html.escape(c.get("title", ""))
            author = c.get("creator") or c.get("author")
            lic = c.get("licence") or c.get("license") or ""
            pieces.append(f'<a href="{html.escape(c.get("page") or c.get("source", ""))}">«{title}»</a>'
                          + (f", {html.escape(author)}" if author else "") + (f", {html.escape(lic)}" if lic else ""))
        credits_html = f"{tr('photos')}: " + "; ".join(pieces) + ", via Wikimedia Commons."
        payload = {
            "models": [{"id": m["model"], "name": model_name(m["model"])[0], "score": m["knowledge"].get("score", 0),
                        "n": m["knowledge"].get("n", 0), "complete": m["complete"], "comparable": m["comparable"],
                        "by_domain": {d: (v.get("score") if v.get("n") else None) for d, v in m["by_domain"].items()},
                        "by_domain_n": {d: v.get("n", 0) for d, v in m["by_domain"].items()}}
                       for m in models],
            "sample": question_sample(models, dataset),
            "t": {**TXT["js"][lang], "interval": TXT["interval"][lang]},
            "dec": "." if lang == "en" else ",",
        }
        notice = tr("notice").format(n=len(models), c=n_comparable, k=n_complete, t=len(rows))
        langs = "".join(f'<a href="{f}" hreflang="{i}" lang="{i}"' + (' aria-current="page"' if i == lang else "")
                        + f">{LANG_LABEL[i]}</a>" for i, f in LANGS.items())
        today = datetime.date.today()
        subst = {
            "__ROWS__": table_rows(models, len(rows)),
            "__BARS__": summit_bars(models),
            "__BARS_CLS__": "rows" if sum(1 for m in models if m["knowledge"].get("n")) > 14 else "",
            "__FILTER__": topic_filter(models),
            "__HERO_BARS__": hero_bars(models),
            "__DOMAINS__": domain_tiles(models),
            **case_numbers(models),
            "__LANGS__": langs,
            "__LANG__": lang,
            "__TRAINING__": TRAINING[lang],
            "__SOCIAL__": social_tags(re.sub(r"</?title>", "", strings["title"][lang]), strings["meta"][lang], filename),
            "__N_MODELS__": str(len(models)),
            "__N_COMPARABLE__": str(n_comparable),
            "__BEST_NAME__": html.escape(model_name(models[0]["model"])[0]) if models else "–",
            "__BEST_SCORE__": pct(models[0]["knowledge"]["score"]) if models else "–",
            "__BEST_M__": metres(models[0]["knowledge"]["score"]) if models else "–",
            "__NOTICE__": html.escape(notice),
            "__DATE__": today.isoformat() if lang == "en" else today.strftime("%d/%m/%Y"),
            "__CREDITS__": credits_html,
            "__PAYLOAD__": json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"),
        }
        page = template
        for key, t in strings.items():
            page = page.replace(f"__T:{key}__", t[lang])
        # translated strings may carry data placeholders: they are substituted afterwards
        subst.update({
            "__VERSION__": html.escape(version), "__JUDGE__": html.escape(model_name(JUDGE)[0]),
            "__N_MULTIPLE_CHOICE__": str(type_counts["multiple_choice"]), "__N_OPEN__": str(type_counts["open"]),
            "__N_TRAP__": str(type_counts["trap"]),
            "__N_TOTAL__": str(len(rows)),
            "__N_ARTICLES__": f"{len({d for r in rows for d in r['documents']})}",
            "__N_UNSEEN__": str(sum(1 for r in rows if r.get("unseen"))),
            "__N_FACT_SHEETS__": str(len(fact_sheets)),
        })
        for k, v in subst.items():
            page = page.replace(k, v)
        out = os.path.join(ROOT, "web", filename)
        open(out, "w", encoding="utf-8").write(page)
        print(f"{out}: {len(models)} models, {len(payload['sample'])} questions in «Try it»")
        out = os.path.join(ROOT, "web", TRAINING[lang])
        page = training_page(lang, template, strings, train_template, train_strings, credits_html)
        open(out, "w", encoding="utf-8").write(page)
        print(out)


if __name__ == "__main__":
    main()
