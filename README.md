# maia-bench

Benchmark per mesurar **quant sap un model d'Andorra** i **com de bé parla andorrà**.

Neix del projecte [maia](https://github.com/ericrisco/maia) (Gemma 4 especialitzat en Andorra), però és independent:
serveix per avaluar qualsevol model.

> **Estat: en construcció.** Encara no hi ha preguntes ni resultats. Aquest README descriu el que es vol construir.

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

## Pendent de decidir abans de publicar

- **Llicència** del repositori i de les dades (depèn dels termes de les fonts del corpus; encara no s'ha triat).
- **Quina part és pública.** Si les preguntes són públiques, els models futurs les veuran: es preveu reservar un tram
  privat i afegir una marca (*canary string*) per poder detectar contaminació.
- **Les peces de parla reservades** per a la perplexitat provenen de fonts amb redistribució `pendent` o `no`: no es
  poden publicar senceres.

## Estructura prevista

```
maia-bench/
├── coneixement/    test, obertes, trampes, no vistes
├── llengua/        dialectal, perplexitat, cega
└── avalua/         codi que passa el benchmark a un model i en treu la taula
```
