"""LLM-Aufrufe mit strukturierter Ausgabe — robust auch für Modelle, die kein Schema erzwingen.

Ollama Cloud ignoriert erzwungene Schemas (Erfahrung aus dem Spesen-Agent). Deshalb steht das
JSON-Schema im Prompt, die Antwort wird mit Pydantic geprüft, bei Fehler gibt es einen zweiten Versuch.
"""
import hashlib
import json
import os
import re
import sqlite3
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from agent.config import BASIS, get_llm, modellname

# Eigener Cache statt LangChain-SQLiteCache: Der LangChain-Schlüssel enthält bei ChatOllama den
# Modellnamen NICHT — Cloud- und lokales Modell würden sich sonst gegenseitig Antworten liefern.
CACHE = BASIS / "llm_cache.db"


def _cache_db():
    con = sqlite3.connect(CACHE)
    con.execute("CREATE TABLE IF NOT EXISTS cache (schluessel TEXT PRIMARY KEY, modell TEXT, antwort TEXT)")
    return con


@lru_cache(maxsize=4)
def llm(modell: str):
    return get_llm(modell)


def _text(antwort) -> str:
    c = getattr(antwort, "content", antwort)
    if isinstance(c, list):
        c = "".join(t.get("text", "") if isinstance(t, dict) else str(t) for t in c)
    return str(c)


def _json(text: str) -> dict:
    """Erstes JSON-Objekt im Text; Text davor/danach und <think>-Blöcke werden ignoriert."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        return json.loads(m.group(1))
    start = text.find("{")
    if start < 0:
        raise ValueError("kein JSON-Objekt in der Antwort")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])      # "Extra data" dahinter ist egal
    return obj


def _glaetten(obj: dict, schema: type[BaseModel]) -> dict:
    """Manche Modelle spiegeln das Schema: {"sql": {"description": "...", "value": "SELECT ..."}}.
    Dann den eigentlichen Wert herausziehen."""
    if not isinstance(obj, dict):
        return obj
    for name in schema.model_fields:
        v = obj.get(name)
        if isinstance(v, dict):
            kandidaten = [w for k, w in v.items() if k not in ("description", "title", "type") and w not in (None, "")]
            obj[name] = kandidaten[-1] if kandidaten else ""
    return obj


def _vorlage(schema: type[BaseModel]) -> str:
    """Konkrete Antwortvorlage + Feldbeschreibungen (statt JSON-Schema, das Modelle gern nachbauen)."""
    beispiel, zeilen = {}, []
    for name, feld in schema.model_fields.items():
        beispiel[name] = [] if "list" in str(feld.annotation).lower() else "..."
        zeilen.append(f"- {name}: {feld.description or ''}")
    return (f"\n\nAntworte NUR mit einem JSON-Objekt in genau dieser Form (Werte ersetzen):\n"
            f"{json.dumps(beispiel, ensure_ascii=False)}\nFelder:\n" + "\n".join(zeilen) +
            "\nKein Text vor oder nach dem JSON.")


def text_aufruf(modell: str, system: str, nutzer: str) -> str:
    name = modellname(modell)
    cache_an = os.getenv("LLM_CACHE", "1") != "0" and not name.startswith("orakel")
    schluessel = hashlib.sha256(json.dumps([name, system, nutzer]).encode()).hexdigest()
    if cache_an:
        with _cache_db() as con:
            treffer = con.execute("SELECT antwort FROM cache WHERE schluessel = ?", (schluessel,)).fetchone()
        if treffer:
            return treffer[0]
    antwort = _text(llm(modell).invoke([SystemMessage(system), HumanMessage(nutzer)])).strip()
    if cache_an and antwort:
        with _cache_db() as con:
            con.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (schluessel, name, antwort))
    return antwort


def struktur_aufruf(modell: str, system: str, nutzer: str, schema: type[BaseModel]):
    """Rückgabe: (objekt, anzahl_aufrufe)."""
    format_hinweis = _vorlage(schema)
    nachricht = nutzer + format_hinweis
    letzter_fehler = None
    for versuch in (1, 2):
        roh = text_aufruf(modell, system, nachricht)
        try:
            return schema.model_validate(_glaetten(_json(roh), schema)), versuch
        except (ValueError, ValidationError) as e:
            letzter_fehler = e
            nachricht = (nutzer + format_hinweis +
                         f"\n\nDeine letzte Antwort war kein gültiges JSON ({str(e)[:150]}). Nur das JSON-Objekt!")
    raise RuntimeError(f"LLM lieferte kein gültiges JSON: {letzter_fehler}")
