# Knowledge dataset format

Each file `knowledge/<subtopic>.jsonl` has one entry per line. Entries about holdout fact sheets (which never
enter a training run) are in `knowledge/unseen-*.jsonl`.

## Fields

| Field | Type | Required | What it is |
|---|---|---|---|
| `id` | text | always | `<subtopic>/NNN`; for unseen questions, `unseen-<batch>/NNN` |
| `type` | `multiple_choice` · `open` · `trap` | always | How it is answered and scored |
| `domain`, `subtopic` | text | always | Where it falls within the corpus |
| `level` | 1 · 2 · 3 | always | 1 one fact · 2 relates two facts · 3 needs several articles |
| `question` | text | always | Understandable on its own; ends in `?` |
| `options` | `{A,B,C,D}` | `multiple_choice` only | Four distinct, plausible options |
| `correct` | `A`–`D` | `multiple_choice` only | The correct letter |
| `context` | text | always | 40–400 words; explains in detail the facts the answer is based on |
| `reference_answer` | text | always | The factual answer drawn from the context |
| `key_facts` | list | `open`, `trap` | The facts a correct answer must contain |
| `errors_to_penalise` | list | `open`, `trap` | Typical false claims; an answer that includes one cannot get the top score |
| `false_premise` | text | `trap` only | What is false in the question and why |
| `documents` | list | always | Internal provenance (paths inside maia). Not part of the question |
| `unseen` | `true` | unseen only | The source is a holdout fact sheet |

## Types

- **multiple_choice**: four options, one correct. Scored automatically, without a judge.
- **open**: answered with free text. A judge scores it using the reference answer, the key facts and the errors to penalise.
- **trap**: the question takes a **false** premise for granted and a model must reject it, not make up an
  answer. The falsehood must be **proven** by the context: something not being mentioned does not make it false.
- **unseen**: questions about fact sheets that have never been used for training. They measure whether the model makes up what it does not know.

## Rules

- Neither the question, nor the options, nor the context, nor the answer refer to the corpus or its fact sheets.
- No question depends on data that expires (laws in force, prices, current office-holders, timetables).
- No question asks for something the source marks as unknown or disputed.
- The correct letter is spread across A, B, C and D.

## Example (illustrative)

```json
{"id": "people/001", "type": "open", "domain": "people", "subtopic": "people", "level": 1,
 "question": "Amb quants anys va competir Albert Llovera als Jocs d'hivern de Sarajevo i en quina disciplina?",
 "context": "Albert Llovera, nascut a Andorra la Vella el 1966, va participar als Jocs Olímpics d'hivern de Sarajevo del 1984 amb disset anys. Hi va competir en esquí alpí: va fer 48è al descens i no va acabar ni l'eslàlom gegant ni l'eslàlom. Era un dels dos esportistes de la delegació andorrana.",
 "reference_answer": "Hi va competir amb 17 anys, l'any 1984, en esquí alpí.",
 "key_facts": ["17 anys", "Sarajevo 1984", "esquí alpí"],
 "errors_to_penalise": ["afirmar que va ser l'esportista més jove de la història dels Jocs d'hivern"],
 "documents": ["docs/temes/persones/albert-llovera.md"]}
```
