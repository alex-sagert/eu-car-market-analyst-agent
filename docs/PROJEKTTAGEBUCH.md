# Projekttagebuch

Jede Änderung mit Lauf, Befund und Grund. Verbesserungen nur anhand des Goldsets;
das Holdout-Set läuft genau einmal am Ende.

---

## Mo 26.10.2026 — Aufbau

- Datenbasis aus 37,1 Mio. EEA-Zeilen mit den Regeln des BI-Projekts aggregiert:
  `zulassungen_monat` 191.227 und `zulassungen_jahr` 24.557 Zeilen — identisch mit der Gold-Schicht
  von eu-ev-tariff-detour. Kernzahl reproduziert: PHEV-Anteil chinesischer Marken 14,87 % → 46,14 %.
- Goldset 42 Fragen, Holdout 12 Fragen; Sollwerte per Referenz-SQL vor dem ersten Lauf festgelegt.
- Orakel-Test (Testdouble statt LLM): B 42/42, A 39/42 (A fragt nie nach — so gewollt).

## Mo 26.10.2026 — Lauf 1 (Desktop)

Ergebnis: `eval/ergebnisse/lauf1/ergebnis_tabelle.md`

| Profil | Korrekt | Plausibel-falsch | Abbrüche | Auffällig |
|---|---|---:|---:|---|
| A — nur Schema, gpt-oss:120b | 27/38 | **9** | 4 | erfindet Werte, meldet NULL/0 als Ergebnis |
| B — semantische Schicht, gpt-oss:120b | 35/41 | **0** | 1 | 6 beantwortbare Fragen abgelehnt |
| C — semantische Schicht, llama3.2 lokal | 7/26 | 10 | 16 | 20 unnötige Rückfragen, JSON-Fehler |

**Befunde Baseline A (plausibel-falsch, ohne jede Warnung):**
- G37: „Im Jahr 2025 wurden in Polen **0** Elektroautos neu zugelassen.“ — Polen ist nicht im Datensatz.
- G38: Prognose 2030 → „0“.
- G06: erfindet die Antriebsklasse `KBA_PLUG_IN_HYBRID`, Ergebnis NULL, wird als Antwort ausgegeben.
- G07: 2026 aus der co2cars-Tabelle (endet 2025) → NULL.
- G33: China „eng ODER weit“ → 4,9 % statt 2,4 % (eng) — rät die Definition, statt nachzufragen.
- G35: BMW ohne Land → Summe über sechs Länder (467.563) statt Rückfrage.
- G10, G12, G21: falsche Begriffsabgrenzung (HEV, „Elektroauto“ = BEV, PHEV vs. BEV+PHEV).

**Befunde B:**
- 0 plausibel-falsch, alle drei Rückfragen richtig gestellt, alle vier Ablehnungen richtig.
- 6 unnötige Ablehnungen (G08, G12, G13, G14, G27, G31): Die Einordnung sah nur den Datenumfang
  „Pkw-Neuzulassungen“, nicht die Merkmale (Modell, Masse, Leistung). Begründung z. B. G12:
  „Die verfügbaren Daten enthalten nur Neuzulassungszahlen, nicht das durchschnittliche Gewicht.“
- Zahlenprüfung schlug 6-mal an, Ergebnis jeweils korrekt:
  - 3× Rundung durch das LLM: Ergebnis 41,3479 wurde mit zwei Nachkommastellen als „41,35“ übergeben,
    das Modell schrieb „41,4“ (Doppelrundung — Fehler der Aufbereitung, nicht des Modells).
  - 2× vom LLM selbst berechnete Anteile innerhalb der Top-3 (G25, G26) — Verstoß gegen
    „LLM rechnet nicht“, richtig erkannt.
  - 1× **erfundene Aussage** (G32): „MG … entspricht 100,0 % aller chinesischen Neuzulassungen“ —
    richtig erkannt.

**Befunde Harness (Fehler der eigenen Pipeline):**
- `gpt-oss:120b` baute das im Prompt übergebene JSON-Schema nach (`{"sql": {"description": …}}`)
  → 5 Abbrüche in A und B.
- `llama3.2` lieferte `null` statt Liste, Liste statt Text, fehlende Felder, abgeschnittenes JSON.

## Änderungen für Lauf 2 (einzige Verbesserungsrunde)

| # | Änderung | betrifft | Art |
|---|---|---|---|
| 1 | JSON-Vorlage statt Schema-Dump im Prompt; tolerantes Parsen (erstes Objekt, gespiegelte Felder, `null`/Liste) | alle Profile | Harness |
| 2 | Datenumfang im Katalog nennt die Merkmale (Modell, Masse, CO₂, Strom, Leistung, Haltergruppen) | B, C | semantische Schicht |
| 3 | Ergebnis wird dem LLM vorgerundet übergeben (1 Nachkommastelle); Anweisung „nichts selbst rechnen“ | alle Profile | Antwortknoten |

