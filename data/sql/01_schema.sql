-- Schema "markt": die Daten, die der Agent lesen darf.
-- Wird von data/load_postgres.py ausgeführt (als Admin, z. B. postgres).
-- Alle Kennzahlen sind additiv gespeichert (Summen und Anzahlen). Durchschnitte und Anteile
-- entstehen erst in der Abfrage: Summe / Anzahl.

DROP SCHEMA IF EXISTS markt CASCADE;
CREATE SCHEMA markt;
COMMENT ON SCHEMA markt IS 'Pkw-Neuzulassungen Europa (EEA co2cars 2021-2025: DE, FR, IT, ES, NL, NO) und Deutschland-Monatsstatistik des KBA. Nur lesen.';

-- ---------------------------------------------------------------- Dimensionen
CREATE TABLE markt.laender (
    land          char(2) PRIMARY KEY,
    land_name     text    NOT NULL,
    eu_zollunion  boolean NOT NULL
);
INSERT INTO markt.laender VALUES
    ('DE', 'Deutschland', true), ('ES', 'Spanien', true), ('FR', 'Frankreich', true),
    ('IT', 'Italien', true), ('NL', 'Niederlande', true), ('NO', 'Norwegen', false);
COMMENT ON TABLE  markt.laender IS 'Die sechs Länder im Datensatz. Andere EU-Länder sind NICHT enthalten.';
COMMENT ON COLUMN markt.laender.land IS 'ISO-Ländercode: DE, ES, FR, IT, NL, NO';
COMMENT ON COLUMN markt.laender.eu_zollunion IS 'false nur für Norwegen - dort gelten EU-Zölle nicht';

CREATE TABLE markt.antriebe (
    antriebsklasse      text PRIMARY KEY,
    bezeichnung         text    NOT NULL,
    gruppe              text    NOT NULL,
    ist_elektrifiziert  boolean NOT NULL,
    ist_extern_ladbar   boolean NOT NULL
);
INSERT INTO markt.antriebe VALUES
    ('BEV',            'Batterieelektrisch (Elektroauto)',      'BEV',          true,  true),
    ('PHEV',           'Plug-in-Hybrid',                        'PHEV',         true,  true),
    ('HEV',            'Hybrid ohne Stecker (inkl. Mild-Hybrid)', 'HEV',        true,  false),
    ('BENZIN',         'Benzin',                                'Verbrenner',   false, false),
    ('DIESEL',         'Diesel',                                'Verbrenner',   false, false),
    ('KBA_VERBRENNER', 'Benzin und Diesel zusammen (nur KBA)',  'Verbrenner',   false, false),
    ('GAS',            'Gas (LPG/CNG)',                         'Gas/Sonstige', false, false),
    ('FLEX',           'Flex-Fuel E85',                         'Gas/Sonstige', false, false),
    ('FCEV',           'Brennstoffzelle (Wasserstoff)',         'Gas/Sonstige', true,  false),
    ('SONST',          'Sonstige/unbekannt',                    'Gas/Sonstige', false, false);
COMMENT ON TABLE markt.antriebe IS 'Antriebsklassen. BEV = reines Elektroauto, PHEV = Plug-in-Hybrid, HEV = Hybrid ohne Stecker.';

CREATE TABLE markt.marken (
    marke          text PRIMARY KEY,
    marke_anzeige  text    NOT NULL,
    konzern        text    NOT NULL,
    markenland     text,
    heimatmarkt    text,
    cn_eng         boolean NOT NULL,
    cn_weit        boolean NOT NULL
);
COMMENT ON TABLE  markt.marken IS 'Marken-Stammdaten. marke ist in GROSSBUCHSTABEN normiert (z. B. VOLKSWAGEN, MERCEDES-BENZ, BYD, MG, TESLA).';
COMMENT ON COLUMN markt.marken.marke IS 'Normierter Markenname in Großbuchstaben, Schlüssel für alle Faktentabellen';
COMMENT ON COLUMN markt.marken.konzern IS 'Konzern, z. B. Volkswagen AG, Stellantis, BYD, SAIC, Geely; Sonstige = nicht gepflegt';
COMMENT ON COLUMN markt.marken.markenland IS 'Herkunftsland der Marke (CN = China)';
COMMENT ON COLUMN markt.marken.heimatmarkt IS 'Land, in dem die Marke Heimvorteil hat (DE, FR, IT, ES), sonst leer';
COMMENT ON COLUMN markt.marken.cn_eng IS 'Chinesische Marke im engen Sinn: Marken chinesischer Konzerne mit eigenem Auftritt (BYD, MG, Leapmotor, Omoda, Jaecoo, Xpeng ...)';
COMMENT ON COLUMN markt.marken.cn_weit IS 'Chinesische Marke im weiten Sinn: cn_eng plus Marken unter chinesischer Kontrolle oder auf chinesischer Plattform (Volvo, Polestar, smart, Lotus, DR, EVO, Ebro, Elaris)';

