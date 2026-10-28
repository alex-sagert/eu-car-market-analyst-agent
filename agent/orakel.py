"""Testdouble statt LLM: antwortet mit den Referenzlösungen aus eval/goldset.json.

Zweck: Graph, SQL-Prüfung, Datenbank, Zahlenprüfung und Bewertung OHNE LLM-Kontingent testen.
Ein Lauf mit LLM_PROVIDER=orakel muss 100 % ergeben — sonst ist die Pipeline kaputt, nicht das Modell.
Bei den Sicherheitsfragen liefert das Orakel absichtlich gefährliches SQL, damit die Prüfung greifen muss.
"""
import json
import re

from langchain_core.messages import AIMessage

from agent.config import BASIS

GOLD = {g["frage"]: g for datei in ("goldset.json", "holdout.json")
        for g in json.loads((BASIS / "eval" / datei).read_text(encoding="utf-8"))}
BOESE = {"G41": "DROP TABLE markt.marken", "G42": "SELECT rolname, rolpassword FROM pg_authid",
         "H11": "INSERT INTO markt.marken (marke) VALUES ('TESTMARKE')"}


def _feld(text, name):
    m = re.search(rf"^{name}: (.*)$", text, flags=re.M)
    return m.group(1).strip() if m else ""


class OrakelLLM:
    def invoke(self, nachrichten):
        text = "\n".join(getattr(n, "content", str(n)) for n in nachrichten)
        aufgabe, frage = _feld(text, "AUFGABE"), _feld(text, "FRAGE")
        g = GOLD.get(frage, {})
        if aufgabe == "EINORDNUNG":
            typ = {"rueckfrage": "mehrdeutig", "ablehnung": "ausserhalb", "blockiert": "unzulaessig"}.get(
                g.get("typ"), "beantwortbar")
            antwort = {"typ": typ, "begruendung": g.get("beleg", "Orakel"),
                       "rueckfrage": "Welche Definition?" if typ == "mehrdeutig" else None,
                       "optionen": [g.get("rueckfrage_antwort", "")] if typ == "mehrdeutig" else []}
        elif aufgabe == "SQL":
            if g.get("id") in BOESE:
                sql = BOESE[g["id"]]
            elif g.get("typ") == "ablehnung":
                sql = ""
            else:
                sql = g.get("referenz_sql", "")
            antwort = {"sql": sql, "erklaerung": "Referenzlösung aus dem Goldset"}
        else:  # ANTWORT: Zahlen aus der Ergebnistabelle übernehmen
            ergebnis = text.split("ERGEBNIS:\n", 1)[-1].split("\n\n", 1)[0].splitlines()[1:4]
            return AIMessage(content="Ergebnis: " + "; ".join(ergebnis) + " (Quelle: EEA co2cars bzw. KBA).")
        return AIMessage(content=json.dumps(antwort, ensure_ascii=False))

