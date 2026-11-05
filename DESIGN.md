---
name: maia-bench
description: Coma Pedrosa (2,942 m) is 100 %; each model is a bar that rises from the foot to its score.
colors:
  ground: "#111111"
  surface: "#1c1c1c"
  surface-2: "#262626"
  bar: "#4a4a4a"
  ink: "#f2f2f2"
  muted: "#c8c8c8"
  accent: "#fedd00"
  field-blue: "#1f4fd1"
  field-red: "#d50032"
typography:
  display: { fontFamily: "General Sans", fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 0.9 }
  text: { fontFamily: "General Sans", fontSize: "17-19px", lineHeight: 1.45 }
rounded: { tile: "0px", bar-end: "4px", button: "0px" }
spacing: { margin: "16px", gap: "8px (6px on mobile)", section: "160px (112px on mobile)" }
direction: { id: "dense-tiles", seed: 448745881 }
---

# DESIGN.md — maia-bench results page

## Overview

Public results page (Persuade mode, but with the charts as the protagonists, at Eric's request: "more
technological, make them charts"). Direction "The well-kept board": the
whole page is a dark board of full tiles, edge to edge, with 8 px gaps. It replaces "The printed annual" (seed
605962653), which was light and editorial.

- **Idea:** the summit of Coma Pedrosa is 100 %. On the first screen, the dark background of each column is the summit
  and the bar is the score; in the leaderboard, the bars rise from the foot and the label «Cim · 2.942 m · 100 %» marks
  the ceiling.
- **Live element:** «Prova-ho» ("Try it"): a random question with the answer and the verdict of each model.

## Colors

Soft black background, tiles one step lighter, white ink. A single accent, the yellow of the flag: the first model (bar,
open table row), the model selected in the domains, the button and the moving band. The blue and red of the flag
only as whole fields (method stages, reference answer, «incorrecta», the footer). A domain where the selected model
fails most is marked with the field `#2a1a1d`. Photos in greyscale.

## Typography

General Sans 400/500/700, five sizes: `--step-small`, `--step-body`, `--step-lead`, `--step-head` and the display one
(the name strip, the big figure and the band). Tabular figures wherever there are numbers. Monospace only inside
`<code>`.

## Components

- Full tiles, no border or shadow. Square corners; only the ends of the bars get 4 px.
- Charts in HTML and CSS with `data-ui`: heights come from `--v` (score 0–1), the interval from `--lo`/`--hi`.
- The table is a board of `<details name="taula">` rows; the open row is painted yellow.
- FAQ with `<details name="faq">`, one open at a time; the plus sign is two 3 px bars.
- Footer: the name built from coloured blocks of different heights.
- The only element with a shadow is the bar tooltip, because it floats.
- The training page (`web/training-template.html`) reuses these tiles and styles; intervals are drawn as a block on an
  axis with a white mark at zero.

## Layout

16 px margins at every width, 12-column grid. On mobile the board switches to two columns; the
leaderboard is drawn with horizontal bars and the domains become rows.

## Motion

Moving yellow band (the main motion), bars that grow on entry, staggered entrances per section,
looping cow video. Everything stops with `prefers-reduced-motion`.

## Do / Don't

- Pair every figure with its chart; no chart without readable values or a tooltip.
- Do not use the yellow for anything other than the highlighted model or the action.
- Do not add gradients, thin lines, letter-spaced capitals or icon cards.
- The photos come from Wikimedia Commons; credits go in `web/assets/credits.json` and in the footer.
