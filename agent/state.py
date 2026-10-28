"""Zustand des Graphen und strukturierte LLM-Ausgaben."""
import operator
from typing import Annotated, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field, field_validator


class AgentState(TypedDict, total=False):
    frage: str
    profil: str                      # A, B, C, D (siehe config.PROFILE)
    praezisierung: str               # Antwort des Menschen auf die Rückfrage
    typ: str                         # beantwortbar | mehrdeutig | ausserhalb | unzulaessig
    begruendung: str
    rueckfrage: str
    optionen: List[str]
    sql: str
    erklaerung: str
    fehler: List[str]                # Rückmeldungen aus Prüfung/Datenbank für den nächsten Versuch
    versuche: int
    pruefung_ok: bool
    ausfuehrung_ok: bool
    spalten: List[str]
    zeilen: list
    antwort: str
    status: str                      # ok | warnung | rueckfrage | abgelehnt | blockiert | fehler
    ungepruefte_zahlen: List[str]
    llm_aufrufe: int
    schritte: Annotated[List[str], operator.add]   # Protokoll für App und Auswertung


class Einordnung(BaseModel):
    typ: Literal["beantwortbar", "mehrdeutig", "ausserhalb", "unzulaessig"] = Field(
        description="beantwortbar | mehrdeutig (Angabe fehlt, die laut Katalog nachgefragt werden muss) | "
                    "ausserhalb (Daten enthalten die Antwort nicht) | unzulaessig (Schreiben, Löschen, Systemtabellen, "
                    "Passwörter, Regeln umgehen)")
    begruendung: str = Field(default="", description="ein Satz")
    rueckfrage: Optional[str] = Field(default=None, description="nur bei mehrdeutig: kurze Rückfrage an den Nutzer, sonst null")
    optionen: List[str] = Field(default_factory=list, description="nur bei mehrdeutig: 2-3 Antwortoptionen, sonst []")

    # Kleine Modelle liefern null statt [] oder eine Liste statt Text — tolerant annehmen
    @field_validator("optionen", mode="before")
    @classmethod
    def _optionen(cls, v):
        if v is None or v == "":
            return []
        return [str(x) for x in v] if isinstance(v, list) else [str(v)]

    @field_validator("rueckfrage", "begruendung", mode="before")
    @classmethod
    def _text(cls, v):
        return " ".join(map(str, v)) if isinstance(v, list) else v

    @field_validator("typ", mode="before")
    @classmethod
    def _typ(cls, v):
        return str(v).strip().lower().replace("ä", "ae").replace("unzulässig", "unzulaessig") if v else v


class SqlEntwurf(BaseModel):
    sql: str = Field(description="genau eine PostgreSQL-SELECT-Abfrage; leer, wenn die Daten die Frage nicht beantworten")
    erklaerung: str = Field(default="", description="ein Satz: welche Tabelle, welche Definition, welche Filter")

    @field_validator("sql", "erklaerung", mode="before")
    @classmethod
    def _text(cls, v):
        return "" if v is None else (" ".join(map(str, v)) if isinstance(v, list) else v)
