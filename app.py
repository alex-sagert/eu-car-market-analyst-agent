"""Streamlit-Oberfläche:  streamlit run app.py"""
import uuid

import pandas as pd
import streamlit as st

from agent.config import PROFILE, modellname
from agent.graph import Agent

st.set_page_config(page_title="Frag den Neuwagenmarkt", page_icon="🚗", layout="wide")

BEISPIELE = [
    "Wie hoch war der BEV-Anteil in den Niederlanden 2025?",
    "Wie hoch war der Marktanteil chinesischer Marken in Deutschland 2025?",
    "Wie stark ist der PHEV-Anteil bei chinesischen Marken seit den EU-Zöllen gestiegen?",
    "Welche drei Marken hatten 2025 in Spanien die meisten Elektroauto-Neuzulassungen?",
    "Wie hoch ist der Restwert eines VW ID.3 nach drei Jahren?",
]


@st.cache_resource
def agent_fuer(profil: str) -> Agent:
    return Agent(profil)


with st.sidebar:
    st.header("Einstellungen")
    profil = st.radio("Profil", list(PROFILE), index=1,
                      format_func=lambda p: f"{p} — {PROFILE[p]['name']}")
    st.caption(modellname(PROFILE[profil]["modell"]))
    st.divider()
    st.caption("Beispielfragen")
    for b in BEISPIELE:
        if st.button(b, width="stretch"):
            st.session_state.vorschlag = b
    if st.button("Verlauf löschen"):
        st.session_state.verlauf = []
        st.session_state.offen = None

st.title("Frag den Neuwagenmarkt")
st.caption("37,1 Mio. Pkw-Neuzulassungen (EEA co2cars 2021–2025: DE, FR, IT, ES, NL, NO) + KBA Deutschland bis 08/2026. "
           "Jede Zahl stammt aus einer geprüften SQL-Abfrage.")

st.session_state.setdefault("verlauf", [])
st.session_state.setdefault("offen", None)       # (thread_id, rueckfrage_daten, frage, profil)


def ergebnis_zeigen(erg):
    status = erg.get("status")
    farbe = {"ok": "green", "warnung": "orange", "abgelehnt": "gray", "blockiert": "red", "fehler": "red"}.get(status, "blue")
    st.markdown(f":{farbe}[**{status}**] · {erg.get('sekunden', 0)} s · {erg.get('llm_aufrufe', 0)} LLM-Aufrufe · "
                f"{erg.get('versuche', 0)} SQL-Versuch(e)")
    st.write(erg.get("antwort", ""))
    if erg.get("zeilen"):
        df = pd.DataFrame(erg["zeilen"], columns=erg.get("spalten"))
        st.dataframe(df, hide_index=True, width="stretch")
        zahlen = df.select_dtypes("number").columns
        if len(df) > 1 and len(zahlen) >= 1 and len(df.columns) > len(zahlen):
            st.bar_chart(df, x=df.columns[0], y=list(zahlen)[:3])
    if erg.get("sql"):
        with st.expander("SQL und Ablauf"):
            st.code(erg["sql"], language="sql")
            for s in erg.get("schritte", []):
                st.text("• " + s)


for eintrag in st.session_state.verlauf:
    with st.chat_message("user"):
        st.write(eintrag["frage"])
    with st.chat_message("assistant"):
        ergebnis_zeigen(eintrag["erg"])

offen = st.session_state.offen
if offen:
    thread_id, daten, frage, p = offen
    with st.chat_message("user"):
        st.write(frage)
    with st.chat_message("assistant"):
        st.info(f"**Rückfrage:** {daten['rueckfrage']}")
        wahl = None
        for o in daten.get("optionen", []):
            if st.button(o, key=f"opt-{thread_id}-{o}"):
                wahl = o
        eigene = st.text_input("oder eigene Präzisierung", key=f"eigen-{thread_id}")
        if st.button("Senden", key=f"senden-{thread_id}") and eigene:
            wahl = eigene
        if wahl:
            with st.spinner("Rechne ..."):
                erg = agent_fuer(p).antworten(thread_id, wahl)
            st.session_state.offen = None
            st.session_state.verlauf.append({"frage": f"{frage}  →  {wahl}", "erg": erg})
            st.rerun()

frage = st.chat_input("Frage zu Neuzulassungen stellen ...") or st.session_state.pop("vorschlag", None)
if frage and not offen:
    with st.spinner("Rechne ..."):
        erg = agent_fuer(profil).fragen(frage, thread_id=str(uuid.uuid4()))
    if erg.get("status") == "rueckfrage":
        st.session_state.offen = (erg["thread_id"], erg["rueckfrage_daten"], frage, profil)
    else:
        st.session_state.verlauf.append({"frage": frage, "erg": erg})
    st.rerun()
