#!/usr/bin/env python3
"""Builds one dataset with every model's answer to every question, and a model x topic score table.

Usage:  python3 tools/consolidate.py
Writes: results/all_answers.jsonl  one line per (model, question): answer, points, verdict, judge reason
        results/by_topic.json      one entry per model: overall score and the score in each domain

Reads answers.jsonl and scores.jsonl of every folder in results/ (the last answer and the score that matches it, as
score.py does). Only models that answered every question are included, the same rule as the page.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import ROOT, load_questions  # noqa: E402
from score import answer_hash  # noqa: E402

RESULTS = os.path.join(ROOT, "results")


def verdict(points):
    if points is None:
        return "pending"
    return "right" if points == 1 else "partial" if points > 0 else "wrong"


def load(folder):
    answers = {}
    for line in open(os.path.join(folder, "answers.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if not r.get("error"):
            answers[r["id"]] = r
    scores = {}
    path = os.path.join(folder, "scores.jsonl")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            a = answers.get(r["id"])
            # a score only counts for the answer it was given to (rows without a hash predate it)
            if a is not None and r.get("answer_hash", answer_hash(a["answer"])) == answer_hash(a["answer"]):
                scores[r["id"]] = r
    return answers, scores


def main():
    dataset = {q["id"]: q for q in load_questions()}
    domains = sorted({q["domain"] for q in dataset.values()})
    table, total = [], 0
    with open(os.path.join(RESULTS, "all_answers.jsonl"), "w", encoding="utf-8") as out:
        for meta_path in sorted(glob.glob(os.path.join(RESULTS, "*", "meta.json"))):
            folder = os.path.dirname(meta_path)
            model = json.load(open(meta_path))["model"]
            answers, scores = load(folder)
            if len(answers) < len(dataset):
                continue
            per_domain = {d: [] for d in domains}
            for qid, q in dataset.items():
                a, s = answers[qid], scores.get(qid, {})
                points = s.get("points")
                out.write(json.dumps({"model": model, "folder": os.path.basename(folder), "id": qid,
                                      "domain": q["domain"], "type": q["type"], "answer": a["answer"],
                                      "reasoning": a.get("reasoning"), "points": points, "verdict": verdict(points),
                                      "judge_reason": s.get("reason")}, ensure_ascii=False) + "\n")
                total += 1
                if points is not None:
                    per_domain[q["domain"]].append(points)
            scored = [x for v in per_domain.values() for x in v]
            table.append({"model": model, "folder": os.path.basename(folder), "scored": len(scored),
                          "score": round(sum(scored) / len(scored), 4) if scored else None,
                          "by_domain": {d: round(sum(v) / len(v), 4) if v else None for d, v in per_domain.items()}})

    table.sort(key=lambda r: r["score"] or 0, reverse=True)
    with open(os.path.join(RESULTS, "by_topic.json"), "w", encoding="utf-8") as f:
        json.dump({"domains": domains, "models": table}, f, ensure_ascii=False, indent=1)

    print(f"{len(table)} models, {total} answers -> results/all_answers.jsonl, results/by_topic.json")
    for d in domains:
        best = max((r for r in table if r["by_domain"][d] is not None), key=lambda r: r["by_domain"][d], default=None)
        if best:
            print(f"  {d:14} {best['model']:45} {best['by_domain'][d]:.1%}")


if __name__ == "__main__":
    main()
