---
type: spec
title: Spec — Andorranness benchmark
description: What the benchmark comparing base Gemma 4 with maia measures (knowledge of Andorra and Andorran speech), how it is protected from contamination and where it runs.
tags: [sdd, spec, benchmark, evaluation, gemma-4]
timestamp: 2026-10-20T09:00:00Z
topic: sdd
slug: andorranness-benchmark
status: draft
---

# Spec — Andorranness benchmark

> Slug: `andorranness-benchmark` · Status: draft · Created: 2026-10-20
> Inherits: the maia project constitution — principles 11, 12, 16 and 17.
> Target contract: the `andorran-gemma-finetune` spec of the maia project.

## Problem and why

The project trains Gemma 4 so that it **knows about Andorra** and **speaks Andorran Catalan**. Without a measurement
fixed before training, neither can be demonstrated: any improvement would be an impression.
The constitution requires it (principle 16: a holdout set never seen in training and validation with native
speakers; principle 17: a fine-tune that does not beat the base is not published).

## What is compared

Four models, with the same questions and the same configuration (temperature 0, same prompt):

| | Base | Fine-tune |
|---|---|---|
| Small | Gemma 4 **E4B** (dense, mobile-oriented) | maia-E4B |
| Large | Gemma 4 **31B** (dense) — *or 26B A4B MoE, open decision* | maia-31B |

Gemma 4 comes in four sizes: E2B, E4B, 26B A4B (MoE: 25.2B total, 3.8B active) and 31B (dense). Licence
Apache 2.0 (April 2026).

## The three parts of the benchmark

### 1. Knowledge — "does it know about Andorra?"

| Type | What it measures | Scoring | Size |
|---|---|---|---|
| 4-option multiple choice | It has learnt the fact | Automatic, exact | ~600 |
| Short open answer | It can explain it | LLM judge with reference answer and rubric | ~300 |
| Traps | It does not make anything up | Scores rejecting the false premise or saying it is not known | ~100 |

- Spread across the 13 domains of `docs/temes/`, proportional to the number of articles, with a minimum per domain.
- Three levels: one fact · relation between two fact sheets · reasoning over several fact sheets.
- **No facts that expire** (principle 11): no laws in force, prices, current office-holders or timetables.

### 2. Language — "does it speak Andorran Catalan?"

| Test | What it measures | Scoring | Size |
|---|---|---|---|
| Perplexity on real speech | How natural authentic Andorran Catalan feels to it | Automatic | Held-out Parla pieces (~10–15% of the words) |
| Dialect choice | It knows the Andorran forms | Multiple choice, automatic | ~200, from `temes/llengua/` |
| Blind test with Andorrans | It genuinely sounds Andorran | Human votes, blind A/B | ~150 pairs, 5–10 people |

The blind test is being prepared now (prompts, protocol and rubric). The answers can only be generated once
the trained models exist.

### 3. Control — "has it not got worse?"

A general Catalan benchmark (CatalanBench, in `lm-evaluation-harness`) to detect catastrophic forgetting.

## Contamination: the rule everything rests on

1. **Holdout fact sheets (~3%, ~40 articles):** never enter training. They serve to measure whether the
   model makes things up when it does not know them.
2. **Holdout Parla pieces (4–5, from different speakers and topics):** never enter training.
   **They must be decided before exporting Parla.**
3. **New questions:** knowledge questions about trained fact sheets are written from scratch and
   checked against the 19,421 records of `training-data/datasets/`. If one is too similar, it is discarded.
4. **Frozen before training:** the benchmark carries a version (`v1`) and is not touched. A correction is a `v2`.

## Where it lives

- **Updated 2026-10-26:** the benchmark has its own repository, [`ericrisco/maia-bench`](https://github.com/ericrisco/maia-bench)
  (folder `03-PROJECTS/maia-bench`). How it runs, how it is published and what stays private is in
  [maia-bench-platform](./maia-bench-platform.md).
- **Updated 2026-10-27:** the holdout lives in `holdout/` of this repository (`fact-sheets.txt` and `speech.txt`). maia
  keeps a copy at `training-data/excloses-benchmark.txt`, which is the one the exporter reads. **The two must match.**

## Infrastructure (Google Cloud)

- Project **`maia-andorra`**, linked to the billing account **MAIA** (`01AB95-BF27B5-6545A2`, EUR, open).
  Active APIs: Compute Engine, Vertex AI, Cloud Storage. Available credit: ~1,000 USD.
- **GPU quota = 0** (`GPUS_ALL_REGIONS`). An increase must be requested before switching anything on.
- Approximate needs:
  - E4B: 1× L4 (24 GB) is enough to evaluate and to run QLoRA.
  - 31B: 1× A100 80 GB or H100 80 GB to evaluate in bf16 and to run QLoRA.
- LLM judge: a Gemini model on Vertex AI, with a pinned version, in the same project.
- Cost rule: no GPU machine stays on without work; it is shut down at the end of every run.

## Acceptance criteria

- [ ] List of holdout fact sheets and pieces, frozen and excluded from the export.
- [ ] ~1,000 knowledge questions, with reference answer, domain, level and supporting fact sheets.
- [ ] No benchmark question has a near-duplicate in the training datasets.
- [ ] A sample of 100 questions reviewed by a person, with less than 3% errors.
- [ ] ~200 dialect-choice questions with Andorran form and standard form documented in the corpus.
- [ ] Prompts, protocol and rubric of the blind test ready.
- [ ] Code that runs the benchmark on a model and produces the comparison table.
- [ ] Results of the two base models recorded before any fine-tune.

## Out of scope (for now)

- The web page for the benchmark and the blind test. To be decided when the data is done.
- Training.

## Open decisions (clarify)

1. Large model: **31B dense** (simpler fine-tune, more capacity) or **26B A4B MoE** (cheaper inference)?
2. Which Parla pieces are held out?
3. Who reviews the 100-question sample, and who are the blind-test voters?
4. Should the GPU quota increase be requested now, and in which region (Europe)?
