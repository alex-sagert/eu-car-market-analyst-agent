"""Baut die Datenbasis des Agenten aus den EEA-co2cars-Parquet-Dateien (37,1 Mio. Zeilen).

Ergebnis (data/csv/, gzip): kleine, additive Aggregat-Tabellen für PostgreSQL.
Die fachlichen Regeln sind 1:1 aus dem BI-Projekt `eu-ev-tariff-detour`
(02_databricks/0_setup/00_config.py und 3_silver/30_load_silver.py) übernommen,
damit die Zahlen mit dem BI-Bericht übereinstimmen.

Aufruf (nur nötig, wenn die CSVs neu gebaut werden sollen — sie liegen bereits im Repo):
    pip install duckdb
    python data/build_data.py --parquet "<Ordner mit co2cars_2021.parquet ... co2cars_2025.parquet>"
"""
import argparse
import csv
import gzip
import re
import time
from pathlib import Path

import duckdb

HIER = Path(__file__).resolve().parent
OUT = HIER / "csv"

# --- Regeln aus eu-ev-tariff-detour/02_databricks/0_setup/00_config.py -------------------
NICHT_PKW = ("N1", "N1G", "N2", "N2G", "M2", "M2G", "M3")
KLASSE_SQL = """
CASE
  WHEN lower(ft) = 'hydrogen'                 THEN 'FCEV'
  WHEN fm = 'E'                               THEN 'BEV'
  WHEN fm = 'P'                               THEN 'PHEV'
  WHEN fm = 'H'                               THEN 'HEV'
  WHEN fm = 'B' OR lower(ft) IN ('lpg', 'ng') THEN 'GAS'
  WHEN fm = 'F' OR lower(ft) = 'e85'          THEN 'FLEX'
  WHEN fm = 'M' AND lower(ft) = 'diesel'      THEN 'DIESEL'
  WHEN fm = 'M' AND lower(ft) = 'petrol'      THEN 'BENZIN'
  ELSE 'SONST'
END"""
SOLL = {2021: 7164289, 2022: 6853648, 2023: 7685055, 2024: 7666174, 2025: 7770432}

# --- Modellfamilie aus eu-ev-tariff-detour/02_databricks/3_silver/30_load_silver.py ------
STRIP = ['MITSUBISHI ', 'TOYOTA ', 'MAZDA ', 'CUPRA ', 'LYNK & CO ', 'LYNK&CO ', 'BYD ', 'MG ', 'KIA ',
         'HYUNDAI ', 'NISSAN ', 'OPEL ', 'FORD ', 'JEEP ', 'SEAT ', 'LEXUS ', 'SUZUKI ', 'RENAULT ',
         'DACIA ', 'PEUGEOT ', 'CITROEN ', 'FIAT ', 'VOLVO ', 'SKODA ', 'AUDI ', 'TESLA ']


