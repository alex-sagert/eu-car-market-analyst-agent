"""Zentrale Konfiguration: Profile, Modelle, Cache — an genau einer Stelle."""
import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

warnings.filterwarnings("ignore", message=".*langchain-community.*")
BASIS = Path(__file__).resolve().parent.parent
load_dotenv(BASIS / ".env")

# ---------------------------------------------------------------------------------------
# Profile = Versuchsbedingungen der Evaluation. Gleiche Sicherheitsschicht (SQL-Prüfung +
# Nur-Lese-Rolle) in allen Profilen; unterschiedlich ist nur der fachliche Kontext.
# ---------------------------------------------------------------------------------------
PROFILE = {
    "A": dict(name="Baseline: nur Schema", modell="cloud",
              kommentare=False, katalog=False, beispiele=0, einordnen=False, zahlen_pruefen=False),
    "B": dict(name="Semantische Schicht (Cloud-Modell)", modell="cloud",
              kommentare=True, katalog=True, beispiele=4, einordnen=True, zahlen_pruefen=True),
    "C": dict(name="Semantische Schicht (lokales Modell)", modell="lokal",
              kommentare=True, katalog=True, beispiele=4, einordnen=True, zahlen_pruefen=True),
    "D": dict(name="Baseline lokal: nur Schema", modell="lokal",
              kommentare=False, katalog=False, beispiele=0, einordnen=False, zahlen_pruefen=False),
    # Zusatz nach Lauf 2: größeres lokales Code-Modell (passt in 8 GB VRAM) — prüft H2 mit 7B statt 3B
    "E": dict(name="Semantische Schicht (lokales 7B-Code-Modell)", modell="lokal2",
              kommentare=True, katalog=True, beispiele=4, einordnen=True, zahlen_pruefen=True),
}
MAX_VERSUCHE = 3          # SQL-Entwürfe pro Frage (Selbstkorrektur nach Fehler), alle Profile gleich

# Modelle: Wechsel nur über .env
CLOUD_PROVIDER = os.getenv("LLM_PROVIDER", "ollama_cloud")      # ollama_cloud | gemini | orakel
OLLAMA_CLOUD_MODEL = os.getenv("OLLAMA_CLOUD_MODEL", "gpt-oss:120b")
OLLAMA_LOCAL_MODEL = os.getenv("OLLAMA_LOCAL_MODEL", "llama3.2")
OLLAMA_LOCAL_MODEL_2 = os.getenv("OLLAMA_LOCAL_MODEL_2", "qwen2.5-coder:7b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

def get_llm(modell: str = "cloud"):
    """modell: 'cloud' (Provider aus LLM_PROVIDER) oder 'lokal' (Ollama auf diesem Rechner)."""
    provider = {"lokal": "ollama_local", "lokal2": "ollama_local2"}.get(modell, CLOUD_PROVIDER)
    if os.getenv("LLM_PROVIDER") == "orakel":
        provider = "orakel"
    if provider == "orakel":
        from agent.orakel import OrakelLLM
        return OrakelLLM()
    if provider == "ollama_cloud":
        from langchain_ollama import ChatOllama
        key = os.getenv("OLLAMA_API_KEY")
        if not key:
            raise RuntimeError("OLLAMA_API_KEY fehlt in .env (ollama.com -> Settings -> Keys)")
        return ChatOllama(model=OLLAMA_CLOUD_MODEL, base_url="https://ollama.com", temperature=0,
                          client_kwargs={"headers": {"Authorization": f"Bearer {key}"}, "timeout": 120})
    if provider in ("ollama_local", "ollama_local2"):
        from langchain_ollama import ChatOllama
        name = OLLAMA_LOCAL_MODEL if provider == "ollama_local" else OLLAMA_LOCAL_MODEL_2
        # Schutz gegen Endlosschleifen kleiner Modelle (Lauf 2, Profil E hing bei G22):
        # höchstens 1.024 Antwort-Tokens, nach 180 s Abbruch -> Frage zählt als "abbruch", Lauf geht weiter
        return ChatOllama(model=name, temperature=0, num_ctx=8192, num_predict=1024,
                          client_kwargs={"timeout": 180})
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0)
    raise ValueError(f"Unbekannter LLM_PROVIDER: {provider}")


def modellname(modell: str) -> str:
    if os.getenv("LLM_PROVIDER") == "orakel":
        return "orakel (Testdouble)"
    if modell == "lokal":
        return f"ollama lokal: {OLLAMA_LOCAL_MODEL}"
    if modell == "lokal2":
        return f"ollama lokal: {OLLAMA_LOCAL_MODEL_2}"
    return {"ollama_cloud": f"ollama cloud: {OLLAMA_CLOUD_MODEL}", "gemini": f"gemini: {GEMINI_MODEL}"}.get(
        CLOUD_PROVIDER, CLOUD_PROVIDER)
