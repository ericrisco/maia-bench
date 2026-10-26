# Format del dataset de coneixement

Cada fitxer `coneixement/<subtema>.jsonl` té una entrada per línia. Les entrades sobre fitxes reservades (que mai
entren a un entrenament) són a `coneixement/nv-*.jsonl`.

## Camps

| Camp | Tipus | Obligatori | Què és |
|---|---|---|---|
| `id` | text | sempre | `<subtema>/NNN`; per a les no vistes, `nv-<lot>/NNN` |
| `tipus` | `test` · `oberta` · `trampa` | sempre | Com es respon i es puntua |
| `domini`, `subtema` | text | sempre | On cau dins del corpus |
| `nivell` | 1 · 2 · 3 | sempre | 1 un fet · 2 relaciona dos fets · 3 necessita diversos articles |
| `pregunta` | text | sempre | Entenedora per ella sola; acaba en `?` |
| `opcions` | `{A,B,C,D}` | només `test` | Quatre opcions diferents i versemblants |
| `correcta` | `A`–`D` | només `test` | La lletra correcta |
| `context` | text | sempre | 40–400 paraules; explica amb detall els fets en què es basa la resposta |
| `resposta` | text | sempre | La resposta factual a partir del context |
| `fets_clau` | llista | `oberta`, `trampa` | Els fets que ha de contenir una resposta correcta |
| `errors_a_penalitzar` | llista | `oberta`, `trampa` | Afirmacions falses típiques; una resposta que n'inclou una no pot treure la nota màxima |
| `premissa_falsa` | text | només `trampa` | Què és fals de la pregunta i per què |
| `documents` | llista | sempre | Procedència interna (rutes dins de maia). No forma part de l'enunciat |
| `no_vista` | `true` | només no vistes | La font és una fitxa reservada |

## Tipus

- **test**: quatre opcions, una de correcta. Es corregeix automàticament, sense jutge.
- **oberta**: es respon amb text lliure. La puntua un jutge amb la resposta, els fets clau i els errors a penalitzar.
- **trampa**: la pregunta dona per bona una premissa **falsa** i un model ha de rebutjar-la, no inventar-se una
  resposta. La falsedat ha d'estar **demostrada** pel context: que una cosa no hi consti no la fa falsa.
- **no vista**: preguntes sobre fitxes que mai s'han fet servir per entrenar. Mesuren si el model s'inventa el que no sap.

## Regles

- Ni la pregunta, ni les opcions, ni el context, ni la resposta fan referència al corpus ni a les seves fitxes.
- Cap pregunta depèn d'una dada que caduca (lleis vigents, preus, càrrecs actuals, horaris).
- Cap pregunta demana una cosa que la font marca com a desconeguda o en discrepància.
- La lletra correcta es reparteix entre A, B, C i D.

## Exemple (illustratiu)

```json
{"id": "persones/001", "tipus": "oberta", "domini": "persones", "subtema": "persones", "nivell": 1,
 "pregunta": "Amb quants anys va competir Albert Llovera als Jocs d'hivern de Sarajevo i en quina disciplina?",
 "context": "Albert Llovera, nascut a Andorra la Vella el 1966, va participar als Jocs Olímpics d'hivern de Sarajevo del 1984 amb disset anys. Hi va competir en esquí alpí: va fer 48è al descens i no va acabar ni l'eslàlom gegant ni l'eslàlom. Era un dels dos esportistes de la delegació andorrana.",
 "resposta": "Hi va competir amb 17 anys, l'any 1984, en esquí alpí.",
 "fets_clau": ["17 anys", "Sarajevo 1984", "esquí alpí"],
 "errors_a_penalitzar": ["afirmar que va ser l'esportista més jove de la història dels Jocs d'hivern"],
 "documents": ["docs/temes/persones/albert-llovera.md"]}
```
