# DESIGN.md — pàgina de resultats de maia-bench

Registre del sistema visual de `web/` perquè els canvis futurs el mantinguin.

- **Direcció:** «The printed annual» (editorial-report, llavor 605962653): informe imprès a dues tintes, eix vertical
  al 42 % de l'amplada, pàgines de text alternades amb camps de color sencers.
- **Idea:** la pujada al Coma Pedrosa (2.942 m, el cim d'Andorra) és l'escala de les notes: 100 % = el cim.
- **Cosa viva:** «Prova-ho» — una pregunta a l'atzar i el que hi ha respost cada model, amb el veredicte del jutge.
- **Tipografia:** Hanken Grotesk 400/500, cinc mides (`--step-small`, `--step-body`, `--step-lead`, `--step-head`,
  `--step-display`). Sense negreta, sense majúscules espaiades, sense monoespai fora del codi.
- **Color:** proporcions de la paleta dealt, colors de la bandera: paper `#e3e3e0`, tinta blava `#0b3a9e`, camp
  vermell `#d50032` (també el botó), groc `#fedd00` només per a la barra del domini on el model falla més. Fotos en
  escala de grisos.
- **Peces:** botó rectangular sense arrodonir; cap ombra, cap degradat, cap línia fina; els fragments de producte
  porten `data-ui`.
- **Moviment:** el titular puja línia a línia en carregar; entrades escalonades per secció; barres que creixen;
  deriva lenta de la foto del Coma Pedrosa; tot desactivat amb `prefers-reduced-motion`.
- **Fotos:** Wikimedia Commons, crèdits a `web/assets/credits.json` i al peu de la pàgina.
