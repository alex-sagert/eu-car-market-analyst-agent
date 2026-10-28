"""Zahlenprüfung: Steht jede Zahl der Antwort auch im Abfrageergebnis?

Lehre aus dem Churn-Projekt (verify_number): Das LLM formuliert, aber jede Zahl muss aus dem
Ergebnis stammen. Erlaubt sind Rundungen, Prozent statt Anteil (x100), Tausend/Millionen und
Differenzen zweier Ergebniswerte (z. B. Anstieg in Prozentpunkten).
"""
import re
from itertools import combinations

SKALA = {"mio": 1e6, "millionen": 1e6, "million": 1e6, "mrd": 1e9, "tsd": 1e3, "tausend": 1e3}
ZAHL = re.compile(r"(?<![\w.,])-?\d{1,3}(?:\.\d{3})+(?:,\d+)?(?![\d])|(?<![\w.,])-?\d+(?:[.,]\d+)?(?![\d])")


def _lesarten(token: str):
    """Eine Zahl im Text kann deutsch oder englisch geschrieben sein. Rückgabe: [(wert, nachkommastellen)]."""
    t = token
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):           # 2.772.310 oder 1.234,5
        ganz, _, nach = t.partition(",")
        return [(float(ganz.replace(".", "") + ("." + nach if nach else "")), len(nach))]
    if "," in t:                                                   # 46,1
        return [(float(t.replace(",", ".")), len(t.split(",")[1]))]
    if "." in t:                                                   # 46.14 oder 2.772 (mehrdeutig)
        w = [(float(t), len(t.split(".")[1]))]
        if re.fullmatch(r"-?\d{1,3}\.\d{3}", t):
            w.append((float(t.replace(".", "")), 0))
        return w
    return [(float(t), 0)]


def zahlen_im_text(text: str):
    """Liefert [(token, [(wert, stellen), ...])], Skalenwörter (Mio., Tsd.) eingerechnet."""
    gefunden = []
    for m in ZAHL.finditer(text or ""):
        token = m.group(0)
        nach = text[m.end():m.end() + 12].lower().strip(" .")
        faktor = next((f for w, f in SKALA.items() if nach.startswith(w)), 1)
        gefunden.append((token, [(w * faktor, s if faktor == 1 else 3) for w, s in _lesarten(token)]))
    return gefunden


def _kandidaten(zeilen):
    werte = []
    for z in zeilen[:50]:
        for v in z:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                werte.append(float(v))
    werte = werte[:40]
    k = set()
    for v in werte:
        k.update({v, v * 100, v / 100, abs(v), abs(v) * 100})
    for a, b in combinations(werte, 2):                 # Differenzen (pp) und Veränderung in %
        k.update({a - b, b - a, abs(a - b)})
        if a:
            k.add((b - a) / abs(a) * 100)
        if b:
            k.add((a - b) / abs(b) * 100)
    return k


def pruefe_antwort(antwort: str, zeilen, frage: str = ""):
    """Rückgabe: Liste der Zahlen in der Antwort, die NICHT aus dem Ergebnis ableitbar sind."""
    kandidaten = _kandidaten(zeilen)
    in_frage = {t for t, _ in zahlen_im_text(frage)}
    ungeprueft = []
    for token, lesarten in zahlen_im_text(antwort):
        if token in in_frage:
            continue
        wert0 = lesarten[0][0]
        if lesarten[0][1] == 0 and (2000 <= wert0 <= 2035 or 0 <= wert0 <= 12):
            continue                                   # Jahreszahlen, Monate, "Top 3"
        passt = False
        for wert, stellen in lesarten:
            tol = 0.5 * 10 ** (-stellen) + 1e-9
            if stellen == 3 and abs(wert) >= 1000:     # "2,77 Mio." -> relative Toleranz
                tol = abs(wert) * 0.005
            if any(abs(wert - c) <= tol for c in kandidaten):
                passt = True
                break
        if not passt:
            ungeprueft.append(token)
    return ungeprueft


def formatiere(v) -> str:
    """Zahl deutsch formatieren: 2.772.310 bzw. 46,14."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    if float(v).is_integer() and abs(v) >= 1:
        return f"{int(v):,}".replace(",", ".")
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
