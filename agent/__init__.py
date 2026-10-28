import sys

# Windows-Konsole: Sonderzeichen (✔, ✘, ⚠) nicht an cp1252 scheitern lassen
for _strom in (sys.stdout, sys.stderr):
    try:
        _strom.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
