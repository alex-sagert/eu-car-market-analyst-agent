"""Aufbau des LangGraph-Agenten.  `python -m agent.graph` schreibt docs/graph.md (Mermaid)."""
import time
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from agent import nodes
from agent.config import MAX_VERSUCHE, PROFILE
from agent.state import AgentState


def _nach_start(s):
    return "einordnen" if PROFILE[s["profil"]]["einordnen"] else "sql_entwerfen"


def _nach_einordnen(s):
    return {"beantwortbar": "sql_entwerfen", "mehrdeutig": "rueckfrage"}.get(s["typ"], "ablehnen")


def _nach_entwurf(s):
    return "sql_pruefen" if s.get("sql") else "ablehnen"


def _nach_pruefung(s):
    if s.get("status") == "blockiert":
        return END
    if s.get("pruefung_ok"):
        return "ausfuehren"
    return "sql_entwerfen" if s.get("versuche", 0) < MAX_VERSUCHE else "aufgeben"


def _nach_ausfuehren(s):
    if s.get("ausfuehrung_ok"):
        return "antworten"
    return "sql_entwerfen" if s.get("versuche", 0) < MAX_VERSUCHE else "aufgeben"


def _nach_antwort(s):
    return "zahlen_pruefen" if PROFILE[s["profil"]]["zahlen_pruefen"] else END


def baue_graph(checkpointer=None):
    g = StateGraph(AgentState)
    for name in ("einordnen", "rueckfrage", "ablehnen", "sql_entwerfen", "sql_pruefen", "ausfuehren",
                 "antworten", "zahlen_pruefen", "aufgeben"):
        g.add_node(name, getattr(nodes, name))
    g.add_conditional_edges(START, _nach_start, ["einordnen", "sql_entwerfen"])
    g.add_conditional_edges("einordnen", _nach_einordnen, ["sql_entwerfen", "rueckfrage", "ablehnen"])
    g.add_edge("rueckfrage", "sql_entwerfen")
    g.add_conditional_edges("sql_entwerfen", _nach_entwurf, ["sql_pruefen", "ablehnen"])
    g.add_conditional_edges("sql_pruefen", _nach_pruefung, ["ausfuehren", "sql_entwerfen", "aufgeben", END])
    g.add_conditional_edges("ausfuehren", _nach_ausfuehren, ["antworten", "sql_entwerfen", "aufgeben"])
    g.add_conditional_edges("antworten", _nach_antwort, ["zahlen_pruefen", END])
    for n in ("ablehnen", "zahlen_pruefen", "aufgeben"):
        g.add_edge(n, END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())


class Agent:
    """Bequeme Hülle: fragen() startet, antworten() setzt nach einer Rückfrage fort."""

    def __init__(self, profil="B"):
        self.profil = profil
        self.graph = baue_graph()

    def fragen(self, frage: str, thread_id: str | None = None) -> dict:
        thread_id = thread_id or str(uuid.uuid4())
        start = {"frage": frage, "profil": self.profil, "fehler": [], "versuche": 0, "llm_aufrufe": 0,
                 "schritte": [], "zeilen": None}
        return self._lauf(start, thread_id)

    def antworten(self, thread_id: str, antwort: str) -> dict:
        return self._lauf(Command(resume=antwort), thread_id)

    def _lauf(self, eingabe, thread_id) -> dict:
        cfg = {"configurable": {"thread_id": thread_id}, "recursion_limit": 30}
        t0 = time.time()
        erg = self.graph.invoke(eingabe, cfg)
        erg = dict(erg)
        erg["thread_id"] = thread_id
        erg["sekunden"] = round(time.time() - t0, 2)
        if erg.get("__interrupt__"):
            erg["status"] = "rueckfrage"
            erg["rueckfrage_daten"] = erg["__interrupt__"][0].value
        return erg


if __name__ == "__main__":
    from agent.config import BASIS
    mermaid = baue_graph().get_graph().draw_mermaid()
    (BASIS / "docs" / "graph.md").write_text(f"# Agent-Graph\n\n```mermaid\n{mermaid}\n```\n", encoding="utf-8")
    print(mermaid)