-- ---------------------------------------------------------------- Fakten co2cars
CREATE TABLE markt.zulassungen_monat (
    monat               date    NOT NULL,
    jahr                int     NOT NULL,
    land                char(2) NOT NULL REFERENCES markt.laender,
    marke               text    NOT NULL REFERENCES markt.marken,
    modell              text,
    antriebsklasse      text    NOT NULL REFERENCES markt.antriebe,
    anzahl              int     NOT NULL,
    summe_masse_kg      double precision, anzahl_mit_masse    int,
    summe_co2_wltp      double precision, anzahl_mit_co2      int,
    summe_strom_whkm    double precision, anzahl_mit_strom    int,
    summe_leistung_kw   double precision, anzahl_mit_leistung int,
    anzahl_ueber_2t     int
);
COMMENT ON TABLE markt.zulassungen_monat IS 'Pkw-Neuzulassungen je Monat x Land x Marke x Modellfamilie x Antriebsklasse (EEA co2cars, 2021-01 bis 2025-12). Nur Fahrzeuge MIT Zulassungsdatum - für Jahressummen markt.zulassungen_jahr verwenden.';
COMMENT ON COLUMN markt.zulassungen_monat.monat IS 'Erster Tag des Zulassungsmonats, z. B. 2024-11-01';
COMMENT ON COLUMN markt.zulassungen_monat.modell IS 'Modellfamilie, z. B. Model Y, ID.3, Seal U, KUGA (Schreibweise uneinheitlich, mit ILIKE filtern)';
COMMENT ON COLUMN markt.zulassungen_monat.anzahl IS 'Anzahl neu zugelassener Pkw';
COMMENT ON COLUMN markt.zulassungen_monat.summe_masse_kg IS 'Summe Fahrzeugmasse; Durchschnitt = sum(summe_masse_kg)/sum(anzahl_mit_masse)';
COMMENT ON COLUMN markt.zulassungen_monat.summe_co2_wltp IS 'Summe CO2 WLTP g/km; Durchschnitt = sum(summe_co2_wltp)/sum(anzahl_mit_co2)';
COMMENT ON COLUMN markt.zulassungen_monat.summe_strom_whkm IS 'Summe Stromverbrauch Wh/km; Durchschnitt = sum(summe_strom_whkm)/sum(anzahl_mit_strom)';
COMMENT ON COLUMN markt.zulassungen_monat.summe_leistung_kw IS 'Summe Leistung kW; Durchschnitt = sum(summe_leistung_kw)/sum(anzahl_mit_leistung)';
COMMENT ON COLUMN markt.zulassungen_monat.anzahl_ueber_2t IS 'Fahrzeuge mit Masse über 2000 kg';

CREATE TABLE markt.zulassungen_jahr (LIKE markt.zulassungen_monat);
ALTER TABLE markt.zulassungen_jahr DROP COLUMN monat;
COMMENT ON TABLE markt.zulassungen_jahr IS 'Pkw-Neuzulassungen je Jahr x Land x Marke x Modellfamilie x Antriebsklasse (EEA co2cars 2021-2025). Enthält ALLE Fahrzeuge, auch ohne Zulassungsdatum (2021 rund 7 %). Für Jahreswerte immer diese Tabelle.';
COMMENT ON COLUMN markt.zulassungen_jahr.anzahl IS 'Anzahl neu zugelassener Pkw';

-- ---------------------------------------------------------------- Fakten KBA
CREATE TABLE markt.kba_monat (
    monat           date NOT NULL,
    marke           text NOT NULL,
    antriebsklasse  text NOT NULL REFERENCES markt.antriebe,
    anzahl          int  NOT NULL
);
COMMENT ON TABLE markt.kba_monat IS 'KBA FZ 28.4: Pkw-Neuzulassungen NUR Deutschland je Monat x Marke x Antrieb, 2025-01 bis 2026-08. Benzin und Diesel sind zusammengefasst (KBA_VERBRENNER). Einzige Quelle für 2026.';

CREATE TABLE markt.kba_halter_monat (
    monat         date NOT NULL,
    haltergruppe  text NOT NULL,
    kategorie     text NOT NULL,
    anzahl        int  NOT NULL
);
COMMENT ON TABLE markt.kba_halter_monat IS 'KBA FZ 28.3: Pkw-Neuzulassungen NUR Deutschland je Monat nach Haltergruppe, 2025-01 bis 2026-08.';
COMMENT ON COLUMN markt.kba_halter_monat.haltergruppe IS 'Insgesamt, Privat, Gewerblich; davon-Zeilen (Teilmengen von Gewerblich): davon Kfz-Handel, davon Kfz-Hersteller, davon Vermietung/Carsharing';
COMMENT ON COLUMN markt.kba_halter_monat.kategorie IS 'GESAMT, BEV, PHEV, HEV';
