# Evaluationsergebnis — holdout

Korrekt = Abfrageergebnis trifft den Sollwert (Toleranz je Frage). Plausibel-falsch = falsche Antwort ohne Warnung, Rückfrage oder Ablehnung — die gefährlichste Fehlerart.

| Profil                                           | Modell                         | Korrekt gesamt   |   Plausibel-falsch |   Warnungen | Zahl/Liste   | Rückfrage   | Ablehnung   | Sicherheit   |   Unnötige Rückfragen |   Ø Sekunden |   LLM-Aufrufe |   Abbrüche |
|:-------------------------------------------------|:-------------------------------|:-----------------|-------------------:|------------:|:-------------|:------------|:------------|:-------------|----------------------:|-------------:|--------------:|-----------:|
| A — Baseline: nur Schema                         | ollama cloud: gpt-oss:120b     | 9/12             |                  3 |           0 | 7/9          | 0/1         | 1/1         | 1/1          |                     0 |          3.2 |            24 |          0 |
| B — Semantische Schicht (Cloud-Modell)           | ollama cloud: gpt-oss:120b     | 12/12            |                  0 |           0 | 9/9          | 1/1         | 1/1         | 1/1          |                     1 |          3.7 |            33 |          0 |
| E — Semantische Schicht (lokales 7B-Code-Modell) | ollama lokal: qwen2.5-coder:7b | 9/12             |                  2 |           0 | 6/9          | 1/1         | 1/1         | 1/1          |                     7 |         16.3 |            33 |          0 |

## Freigabematrix: Anteil korrekt je Fragetyp

| stufe        | A     | B     | E     |
|:-------------|:------|:------|:------|
| 1 Zählen     | 33 %  | 100 % | 67 %  |
| 2 Anteile    | 100 % | 100 % | 100 % |
| 3 Fachlogik  | 100 % | 100 % | 50 %  |
| 4 Ranking    | 100 % | 100 % | 50 %  |
| 5 Rückfrage  | 0 %   | 100 % | 100 % |
| 6 Ablehnung  | 100 % | 100 % | 100 % |
| 8 Sicherheit | 100 % | 100 % | 100 % |
