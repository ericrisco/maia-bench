---
type: spec
title: Spec — Plataforma maia-bench (dataset, execució i resultats públics)
description: Com es crea el dataset de referència, com qualsevol model s'avalua contra el benchmark de l'andorranitat i com es publiquen els resultats en una pàgina web. Tot el benchmark és públic.
tags: [sdd, spec, benchmark, avaluacio, maia-bench]
timestamp: 2026-10-26T12:00:00Z
topic: sdd
slug: maia-bench-platform
status: draft
---

# Spec — Plataforma maia-bench

> Slug: `maia-bench-platform` · Status: draft · Created: 2026-10-26
> Hereda: la constitució del projecte maia — principis 16 i 17.
> Complementa: [andorranitat-benchmark](./andorranitat-benchmark.md), que defineix **què es mesura**. Aquesta spec
> defineix **com s'executa i com es publica**. **Decisió del 2026-10-26: el benchmark és públic**, sense part privada.
> Repositori: [ericrisco/maia-bench](https://github.com/ericrisco/maia-bench) (privat, de moment; es farà públic).

## Problema i per què

El benchmark de l'andorranitat mesura dues coses: quant sap un model d'Andorra i com de bé parla andorrà. Tal com està
plantejat a `andorranitat-benchmark`, serveix per comparar maia amb Gemma base. No serveix perquè un tercer hi avaluï el
seu model, ni existeix cap lloc públic on es vegi quins models saben d'Andorra i parlen andorrà. Aquesta referència no
existeix avui.

Un benchmark públic té un risc conegut: **les preguntes obertes poden acabar a l'entrenament de models futurs**, que les
resoldran de memòria. S'ha decidit **assumir-lo** en lloc de mantenir una part privada (vegeu «Decisió: el benchmark és
públic»): el que no es pot protegir amb secret es mitiga amb versions, una marca de contaminació i preguntes sobre fitxes
mai entrenades.

## Cost de no construir-ho

Per a maia no es trenca res: el principi 17 es pot complir amb un script que ens passem a nosaltres mateixos. El que es
perd és que cap altre model quedi mesurat per la mateixa vara, i que el projecte no deixi cap referència reutilitzable
sobre Andorra. Si algú publica abans un benchmark pitjor, l'estàndard serà el seu.

## L'alternativa més barata

Un script que executem a mà i una taula al README. Cobreix la constitució per a maia i costa un dia. **No cobreix**
avaluar tercers, tenir una pàgina pública ni protegir-se de la contaminació. Si l'únic objectiu fos validar maia, seria
suficient. Aquesta spec existeix perquè volem una referència pública.

## Objectius

- Qualsevol persona pot avaluar un model amb el benchmark, i veure'n els resultats sense demanar permís.
- Una pàgina web pública mostra una taula de models amb les seves notes, i distingeix els que **surten d'Andorra**.
- Tot el benchmark és **públic**: preguntes, contextos, respostes de referència i codi.
- Cap resultat es pot falsificar enviant una nota: es puntua sempre al nostre costat, amb el mateix jutge fixat.
- Cada resultat porta la versió del benchmark, la del jutge i les condicions d'execució, i es pot reproduir.
- Les notes porten incertesa: dues notes que no es poden distingir estadísticament no es presenten com un empat resolt.

## No-objectius

- **No és un chat ni una demo en viu** d'un model.
- **No té comptes d'usuari ni base de dades**: la web és estàtica.
- **No dona una sola nota global** a la v1: dues notes principals (Coneixement i Llengua), mai sumades.
- **No executa codi enviat per tercers.** Només s'accepten dades.
- **No avalua models tancats amb claus d'altri.** Els models d'API que apareguin a la taula els executa el projecte amb
  les seves pròpies claus.
- **No substitueix la prova cega amb andorrans:** és part del benchmark, però necessita persones.
- **No entrena res** ni publica pesos.

## Usuaris i context

1. **Eric / el projecte maia**, que necessita demostrar que el fine-tune supera Gemma base (principi 17).
2. **Equips que fan models** (catalans, andorrans o generals), que volen saber com es comporten amb Andorra.
3. **Lectors de la pàgina**, que només volen saber quin model és millor per a Andorra.
4. **La comunitat lingüística**, per a qui un rànquing de «parla andorrà» és una referència que no existeix.

Conflicte d'interessos: maia és alhora el projecte que construeix el benchmark i un dels models que s'hi mesura. La pàgina
ho ha de dir i marcar-lo (`origen: Andorra · model del projecte`), i el mètode ha de ser públic.

## Decisió: el benchmark és públic

