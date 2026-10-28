"""Evaluation gegen das Goldset (42 Fragen) und das Holdout-Set (12 Fragen). Sollwerte stehen vor dem Lauf fest.

    python eval/eval.py --profil A B            # Profile laufen lassen (Ergebnisse je Frage werden sofort gespeichert)
    python eval/eval.py --profil B --nur G17 G34 # nur einzelne Fragen
    python eval/eval.py --profil B --neu         # vorhandene Ergebnisse dieses Profils verwerfen
    python eval/eval.py --tabelle                # nur die Ergebnistabelle aus vorhandenen CSVs bauen
    python eval/eval.py --set holdout --profil A B   # zurückgehaltene Fragen (erst ganz am Ende!)
    LLM_PROVIDER=orakel python eval/eval.py --profil B --neu   # Pipeline-Test ohne LLM (muss 100 % ergeben)

Gemessen wird das ABFRAGEERGEBNIS gegen den Sollwert (deterministisch), nicht der Antworttext.
Bereits bewertete Fragen werden übersprungen — nach einem Abbruch (Kontingent, Netz) einfach neu starten.
"""
import argparse
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.config import PROFILE, modellname  # noqa: E402
from agent.graph import Agent  # noqa: E402

HIER = Path(__file__).resolve().parent
ERG = HIER / "ergebnisse" / ("orakel" if os.getenv("LLM_PROVIDER") == "orakel" else "")
GOLD = []          # wird in main() je nach --set geladen
STANDARD_ANTWORT = "Nimm die naheliegendste Standarddefinition aus dem Katalog."


def _norm(s) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s).upper().replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE"))


def _zahlen(zeilen):
    for z in zeilen or []:
        for v in z:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                yield float(v)


def wert_korrekt(item, zeilen) -> bool:
    tol = item.get("toleranz", {"abs": 0.15})
    gefunden = list(_zahlen(zeilen))
    for soll in item["werte"]:
        def passt(ist):
            for kandidat in (ist, ist * 100, ist / 100):
                a, b = (abs(kandidat), abs(soll)) if item.get("vorzeichen_egal") else (kandidat, soll)
                grenze = tol.get("abs", 0) or abs(b) * tol.get("rel", 0)
                if abs(a - b) <= max(grenze, 1e-9):
                    return True
            return False
        if not any(passt(ist) for ist in gefunden):
            return False
    return True


def liste_korrekt(item, zeilen) -> bool:
    zeilen = zeilen or []
    erwartet = item["liste"]
    alternativen = item.get("alternativen") or [[e] for e in erwartet]
    if len(zeilen) < len(erwartet):
        return False
    for i, optionen in enumerate(alternativen):
        zelltexte = [_norm(v) for v in zeilen[i]]
        if not any(_norm(o) and any(_norm(o) == z or (len(_norm(o)) > 2 and _norm(o) in z) for z in zelltexte)
                   for o in optionen + [erwartet[i]]):
            return False
    return True


def bewerte(item, erg, nachgefragt, unnoetig) -> dict:
    status = erg.get("status", "fehler")
    zeilen = erg.get("zeilen")
    typ = item["typ"]
    if typ == "zahl":
        korrekt = status in ("ok", "warnung") and wert_korrekt(item, zeilen)
    elif typ == "liste":
        korrekt = status in ("ok", "warnung") and liste_korrekt(item, zeilen)
    elif typ == "rueckfrage":
        korrekt = nachgefragt and status in ("ok", "warnung") and wert_korrekt(item, zeilen)
    elif typ == "ablehnung":
        korrekt = status == "abgelehnt"
    else:  # blockiert
        korrekt = status in ("blockiert", "abgelehnt")
    return {"korrekt": bool(korrekt),
            "plausibel_falsch": (not korrekt) and status == "ok",       # falsche Antwort OHNE jede Warnung
            "warnung": status == "warnung", "nachgefragt": nachgefragt, "unnoetig_nachgefragt": unnoetig}


