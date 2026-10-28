# Projektstruktur — Frag den Neuwagenmarkt

Ordner `eu-car-market-analyst-agent`: Was in jeder Datei steckt und was dort passiert.

## Hauptordner

| Datei | Was sie macht |
|---|---|
| `app.py` | Streamlit-Oberfläche für die Demo: Profil wählen, Frage stellen, Rückfrage beantworten, Antwort mit SQL und Tabelle |
| `main.py` | Konsolenprogramm (MVD-Vorgabe), kann dasselbe im Terminal |
| `test_verbindung.py` | Prüft Datenbank und Modellzugang, vor der Demo einmal ausführen |
| `requirements.txt` | Benötigte Python-Pakete |
| `docker-compose.yml` | PostgreSQL per Docker, falls keins installiert ist |
| `.env.example` | Vorlage für die eigene `.env` mit Zugangsdaten (die `.env` selbst wird nie hochgeladen) |
| `.gitignore` | Was nicht auf GitHub darf (`.env`, `.venv`, Kursabgabe) |
| `llm_cache.db` | Gespeicherte Modellantworten: Auf eine schon gestellte Frage kommt dieselbe Antwort sofort |
| `README.md` | Projektbeschreibung, Ergebnisse, Schnellstart |
| `LICENSE` | MIT-Lizenz |

## agent/ — der Agent

| Datei | Was sie macht |
|---|---|
| `graph.py` | Baut den Ablauf in LangGraph aus den 7 Schritten und legt fest, wann es wohin geht, z. B. bei einem Fehler zurück zum SQL-Entwurf (höchstens 3 Versuche). Enthält die Klasse `Agent`, die App und Konsole benutzen. |
| `nodes.py` | Die 7 Schritte selbst, mit den Anweisungen ans Modell: einordnen → Rückfrage → SQL entwerfen → SQL prüfen → ausführen → antworten → Zahlen prüfen |
| `state.py` | Was sich der Agent zwischen den Schritten merkt (Frage, SQL, Ergebnis, Status) und welche Felder das Modell liefern muss |
| `llm.py` | Ruft das Modell auf, liest seine JSON-Antwort robust ein und speichert jede Antwort im Cache |
| `config.py` | Zentrale Einstellungen: Profile A–E (mit oder ohne semantische Schicht, welches Modell), Modellwahl, Zeitlimits |
| `sql_guard.py` | Sicherheitsstufe 2: lässt nur SELECT auf das Schema `markt` durch, blockiert Systemtabellen und gefährliche Funktionen |
| `zahlen.py` | Zahlenprüfung: Findet jede Zahl in der Antwort und prüft, ob sie im Abfrageergebnis steht, sonst gibt es eine Warnung |
| `db.py` | Datenbankzugriff als Nur-Lese-Benutzer, liefert Schema, Beispielzeilen und Abfrageergebnisse |
| `katalog.py` | Lädt die semantische Schicht und sucht per BM25 die 4 passendsten Beispielabfragen zur Frage |
| `orakel.py` | Testdouble statt Modell: liefert die Musterlösungen, damit die ganze Pipeline ohne LLM getestet werden kann |
| `__init__.py` | Macht den Ordner zum Python-Paket und stellt die Windows-Konsole auf UTF-8 |

## semantik/ — die semantische Schicht („Kennzahlen-Handbuch“)

| Datei | Was sie macht |
|---|---|
| `katalog.yaml` | 18 verbindliche Fachbegriffe mit Definition und SQL-Muster, z. B. „Elektroauto = nur BEV“. 3 davon mit Rückfragepflicht: China eng/weit, Zeitfenster „seit den Zöllen“, fehlendes Land. Dazu der Datenumfang, also was in den Daten steckt und was nicht. |
| `beispiele.yaml` | 15 Musterfragen mit fertigem SQL, ohne Überschneidung mit den Testfragen |

Profil B nutzt diesen Ordner, Profil A nicht — das ist der ganze Unterschied zwischen den beiden.

## data/ — die Daten

| Datei / Ordner | Was drin ist |
|---|---|
| `load_postgres.py` | Legt Datenbank `markt_agent`, Schema `markt`, Tabellen und den Nur-Lese-Benutzer `agent_leser` an und lädt die CSVs |
| `build_data.py` | Verdichtet die 37,1 Mio. EEA-Zeilen (Parquet aus dem BI-Projekt) mit DuckDB zu den CSVs, nur für einen Neuaufbau nötig |
| `csv/` | Die 5 Tabellen des Agenten: `zulassungen_monat`, `zulassungen_jahr`, `kba_monat`, `kba_halter_monat`, `marken` |
| `sql/01_schema.sql` | Tabellendefinitionen mit Spaltenkommentaren, die der Agent mitliest, plus die kleinen Tabellen `laender` und `antriebe` |
| `kba/` | KBA-Monatszahlen Deutschland (Marke × Antrieb, Haltergruppen), Eingang für `build_data.py` |
| `referenz/` | Marken-Stammdaten und Zuordnung der Rohschreibweisen aus dem BI-Projekt, Eingang für `build_data.py` |

## eval/ — die Messung

| Datei / Ordner | Was sie macht |
|---|---|
| `goldset.json` | 42 Testfragen in 8 Stufen, je Frage mit Referenz-SQL und Sollwert |
| `holdout.json` | 12 zurückgehaltene Fragen, nur einmal am Ende gelaufen |
| `eval.py` | Stellt alle Fragen je Profil, bewertet das Abfrageergebnis gegen den Sollwert und schreibt die Ergebnistabellen |
| `goldset_pruefen.py` | Rechnet alle Sollwerte gegen die Datenbank nach |
| `ergebnisse/` | `details_A…E.csv` und `holdout_A…E.csv` (je Frage: SQL, Ergebnis, Antwort, richtig/falsch), `ergebnis_tabelle.md`, Archiv `lauf1/` und `lauf2/`, Pipeline-Test `orakel/` |

## docs/ — die Dokumentation

| Datei / Ordner | Was drin ist |
|---|---|
| `abgabe/` | NvS, CAT und Präsentation — nur in der Kursabgabe, nicht im Repository |
| `PROJEKTTAGEBUCH.md` | Jeder Lauf mit Befund, jede Änderung mit Grund |
| `ANLEITUNG.md` | Installation und Bedienung Schritt für Schritt |
| `graph.md` | Ablaufdiagramm des Agenten (Mermaid) |
| `screenshots/` | Bilder der Streamlit-App, auch für die Folien 8 und 9 |

## tests/

| Datei | Was sie macht |
|---|---|
| `test_sicherheit_und_zahlen.py` | 18 SQL-Fälle (4 erlaubt, 14 blockiert) und die Zahlenprüfung, ohne Modell und ohne Datenbank |
