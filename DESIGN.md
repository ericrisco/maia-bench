---
name: maia-bench
description: El Coma Pedrosa (2.942 m) és el 100 %; cada model és una barra que s'aixeca des del peu fins a la seva nota.
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
spacing: { margin: "16px", gap: "8px (6px al mòbil)", section: "160px (112px al mòbil)" }
direction: { id: "dense-tiles", seed: 448745881 }
---

# DESIGN.md — pàgina de resultats de maia-bench

## Overview

Pàgina pública de resultats (mode Persuade, però amb els gràfics com a protagonistes, a petició d'Eric: «més
tecnològica, que siguin gràfics»). Direcció «The well-kept board»: tota la pàgina és un tauler fosc de rajoles
plenes, de vora a vora, amb 8 px de separació. Substitueix «The printed annual» (llavor 605962653), que era clara i
editorial.

- **Idea:** el cim del Coma Pedrosa és el 100 %. A la primera pantalla, el fons fosc de cada columna és el cim i la
  barra n'és la nota; a la classificació, les barres s'aixequen des del peu i l'etiqueta «Cim · 2.942 m · 100 %» marca
  el sostre.
- **Cosa viva:** «Prova-ho»: una pregunta a l'atzar amb la resposta i el veredicte de cada model.

## Colors

Fons negre suau, rajoles un pas més clares, tinta blanca. Un sol accent, el groc de la bandera: el model primer (barra,
fila oberta de la taula), el model triat als dominis, el botó i la faixa en moviment. El blau i el vermell de la bandera
només com a camps sencers (etapes del mètode, resposta de referència, «incorrecta», el peu). Un domini on el model triat
falla més es marca amb el camp `#2a1a1d`. Fotos en escala de grisos.

## Typography

General Sans 400/500/700, cinc mides: `--step-small`, `--step-body`, `--step-lead`, `--step-head` i la de display
(la franja del nom, la xifra gran i la faixa). Xifres tabulars a tot arreu on hi ha números. Monoespai només dins
`<code>`.

## Components

- Rajoles plenes, sense vora ni ombra. Cantonades rectes; només els extrems de les barres porten 4 px.
- Gràfics en HTML i CSS amb `data-ui`: les alçades surten de `--v` (nota 0–1), l'interval de `--lo`/`--hi`.
- La taula és un tauler de files `<details name="taula">`; la fila oberta es pinta groga.
- FAQ amb `<details name="faq">`, una oberta cada vegada; el signe més són dues barres de 3 px.
- Peu: el nom construït amb blocs de colors d'alçades diferents.
- L'únic element amb ombra és el tooltip de les barres, perquè flota.

## Layout

Marges de 16 px a totes les amplades, graella de 12 columnes. Al mòbil el tauler passa a dues columnes; la
classificació es dibuixa amb barres horitzontals i els dominis passen a files.

## Motion

Faixa groga en moviment (el moviment principal), barres que creixen en entrar, entrades escalonades per secció,
vídeo de vaques en bucle. Tot s'atura amb `prefers-reduced-motion`.

## Do / Don't

- Fes que cada xifra vagi amb el seu gràfic; cap gràfic sense valors llegibles o tooltip.
- No facis servir el groc per a res que no sigui el model destacat o l'acció.
- No hi posis degradats, línies fines, majúscules espaiades ni targetes amb icona.
- Les fotos són de Wikimedia Commons; els crèdits van a `web/assets/credits.json` i al peu.