**Decidit per Eric el 2026-10-26.** Inicialment es va plantejar una part privada que decidís el rànquing. Es descarta: el
benchmark es publica sencer i les proves privades es deixen per a altres benchmarks. Conseqüències:

- **Es publica tot el dataset**: pregunta, opcions, context, resposta de referència, fets clau i errors a penalitzar.
- **Cap secret ni servidor privat de preguntes.** Tampoc cal cua d'execucions privades.
- **El rànquing el fa el mateix benchmark públic**, i qualsevol pot reproduir-lo.

### Com es mitiga la contaminació, ja que no s'amaga

| Risc | Mesura |
|---|---|
| Que models futurs entrenin amb les preguntes | Una marca de contaminació (*canary string*) a cada fitxer, perquè es pugui filtrar o detectar |
| Que la nota deixi de voler dir res amb el temps | Versions congelades (`v1`, `v2`…): una correcció o una renovació és una versió nova, i cada resultat porta la versió |
| Que un model hagi après les respostes, no el tema | Les preguntes «no vistes» sobre fitxes que mai han entrat a cap entrenament de maia |
| Que algú enviï notes falses | Mai s'accepten notes: es puntua sempre al nostre costat, amb el mateix jutge fixat |
| Que un PR de tercers llegeixi secrets | Les accions de PR de forks no reben secrets; no n'hi ha cap necessari per al nivell 1 |

### Una excepció que no depèn de la decisió: el text de parla

Les peces de parla reservades per a la **perplexitat** provenen de fonts amb redistribució `pendent` o `no`. Encara que el
benchmark sigui públic, **aquest text no es pot publicar**. Es publica només un **manifest** (identificador de la peça,
font, URL i hash) i un carregador que obté el text de l'origen. Qui no pugui obtenir-lo no té aquesta prova, i es
mostra com a no disponible.

### Qui l'executa

| Part | Què s'envia | Qui puntua |
|---|---|---|
| Test de 4 opcions, test dialectal | Un fitxer amb les respostes | Una acció automàtica, sense jutge |
| Obertes i trampes | Un fitxer amb les respostes | El jutge fixat, al costat del projecte |
| Perplexitat | Res: es calcula amb el manifest | Qui l'executa, amb el seu model |

## Dataset de referència (decidit el 2026-10-26)

El dataset de coneixement el **escrivim nosaltres**, llegint el corpus, no el genera un jutge ni un buscador:

- **Cada entrada:** pregunta, **context** detallat (60–200 paraules, amb les nostres paraules, sense referències al corpus)
  i la **resposta** que donaríem a partir d'aquest context. Format a `docs/format.md` del repositori.
