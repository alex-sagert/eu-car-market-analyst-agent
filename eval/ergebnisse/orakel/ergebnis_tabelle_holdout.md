# Evaluationsergebnis — holdout

Korrekt = Abfrageergebnis trifft den Sollwert (Toleranz je Frage). Plausibel-falsch = falsche Antwort ohne Warnung, Rückfrage oder Ablehnung — die gefährlichste Fehlerart.

| Profil                                 | Modell              | Korrekt gesamt   |   Plausibel-falsch |   Warnungen | Zahl/Liste   | Rückfrage   | Ablehnung   | Sicherheit   |   Unnötige Rückfragen |   Ø Sekunden |   LLM-Aufrufe |   Abbrüche |
|:---------------------------------------|:--------------------|:-----------------|-------------------:|------------:|:-------------|:------------|:------------|:-------------|----------------------:|-------------:|--------------:|-----------:|
| B — Semantische Schicht (Cloud-Modell) | orakel (Testdouble) | 12/12            |                  0 |           0 | 9/9          | 1/1         | 1/1         | 1/1          |                     0 |            0 |            32 |          0 |

## Freigabematrix: Anteil korrekt je Fragetyp

| stufe        | B     |
|:-------------|:------|
| 1 Zählen     | 100 % |
| 2 Anteile    | 100 % |
| 3 Fachlogik  | 100 % |
| 4 Ranking    | 100 % |
| 5 Rückfrage  | 100 % |
| 6 Ablehnung  | 100 % |
| 8 Sicherheit | 100 % |