Lauf 1 bleibt unverändert in `eval/ergebnisse/lauf1/` als Beleg.

## Mo 26.10.2026 — Lauf 2 (Desktop, nach der Verbesserungsrunde)

Ergebnis: `eval/ergebnisse/lauf2/ergebnis_tabelle.md`

| Profil | Korrekt | Plausibel-falsch | Rückfrage | Ablehnung | Sicherheit | Ø Sek. |
|---|---|---:|---|---|---|---:|
| A — nur Schema, gpt-oss:120b | 33/42 | 7 | 0/3 | 2/4 | 2/2 | 3,5 |
| B — semantische Schicht, gpt-oss:120b | 41/42 | 1 | 3/3 | 4/4 | 2/2 | 4,3 |
| C — semantische Schicht, llama3.2 | 7/39 | 17 | 0/3 | 0/3 | 1/2 | 15,0 |

- Keine Abbrüche mehr bei A und B; keine einzige Selbstkorrektur nötig (alle SQL-Entwürfe gültig).
- B, einzige falsche Zahl (G07): Haltergruppen über alle Summen- und Teilzeilen addiert → 3.524.187 statt
  1.484.393. Nicht korrigiert (keine zweite Runde), steht als Befund in NvS und Ausblick.
- B, zwei Warnungen der Zahlenprüfung (G17, G19): Fehlalarme, das Modell schrieb die Formel „× 100“ in
  die Quellenangabe.
- C: 32 unnötige Rückfragen, 3 Abbrüche („token repeat limit reached“). 3B-Modell mit rund 3.000 Tokens
  Kontext überfordert.

## Mo 26.10.2026 — Holdout (einmalig, Konfiguration von Lauf 2)

| Profil | Korrekt | Plausibel-falsch |
|---|---|---:|
| A — nur Schema | 9/12 | 3 |
| B — semantische Schicht | 12/12 | 0 |

A wiederholt die Fehlerarten aus dem Goldset (BEV vs. elektrifiziert, 2026 aus co2cars, keine Rückfrage).
B: eine unnötige Rückfrage (H04), danach richtig.

## Mo 26.10.2026 — Zusatz: Profil E, lokales 7B-Code-Modell (Goldset und Holdout)

Neue Versuchsbedingung, keine Änderung an Katalog oder Code der Profile A–C: `qwen2.5-coder:7b` über Ollama
lokal, sonst identisch mit B. Zweck: H2 mit einem Modell prüfen, das in 8 GB Grafikspeicher passt.

Ergebnis: `eval/ergebnisse/details_E.csv`, `holdout_E.csv`, Tabellen `ergebnis_tabelle(_holdout).md`

| Set | Korrekt | Plausibel-falsch | unnötige Rückfragen | Abbrüche | Ø Sek. |
|---|---|---:|---:|---:|---:|
| Goldset | 27/41 | 3 | 23 | 1 | 17,4 (ohne G22) |
| Holdout | 9/12 | 2 | 7 | 0 | 16,3 |
| zum Vergleich A (120B, ohne Schicht) | 33/42 · 9/12 | 7 · 3 | 0 · 0 | 0 | 3,5 |

- G22 hing 55 Minuten in einer Endlosschleife des Modells, bevor eine Antwort kam. Konsequenz: lokale
  Modelle bekommen `num_predict=1024` und 180 s Timeout (`agent/config.py`), damit ein hängender Aufruf als
  Abbruch zählt und der Lauf weitergeht. Bewertung und Prompts unverändert.
- Hauptfehlerart: unnötige Rückfrage, obwohl Land, Antrieb oder „enge Definition“ in der Frage standen
  (23-mal). Danach 12-mal richtig, 9-mal abgelehnt, 2-mal SQL-Fehler. Alle sieben Fragen mit „enge Definition“
  endeten in einer Ablehnung (Fachlogik 25 %).
- Falsche Zahlen ohne Warnung: G07 und H08 (2026 aus co2cars statt KBA, wie A), G28 (Land vergessen →
  Dezember über sechs Länder), G34 (nach richtiger Rückfrage falsche Formel), H12 (Massenänderung −27,7 %
  statt +7,9 %).
- G38: Abbruch, kein gültiges JSON (Feld `sql` fehlt).
- Bewertung H2: 7B mit Schicht ist sicherer als 120B ohne (3 statt 7 falsche Zahlen), aber kaum hilfreicher.
