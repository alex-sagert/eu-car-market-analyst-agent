# Anleitung — heute am Desktop, morgen am Laptop

Alle Befehle in **PowerShell**, im Projektordner:

```powershell
cd "C:\Users\Alex\Desktop\Weiterbildung\educx\06_KI Anwendungen\Woche 4\eu-car-market-analyst-agent"
```

---

## A · Heute am Desktop (Mo 26.10.) — ca. 20 Minuten Einrichtung, dann laufen lassen

### 1. Python-Umgebung

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. `.env` ergänzen

Die `.env` liegt schon im Ordner; `OLLAMA_API_KEY` und `GOOGLE_API_KEY` sind aus dem Spesen-Agent
übernommen. Es fehlt nur das Datenbank-Passwort:

```powershell
notepad .env
```

- `PG_ADMIN_PASSWORD` = Passwort des Benutzers **postgres** aus der PostgreSQL-Installation (dasselbe wie in pgAdmin)

### 3. PostgreSQL läuft?

Windows-Taste → „Dienste“ → `postgresql-x64-18` → Status „Wird ausgeführt“. Sonst: Rechtsklick → Starten.

### 4. Daten laden

```powershell
python data/load_postgres.py
```

Erwartet:
```
Datenbank markt_agent angelegt
  zulassungen_monat    191,227 Zeilen  ✔ = BI-Projekt
  zulassungen_jahr      24,557 Zeilen  ✔ = BI-Projekt
✔ Schreibversuch als agent_leser abgewiesen: ReadOnlySqlTransaction
```

In pgAdmin erscheint danach unter *Databases* die Datenbank **markt_agent** mit dem Schema **markt**
(ggf. Rechtsklick → Refresh).

### 5. Tests

```powershell
python tests/test_sicherheit_und_zahlen.py
python eval/goldset_pruefen.py                     # ✔ Alle Sollwerte stimmen ...
$env:LLM_PROVIDER="orakel"; python eval/eval.py --profil A B --neu; Remove-Item Env:LLM_PROVIDER
```
Orakel-Lauf: **B = 42/42**, A = 39/42 (A stellt keine Rückfragen — so gewollt).

```powershell
python test_verbindung.py          # Datenbank + Ollama Cloud
python main.py --details "Wie hoch war der BEV-Anteil in den Niederlanden 2025?"
```

### 6. Evaluation mit echtem LLM (läuft von allein, ca. 15–30 Minuten)

```powershell
python eval/eval.py --profil A B
```
Jede Frage wird sofort gespeichert. Bricht der Lauf ab (Kontingent, Netz), einfach denselben
Befehl erneut starten — fertige Fragen werden übersprungen.
Ergebnis: `eval/ergebnisse/ergebnis_tabelle.md` und `details_A.csv`, `details_B.csv`.

### 7. Lokales Modell — parallel in einem zweiten PowerShell-Fenster starten

```powershell
ollama pull llama3.2
python test_verbindung.py --lokal
python eval/eval.py --profil C          # auf CPU langsam (grob 1–3 h) — einfach laufen lassen
python eval/eval.py --profil D          # optional, falls Zeit
```

### 8. App ansehen, Screenshots machen

```powershell
streamlit run app.py
```
Screenshots für die Präsentation: Rückfrage bei „Marktanteil chinesischer Marken 2025“,
Ablehnung „Restwert ID.3“, gleiche Frage in Profil A und B.

### 9. Auf GitHub sichern — damit der Laptop morgen alles hat

Auf github.com → *New repository* → Name `eu-car-market-analyst-agent`, **ohne** README anlegen. Dann:

```powershell
git init
git add .
git commit -m "Analytics-Agent: Datenbasis, LangGraph-Agent, Goldset, Evaluation"
git branch -M main
git remote add origin https://github.com/alex-sagert/eu-car-market-analyst-agent.git
git push -u origin main
```
`.env` wird nicht hochgeladen. `llm_cache.db` schon — damit laufen alle Auswertungen am Laptop
ohne neues Kontingent. Nach Ende von Profil C: `git add . ; git commit -m "Lauf C" ; git push`.

**Die `.env` separat mitnehmen** (USB-Stick oder abtippen): ohne sie kein Datenbank- und LLM-Zugang.

---

## B · Morgen am Laptop (Di 27.10.)

Vorab heute Abend prüfen: `py --version` (3.12?), `git --version`, `docker --version`.

```powershell
git clone https://github.com/alex-sagert/eu-car-market-analyst-agent.git
cd eu-car-market-analyst-agent
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# .env vom Desktop hierher kopieren
```

**Datenbank — eine von zwei Varianten:**

| Laptop hat … | Dann |
|---|---|
| Docker Desktop | `docker compose up -d`; in `.env`: `PG_PORT=5433`, `PG_ADMIN_PASSWORD=postgres` |
| kein Docker | PostgreSQL von postgresql.org/download/windows installieren (Port 5432, Passwort merken → `.env`) |

```powershell
python data/load_postgres.py
python test_verbindung.py
python eval/eval.py --tabelle          # Ergebnisse vom Desktop anzeigen
```

Am Laptop **nur Cloud-Profile (A, B)** laufen lassen; das lokale Modell bleibt am Desktop.

---

## C · Plan bis Freitag

| Tag | Was | Ergebnis |
|---|---|---|
| **Mo** (Desktop) | Einrichtung, Orakel-Test, Lauf A + B, Lauf C starten, Screenshots, GitHub | Lauf 1 gemessen |
| **Di** (Laptop) | Fehleranalyse aus `details_*.csv`; **eine** dokumentierte Verbesserungsrunde am Katalog (Lauf 2); NvS-Gerüst | Lauf 2 + Fehlerkatalog |
| **Mi** (Desktop) | Lauf C/D fertig, **Holdout** A + B (danach nichts mehr ändern), App-Feinschliff, Präsentation | Endergebnis |
| **Do** | 8–10 Uhr Puffer · **10–11 MC-Test** · CAT + NvS final, README-Ergebnisse, ZIP → LMS | Abgabe |
| **Fr** | Präsentation: gleiche Frage live an A und B, Fallback aus dem Cache | |

**Regel gegen Selbstbetrug:** Verbesserungen nur anhand des Goldsets, das Holdout läuft genau
einmal am Ende. Jede Katalogänderung bekommt eine Zeile im Projekttagebuch (Lauf, Änderung, Grund).
