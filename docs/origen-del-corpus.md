# Com s'ha creat el corpus d'on surt aquest benchmark

Aquest benchmark no avalua contra un coneixement abstracte d'Andorra: avalua contra **un corpus concret**, el de
[maia](https://github.com/ericrisco/maia). Per interpretar bé els resultats cal saber com es va fer aquest corpus i
quines limitacions té. Aquest document ho resumeix. El detall viu al projecte maia.

## El procés

1. **Cercar i registrar les fonts.** Les fonts són públiques (documents oficials, normativa, publicacions, premsa,
   arxius, material audiovisual). Cada font té una fitxa pròpia amb titular, URL, llicència declarada, si en permet la
   redistribució i la data de consulta. Una fitxa per **font**, no per document.
2. **Llegir i destil·lar.** Cada lectura queda registrada com a *unitat*: font, versió, localitzador (secció, pàgina),
   hash SHA-256 de la còpia llegida, estat (destil·lada o només llegida), article de destinació i feina pendent. El
   registre diu què es va llegir, no que tota la font estigui coberta. Es va treballar per tandes de domini (a la del
   13-09-2026: 446 unitats de desocupació, demografia, recurs hídric, pressupost, allaus, institucions, llengua, educació i
   relacions exteriors).
3. **Escriure els articles.** Els redacten agents d'IA a partir de les unitats llegides. Tots són `veu: compilada`: parlen
   **sobre** Andorra, no són llengua andorrana. Un article que no es pot fonamentar **no es publica**: es converteix en un
   buit registrat, no en text versemblant.
4. **Validar contra un contracte.** `CONTRACT.md` fixa els camps obligatoris (`veu`, `epoca`, `font`, `tema`…) i 14
   regles (R001–R014): camps absents, enllaços trencats, fonts inexistents, cites sense atribuir… La regla de llengua
   és mecànica: `apte_llengua = (veu == originària) i (època == contemporània)`.
5. **Parla.** A part, transcripcions literals de persones andorranes extretes de fonts audiovisuals públiques. Són
   `veu: originària`, i són l'única part del corpus que és llengua andorrana de debò. Les transcripcions són
   automàtiques i **no estan verificades contra l'àudio**.
6. **Tancament de la v1.** La recopilació inicial es va tancar el **24 de setembre de 2026** per instrucció del
   responsable del projecte. No és una publicació ni una certificació del contingut.

## La foto, a dia 26-10-2026

Recompte directe segons el camp `type` del frontmatter, sobre el commit `32c7797b3e` de maia.

| Unitat | Recompte |
| --- | ---: |
| Articles temàtics (`docs/temes/`) | 1.348 |
| Índexs de navegació (no compten com a contingut) | 129 |
| Dominis | 13 |
| Subtemes | 111 |
| Fitxes de font (`docs/fonts/`) | 664 |
| Documents de parla (`docs/parla/oral/`) | 40 (38 de veu originària, 2 compilats) |
| Corpus independent de parla (registres de persones) | 66 (3 en quarantena per qualitat) |

Els articles sumen uns 1,8 milions de paraules. Tots els articles temàtics són `veu: compilada`.

| Domini | Articles |
| --- | ---: |
| institucions | 350 |
| esports | 280 |
| historia | 241 |
| societat | 156 |
| economia | 104 |
| cultura | 83 |
| territori | 65 |
| llengua | 56 |
| persones | 44 |
| costums | 34 |
| politica | 24 |
| gastronomia | 22 |
| vida-quotidiana | 18 |

(Aquests recomptes de domini inclouen els índexs de cada carpeta.)

## Limitacions que afecten el benchmark

- **No s'ha verificat exhaustivament cada afirmació.** Que una pregunta tingui resposta al corpus no garanteix que la
  resposta sigui certa: per això cada pregunta es verifica contra el document de manera independent, però la veritat
  externa no es comprova.
- **Compilat per agents.** Els articles els escriu una IA. Un model que els aprengui aprèn el que diu el corpus, errors
  inclosos.
- **Cobertura desigual.** El nombre d'articles per domini no mesura la diversitat d'evidència: institucions i esports
  pesen molt, i hi ha dominis petits.
- **Llicències no normalitzades.** El camp de redistribució de les fitxes de font és text lliure en molts casos; no es
  pot resumir en «sí / no / pendent» sense normalitzar-lo. Per això aquest repositori deixa per decidir què es publica.
- **Absència no és negació.** Que una cosa no hi consti al corpus no vol dir que sigui falsa a Andorra. Per això les
  preguntes «trampa» només es fan sobre premisses demostrablement falses.
- **Dades que caduquen.** Lleis vigents, preus, càrrecs i horaris queden fora del benchmark.
- **Parla no verificada.** La transcripció és automàtica; una part és dubtosa i s'ha marcat.

## Pendent de completar pel responsable del projecte

La documentació del projecte no deixa constància de **quines eines o models de recerca profunda es van fer servir** per
localitzar i llegir les fonts, ni de quantes consultes es van fer. Només hi ha rastre de les sessions d'agents que van
llegir les fonts i van escriure els articles. Aquest apartat s'ha d'omplir amb el procés real; no s'ha volgut inventar.

## De corpus a benchmark

1. Les preguntes es generen per domini a partir dels articles, en tres nivells (un fet, relació entre dos articles,
   diversos articles).
2. Un segon agent, sense veure la resposta, intenta respondre només amb el document. Si no hi arriba, es descarta.
3. Cada pregunta es compara amb les dades d'entrenament de maia i es descarta si s'hi assembla massa.
4. Una part dels articles i de les peces de parla es **reserva** i no entra mai a l'entrenament.
5. Es congela com a `v1`. Una correcció és una `v2`.
