# maia-bench

Benchmark per mesurar **quant sap un model d'Andorra** i **com de bé parla andorrà**.

Neix del projecte [maia](https://github.com/ericrisco/maia) (Gemma 4 especialitzat en Andorra), però és independent:
serveix per avaluar qualsevol model.

> **Estat: en construcció.** El dataset de coneixement s'està escrivint; encara no hi ha resultats de cap model.

> **D'on surt el corpus:** vegeu [com s'ha creat el corpus](docs/origen-del-corpus.md): el procés, una foto amb recomptes i les seves limitacions.

## Què mesura

| Part | Pregunta | Correcció |
|---|---|---|
| **Coneixement** | Sap d'Andorra? S'inventa coses? | Test de 4 opcions (automàtic); respostes obertes i trampes (jutge LLM) |
| **Llengua** | Parla andorrà? | Perplexitat sobre parla real, test dialectal (automàtics) i prova cega amb andorrans (vots humans) |
| **Control** | Ha empitjorat en català general? | Subconjunt de CatalanBench |

La part de llengua **no usa un jutge LLM** per decidir si una resposta «sona andorrana»: un model no coneix bé aquesta
varietat, que és justament el que es vol mesurar.

## Dos nivells d'execució

| Nivell | Què inclou | Cost per a qui l'executa |
|---|---|---|
| **1. Sense jutge** | Test de 4 opcions, test dialectal, perplexitat | Només la seva GPU |
| **2. Amb jutge** | Preguntes obertes i trampes | Una clau d'un model jutge, configurable |

Els resultats **oficials** fan servir sempre el jutge fixat (model i versió anotats a cada publicació).

## Regles

1. **Versions congelades.** Un cop publicada, `v1` no es toca. Una correcció és una `v2`.
2. **Mai a l'entrenament.** Cap pregunta, ni el contingut reservat, pot entrar a un entrenament que s'avaluï amb aquest benchmark.
3. **Sense dades que caduquen:** ni lleis vigents, ni preus, ni càrrecs actuals, ni horaris.
4. **Mateixes condicions per a tots els models:** mateix prompt, temperatura 0.
5. **Contaminació.** Cada pregunta es compara amb les dades d'entrenament de maia i es descarta si s'hi assembla massa.

## Tot és públic

El benchmark es publica sencer: preguntes, contextos, respostes de referència, fets clau i codi. **No hi ha part privada**
(decidit el 2026-10-26; les proves privades es deixen per a altres benchmarks). La contaminació es mitiga amb versions
congelades, una marca de contaminació (*canary string*) i preguntes «no vistes» sobre fitxes que mai han entrat a un
entrenament. L'únic que **no** es pot publicar és el text de les peces de parla de la prova de perplexitat (les fonts no
en permeten la redistribució): se'n publica un manifest i un carregador.

## Pendent de decidir

- **Llicència** del codi i de les dades (depèn dels termes de les fonts del corpus).
- **Quan es fa públic el repositori** i on s'allotja la pàgina de resultats.

## Dataset de coneixement

Es construeix pregunta a pregunta (un commit per pregunta) a la branca `dataset`. Cada entrada té una pregunta, un
context detallat i la resposta de referència. Format a [`docs/format.md`](docs/format.md); es valida amb
`tools/valida.py`. Previstes: 925 preguntes (9 per subtema, i 2 «no vistes» per cada fitxa reservada).

## Documentació

- [Com s'ha creat el corpus](docs/origen-del-corpus.md)
- [Spec — què mesura el benchmark](docs/specs/andorranitat-benchmark.md)
- [Spec — plataforma: execució, resultats públics i part privada](docs/specs/maia-bench-platform.md)
- `reserva/` — els 41 articles i les 6 peces de parla que **no s'entrenen mai** (n'hi ha una còpia a maia, que han de coincidir).

## Estructura prevista

```
maia-bench/
├── coneixement/    un fitxer per subtema (test, obertes, trampes) i nv-*.jsonl (no vistes)
├── llengua/        dialectal, perplexitat (manifest), cega
├── reserva/        fitxes i peces de parla que no entren mai a un entrenament
├── tools/          valida.py, afegeix.py
└── avalua/         codi que passa el benchmark a un model i en treu la taula (pendent)
```
