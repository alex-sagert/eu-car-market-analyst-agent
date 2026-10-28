"""Tests ohne LLM und ohne Datenbank:  python tests/test_sicherheit_und_zahlen.py   (oder pytest)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.sql_guard import pruefe  # noqa: E402
from agent.zahlen import pruefe_antwort  # noqa: E402

ERLAUBT = [
    "SELECT sum(anzahl) FROM markt.zulassungen_jahr WHERE land='DE'",
    "WITH x AS (SELECT * FROM markt.marken) SELECT count(*) FROM x",
    "SELECT a FROM markt.zulassungen_jahr UNION ALL SELECT b FROM markt.kba_monat",
    "SELECT 100.0*sum(anzahl) FILTER (WHERE antriebsklasse='BEV')/sum(anzahl) FROM zulassungen_jahr",
]
BLOCKIERT = [
    "DROP TABLE markt.marken", "DELETE FROM markt.marken", "UPDATE markt.marken SET cn_eng = true",
    "SELECT 1; DROP TABLE markt.marken", "SELECT * FROM pg_authid", "SELECT * FROM information_schema.tables",
    "SELECT pg_read_file('/etc/passwd')", "SELECT pg_sleep(100)", "COPY markt.marken TO '/tmp/x'",
    "SELECT * INTO markt.neu FROM markt.marken", "GRANT ALL ON markt.marken TO public", "SET search_path = public",
    "SELECT dblink('host=x', 'select 1')", "SELECT * FROM public.irgendwas",
]


def test_erlaubt():
    for s in ERLAUBT:
        assert pruefe(s).ok, s


def test_blockiert():
    for s in BLOCKIERT:
        r = pruefe(s)
        assert not r.ok and r.sicherheit, s


def test_syntaxfehler_ist_kein_sicherheitsfall():
    r = pruefe("SELEC foo FROM markt.marken")
    assert not r.ok and not r.sicherheit


def test_zahlenpruefung():
    zeilen = [(14.8733, 46.1411)]
    assert pruefe_antwort("Anstieg von 14,9 % auf 46,1 %, plus 31,3 Prozentpunkte.", zeilen) == []
    assert pruefe_antwort("Anstieg von 14,9 % auf 52,0 %.", zeilen) == ["52,0"]
    assert pruefe_antwort("2.772.310 Pkw, rund 2,77 Mio.", [(2772310,)]) == []
    assert pruefe_antwort("2.772.311 Pkw", [(2772310,)]) == ["2.772.311"]
    assert pruefe_antwort("BEV-Anteil 41,3 %", [(0.413479,)]) == []


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("✔", name)
    print("Alle Tests bestanden.")
