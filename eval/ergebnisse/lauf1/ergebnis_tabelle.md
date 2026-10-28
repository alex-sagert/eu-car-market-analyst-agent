# Evaluationsergebnis — goldset

Korrekt = Abfrageergebnis trifft den Sollwert (Toleranz je Frage). Plausibel-falsch = falsche Antwort ohne Warnung, Rückfrage oder Ablehnung — die gefährlichste Fehlerart.

| Profil                                   | Modell                     | Korrekt gesamt   |   Plausibel-falsch |   Warnungen | Zahl/Liste   | Rückfrage   | Ablehnung   | Sicherheit   |   Unnötige Rückfragen |   Ø Sekunden |   LLM-Aufrufe |   Abbrüche |
|:-----------------------------------------|:---------------------------|:-----------------|-------------------:|------------:|:-------------|:------------|:------------|:-------------|----------------------:|-------------:|--------------:|-----------:|
| A — Baseline: nur Schema                 | ollama cloud: gpt-oss:120b | 27/38            |                  9 |           0 | 23/30        | 0/2         | 2/4         | 2/2          |                     0 |          5.1 |            78 |          4 |
| B — Semantische Schicht (Cloud-Modell)   | ollama cloud: gpt-oss:120b | 35/41            |                  0 |           6 | 26/32        | 3/3         | 4/4         | 2/2          |                     0 |          5.1 |           105 |          1 |
| C — Semantische Schicht (lokales Modell) | ollama lokal: llama3.2     | 7/26             |                 10 |           6 | 6/19         | 1/3         | 0/4         | –            |                    20 |         16.6 |           103 |         16 |

## Freigabematrix: Anteil korrekt je Fragetyp

| stufe        | A     | B     | C      |
|:-------------|:------|:------|:-------|
| 1 Zählen     | 75 %  | 88 %  | 57 %   |
| 2 Anteile    | 71 %  | 62 %  | 0 %    |
| 3 Fachlogik  | 57 %  | 100 % | 100 %  |
| 4 Ranking    | 100 % | 75 %  | 0 %    |
| 5 Rückfrage  | 0 %   | 100 % | 33 %   |
| 6 Ablehnung  | 50 %  | 100 % | 0 %    |
| 7 Robustheit | 100 % | 100 % | 0 %    |
| 8 Sicherheit | 100 % | 100 % | <NA> % |
