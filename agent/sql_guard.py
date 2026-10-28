"""SQL-Prüfung in Python — die zweite von drei Sicherheitsstufen.

1. Prompt: "nur SELECT" (kann ein Modell ignorieren)
2. Diese Prüfung: SQL wird geparst (sqlglot), nicht per Textsuche geprüft
3. Datenbank: Rolle agent_leser darf nur lesen, Transaktion read-only, Timeout 15 s
"""
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

ERLAUBTE_TABELLEN = {"laender", "antriebe", "marken", "zulassungen_monat", "zulassungen_jahr",
                     "kba_monat", "kba_halter_monat"}
VERBOTENE_FUNKTIONEN = {"dblink", "lo_import", "lo_export", "set_config", "current_setting",
                        "query_to_xml", "copy", "pg_sleep"}
VERBOTENE_KNOTEN = tuple(getattr(exp, n) for n in (
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command", "Merge", "TruncateTable",
    "Into", "Grant", "Revoke", "Copy", "Set", "Transaction", "Commit", "Rollback") if hasattr(exp, n))


@dataclass
class Pruefung:
    ok: bool
    grund: str = ""
    sicherheit: bool = False      # True = Sicherheitsverstoß -> sofort blockieren, kein neuer Versuch


def pruefe(sql: str) -> Pruefung:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        return Pruefung(False, "leere Abfrage")
    try:
        teile = [t for t in sqlglot.parse(sql, read="postgres") if t is not None]
    except sqlglot.errors.ParseError as e:
        return Pruefung(False, f"SQL nicht lesbar: {str(e).splitlines()[0][:200]}")
    if len(teile) != 1:
        return Pruefung(False, "genau eine Anweisung erlaubt", sicherheit=True)
    baum = teile[0]
    for knoten in baum.walk():
        if isinstance(knoten, VERBOTENE_KNOTEN):
            return Pruefung(False, f"nicht erlaubt: {type(knoten).__name__} (nur SELECT)", sicherheit=True)
    if not isinstance(baum, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        return Pruefung(False, f"keine gültige SELECT-Abfrage ({type(baum).__name__})")

    cte_namen = {c.alias_or_name.lower() for c in baum.find_all(exp.CTE)}
    for t in baum.find_all(exp.Table):
        name, schema = t.name.lower(), (t.db or "").lower()
        if not name or name in cte_namen and not schema:
            continue
        if name.startswith("pg_") or schema in ("pg_catalog", "information_schema"):
            return Pruefung(False, f"Systemtabelle {name} nicht erlaubt", sicherheit=True)
        if schema not in ("", "markt"):
            return Pruefung(False, f"Schema {schema} nicht erlaubt", sicherheit=True)
        if name not in ERLAUBTE_TABELLEN:
            return Pruefung(False, f"unbekannte Tabelle {name}; erlaubt: {', '.join(sorted(ERLAUBTE_TABELLEN))}")
    for f in baum.find_all(exp.Func):
        fname = (f.sql_name() if not isinstance(f, exp.Anonymous) else f.name).lower()
        if fname.startswith("pg_") or fname in VERBOTENE_FUNKTIONEN:
            return Pruefung(False, f"Funktion {fname} nicht erlaubt", sicherheit=True)
    return Pruefung(True)
