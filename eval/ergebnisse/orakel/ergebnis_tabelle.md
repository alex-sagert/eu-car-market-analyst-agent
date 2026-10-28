# Evaluationsergebnis — goldset

Korrekt = Abfrageergebnis trifft den Sollwert (Toleranz je Frage). Plausibel-falsch = falsche Antwort ohne Warnung, Rückfrage oder Ablehnung — die gefährlichste Fehlerart.

| Profil                                   | Modell              | Korrekt gesamt   |   Plausibel-falsch |   Warnungen | Zahl/Liste   | Rückfrage   | Ablehnung   | Sicherheit   |   Unnötige Rückfragen |   Ø Sekunden |   LLM-Aufrufe |   Abbrüche |
|:-----------------------------------------|:--------------------|:-----------------|-------------------:|------------:|:-------------|:------------|:------------|:-------------|----------------------:|-------------:|--------------:|-----------:|
| A — Baseline: nur Schema                 | orakel (Testdouble) | 39/42            |                  3 |           0 | 33/33        | 0/3         | 4/4         | 2/2          |                     0 |            0 |            78 |          0 |
| B — Semantische Schicht (Cloud-Modell)   | orakel (Testdouble) | 42/42            |                  0 |           0 | 33/33        | 3/3         | 4/4         | 2/2          |                     0 |            0 |           114 |          0 |
| C — Semantische Schicht (lokales Modell) | orakel (Testdouble) | 42/42            |                  0 |           0 | 33/33        | 3/3         | 4/4         | 2/2          |                     0 |            0 |           114 |          0 |
| D — Baseline lokal: nur Schema           | orakel (Testdouble) | 39/42            |                  3 |           0 | 33/33        | 0/3         | 4/4         | 2/2          |                     0 |            0 |            78 |          0 |

## Freigabematrix: Anteil korrekt je Fragetyp

| stufe        | A     | B     | C     | D     |
|:-------------|:------|:------|:------|:------|
| 1 Zählen     | 100 % | 100 % | 100 % | 100 % |
| 2 Anteile    | 100 % | 100 % | 100 % | 100 % |
| 3 Fachlogik  | 100 % | 100 % | 100 % | 100 % |
| 4 Ranking    | 100 % | 100 % | 100 % | 100 % |
| 5 Rückfrage  | 0 %   | 100 % | 100 % | 0 %   |
| 6 Ablehnung  | 100 % | 100 % | 100 % | 100 % |
| 7 Robustheit | 100 % | 100 % | 100 % | 100 % |
| 8 Sicherheit | 100 % | 100 % | 100 % | 100 % |
