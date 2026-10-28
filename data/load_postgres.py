"""Lädt die Agent-Daten in PostgreSQL und legt den Nur-Lese-Benutzer an.

Einmal ausführen (Werte kommen aus .env):
    python data/load_postgres.py

Was passiert:
1. Datenbank PG_DB anlegen (falls nicht vorhanden)
2. Schema "markt" mit Tabellen und Kommentaren (data/sql/01_schema.sql)
3. CSV-Dateien aus data/csv/ per COPY laden, Zeilen kontrollieren
4. Rolle PG_AGENT_USER anlegen: darf NUR lesen (SELECT), Transaktionen read-only, Timeout 15 s
"""
import gzip
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

HIER = Path(__file__).resolve().parent
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass
load_dotenv(HIER.parent / ".env")

HOST = os.getenv("PG_HOST", "localhost")
PORT = os.getenv("PG_PORT", "5432")
DB = os.getenv("PG_DB", "markt_agent")
ADMIN = os.getenv("PG_ADMIN_USER", "postgres")
ADMIN_PW = os.getenv("PG_ADMIN_PASSWORD", "")
AGENT = os.getenv("PG_AGENT_USER", "agent_leser")
AGENT_PW = os.getenv("PG_AGENT_PASSWORD", "nur_lesen")

# Soll-Zeilen = Grain des BI-Projekts eu-ev-tariff-detour (fact_zulassung_monat 191.227, _jahr 24.557)
TABELLEN = {
    "marken": None,
    "zulassungen_monat": 191227,
    "zulassungen_jahr": 24557,
    "kba_monat": None,
    "kba_halter_monat": None,
}


def verbinden(datenbank: str, autocommit=False):
    return psycopg.connect(host=HOST, port=PORT, dbname=datenbank, user=ADMIN, password=ADMIN_PW,
                           autocommit=autocommit)


def main():
    if not ADMIN_PW:
        sys.exit("PG_ADMIN_PASSWORD fehlt in .env (Passwort des Benutzers postgres aus der Installation).")

    with verbinden("postgres", autocommit=True) as con:
        if not con.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB,)).fetchone():
            con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB)))
            print(f"Datenbank {DB} angelegt")
        else:
            print(f"Datenbank {DB} vorhanden")

    with verbinden(DB) as con:
        con.execute((HIER / "sql" / "01_schema.sql").read_text(encoding="utf-8"))
        print("Schema markt angelegt")
        for tabelle, soll in TABELLEN.items():
            pfad = HIER / "csv" / f"{tabelle}.csv.gz"
            with gzip.open(pfad, "rt", encoding="utf-8") as fh:
                kopf = fh.readline().strip().split(";")
                spalten = sql.SQL(", ").join(sql.Identifier(s) for s in kopf)
                befehl = sql.SQL("COPY markt.{} ({}) FROM STDIN WITH (FORMAT csv, DELIMITER ';', NULL '')").format(
                    sql.Identifier(tabelle), spalten)
                with con.cursor().copy(befehl) as cp:
                    while daten := fh.read(1 << 20):
                        cp.write(daten)
            n = con.execute(sql.SQL("SELECT count(*) FROM markt.{}").format(sql.Identifier(tabelle))).fetchone()[0]
            status = "" if soll is None else ("  ✔ = BI-Projekt" if n == soll else f"  ✘ Soll {soll:,}")
            print(f"  {tabelle:<20} {n:>9,} Zeilen{status}")

        # Indizes für die typischen Filter
        con.execute("CREATE INDEX ON markt.zulassungen_monat (monat, land)")
        con.execute("CREATE INDEX ON markt.zulassungen_monat (marke)")
        con.execute("CREATE INDEX ON markt.zulassungen_jahr (jahr, land)")
        con.execute("ANALYZE")

        # Nur-Lese-Rolle (dritte Sicherheitsstufe nach Prompt und SQL-Prüfung)
        if not con.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (AGENT,)).fetchone():
            con.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(AGENT), sql.Literal(AGENT_PW)))
        else:
            con.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(AGENT), sql.Literal(AGENT_PW)))
        r = sql.Identifier(AGENT)
        con.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(DB), r))
        con.execute(sql.SQL("GRANT USAGE ON SCHEMA markt TO {}").format(r))
        con.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA markt TO {}").format(r))
        con.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(r))
        con.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(r))
        con.execute(sql.SQL("ALTER ROLE {} SET statement_timeout = '15s'").format(r))
        con.execute(sql.SQL("ALTER ROLE {} SET search_path = markt").format(r))
        con.commit()
        print(f"Rolle {AGENT}: nur SELECT auf Schema markt, read-only, Timeout 15 s")

    # Gegenprobe: darf der Agent-Benutzer wirklich nicht schreiben?
    with psycopg.connect(host=HOST, port=PORT, dbname=DB, user=AGENT, password=AGENT_PW) as con:
        try:
            con.execute("DELETE FROM markt.laender WHERE land = 'NO'")
            print("✘ ACHTUNG: Agent-Benutzer konnte schreiben!")
        except psycopg.Error as e:
            print(f"✔ Schreibversuch als {AGENT} abgewiesen: {type(e).__name__}")
    print("Fertig.")


if __name__ == "__main__":
    main()
