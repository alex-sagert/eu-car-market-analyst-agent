"""Prüft Datenbank und LLM-Zugang:  python test_verbindung.py [--lokal | --lokal2]"""
import sys

from agent import db
from agent.config import CLOUD_PROVIDER, modellname

print("1) Datenbank (als Nur-Lese-Benutzer)")
try:
    _, z = db.abfrage("SELECT count(*) FROM markt.zulassungen_monat")
    _, s = db.abfrage("SELECT sum(anzahl) FROM markt.zulassungen_jahr")
    print(f"   ✔ zulassungen_monat: {z[0][0]:,} Zeilen (Soll 191.227), Summe Pkw: {s[0][0]:,} (Soll 37.138.202)")
except Exception as e:  # noqa: BLE001
    sys.exit(f"   ✘ {e}\n   -> .env prüfen (PG_HOST, PG_PORT, PG_DB, PG_AGENT_USER) und data/load_postgres.py ausführen")

modell = "lokal2" if "--lokal2" in sys.argv else ("lokal" if "--lokal" in sys.argv else "cloud")
print(f"2) LLM: {modellname(modell)} (LLM_PROVIDER={CLOUD_PROVIDER})")
try:
    from agent.llm import text_aufruf
    antwort = text_aufruf(modell, "Antworte mit genau einem Wort.", "Wie heißt die Hauptstadt von Frankreich?")
    print(f"   ✔ Antwort: {antwort[:80]}")
except Exception as e:  # noqa: BLE001
    sys.exit(f"   ✘ {type(e).__name__}: {e}\n   -> OLLAMA_API_KEY in .env? Bei --lokal: läuft Ollama, ist das Modell gepullt?")
print("Alles bereit.")
