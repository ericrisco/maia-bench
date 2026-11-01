# How the corpus behind this benchmark was built

This benchmark does not evaluate against an abstract knowledge of Andorra: it evaluates against **a specific corpus**,
the one from [maia](https://github.com/ericrisco/maia). To interpret the results correctly you need to know how that
corpus was made and what its limitations are. This document summarises it. The detail lives in the maia project.

## The process

1. **Find and register the sources.** The sources are public (official documents, legislation, publications, press,
   archives, audiovisual material). Each source has its own record with owner, URL, declared licence, whether it allows
   redistribution and the date it was consulted. One record per **source**, not per document.
2. **Read and distil.** Each reading is recorded as a *unit*: source, version, locator (section, page),
   SHA-256 hash of the copy read, status (distilled or only read), destination article and pending work. The
   register says what was read, not that the whole source is covered. The work was done in domain batches (the one on
   13-09-2026: 446 units on unemployment, demography, water resources, budget, avalanches, institutions, language,
   education and foreign relations).
3. **Write the articles.** AI agents write them from the units read. All of them are `veu: compilada` (compiled voice):
   they talk **about** Andorra, they are not Andorran language. An article that cannot be grounded **is not published**:
   it becomes a recorded gap, not plausible-sounding text.
4. **Validate against a contract.** `CONTRACT.md` sets the required fields (`veu`, `epoca`, `font`, `tema`…) and 14
   rules (R001–R014): missing fields, broken links, non-existent sources, unattributed quotes… The language rule
   is mechanical: `apte_llengua = (veu == originària) i (època == contemporània)` (fit for language = native voice and
   contemporary period).
5. **Speech.** Separately, verbatim transcriptions of Andorran people taken from public audiovisual sources. They are
   `veu: originària` (native voice), and they are the only part of the corpus that is genuinely Andorran language. The
   transcriptions are automatic and **have not been verified against the audio**.
6. **Closing v1.** The initial collection was closed on **24 September 2026** on the instruction of the project
   lead. It is neither a release nor a certification of the content.

## The snapshot, as of 26-10-2026

Direct count by the `type` field of the frontmatter, on maia commit `32c7797b3e`.

| Unit | Count |
| --- | ---: |
| Topic articles (`docs/temes/`) | 1,348 |
| Navigation indexes (not counted as content) | 129 |
| Domains | 13 |
| Subtopics | 111 |
| Source records (`docs/fonts/`) | 664 |
| Speech documents (`docs/parla/oral/`) | 40 (38 native voice, 2 compiled) |
| Independent speech corpus (person records) | 66 (3 quarantined for quality) |

The articles add up to about 1.8 million words. All topic articles are `veu: compilada`.

| Domain | Articles |
| --- | ---: |
| institutions | 350 |
| sports | 280 |
| history | 241 |
| society | 156 |
| economy | 104 |
| culture | 83 |
| territory | 65 |
| language | 56 |
| people | 44 |
| customs | 34 |
| politics | 24 |
| gastronomy | 22 |
| daily-life | 18 |

(These domain counts include each folder's indexes.)

## Limitations that affect the benchmark

- **Not every claim has been exhaustively verified.** A question having an answer in the corpus does not guarantee that
  the answer is true: that is why each question is verified against the document independently, but external truth is
  not checked.
- **Compiled by agents.** The articles are written by an AI. A model that learns them learns what the corpus says,
  errors included.
- **Uneven coverage.** The number of articles per domain does not measure the diversity of evidence: institutions and
  sports weigh heavily, and there are small domains.
- **Non-normalised licences.** The redistribution field of the source records is free text in many cases; it cannot be
  summarised as "yes / no / pending" without normalising it. That is why this repository leaves open what gets published.
- **Absence is not negation.** Something not appearing in the corpus does not mean it is false in Andorra. That is why
  "trap" questions are only built on demonstrably false premises.
- **Data that expires.** Laws in force, prices, office-holders and timetables are left out of the benchmark.
- **Unverified speech.** The transcription is automatic; part of it is doubtful and has been flagged.

## To be completed by the project lead

The project documentation does not record **which deep-research tools or models were used** to locate and read the
sources, nor how many queries were made. There is only a trace of the agent sessions that read the sources and wrote
the articles. This section must be filled in with the real process; it has deliberately not been invented.

## From corpus to benchmark

1. Questions are generated per domain from the articles, at three levels (one fact, relation between two articles,
   several articles).
2. A second agent, without seeing the answer, tries to answer using only the document. If it cannot, the question is discarded.
3. Each question is compared against maia's training data and discarded if it is too similar.
4. Part of the articles and speech pieces is **held out** and never enters training.
5. It is frozen as `v1`. A correction is a `v2`.
