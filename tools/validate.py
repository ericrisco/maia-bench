#!/usr/bin/env python3
"""Validates maia-bench knowledge dataset files.

Usage:  python3 tools/validate.py knowledge/<file>.jsonl [...] [--maia <maia root>] [--holdout <file>]

Only reports errors for the given files, but always loads every `knowledge/*.jsonl` to detect duplicate ids and
questions. Exit code 1 if there are errors.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

# These patterns check the Catalan question text, so they are written in Catalan.
FORBIDDEN = re.compile(
    r"\bcorpus\b|\bfitxa\b|segons (el|l')\s*(text|article|document)|\bdocs/|\.md\b", re.I
)
EXPIRES = re.compile(
    r"\b(actualment|avui dia|a dia d'avui|vigent|ministre actual|cap de govern actual)\b", re.I
)
TYPES = {"multiple_choice", "open", "trap"}
BASE = {"id", "type", "domain", "subtopic", "level", "question", "context", "reference_answer", "documents"}
TEXT_FIELDS = ("question", "context", "reference_answer", "false_premise")


def norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


def texts(r):
    for k in TEXT_FIELDS:
        if isinstance(r.get(k), str):
            yield k, r[k]
    for k in ("key_facts", "errors_to_penalise"):
        for i, v in enumerate(r.get(k) or []):
            if isinstance(v, str):
                yield f"{k}[{i}]", v
    for k, v in (r.get("options") or {}).items():
        if isinstance(v, str):
            yield f"options.{k}", v


def check_entry(r, holdout, maia, errs):
    missing = BASE - set(r)
    if missing:
        errs.append(f"missing keys: {sorted(missing)}")
        return
    if r["type"] not in TYPES:
        errs.append(f"invalid type: {r['type']!r}")
    if r["level"] not in (1, 2, 3):
        errs.append(f"invalid level: {r['level']!r}")
    if not re.fullmatch(r"[a-z0-9-]+/\d{3}", r["id"]):
        errs.append(f"badly formatted id: {r['id']!r}")
    elif r.get("unseen"):
        if not r["id"].startswith("unseen-"):
            errs.append("an unseen entry must have id 'unseen-<batch>/NNN'")
    elif r["id"].split("/")[0] != r["subtopic"]:
        errs.append(f"the id must start with the subtopic ({r['subtopic']})")

    if r["type"] == "multiple_choice":
        op = r.get("options")
        if not isinstance(op, dict) or sorted(op) != ["A", "B", "C", "D"]:
            errs.append("multiple_choice: needs options A, B, C and D")
        else:
            vals = [str(v).strip() for v in op.values()]
            if any(not v for v in vals) or len({norm(v) for v in vals}) != 4:
                errs.append("multiple_choice: the 4 options must be non-empty and different")
            if r.get("correct") not in op:
                errs.append("multiple_choice: 'correct' must be A, B, C or D")
    else:
        if "options" in r or "correct" in r:
            errs.append(f"{r['type']}: cannot have options or correct")
        for k in ("key_facts", "errors_to_penalise"):
            v = r.get(k)
            if not isinstance(v, list) or not v or not all(isinstance(x, str) and x.strip() for x in v):
                errs.append(f"{r['type']}: needs '{k}' (non-empty list of strings)")
    if r["type"] == "trap" and not str(r.get("false_premise", "")).strip():
        errs.append("trap: needs 'false_premise'")

    n = len(str(r["context"]).split())
    if not 40 <= n <= 400:
        errs.append(f"context of {n} words (must be 40 to 400)")
    minimum = 1 if r["type"] == "multiple_choice" else 3
    if len(str(r["reference_answer"]).split()) < minimum:
        errs.append("reference answer too short")
    if not str(r["question"]).strip().endswith("?"):
        errs.append("the question must end with '?'")

    for field, txt in texts(r):
        m = FORBIDDEN.search(txt)
        if m:
            errs.append(f"{field}: forbidden expression {m.group(0)!r}")

    docs = r["documents"]
    if not isinstance(docs, list) or not docs or not all(isinstance(d, str) and d.endswith(".md") for d in docs):
        errs.append("documents: non-empty list of .md paths")
        return
    in_holdout = [d in holdout for d in docs] if holdout else []
    if holdout:
        if r.get("unseen") and not all(in_holdout):
            errs.append("unseen: every document must be a holdout fact sheet")
        if not r.get("unseen") and any(in_holdout):
            errs.append("a normal entry cannot cite a holdout fact sheet")
    if maia:
        for d in docs:
            if not os.path.exists(os.path.join(maia, d)):
                errs.append(f"the document does not exist: {d}")


def warnings(r, warns):
    for field, txt in texts(r):
        m = EXPIRES.search(txt)
        if m:
            warns.append(f"{field}: possibly expiring fact ({m.group(0)!r})")
    if r.get("type") == "multiple_choice" and isinstance(r.get("options"), dict) and r.get("correct") in r["options"]:
        if norm(r["options"][r["correct"]]) not in norm(r.get("reference_answer", "")):
            warns.append("the reference answer does not contain the correct option's text")


def read(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append((i, json.loads(line)))
            except json.JSONDecodeError as e:
                out.append((i, e))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--maia", default=os.environ.get("MAIA_ROOT"))
    ap.add_argument("--holdout", default=None)
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hf = a.holdout or os.path.join(root, "holdout", "fact-sheets.txt")
    holdout = set(open(hf).read().split()) if os.path.exists(hf) else set()
    if not a.maia:
        print("warning: without --maia / MAIA_ROOT the documents are not checked to exist", file=sys.stderr)

    ids, questions = collections.defaultdict(list), collections.defaultdict(list)
    for p in glob.glob(os.path.join(root, "knowledge", "*.jsonl")):
        for i, r in read(p):
            if isinstance(r, dict) and "id" in r:
                ids[r["id"]].append(os.path.basename(p))
                questions[norm(str(r.get("question", "")))].append(r["id"])

    errors, warns, count = [], [], collections.Counter()
    for file in a.files:
        p = file if os.path.isabs(file) else os.path.join(root, file)
        letters = collections.Counter()
        for i, r in read(p):
            ref = f"{os.path.basename(p)}:{i}"
            if isinstance(r, Exception):
                errors.append(f"{ref}: invalid JSON ({r})")
                continue
            e = []
            check_entry(r, holdout, a.maia, e)
            if len(ids.get(r.get("id"), [])) > 1:
                e.append("repeated id")
            if len(questions.get(norm(str(r.get("question", ""))), [])) > 1:
                e.append("repeated question")
            errors += [f"{ref} ({r.get('id')}): {x}" for x in e]
            w = []
            warnings(r, w)
            warns += [f"{ref} ({r.get('id')}): {x}" for x in w]
            count[r.get("type")] += 1
            if r.get("type") == "multiple_choice" and r.get("correct"):
                letters[r["correct"]] += 1
        if sum(letters.values()) >= 4 and max(letters.values()) / sum(letters.values()) > 0.5:
            warns.append(f"{os.path.basename(p)}: the correct letter is unbalanced {dict(letters)}")

    for w in warns:
        print("WARNING", w)
    for e in errors:
        print("ERROR  ", e)
    print(f"{sum(count.values())} entries {dict(count)}: {len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