def modellfamilie(marke: str, handelsname: str) -> str:
    s = (handelsname or '').upper().strip()
    for p in STRIP:
        if s.startswith(p) and len(s) > len(p):
            s = s[len(p):]
    s = re.sub(r'\s+', ' ', s.replace(',', ' '))
    m = marke or ''
    if m == 'TESLA':
        r = re.search(r'MODEL ?([3YSX])', s); return f'Model {r.group(1)}' if r else s
    if m == 'VOLKSWAGEN':
        r = re.search(r'ID\.? ?(\d|BUZZ)', s)
        if r: return 'ID.' + r.group(1).title()
        if 'UP' in s: return 'e-up!'
        return s.split(' ')[0].title() if s else s
    if m == 'BMW':
        r = re.match(r'(I?X\d|I\d|IX|Z4|M\d+)', s)
        if r:
            t = r.group(1); return t[0].lower() + t[1:] if t.startswith('I') else t
        r = re.match(r'M?(\d)\d\d', s)
        if r: return f'{r.group(1)}er'
    if m == 'MERCEDES-BENZ':
        r = re.match(r'(EQ[ABCESTV]|GL[ABCES]|CLA|CLE|CLS|SL|[ABCEGSTV])\b', s)
        if r:
            t = r.group(1); return t + ('-Klasse' if len(t) == 1 else '')
    if m == 'AUDI':
        r = re.match(r'(Q\d|A\d|E-TRON GT|E-TRON|S\d|RS ?\d)', s)
        if r: return r.group(1)
    if m == 'HYUNDAI':
        r = re.match(r'IONIQ ?(\d)', s)
        if r: return 'IONIQ ' + r.group(1)
    if m == 'SMART':
        if 'FORTWO' in s or 'FORFOUR' in s: return 'fortwo/forfour'
        r = re.search(r'#\d', s); return r.group(0) if r else s
    if m == 'POLESTAR':
        r = re.search(r'(\d)', s); return f'Polestar {r.group(1)}' if r else s
    if m == 'FORD' and 'MACH' in s: return 'Mustang Mach-E'
    if m == 'MINI': return 'Cooper' if 'COOPER' in s else (s.split(' ')[0].title() if s else s)
    if m == 'KIA' and s.startswith('E-NIRO'): return 'NIRO'
    if m == 'MITSUBISHI' and 'ECLIPSE' in s: return 'Eclipse Cross'
    if m == 'MG':
        r = re.match(r'(MG ?\d|ZS|EHS|HS|MARVEL|CYBERSTER|MG ?S\d)', s)
        if r: return r.group(1).replace(' ', '')
    if m == 'BYD':
        r = re.match(r'(ATTO ?\d|SEAL ?U|SEAL ?\d|SEAL(ION)? ?\d?|DOLPHIN( SURF)?|HAN|TANG)', s)
        if r: return r.group(1).title()
    if m == 'RENAULT':
        for k in ['ZOE', 'MEGANE', 'SCENIC', 'TWINGO', 'R5', 'AUSTRAL', 'CAPTUR', 'RAFALE', 'ARKANA', 'KANGOO', 'CLIO']:
            if s.startswith(k): return k.title()
    first = re.sub(r'[.,;:-]+$', '', s.split(' ')[0]) if s else '(ohne Namen)'
    return first


ANZEIGE_AKRONYM = {'BMW', 'BYD', 'MG', 'DS', 'KGM', 'NIO', 'DR', 'EVO', 'JAC', 'BAIC', 'FAW', 'SWM', 'INEOS', 'SEAT', 'KIA'}
ANZEIGE_SONDER = {'MERCEDES-BENZ': 'Mercedes-Benz', 'ROLLS-ROYCE': 'Rolls-Royce', 'LYNK & CO': 'Lynk & Co',
                  'DFSK/SERES': 'DFSK/Seres', 'CHANGAN/DEEPAL': 'Changan/Deepal', 'UNBEKANNT': 'Unbekannt'}


def anzeige(m: str) -> str:
    if m in ANZEIGE_AKRONYM: return m
    return ANZEIGE_SONDER.get(m, m.title())


