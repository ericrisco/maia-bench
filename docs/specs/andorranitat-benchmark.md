---
type: spec
title: Spec — Benchmark de l'andorranitat
description: Què mesura el benchmark que compara Gemma 4 base amb maia (coneixement d'Andorra i parla andorrana), com es protegeix de la contaminació i on s'executa.
tags: [sdd, spec, benchmark, avaluacio, gemma-4]
timestamp: 2026-10-20T09:00:00Z
topic: sdd
slug: andorranitat-benchmark
status: draft
---

# Spec — Benchmark de l'andorranitat

> Slug: `andorranitat-benchmark` · Status: draft · Created: 2026-10-20
> Hereda: la constitució del projecte maia — principis 11, 12, 16 i 17.
> Contracte de destí: l'spec `andorran-gemma-finetune` del projecte maia.

## Problema i per què

El projecte entrena Gemma 4 perquè **sàpiga d'Andorra** i perquè **parli andorrà**. Sense una mesura
fixada abans d'entrenar no es pot demostrar cap de les dues coses: qualsevol millora seria una impressió.
La constitució ho exigeix (principi 16: conjunt reservat mai vist en entrenament i validació amb parlants
nadius; principi 17: un fine-tune que no supera el base no es publica).

## Què es compara

Quatre models, amb les mateixes preguntes i la mateixa configuració (temperatura 0, mateix prompt):

| | Base | Fine-tune |
|---|---|---|
| Petit | Gemma 4 **E4B** (dens, cap al mòbil) | maia-E4B |
| Gran | Gemma 4 **31B** (dens) — *o 26B A4B MoE, decisió oberta* | maia-31B |

Gemma 4 té quatre mides: E2B, E4B, 26B A4B (MoE: 25,2B totals, 3,8B actius) i 31B (dens). Llicència
Apache 2.0 (abril del 2026).

## Les tres parts del benchmark

### 1. Coneixement — «sap d'Andorra?»

| Tipus | Què mesura | Correcció | Mida |
|---|---|---|---|
| Test de 4 opcions | Ha après el fet | Automàtica, exacta | ~600 |
| Resposta oberta curta | Ho sap explicar | Jutge LLM amb resposta de referència i rúbrica | ~300 |
| Trampes | No s'inventa res | Puntua negar la premissa falsa o dir que no se sap | ~100 |

- Repartit entre els 13 dominis de `docs/temes/`, proporcional al nombre d'articles, amb un mínim per domini.
- Tres nivells: un fet · relació entre dues fitxes · raonament amb diverses fitxes.
- **Sense fets que caduquen** (principi 11): ni lleis vigents, ni preus, ni càrrecs actuals, ni horaris.

### 2. Llengua — «parla andorrà?»

| Prova | Què mesura | Correcció | Mida |
|---|---|---|---|
| Perplexitat sobre parla real | Com de natural li resulta l'andorrà autèntic | Automàtica | Peces de Parla reservades (~10–15% de les paraules) |
| Elecció dialectal | Coneix les formes andorranes | Test, automàtica | ~200, des de `temes/llengua/` |
| Prova cega amb andorrans | Sona andorrà de debò | Vots humans, A/B a cegues | ~150 parells, 5–10 persones |

La prova cega es prepara ara (prompts, protocol i rúbrica). Les respostes només es poden generar quan
existeixin els models entrenats.

### 3. Control — «no ha empitjorat?»

Un benchmark general de català (CatalanBench, a `lm-evaluation-harness`) per detectar oblit catastròfic.

## Contaminació: la regla que ho sosté tot

1. **Fitxes reservades (~3%, ~40 articles):** no entren mai a l'entrenament. Serveixen per mesurar si el
   model s'inventa coses quan no les sap.
2. **Peces de Parla reservades (4–5, de parlants i temes diferents):** no entren mai a l'entrenament.
   **Cal decidir-les abans d'exportar Parla.**
3. **Preguntes noves:** les preguntes de coneixement sobre fitxes entrenades estan redactades de nou i es
   comproven contra els 19.421 registres de `training-data/datasets/`. Si una s'hi assembla massa, es descarta.
4. **Congelat abans d'entrenar:** el benchmark porta versió (`v1`) i no es toca. Una correcció és una `v2`.

## On viu

- **Actualitzat el 2026-10-26:** el benchmark té repositori propi, [`ericrisco/maia-bench`](https://github.com/ericrisco/maia-bench)
  (carpeta `03-PROJECTS/maia-bench`). Com s'executa, com es publica i què queda privat és a
  [maia-bench-platform](./maia-bench-platform.md).
- **Actualitzat el 2026-10-27:** la reserva viu a `reserva/` d'aquest repositori (`fitxes.txt` i `parla.txt`). maia en
  té una còpia a `training-data/excloses-benchmark.txt`, que és la que llegeix l'exportador. **Les dues han de coincidir.**

## Infraestructura (Google Cloud)

- Projecte **`maia-andorra`**, vinculat a la billing account **MAIA** (`01AB95-BF27B5-6545A2`, EUR, oberta).
  APIs actives: Compute Engine, Vertex AI, Cloud Storage. Crèdit disponible: ~1.000 USD.
- **Quota de GPU = 0** (`GPUS_ALL_REGIONS`). Cal demanar-ne l'augment abans d'encendre res.
- Necessitats aproximades:
  - E4B: 1× L4 (24 GB) n'hi ha prou per avaluar i per fer QLoRA.
  - 31B: 1× A100 80 GB o H100 80 GB per avaluar en bf16 i per fer QLoRA.
- Jutge LLM: un model Gemini a Vertex AI, amb la versió fixada, al mateix projecte.
- Regla de cost: cap màquina amb GPU queda encesa sense feina; s'apaga en acabar cada execució.

## Criteris d'acceptació

- [ ] Llista de fitxes i peces reservades, congelada i exclosa de l'export.
- [ ] ~1.000 preguntes de coneixement, amb resposta de referència, domini, nivell i fitxes de suport.
- [ ] Cap pregunta del benchmark té un duplicat proper als datasets d'entrenament.
- [ ] Una mostra de 100 preguntes revisada per una persona, amb menys d'un 3% d'errors.
- [ ] ~200 preguntes d'elecció dialectal amb forma andorrana i forma estàndard documentades al corpus.
- [ ] Prompts, protocol i rúbrica de la prova cega preparats.
- [ ] Codi que passa el benchmark a un model i en treu la taula comparativa.
- [ ] Resultat dels dos models base registrat abans de cap fine-tune.

## Fora d'abast (per ara)

- La pàgina web del benchmark i de la prova cega. Es decideix quan les dades estiguin fetes.
- L'entrenament.

## Decisions obertes (clarify)

1. Model gran: **31B dens** (fine-tune més simple, més capacitat) o **26B A4B MoE** (inferència més barata)?
2. Quines peces de Parla es reserven?
3. Qui revisa la mostra de 100 preguntes, i qui són els votants de la prova cega?
4. Es demana ja l'augment de quota de GPU, i a quina regió (Europa)?