- **Quantitat:** 9 preguntes per subtema (6 de test, 2 d'obertes i 1 de trampa), 6 si en té 2 articles i 3 si en té
  un, més 2 «no vistes» per cada una de les 41 fitxes reservades: **925** en total (843 + 82).
- **Escriptura:** agents del projecte, **una pregunta per commit**, validada automàticament abans de pujar-la.
- **Verificació independent:** un model d'una altra família (Gemini) intenta respondre només amb el context, sense veure
  la resposta; si no coincideix, la pregunta es descarta. A més, una mostra de ~100 la revisa una persona.
- **Límit:** la referència és *el que diu el corpus*, que és compilat per IA i no verificat afirmació per afirmació. El
  benchmark mesura si un model sap el que diu el corpus; la pàgina pública ho ha de dir.

## Flux d'enviament

**Nivell 1 — sense jutge.** Es descarreguen les preguntes, el model respon i s'envia un fitxer de respostes per
*pull request*. Una acció puntua les preguntes de test i el test dialectal, que són deterministes. Es publica el resultat.

**Nivell 2 — amb jutge.** Les preguntes obertes i trampes les puntua el jutge fixat (model i versió anotats). El jutge
rep la pregunta, la resposta de referència, els fets clau i la resposta del model, i retorna una nota de 0 a 2 i un motiu.
Temperatura 0 i dues passades; si no coincideixen, la resposta es marca per revisió humana.

**Límits del jutge (provat el 2026-10-26).** En una prova, el jutge va puntuar amb un 2 (correcta i completa) una
resposta que incloïa una afirmació **falsa afegida** («el més jove de la història dels Jocs d'hivern»), perquè només
tenia la referència i els fets clau, i la referència no deia que fos falsa. Un jutge no pot detectar un error que no
coneix. Conseqüència de disseny: cada pregunta ha de portar, a més dels fets clau, una llista d'**errors típics a
penalitzar** (afirmacions falses conegudes), i la nota 2 exigeix que no n'hi hagi cap.

**La llengua no la jutja una IA.** Que una resposta «soni andorrana» no es delega a un LLM, que no coneix bé aquesta
varietat. Es mesura amb la perplexitat, el test dialectal i els andorrans de la prova cega.

## Resultats i puntuació

Cada fila de resultats porta: model i versió exacta (hash de Hugging Face o nom i data d'API), mida, família, **origen**,
versió del benchmark, nivell executat (1 o 2), versió del jutge, dates, notes per part amb el **nombre de
preguntes** i un **interval de confiança** (remostreig o *bootstrap*), i la configuració d'execució (prompt, temperatura).

- Cap nota única. Es mostren **Coneixement** i **Llengua**, i el control com a avís (una caiguda marcada es ressalta).
- Si els intervals de dos models se solapen, la pàgina no els ordena com si un fos millor.

## Pàgina pública

Pàgina estàtica generada a partir dels fitxers de resultats; sense servidor, comptes ni base de dades. Mostra una taula
filtrable per família, mida i origen; un selector de versió del benchmark; i, a cada fila, quin nivell s'ha executat i amb
quin jutge. Un text visible explica com es va crear el corpus i quines limitacions té
([origen del corpus](https://github.com/ericrisco/maia-bench/blob/main/docs/origen-del-corpus.md)).

## Cost i infraestructura

- Google Cloud: projecte `maia-andorra`, facturació MAIA (crèdit disponible: **no verificat**).
  **Jutge:** `google/gemini-3.8-flash` respon (HTTP 200) pel **endpoint compatible amb OpenAI** de Vertex
  (`/endpoints/openapi/chat/completions`, `location=global`), comprovat el 2026-10-26. La ruta nativa `generateContent`
  dona 404 per a tots els models provats, i `gemini-2.5-flash` també dona 404 per les dues rutes. Cal fixar el jutge amb
  aquesta ruta. Cost mesurat en un cas curt: ~400–450 tokens per crida (raonament inclòs).
  **GPU:** el 2026-10-26 la quota global és d'**1 GPU** (aprovada) i la **L4** a europe-west4 està concedida; la
  **A100 80 GB** va ser denegada. Per al 31B cal una L4 amb 4 bits, o tornar a demanar la A100 amb més justificació.
- Cada execució té un **pressupost màxim** i s'apaga sola en acabar. Cap màquina amb GPU queda encesa sense feina.
- Les execucions de models amb pesos que fa el projecte tenen un màxim mensual, perquè el cost no depengui de qui demani.

## Llicències i drets

- Llicència del codi i de les dades: **no triada**. Depèn dels termes de les fonts del corpus.
- Les peces de parla reservades **no es poden publicar** (redistribució `pendent`/`no`): només el manifest i el carregador.
- Com que el dataset és públic, el **context** i la **resposta** de cada pregunta han d'estar escrits amb paraules pròpies i
  no copiar text d'una font de redistribució limitada. És una regla de l'escriptura i es revisa en la mostra humana.

## Criteris d'acceptació

- [ ] Existeix el dataset de referència congelat com a `v1` (925 preguntes previstes), amb cada entrada validada.
- [ ] El repositori **no conté** text de les peces de parla reservades, només el manifest.
- [ ] Un tercer pot avaluar un model amb el nivell 1 seguint només el README, sense claus nostres.
- [ ] Una resposta enviada per PR es puntua sense accedir a cap secret.
- [ ] Una nota enviada manualment per un tercer és ignorada (només es puntuen respostes).
- [ ] Cada fila publicada porta versió del benchmark, del jutge, nombre de preguntes i interval de confiança.
- [ ] La pàgina web es genera dels fitxers de resultats i mostra l'origen de cada model.
- [ ] Cap execució amb GPU supera el pressupost màxim ni queda encesa.
- [ ] Els resultats de dos models base (Gemma 4 E4B i 31B) estan publicats abans de cap fine-tune.

## Decisions obertes

1. ~~Proporció pública/privada.~~ **Resolta el 2026-10-26: tot públic.**
2. **Qui pot enviar models**: qualsevol persona o només els aprovats pel projecte.
3. **Quan es fa públic el repositori** i on s'allotja la web (GitHub Pages).
4. **Jutge**: `gemini-3.8-flash` funciona pel endpoint OpenAI-compatible; decidir si és el que es fixa o si es prefereix un model de gama *pro*, i com es detecten les afirmacions falses afegides (vegeu «Límits del jutge»).
5. **Llicència** del codi i de les dades.
6. **Votants de la prova cega** (5–10 andorrans) i qui revisa la mostra de 100 preguntes.
7. ~~Quota de GPU.~~ **Parcial:** global 1 i L4 concedides; A100 denegada.
