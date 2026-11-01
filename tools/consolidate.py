#!/usr/bin/env python3
"""Builds one dataset with every model's answer to every question, and a model x domain score table.

Usage:  python3 tools/consolidate.py
Writes: resultats/totes_les_respostes.csv  one row per (model, question): answer, points, verdict, judge reason
        resultats/per_domini.csv           one row per model: overall score and the score in each domain

Reads respostes.jsonl and puntuacions.jsonl of every folder in resultats/ (the last answer and the score that matches
it, as puntua.py does). Column names follow the project's data schema (Catalan).
"""
import csv
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from executa import preguntes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "resultats")


def fingerprint(answer):
    return hashlib.sha1(answer.encode("utf-8")).hexdigest()[:12]


def verdict(points):
    if points is None:
        return "pendent"
    return "bé" if points == 1 else "parcial" if points > 0 else "malament"


def load(folder):
    answers = {}
    for line in open(os.path.join(folder, "respostes.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if not r.get("error"):
            answers[r["id"]] = r
    scores = {}
    path = os.path.join(folder, "puntuacions.jsonl")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            a = answers.get(r["id"])
            # a score only counts for the answer it was given to (rows without "h" predate the fingerprint)
            if a is not None and r.get("h", fingerprint(a["resposta"])) == fingerprint(a["resposta"]):
                scores[r["id"]] = r
    return answers, scores


def main():
    dataset = {p["id"]: p for p in preguntes()}
    domains = sorted({p["domini"] for p in dataset.values()})
    rows, table = [], []
    for folder in sorted(glob.glob(os.path.join(RESULTS, "*", "meta.json"))):
        folder = os.path.dirname(folder)
        model = json.load(open(os.path.join(folder, "meta.json")))["model"]
        answers, scores = load(folder)
        if len(answers) < len(dataset):
            continue  # same rule as the page: only models that answered every question
        per_domain = {d: [] for d in domains}
        for qid, p in dataset.items():
            a, s = answers[qid], scores.get(qid, {})
            points = s.get("punts")
            rows.append({"model": model, "carpeta": os.path.basename(folder), "id": qid, "domini": p["domini"],
                         "tipus": p["tipus"], "resposta": a["resposta"], "raonament": a.get("raonament", ""),
                         "punts": "" if points is None else points, "veredicte": verdict(points),
                         "motiu_jutge": s.get("motiu", "")})
            if points is not None:
                per_domain[p["domini"]].append(points)
        scored = [x for v in per_domain.values() for x in v]
        line = {"model": model, "carpeta": os.path.basename(folder), "puntuades": len(scored),
                "nota": round(sum(scored) / len(scored), 4) if scored else ""}
        for d in domains:
            v = per_domain[d]
            line[d] = round(sum(v) / len(v), 4) if v else ""
        table.append(line)

    with open(os.path.join(RESULTS, "totes_les_respostes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    table.sort(key=lambda r: r["nota"] or 0, reverse=True)
    with open(os.path.join(RESULTS, "per_domini.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)

    print(f"{len(table)} models, {len(rows)} answers -> resultats/totes_les_respostes.csv, resultats/per_domini.csv")
    for d in domains:
        best = max((r for r in table if r[d] != ""), key=lambda r: r[d], default=None)
        if best:
            print(f"  {d:16} {best['model']:45} {best[d]:.1%}")


if __name__ == "__main__":
    main()
