# maia-bench

A benchmark that measures **how much a model knows about Andorra** and **how well it speaks Andorran Catalan**.

It was born from the [maia](https://github.com/ericrisco/maia) project (Gemma 4 specialised in Andorra), but it is
independent: it can evaluate any model.

> **Status:** the knowledge dataset (926 questions) is done and verified. The language part is under construction.

> **Where the corpus comes from:** see [how the corpus was built](docs/corpus-origin.md): the process, a snapshot with counts, and its limitations.

## What it measures

| Part | Question | Scoring |
|---|---|---|
| **Knowledge** | Does it know about Andorra? Does it make things up? | 4-option multiple choice (automatic); open answers and traps (LLM judge) |
| **Language** | Does it speak Andorran Catalan? | Perplexity on real speech, dialect test (automatic) and a blind test with Andorrans (human votes) |
| **Control** | Has it got worse at general Catalan? | Subset of CatalanBench |

The language part **does not use an LLM judge** to decide whether an answer "sounds Andorran": a model does not know
this variety well, which is exactly what is being measured.

## Two execution levels

| Level | What it includes | Cost for whoever runs it |
|---|---|---|
| **1. Without judge** | 4-option multiple choice, dialect test, perplexity | Only their own GPU |
| **2. With judge** | Open questions and traps | A key for a judge model, configurable |

**Official** results always use the fixed judge (model and version recorded in each publication).

## Rules

1. **Frozen versions.** Once published, `v1` is never touched. A correction is a `v2`.
2. **Never in training.** No question, nor the holdout content, may enter a training run that is evaluated with this benchmark.
3. **No data that expires:** no laws in force, prices, current office-holders or timetables.
4. **Same conditions for every model:** same prompt, temperature 0.
5. **Contamination.** Every question is compared against maia's training data and discarded if it is too similar.
   Training data generated after a benchmark version is frozen is filtered the other way round, against the
   benchmark questions. That filter was too loose for maia 12B, whose score is inflated:
   [how maia was trained](https://ericrisco.github.io/maia-bench/training.html).

## Everything is public

The benchmark is published in full: questions, contexts, reference answers, key facts and code. **There is no private
part** (decided on 2026-10-26; private tests are left for other benchmarks). Contamination is mitigated with frozen
versions, a contamination marker (*canary string*) and "unseen" questions about fact sheets that have never entered a
training run. The only thing that **cannot** be published is the text of the speech pieces used in the perplexity test
(the sources do not allow redistribution): a manifest and a loader are published instead.

## Still to decide

- **Licence** for the code and the data (depends on the terms of the corpus sources).
- **When the repository goes public** and where the results page is hosted.

## Knowledge dataset

It is built question by question (one commit per question) on the `dataset` branch. Each entry has a question, a
detailed context and the reference answer. Format in [`docs/format.md`](docs/format.md); validated with
`tools/validate.py`. Planned: 925 questions (9 per subtopic, and 2 "unseen" per holdout fact sheet).

## Documentation

- [How the corpus was built](docs/corpus-origin.md)
- [Spec — what the benchmark measures](docs/specs/andorranness-benchmark.md)
- [Spec — platform: execution, public results and private part](docs/specs/maia-bench-platform.md)
- `holdout/` — the 41 articles and the 6 speech pieces that are **never trained on** (maia holds a copy, and the two must match).

## Planned structure

```
maia-bench/
├── knowledge/      one file per subtopic (multiple choice, open, traps) and unseen-*.jsonl (unseen)
├── language/       dialect, perplexity (manifest), blind
├── holdout/        fact sheets and speech pieces that never enter a training run
├── tools/          validate.py, add.py
└── evaluate/       code that runs the benchmark on a model and produces the table (pending)
```

## Evaluating a model

```bash
# 1. Answers (the model only sees the question). Resumable.
python3 tools/run.py --model ollama:gemma4:e4b
# 2. Scoring: multiple choice automatic; open and traps with the judge (Gemini 3.8 Flash on Vertex)
python3 tools/score.py results/ollama_gemma4_e4b
#    If Vertex rejects online calls (403), run the same judge in batch and then score.py for the summary:
#    python3 tools/judge_batch.py results/ollama_gemma4_e4b [results/<another> ...]
# 3. Results page (web/index.html)
python3 tools/web.py
```

Models: `ollama:<model>` (local), `openai:<model>` (`OPENAI_API_KEY`), `anthropic:<model>` (`ANTHROPIC_API_KEY`),
`openrouter:<model>` (`OPENROUTER_API_KEY`), `vertex:google/<model>` (authenticated `gcloud`, `GCP_PROJECT`).
Useful options: `--limit 20` to try it out, `--threads 4`, `--origin "Andorra · project model"`.

The page is published to GitHub Pages with `.github/workflows/pages.yml` every time `web/` changes on `main`.