def schreibe(con, sql: str, name: str):
    pfad = OUT / f"{name}.csv.gz"
    df = con.execute(sql).df()
    with gzip.open(pfad, "wt", encoding="utf-8", newline="") as fh:
        df.to_csv(fh, index=False, sep=";")
    print(f"  {name}: {len(df):,} Zeilen -> {pfad.name} ({pfad.stat().st_size/1e6:.1f} MB)")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True, help="Ordner mit co2cars_JJJJ.parquet")
    a = ap.parse_args()
    src = Path(a.parquet).as_posix()
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")

    # Referenzen (Marken-Mapping und Stammdaten aus dem BI-Projekt)
    con.execute(f"""CREATE TABLE map AS SELECT quelle, coalesce(marke_roh,'') marke_roh, marke
                    FROM read_csv('{(HIER/'referenz'/'map_marke_roh.csv').as_posix()}', delim=';', header=true, all_varchar=true)""")
    con.execute(f"""CREATE TABLE stamm AS SELECT * FROM read_csv('{(HIER/'referenz'/'stamm_marke.csv').as_posix()}',
                    delim=';', header=true, all_varchar=true)""")

    nicht_pkw = ", ".join(f"'{k}'" for k in NICHT_PKW)
    print("Silber (Fahrzeugebene, nur im Speicher) ...")
    con.execute(f"""
        CREATE TABLE silber AS
        SELECT c.ms AS land, CAST(c.year AS INT) AS jahr,
               CAST(date_trunc('month', TRY_CAST(c.dr AS DATE)) AS DATE) AS monat,
               coalesce(m.marke, 'UNBEKANNT') AS marke,
               coalesce(upper(trim(c.cn)), '') AS handelsname,
               {KLASSE_SQL} AS antriebsklasse,
               TRY_CAST(c.m_kg AS DOUBLE) AS masse_kg, TRY_CAST(c.ewltp AS DOUBLE) AS co2,
               TRY_CAST(c.z_whkm AS DOUBLE) AS strom, TRY_CAST(c.ep_kw AS DOUBLE) AS kw
        FROM read_parquet('{src}/co2cars_*.parquet') c
        LEFT JOIN map m ON m.quelle = 'co2cars' AND m.marke_roh = coalesce(upper(trim(c.mk)), '')
        WHERE coalesce(trim(c.ct), '') NOT IN ({nicht_pkw})""")
    for jahr, n in con.execute("SELECT jahr, count(*) FROM silber GROUP BY 1 ORDER BY 1").fetchall():
        print(f"  {jahr}: {n:,} Pkw (Quelle {SOLL[jahr]:,}, ohne Nicht-Pkw {SOLL[jahr]-n:,})")

    print("Modellfamilien ...")
    paare = con.execute("SELECT marke, handelsname FROM silber GROUP BY ALL").fetchall()
    con.execute("CREATE TABLE map_modell (marke VARCHAR, handelsname VARCHAR, modell VARCHAR)")
    con.executemany("INSERT INTO map_modell VALUES (?, ?, ?)",
                    [(m, h, modellfamilie(m, h)) for m, h in paare])
    print(f"  {len(paare):,} Paare Marke × Handelsname")

    kennzahlen = """count(*) AS anzahl,
        round(sum(masse_kg)) AS summe_masse_kg, count(masse_kg) AS anzahl_mit_masse,
        round(sum(co2), 1) AS summe_co2_wltp, count(co2) AS anzahl_mit_co2,
        round(sum(strom), 1) AS summe_strom_whkm, count(strom) AS anzahl_mit_strom,
        round(sum(kw), 1) AS summe_leistung_kw, count(kw) AS anzahl_mit_leistung,
        count(*) FILTER (WHERE masse_kg > 2000) AS anzahl_ueber_2t"""
    join = "FROM silber s JOIN map_modell mm ON mm.marke = s.marke AND mm.handelsname = s.handelsname"

    print("Schreibe CSV ...")
    schreibe(con, f"""SELECT s.monat, s.jahr, s.land, s.marke, mm.modell, s.antriebsklasse, {kennzahlen}
                      {join} WHERE s.monat IS NOT NULL GROUP BY ALL ORDER BY ALL""", "zulassungen_monat")
    schreibe(con, f"""SELECT s.jahr, s.land, s.marke, mm.modell, s.antriebsklasse, {kennzahlen}
                      {join} GROUP BY ALL ORDER BY ALL""", "zulassungen_jahr")

    # Marken: Stammdaten + alle Marken, die in den Daten vorkommen (ungepflegte -> 'Sonstige')
    marken = con.execute("""
        WITH alle AS (SELECT DISTINCT marke FROM silber UNION SELECT marke FROM stamm)
        SELECT a.marke, coalesce(s.konzern, 'Sonstige') AS konzern, s.markenland,
               nullif(s.heimatmarkt, '') AS heimatmarkt,
               coalesce(s.cn_eng = 'true', false) AS cn_eng, coalesce(s.cn_weit = 'true', false) AS cn_weit
        FROM alle a LEFT JOIN stamm s USING (marke) ORDER BY 1""").df()
    marken.insert(1, "marke_anzeige", [anzeige(m) for m in marken.marke])
    with gzip.open(OUT / "marken.csv.gz", "wt", encoding="utf-8", newline="") as fh:
        marken.to_csv(fh, index=False, sep=";")
    print(f"  marken: {len(marken)} Zeilen")

    # KBA (nur Deutschland, Monatsstatistik FZ 28) — langes Format wie silver.kba_marke_monat
    con.execute(f"""CREATE TABLE kba AS SELECT * FROM read_csv('{(HIER/'kba'/'kba_fz28_marke.csv').as_posix()}',
                    delim=';', header=true, all_varchar=true)""")
    schreibe(con, """
        WITH b AS (
          SELECT CAST(k.monat || '-01' AS DATE) AS monat, coalesce(m.marke, k.marke_kba) AS marke,
                 CAST(gesamt AS INT) g, CAST(alternativ_gesamt AS INT) alt, CAST(bev AS INT) bev, CAST(phev AS INT) phev,
                 CAST(fcev AS INT) fcev, CAST(hybrid_gesamt AS INT) hev, CAST(gas AS INT) gas, CAST(wasserstoff AS INT) h2
          FROM kba k LEFT JOIN map m ON m.quelle = 'kba' AND m.marke_roh = k.marke_kba
          WHERE k.marke_kba <> 'INSGESAMT')
        SELECT monat, marke, antriebsklasse, CAST(sum(anzahl) AS INT) AS anzahl FROM (
          SELECT monat, marke, 'BEV' antriebsklasse, bev anzahl FROM b UNION ALL
          SELECT monat, marke, 'PHEV', phev FROM b UNION ALL
          SELECT monat, marke, 'FCEV', fcev FROM b UNION ALL
          SELECT monat, marke, 'HEV', hev FROM b UNION ALL
          SELECT monat, marke, 'GAS', gas FROM b UNION ALL
          SELECT monat, marke, 'SONST', h2 FROM b UNION ALL
          SELECT monat, marke, 'KBA_VERBRENNER', g - alt FROM b)
        GROUP BY ALL HAVING sum(anzahl) <> 0 ORDER BY ALL""", "kba_monat")

    con.execute(f"""CREATE TABLE kbah AS SELECT * FROM read_csv('{(HIER/'kba'/'kba_fz28_halter.csv').as_posix()}',
                    delim=';', header=true, all_varchar=true)""")
    schreibe(con, """
        WITH b AS (
          SELECT CAST(monat || '-01' AS DATE) AS monat,
                 CASE WHEN regexp_matches(haltergruppe, '^[A-Za-zäöüÄÖÜ]+ [0-9]{4}$') THEN 'Insgesamt'
                      WHEN haltergruppe LIKE 'Private%'       THEN 'Privat'
                      WHEN haltergruppe LIKE 'Gewerbliche%'   THEN 'Gewerblich'
                      WHEN haltergruppe LIKE '%Kfz-Handel%'   THEN 'davon Kfz-Handel'
                      WHEN haltergruppe LIKE '%Kfz-Herstell%' THEN 'davon Kfz-Hersteller'
                      WHEN haltergruppe LIKE '%Vermietung%'   THEN 'davon Vermietung/Carsharing'
                      ELSE 'Unbekannt' END AS haltergruppe,
                 CAST(gesamt AS INT) g, CAST(bev AS INT) bev, CAST(phev AS INT) phev, CAST(hybrid_gesamt AS INT) hev
          FROM kbah)
        SELECT monat, haltergruppe, kategorie, anzahl FROM (
          SELECT monat, haltergruppe, 'GESAMT' kategorie, g anzahl FROM b UNION ALL
          SELECT monat, haltergruppe, 'BEV', bev FROM b UNION ALL
          SELECT monat, haltergruppe, 'PHEV', phev FROM b UNION ALL
          SELECT monat, haltergruppe, 'HEV', hev FROM b) ORDER BY ALL""", "kba_halter_monat")

    print(f"Fertig in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
