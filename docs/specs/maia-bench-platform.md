---
type: spec
title: Spec — maia-bench platform (dataset, execution and public results)
description: How the reference dataset is built, how any model is evaluated against the andorranness benchmark and how results are published on a web page. The whole benchmark is public.
tags: [sdd, spec, benchmark, evaluation, maia-bench]
timestamp: 2026-10-26T12:00:00Z
topic: sdd
slug: maia-bench-platform
status: draft
---

# Spec — maia-bench platform

> Slug: `maia-bench-platform` · Status: draft · Created: 2026-10-26
> Inherits: the maia project constitution — principles 16 and 17.
> Complements: [andorranness-benchmark](./andorranness-benchmark.md), which defines **what is measured**. This spec
> defines **how it runs and how it is published**. **Decision of 2026-10-26: the benchmark is public**, with no private part.
> Repository: [ericrisco/maia-bench](https://github.com/ericrisco/maia-bench) (private for now; it will be made public).

## Problem and why

The andorranness benchmark measures two things: how much a model knows about Andorra and how well it speaks Andorran
Catalan. As framed in `andorranness-benchmark`, it serves to compare maia with base Gemma. It does not let a third party
evaluate their own model, nor is there any public place showing which models know about Andorra and speak Andorran
Catalan. That reference does not exist today.

A public benchmark has a known risk: **the open questions may end up in the training data of future models**, which
will solve them from memory. The decision is to **accept it** instead of keeping a private part (see "Decision: the
benchmark is public"): what cannot be protected by secrecy is mitigated with versions, a contamination marker and
questions about fact sheets that were never trained on.

## Cost of not building it

Nothing breaks for maia: principle 17 can be met with a script we run on ourselves. What is lost is having any other
model measured by the same yardstick, and the project leaving no reusable reference about Andorra. If someone publishes
a worse benchmark first, theirs becomes the standard.

## The cheapest alternative

A script we run by hand and a table in the README. It covers the constitution for maia and costs a day. It **does not
cover** evaluating third parties, having a public page or protecting against contamination. If the only goal were to
validate maia, it would be enough. This spec exists because we want a public reference.

## Goals

- Anyone can evaluate a model with the benchmark and see its results without asking for permission.
- A public web page shows a table of models with their scores, and distinguishes those that **come from Andorra**.
- The whole benchmark is **public**: questions, contexts, reference answers and code.
- No result can be faked by submitting a score: scoring always happens on our side, with the same fixed judge.
- Each result carries the benchmark version, the judge version and the execution conditions, and can be reproduced.
- Scores carry uncertainty: two scores that cannot be told apart statistically are not presented as a resolved tie.

## Non-goals

- **It is not a chat or a live demo** of a model.
- **It has no user accounts or database**: the website is static.
- **It does not give a single global score** in v1: two main scores (Knowledge and Language), never added together.
- **It does not run code submitted by third parties.** Only data is accepted.
- **It does not evaluate closed models with other people's keys.** API models that appear in the table are run by the
  project with its own keys.
- **It does not replace the blind test with Andorrans:** that is part of the benchmark, but it needs people.
- **It does not train anything** or publish weights.

## Users and context

1. **Eric / the maia project**, which needs to show that the fine-tune beats base Gemma (principle 17).
2. **Teams building models** (Catalan, Andorran or general), who want to know how they behave with Andorra.
3. **Readers of the page**, who only want to know which model is best for Andorra.
4. **The linguistic community**, for whom a "speaks Andorran Catalan" ranking is a reference that does not exist.

Conflict of interest: maia is both the project that builds the benchmark and one of the models measured by it. The page
must say so and mark it (`origin: Andorra · project model`), and the method must be public.

## Decision: the benchmark is public

**Decided by Eric on 2026-10-26.** A private part that would decide the ranking was initially considered. It is
discarded: the benchmark is published in full and private tests are left for other benchmarks. Consequences:

- **The whole dataset is published**: question, options, context, reference answer, key facts and errors to penalise.
- **No secret and no private question server.** No private run queue is needed either.
- **The ranking is produced by the public benchmark itself**, and anyone can reproduce it.

### How contamination is mitigated, since it is not hidden

| Risk | Measure |
|---|---|
| Future models training on the questions | A contamination marker (*canary string*) in every file, so it can be filtered or detected |
| The score ceasing to mean anything over time | Frozen versions (`v1`, `v2`…): a correction or a renewal is a new version, and every result carries the version |
| A model having learnt the answers, not the topic | The "unseen" questions about fact sheets that have never entered any maia training run |
| Someone submitting fake scores | Scores are never accepted: scoring always happens on our side, with the same fixed judge |
| A third-party PR reading secrets | PR actions from forks receive no secrets; none is needed for level 1 |

### An exception that does not depend on the decision: the speech text

The held-out speech pieces used for **perplexity** come from sources with redistribution `pendent` (pending) or `no`.
Even though the benchmark is public, **this text cannot be published**. Only a **manifest** (piece identifier,
source, URL and hash) and a loader that fetches the text from its origin are published. Anyone who cannot obtain it does
not get this test, and it is shown as unavailable.

### Who runs it

| Part | What is submitted | Who scores |
|---|---|---|
| 4-option multiple choice, dialect test | A file with the answers | An automatic action, without a judge |
| Open and traps | A file with the answers | The fixed judge, on the project's side |
| Perplexity | Nothing: it is computed with the manifest | Whoever runs it, with their model |

## Reference dataset (decided on 2026-10-26)

The knowledge dataset is **written by us**, reading the corpus; it is not generated by a judge or a search engine:

- **Each entry:** question, detailed **context** (60–200 words, in our own words, with no references to the corpus)
  and the **reference answer** we would give from that context. Format in the repository's `docs/format.md`.
- **Quantity:** 9 questions per subtopic (6 multiple choice, 2 open and 1 trap), 6 if it has 2 articles and 3 if it has
  one, plus 2 "unseen" for each of the 41 holdout fact sheets: **925** in total (843 + 82).
- **Writing:** project agents, **one question per commit**, validated automatically before pushing.
- **Independent verification:** a model from another family (Gemini) tries to answer using only the context, without
  seeing the answer; if it does not match, the question is discarded. In addition, a sample of ~100 is reviewed by a person.
- **Limit:** the reference is *what the corpus says*, which is compiled by AI and not verified claim by claim. The
  benchmark measures whether a model knows what the corpus says; the public page must say so.

## Submission flow

**Level 1 — without judge.** The questions are downloaded, the model answers and an answers file is submitted by
*pull request*. An action scores the multiple-choice questions and the dialect test, which are deterministic. The result is published.

**Level 2 — with judge.** Open and trap questions are scored by the fixed judge (model and version recorded). The judge
receives the question, the reference answer, the key facts and the model's answer, and returns a grade from 0 to 2 and a reason.
Temperature 0 and two passes; if they disagree, the answer is flagged for human review.

**Judge limits (tested on 2026-10-26).** In one test, the judge gave a 2 (correct and complete) to an answer that
included an **added false** claim («el més jove de la història dels Jocs d'hivern», "the youngest in the history of the
Winter Games"), because it only had the reference and the key facts, and the reference did not say it was false. A
judge cannot detect an error it does not know about. Design consequence: each question must carry, in addition to the
key facts, a list of **typical errors to penalise** (known false claims), and a grade of 2 requires that none be present.

**Language is not judged by an AI.** Whether an answer "sounds Andorran" is not delegated to an LLM, which does not know
this variety well. It is measured with perplexity, the dialect test and the Andorrans in the blind test.

## Results and scoring

Each results row carries: model and exact version (Hugging Face hash or API name and date), size, family, **origin**,
benchmark version, level run (1 or 2), judge version, dates, scores per part with the **number of
questions** and a **confidence interval** (resampling or *bootstrap*), and the execution configuration (prompt, temperature).

- No single score. **Knowledge** and **Language** are shown, and the control as a warning (a marked drop is highlighted).
- If the intervals of two models overlap, the page does not rank them as if one were better.

## Public page

A static page generated from the results files; no server, accounts or database. It shows a table
filterable by family, size and origin; a benchmark version selector; and, on each row, which level was run and with
which judge. Visible text explains how the corpus was built and what its limitations are
([corpus origin](https://github.com/ericrisco/maia-bench/blob/main/docs/corpus-origin.md)).

## Cost and infrastructure

- Google Cloud: project `maia-andorra`, MAIA billing (available credit: **not verified**).
  **Judge:** `google/gemini-3.8-flash` responds (HTTP 200) through Vertex's **OpenAI-compatible endpoint**
  (`/endpoints/openapi/chat/completions`, `location=global`), checked on 2026-10-26. The native `generateContent` route
  returns 404 for every model tried, and `gemini-2.5-flash` also returns 404 on both routes. The judge must be pinned
  with this route. Cost measured on a short case: ~400–450 tokens per call (reasoning included).
  **GPU:** on 2026-10-26 the global quota is **1 GPU** (approved) and the **L4** in europe-west4 is granted; the
  **A100 80 GB** was denied. For the 31B an L4 with 4 bits is needed, or the A100 must be requested again with more justification.
- Each run has a **maximum budget** and shuts itself down at the end. No GPU machine stays on without work.
- Runs of open-weight models done by the project have a monthly cap, so the cost does not depend on who asks.

## Licences and rights

- Licence for the code and data: **not chosen**. It depends on the terms of the corpus sources.
- The held-out speech pieces **cannot be published** (redistribution `pendent`/`no`): only the manifest and the loader.
- Since the dataset is public, the **context** and the **reference answer** of each question must be written in our own
  words and not copy text from a source with limited redistribution. It is a writing rule and is checked in the human sample.

## Acceptance criteria

- [ ] The reference dataset exists, frozen as `v1` (925 questions planned), with every entry validated.
- [ ] The repository **does not contain** text from the held-out speech pieces, only the manifest.
- [ ] A third party can evaluate a model at level 1 following only the README, without our keys.
- [ ] An answer submitted by PR is scored without accessing any secret.
- [ ] A score submitted manually by a third party is ignored (only answers are scored).
- [ ] Each published row carries the benchmark version, the judge version, the number of questions and a confidence interval.
- [ ] The web page is generated from the results files and shows the origin of each model.
- [ ] No GPU run exceeds the maximum budget or stays on.
- [ ] The results of the two base models (Gemma 4 E4B and 31B) are published before any fine-tune.

## Open decisions

1. ~~Public/private split.~~ **Resolved on 2026-10-26: everything public.**
2. **Who can submit models**: anyone, or only those approved by the project.
3. **When the repository goes public** and where the website is hosted (GitHub Pages).
4. **Judge**: `gemini-3.8-flash` works through the OpenAI-compatible endpoint; decide whether it is the one pinned or whether a *pro*-tier model is preferred, and how added false claims are detected (see "Judge limits").
5. **Licence** for the code and the data.
6. **Blind-test voters** (5–10 Andorrans) and who reviews the 100-question sample.
7. ~~GPU quota.~~ **Partial:** global 1 and L4 granted; A100 denied.
