# Evaluationsergebnis — goldset

Korrekt = Abfrageergebnis trifft den Sollwert (Toleranz je Frage). Plausibel-falsch = falsche Antwort ohne Warnung, Rückfrage oder Ablehnung — die gefährlichste Fehlerart.

| Profil                                   | Modell                     | Korrekt gesamt   |   Plausibel-falsch |   Warnungen | Zahl/Liste   | Rückfrage   | Ablehnung   | Sicherheit   |   Unnötige Rückfragen |   Ø Sekunden |   LLM-Aufrufe |   Abbrüche |
|:-----------------------------------------|:---------------------------|:-----------------|-------------------:|------------:|:-------------|:------------|:------------|:-------------|----------------------:|-------------:|--------------:|-----------:|
| A — Baseline: nur Schema                 | ollama cloud: gpt-oss:120b | 33/42            |                  7 |           0 | 29/33        | 0/3         | 2/4         | 2/2          |                     0 |          3.5 |            78 |          0 |
| B — Semantische Schicht (Cloud-Modell)   | ollama cloud: gpt-oss:120b | 41/42            |                  1 |           2 | 32/33        | 3/3         | 4/4         | 2/2          |                     0 |          4.3 |           114 |          0 |
| C — Semantische Schicht (lokales Modell) | ollama lokal: llama3.2     | 7/39             |                 17 |           2 | 6/31         | 0/3         | 0/3         | 1/2          |                    32 |         15   |           136 |          3 |

## Freigabematrix: Anteil korrekt je Fragetyp

| stufe        | A     | B     | C    |
|:-------------|:------|:------|:-----|
| 1 Zählen     | 88 %  | 88 %  | 57 % |
| 2 Anteile    | 75 %  | 100 % | 0 %  |
| 3 Fachlogik  | 88 %  | 100 % | 14 % |
| 4 Ranking    | 100 % | 100 % | 12 % |
| 5 Rückfrage  | 0 %   | 100 % | 0 %  |
| 6 Ablehnung  | 50 %  | 100 % | 0 %  |
| 7 Robustheit | 100 % | 100 % | 0 %  |
| 8 Sicherheit | 100 % | 100 % | 50 % |
