"""Semantische Schicht laden und passende Beispielabfragen finden (Retrieval).

Retrieval mit BM25 über die Beispielfragen: kein Embedding-Modell nötig, läuft auf jedem Rechner
und ist für 15 kurze Fragen genauso treffsicher wie ein Vektorindex.
"""
import math
import re
from functools import lru_cache

import yaml

from agent.config import BASIS

STOPP = set("der die das ein eine einer eines in im am an auf aus bei mit von vom zu zur zum und oder wie viele viel "
            "hoch war waren wurde wurden welche welcher welches hat hatte hatten ist sind den dem des je für was wer "
            "es 2021 2022 2023 2024 2025 2026".split())


def _tokens(text: str):
    t = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return [w for w in re.findall(r"[a-z0-9\.\-]+", t) if w not in STOPP and len(w) > 1]


@lru_cache(maxsize=1)
def katalog() -> dict:
    return yaml.safe_load((BASIS / "semantik" / "katalog.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def beispiele() -> list:
    return yaml.safe_load((BASIS / "semantik" / "beispiele.yaml").read_text(encoding="utf-8"))


def katalog_text() -> str:
    k = katalog()
    zeilen = ["DATENUMFANG:", k["datenumfang"].strip(), "", "FACHBEGRIFFE (verbindlich):"]
    for b in k["begriffe"]:
        z = f"- {b['begriff']}: {' '.join(b['definition'].split())}"
        if b.get("sql"):
            z += f"  SQL-Muster: {b['sql']}"
        if b.get("rueckfrage"):
            z += "  [bei fehlender Angabe NACHFRAGEN]"
        zeilen.append(z)
    zeilen += ["", "REGELN:"] + [f"- {r}" for r in k["regeln"]]
    return "\n".join(zeilen)


def rueckfrage_begriffe() -> str:
    return "\n".join(f"- {b['begriff']}: {' '.join(b['definition'].split())} Optionen: {b.get('optionen', [])}"
                     for b in katalog()["begriffe"] if b.get("rueckfrage"))


def aehnliche_beispiele(frage: str, k: int = 4) -> list:
    """BM25: die k Beispielabfragen, deren Frage der neuen Frage am ähnlichsten ist."""
    bsp = beispiele()
    if k <= 0 or not bsp:
        return []
    docs = [_tokens(b["frage"]) for b in bsp]
    n, avgdl = len(docs), sum(len(d) for d in docs) / len(docs)
    df = {}
    for d in docs:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    q = _tokens(frage)
    scores = []
    for i, d in enumerate(docs):
        s = 0.0
        for w in q:
            if w not in df:
                continue
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            tf = d.count(w)
            s += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(d) / avgdl))
        scores.append((s, i))
    return [bsp[i] for s, i in sorted(scores, reverse=True)[:k]]
