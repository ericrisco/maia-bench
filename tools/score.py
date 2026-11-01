#!/usr/bin/env python3
"""Scores a model's answers and writes its summary.

Usage:  python3 tools/score.py results/<name> [--judge vertex:google/gemini-3.8-flash] [--threads 2] [--no-judge]

- Multiple choice: automatic (1 if the letter is the correct one, 0 otherwise).
- Open and trap questions: the judge gives 0, 1 or 2 against the reference answer, the key facts and the errors to
  penalise (normalised to 0, 0.5 or 1). tools/judge_batch.py does the same through Vertex AI Batch.
Writes scores.jsonl (resumable) and summary.json, with a 95 % bootstrap confidence interval.
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
from providers import ModelError, call  # noqa: E402
from run import load_questions  # noqa: E402

JUDGE = "vertex:google/gemini-3.8-flash"
JUDGE_VERSION = "j1"

# The judge prompt is benchmark data (Catalan) and is versioned by JUDGE_VERSION: changing it means a new version.
JUDGE_SYSTEM = (
    "Ets el jutge d'un benchmark sobre Andorra. Compares la resposta d'un model amb la informació de referència i "
    "puntues només si és correcta i completa segons aquesta referència. No premies l'estil ni la llargada. "
    "Respon únicament amb un objecte JSON."
)

RUBRIC = """Puntua la RESPOSTA DEL MODEL:
- 2: correcta i completa. Conté els fets clau essencials i cap afirmació falsa. Si és una pregunta trampa, rebutja
  explícitament la premissa falsa i diu què és cert.
- 1: parcialment correcta. Encerta part dels fets clau sense cap error greu, o bé (trampa) rebutja la premissa però no
  diu què és cert.
- 0: incorrecta, inventada, evasiva o sense resposta; o conté algun dels ERRORS A PENALITZAR o una altra afirmació falsa
  rellevant; o (trampa) accepta la premissa falsa.
Respon amb aquest JSON exacte: {"nota": 0|1|2, "motiu": "una frase"}"""


def answer_hash(answer):
    # a score only counts for the answer it was given to: if the model answered again (--retry-empty), rescore
    return hashlib.sha1(answer.encode("utf-8")).hexdigest()[:12]


def letter(text):
    t = text.strip()
    m = re.match(r"^\W*([ABCD])\b", t)
    if m:
        return m.group(1)
    found = set(re.findall(r"\b([ABCD])\)", t)) or set(re.findall(r"\b([ABCD])\b", t))
    return found.pop() if len(found) == 1 else None


def judge_prompt(q, answer):
    # the reference is shown to the judge with the j1 Catalan field names, exactly as when the scores were made
    ref = {"pregunta": q["question"], "context": q["context"], "resposta_de_referencia": q["reference_answer"],
           "fets_clau": q.get("key_facts", []), "errors_a_penalitzar": q.get("errors_to_penalise", [])}
    if q["type"] == "trap":
        ref["premissa_falsa"] = q.get("false_premise", "")
        ref["tipus"] = "trampa: la pregunta dona per bona una premissa falsa"
    return [{"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": f"REFERÈNCIA:\n{json.dumps(ref, ensure_ascii=False, indent=1)}\n\n"
                                        f"RESPOSTA DEL MODEL:\n{answer or '(buida)'}\n\n{RUBRIC}"}]


def parse_verdict(text):
    """The judge answers {"nota": 0|1|2, "motiu": "..."}; returns (grade, reason)."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ModelError(f"the judge did not return JSON: {text[:120]!r}")
    v = json.loads(m.group(0))
    if v.get("nota") not in (0, 1, 2):
        raise ModelError(f"invalid grade: {v!r}")
    return v["nota"], v.get("motiu", "")


def judge(judge_model, q, answer):
    if not answer.strip():
        return 0, "resposta buida"
    return parse_verdict(call(judge_model, judge_prompt(q, answer), temperature=0, max_tokens=4000)["text"])


def bootstrap(values, n=1000, seed=7):
    if not values:
        return None, None
    rnd = random.Random(seed)
    k = len(values)
    means = sorted(sum(rnd.choice(values) for _ in range(k)) / k for _ in range(n))
    return round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)


