"""Konsolenprogramm (MVD-Vorgabe): Frage stellen, bei Rückfrage antworten, Ergebnis mit SQL anzeigen.

    python main.py "Wie hoch war der BEV-Anteil in den Niederlanden 2025?"
    python main.py --profil A "..."        # Baseline zum Vergleich
    python main.py                          # interaktiv, Ende mit leerer Eingabe
"""
import argparse
import sys

from agent.config import PROFILE, modellname
from agent.graph import Agent
from agent.zahlen import formatiere


def zeige(erg, details=False):
    print(f"\n[{erg.get('status')}]  {erg.get('sekunden', 0)} s · {erg.get('llm_aufrufe', 0)} LLM-Aufrufe "
          f"· {erg.get('versuche', 0)} SQL-Versuch(e)")
    print(erg.get("antwort", ""))
    if erg.get("sql"):
        print(f"\nSQL: {erg['sql']}")
    if erg.get("zeilen"):
        print(" | ".join(erg.get("spalten", [])))
        for z in erg["zeilen"][:10]:
            print(" | ".join(formatiere(v) for v in z))
        if len(erg["zeilen"]) > 10:
            print(f"... {len(erg['zeilen']) - 10} weitere Zeilen")
    if details:
        print("\nSchritte:")
        for s in erg.get("schritte", []):
            print("  -", s)


def frage_stellen(agent, frage, details):
    erg = agent.fragen(frage)
    while erg.get("status") == "rueckfrage":
        d = erg["rueckfrage_daten"]
        print(f"\nRückfrage: {d['rueckfrage']}")
        for i, o in enumerate(d.get("optionen", []), 1):
            print(f"  {i}) {o}")
        wahl = input("Nummer oder eigene Antwort: ").strip()
        if wahl.isdigit() and 1 <= int(wahl) <= len(d.get("optionen", [])):
            wahl = d["optionen"][int(wahl) - 1]
        erg = agent.antworten(erg["thread_id"], wahl)
    zeige(erg, details)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frage", nargs="*")
    ap.add_argument("--profil", default="B", choices=list(PROFILE))
    ap.add_argument("--details", action="store_true", help="alle Schritte des Graphen anzeigen")
    a = ap.parse_args()
    agent = Agent(a.profil)
    print(f"Profil {a.profil}: {PROFILE[a.profil]['name']} — {modellname(PROFILE[a.profil]['modell'])}")
    if a.frage:
        frage_stellen(agent, " ".join(a.frage), a.details)
        return
    while True:
        frage = input("\nFrage (leer = Ende): ").strip()
        if not frage:
            sys.exit(0)
        frage_stellen(agent, frage, a.details)


if __name__ == "__main__":
    main()
