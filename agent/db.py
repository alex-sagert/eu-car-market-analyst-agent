"""Datenbankzugriff des Agenten — immer als Nur-Lese-Benutzer."""
import os
from functools import lru_cache
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MAX_ZEILEN = 200


def _verbindung():
    con = psycopg.connect(
        host=os.getenv("PG_HOST", "localhost"), port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "markt_agent"),
        user=os.getenv("PG_AGENT_USER", "agent_leser"), password=os.getenv("PG_AGENT_PASSWORD", "nur_lesen"),
        connect_timeout=5)
    # Zusätzlich zur Rollen-Einstellung: jede Sitzung read-only und mit Zeitlimit
    con.execute("SET default_transaction_read_only = on")
    con.execute("SET statement_timeout = '15s'")
    con.execute("SET search_path = markt")
    con.commit()
    return con


def abfrage(sql: str, max_zeilen: int = MAX_ZEILEN):
    """Führt eine Abfrage aus. Rückgabe: (spaltennamen, zeilen). Zeilen sind gekürzt auf max_zeilen."""
    with _verbindung() as con:
        cur = con.execute(sql)
        spalten = [d.name for d in cur.description] if cur.description else []
        zeilen = cur.fetchmany(max_zeilen) if cur.description else []
        con.rollback()
    return spalten, [tuple(_wert(v) for v in z) for z in zeilen]


def erklaeren(sql: str):
    """EXPLAIN ohne Ausführung: prüft Syntax, Tabellen und Spalten, ohne Daten zu lesen."""
    with _verbindung() as con:
        con.execute("EXPLAIN " + sql)
        con.rollback()


def _wert(v):
    from decimal import Decimal
    if isinstance(v, Decimal):
        return float(v)
    return v


@lru_cache(maxsize=4)
def schema_beschreibung(mit_kommentaren: bool) -> str:
    """Tabellen und Spalten des Schemas markt als Text für den Prompt.
    mit_kommentaren=False ist die Baseline (nur Namen und Typen)."""
    sql = """
        SELECT c.table_name, c.column_name, c.data_type,
               col_description(format('markt.%I', c.table_name)::regclass, c.ordinal_position) AS spalte_kom,
               obj_description(format('markt.%I', c.table_name)::regclass, 'pg_class') AS tabelle_kom
        FROM information_schema.columns c
        WHERE c.table_schema = 'markt'
        ORDER BY c.table_name, c.ordinal_position"""
    _, zeilen = abfrage(sql, max_zeilen=1000)
    teile, aktuell = [], None
    for tab, spalte, typ, s_kom, t_kom in zeilen:
        if tab != aktuell:
            aktuell = tab
            teile.append(f"\nTABELLE markt.{tab}" + (f"  -- {t_kom}" if mit_kommentaren and t_kom else ""))
        zeile = f"  {spalte} {typ}"
        if mit_kommentaren and s_kom:
            zeile += f"  -- {s_kom}"
        teile.append(zeile)
    return "\n".join(teile).strip()


@lru_cache(maxsize=1)
def beispielzeilen() -> str:
    """Drei Beispielzeilen je Tabelle — wie das Standard-Tool sql_db_schema aus Lerntag 9."""
    teile = []
    for tab in ("laender", "antriebe", "marken", "zulassungen_monat", "zulassungen_jahr", "kba_monat", "kba_halter_monat"):
        # feste Reihenfolge, damit der Prompt identisch bleibt (Cache, Reproduzierbarkeit)
        sortierung = {"laender": "1", "antriebe": "1", "marken": "konzern = 'Sonstige', marke"}.get(tab, "anzahl DESC")
        spalten, zeilen = abfrage(f"SELECT * FROM markt.{tab} ORDER BY {sortierung} LIMIT 3")
        teile.append(f"markt.{tab}: " + " | ".join(spalten))
        teile += ["  " + " | ".join(str(v) for v in z) for z in zeilen]
    return "\n".join(teile)


@lru_cache(maxsize=1)
def beispielwerte() -> str:
    """Kleine Wertelisten, damit das Modell die Schreibweise kennt (z. B. Marken in GROSSBUCHSTABEN)."""
    _, laender = abfrage("SELECT string_agg(land || '=' || land_name, ', ' ORDER BY land) FROM markt.laender")
    _, antriebe = abfrage("SELECT string_agg(antriebsklasse, ', ') FROM markt.antriebe")
    _, marken = abfrage("""SELECT string_agg(marke, ', ') FROM (SELECT marke FROM markt.zulassungen_jahr
                           GROUP BY marke ORDER BY sum(anzahl) DESC LIMIT 40) t""")
    _, zeit = abfrage("SELECT min(monat), max(monat) FROM markt.zulassungen_monat")
    _, kba = abfrage("SELECT min(monat), max(monat) FROM markt.kba_monat")
    return (f"Länder: {laender[0][0]}\nAntriebsklassen: {antriebe[0][0]}\n"
            f"Die 40 größten Marken (genaue Schreibweise): {marken[0][0]}\n"
            f"co2cars-Monate: {zeit[0][0]} bis {zeit[0][1]}; KBA-Monate (nur DE): {kba[0][0]} bis {kba[0][1]}")
