"""Rechnet die Referenz-SQL des Goldsets gegen die Datenbank nach.

    python eval/goldset_pruefen.py            # prüft: stimmen die gespeicherten Sollwerte noch?
    python eval/goldset_pruefen.py --fuellen  # schreibt Sollwerte aus den Referenzabfragen (einmalig)
    python eval/goldset_pruefen.py --set holdout

Die Sollwerte stehen fest, BEVOR der Agent läuft. Die Referenz-SQL ist von Hand geschrieben
und gegen die Zahlen aus dem BI-Projekt (Feld "beleg") abgeglichen.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.db import abfrage  # noqa: E402

HIER = Path(__file__).resolve().parent


def sollwert(item):
    if not item.get("referenz_sql"):
        return None
    spalten, zeilen = abfrage(item["referenz_sql"])
    if item["typ"] == "liste":
        return [str(z[0]) for z in zeilen]
    return [round(float(v), 4) for v in zeilen[0]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuellen", action="store_true")
    ap.add_argument("--set", default="goldset", choices=["goldset", "holdout"])
    a = ap.parse_args()
    PFAD = HIER / f"{a.set}.json"
    gold = json.loads(PFAD.read_text(encoding="utf-8"))
    fehler = 0
    for it in gold:
        neu = sollwert(it)
        if neu is None:
            print(f"{it['id']}  {it['typ']:<10} (kein Sollwert)  {it['frage'][:70]}")
            continue
        feld = "liste" if it["typ"] == "liste" else "werte"
        alt = it.get(feld)
        if a.fuellen:
            it[feld] = neu
        elif alt != neu:
            fehler += 1
            print(f"✘ {it['id']}: gespeichert {alt}, Datenbank {neu}")
        print(f"{it['id']}  {it['typ']:<10} {str(neu):<28} {it['frage'][:70]}")
    if a.fuellen:
        PFAD.write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Sollwerte geschrieben: {PFAD}")
    elif fehler:
        sys.exit(f"{fehler} Abweichung(en)")
    else:
        print("✔ Alle Sollwerte stimmen mit der Datenbank überein.")


if __name__ == "__main__":
    main()