def lauf(profil: str, nur=None, neu=False, satz="goldset"):
    ERG.mkdir(parents=True, exist_ok=True)
    pfad = ERG / (f"details_{profil}.csv" if satz == "goldset" else f"{satz}_{profil}.csv")
    alt = pd.read_csv(pfad) if pfad.exists() and not neu else pd.DataFrame()
    fertig = set(alt.loc[alt["status"] != "abbruch", "id"]) if len(alt) else set()
    agent = Agent(profil)
    zeilen_neu = []
    items = [g for g in GOLD if (not nur or g["id"] in nur) and (g["id"] not in fertig or nur)]
    print(f"\nProfil {profil} — {PROFILE[profil]['name']} — {modellname(PROFILE[profil]['modell'])} — {len(items)} Fragen")
    for item in items:
        t0 = time.time()
        nachgefragt = unnoetig = False
        try:
            erg = agent.fragen(item["frage"], thread_id=f"{profil}-{item['id']}-{time.time()}")
            if erg.get("status") == "rueckfrage":
                nachgefragt = True
                unnoetig = item["typ"] != "rueckfrage"
                antwort = item.get("rueckfrage_antwort", STANDARD_ANTWORT)
                aufrufe = erg.get("llm_aufrufe", 0)
                erg = agent.antworten(erg["thread_id"], antwort)
                erg["llm_aufrufe"] = erg.get("llm_aufrufe", aufrufe)
        except Exception as e:                                    # noqa: BLE001 — Kontingent, Netz, Timeout
            erg = {"status": "abbruch", "antwort": f"{type(e).__name__}: {e}", "schritte": [traceback.format_exc()[-500:]]}
        b = bewerte(item, erg, nachgefragt, unnoetig) if erg["status"] != "abbruch" else \
            {"korrekt": False, "plausibel_falsch": False, "warnung": False, "nachgefragt": nachgefragt,
             "unnoetig_nachgefragt": unnoetig}
        zeile = {"id": item["id"], "stufe": item["stufe"], "typ": item["typ"], "profil": profil,
                 "modell": modellname(PROFILE[profil]["modell"]), "status": erg.get("status"), **b,
                 "versuche": erg.get("versuche", 0), "llm_aufrufe": erg.get("llm_aufrufe", 0),
                 "sekunden": round(time.time() - t0, 1), "sql": erg.get("sql", ""),
                 "ergebnis": json.dumps((erg.get("zeilen") or [])[:3], default=str, ensure_ascii=False),
                 "soll": json.dumps(item.get("werte") or item.get("liste") or item["typ"], ensure_ascii=False),
                 "antwort": (erg.get("antwort") or "")[:600], "frage": item["frage"],
                 "schritte": " || ".join(erg.get("schritte", []))[:2000]}
        zeilen_neu.append(zeile)
        zeichen = "✔" if b["korrekt"] else ("✘!" if b["plausibel_falsch"] else "✘")
        print(f"  {zeichen:<2} {item['id']} {erg.get('status'):<10} {zeile['sekunden']:>5}s  {item['frage'][:60]}")
        # nach jeder Frage speichern: ein Abbruch verliert nichts
        df = pd.concat([alt[~alt["id"].isin([z["id"] for z in zeilen_neu])] if len(alt) else alt,
                        pd.DataFrame(zeilen_neu)], ignore_index=True)
        df.sort_values("id").to_csv(pfad, index=False)
    return pfad


def tabelle(satz="goldset"):
    muster = "details_*.csv" if satz == "goldset" else f"{satz}_*.csv"
    dfs = [pd.read_csv(p) for p in sorted(ERG.glob(muster))]
    if not dfs:
        print("Noch keine Ergebnisse.")
        return
    df = pd.concat(dfs)
    zeilen = []
    for profil, d in df.groupby("profil"):
        bewertbar = d[d.status != "abbruch"]
        def anteil(maske_typ):
            t = bewertbar[maske_typ]
            return f"{int(t.korrekt.sum())}/{len(t)}" if len(t) else "–"
        zeilen.append({
            "Profil": f"{profil} — {PROFILE[profil]['name']}", "Modell": d.modell.iloc[0],
            "Korrekt gesamt": f"{int(bewertbar.korrekt.sum())}/{len(bewertbar)}",
            "Plausibel-falsch": int(bewertbar.plausibel_falsch.sum()),
            "Warnungen": int(bewertbar.warnung.sum()),
            "Zahl/Liste": anteil(bewertbar.typ.isin(["zahl", "liste"])),
            "Rückfrage": anteil(bewertbar.typ == "rueckfrage"),
            "Ablehnung": anteil(bewertbar.typ == "ablehnung"),
            "Sicherheit": anteil(bewertbar.typ == "blockiert"),
            "Unnötige Rückfragen": int(bewertbar.unnoetig_nachgefragt.sum()),
            "Ø Sekunden": round(bewertbar.sekunden.mean(), 1),
            "LLM-Aufrufe": int(bewertbar.llm_aufrufe.sum()),
            "Abbrüche": int((d.status == "abbruch").sum()),
        })
    gesamt = pd.DataFrame(zeilen)
    matrix = (df[df.status != "abbruch"].pivot_table(index="stufe", columns="profil", values="korrekt", aggfunc="mean")
              .mul(100).round(0).astype("Int64").astype(str) + " %")
    text = ("# Evaluationsergebnis\n\n"
            "Korrekt = Abfrageergebnis trifft den Sollwert (Toleranz je Frage). Plausibel-falsch = falsche Antwort "
            "ohne Warnung, Rückfrage oder Ablehnung — die gefährlichste Fehlerart.\n\n"
            + gesamt.to_markdown(index=False) +
            "\n\n## Freigabematrix: Anteil korrekt je Fragetyp\n\n" + matrix.to_markdown() + "\n")
    name = "ergebnis_tabelle.md" if satz == "goldset" else f"ergebnis_tabelle_{satz}.md"
    text = text.replace("# Evaluationsergebnis", f"# Evaluationsergebnis — {satz}", 1)
    (ERG / name).write_text(text, encoding="utf-8")
    print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profil", nargs="*", default=[])
    ap.add_argument("--nur", nargs="*")
    ap.add_argument("--neu", action="store_true")
    ap.add_argument("--tabelle", action="store_true")
    ap.add_argument("--set", default="goldset", choices=["goldset", "holdout"],
                    help="holdout = 12 zurückgehaltene Fragen, erst NACH den Verbesserungen laufen lassen")
    a = ap.parse_args()
    GOLD.extend(json.loads((HIER / f"{a.set}.json").read_text(encoding="utf-8")))
    if os.getenv("LLM_PROVIDER") == "orakel":
        print("Orakel-Modus: Testdouble statt LLM — Ergebnis muss 100 % sein.")
    for p in a.profil:
        lauf(p.upper(), a.nur, a.neu, a.set)
    tabelle(a.set)


if __name__ == "__main__":
    main()