def block(values):
    if not values:
        return {"n": 0}
    lo, hi = bootstrap(values)
    return {"n": len(values), "score": round(sum(values) / len(values), 4), "ci95": [lo, hi]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--judge", default=JUDGE)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--no-judge", action="store_true", help="multiple choice only; open and trap questions stay pending")
    a = ap.parse_args()

    dataset = {q["id"]: q for q in load_questions()}
    answers = {}
    for line in open(os.path.join(a.folder, "answers.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if not r.get("error"):
            answers[r["id"]] = r["answer"]
    hashes = {i: answer_hash(t) for i, t in answers.items()}

    path = os.path.join(a.folder, "scores.jsonl")
    done = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if (r.get("judge") in (None, a.judge) and r["id"] in answers
                    and r.get("answer_hash", hashes[r["id"]]) == hashes[r["id"]]):
                done[r["id"]] = r

    new, to_judge = [], []
    for i, answer in answers.items():
        if i not in dataset:
            continue
        q = dataset[i]
        if q["type"] == "multiple_choice":
            got = letter(answer)
            if i in done and done[i].get("letter") == got:
                continue
            new.append({"id": i, "type": "multiple_choice", "letter": got,
                        "points": 1.0 if got == q["correct"] else 0.0, "answer_hash": hashes[i]})
        elif i in done:
            continue
        elif not a.no_judge:
            to_judge.append(i)
    print(f"new multiple choice: {len(new)} · for the judge: {len(to_judge)} · already scored: {len(done)}",
          file=sys.stderr)

    errors = 0
    with open(path, "a", encoding="utf-8") as out:
        for r in new:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            done[r["id"]] = r

        def one(i):
            try:
                grade, reason = judge(a.judge, dataset[i], answers[i])
                return {"id": i, "type": dataset[i]["type"], "grade": grade, "points": grade / 2, "reason": reason,
                        "judge": a.judge, "answer_hash": hashes[i]}
            except (ModelError, json.JSONDecodeError) as e:
                return {"id": i, "error": str(e)}

        with cf.ThreadPoolExecutor(a.threads) as ex:
            for res in ex.map(one, to_judge):
                if res.get("error"):
                    errors += 1
                    print(f"ERROR {res['id']}: {res['error']}", file=sys.stderr)
                    continue
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
                done[res["id"]] = res

    meta = json.load(open(os.path.join(a.folder, "meta.json")))
    points = {i: r["points"] for i, r in done.items() if i in dataset}
    by_type, by_domain = collections.defaultdict(list), collections.defaultdict(list)
    unseen, seen = [], []
    for i, v in points.items():
        q = dataset[i]
        by_type[q["type"]].append(v)
        by_domain[q["domain"]].append(v)
        (unseen if q.get("unseen") else seen).append(v)

    summary = {
        "model": meta["model"], "origin": meta.get("origin", ""), "dataset": meta.get("dataset"),
        "dataset_questions": len(dataset), "answers": len(answers), "scored": len(points),
        "complete": len(points) == len(dataset),
        "multiple_choice_only": not any(dataset[i]["type"] != "multiple_choice" for i in points),
        "judge": a.judge, "judge_version": JUDGE_VERSION, "prompt": meta.get("prompt"), "temperature": 0,
        "same_model_as_judge": meta["model"] == a.judge,
        "date": datetime.date.today().isoformat(),
        "knowledge": block(list(points.values())),
        "by_type": {k: block(v) for k, v in sorted(by_type.items())},
        "seen": block(seen), "unseen": block(unseen),
        "by_domain": {k: block(v) for k, v in sorted(by_domain.items())},
    }
    json.dump(summary, open(os.path.join(a.folder, "summary.json"), "w"), ensure_ascii=False, indent=1)
    k = summary["knowledge"]
    print(f"{meta['model']}: knowledge {k.get('score')} CI95 {k.get('ci95')} over {k['n']} questions "
          f"({errors} judge errors)")


if __name__ == "__main__":
    main()
