"""Mitschnitt der Tool-Aufrufe aus `claude --output-format stream-json` (nur Standardbibliothek).

Annahme (unverifiziert): je Zeile ein JSON-Objekt; Tool-Aufrufe stehen in {"type": "assistant", "message":
{"content": [{"type": "tool_use", "name": "Bash", "input": {"command": ...}}]}}. Alles andere wird übersprungen.
"""
import json
import re

GIT_STASH = re.compile(r"\bgit(?:\s+(?:-[Cc]\s+\S+|-\S+))*\s+stash\b")


def tool_calls(text):
    """[{"name": ..., "input": {...}}, ...] in Reihenfolge; unbekannte Ereignisse und kaputte Zeilen werden ignoriert."""
    aufrufe = []
    for zeile in text.splitlines():
        try:
            ereignis = json.loads(zeile)
            inhalt = ereignis["message"]["content"]
        except (ValueError, KeyError, TypeError):
            continue
        if ereignis.get("type") != "assistant" or not isinstance(inhalt, list):
            continue
        for block in inhalt:
            if isinstance(block, dict) and block.get("type") == "tool_use" and isinstance(block.get("input"), dict):
                aufrufe.append({"name": block.get("name"), "input": block["input"]})
    return aufrufe


def nutzt_git_stash(befehl):
    return bool(GIT_STASH.search(befehl))


def ergebnis(text):
    """(Kosten in USD, Dauer in ms) aus dem letzten `result`-Ereignis; fehlende oder unpassende Felder sind None (Format unverifiziert)."""
    letzt = {}
    for zeile in text.splitlines():
        try:
            e = json.loads(zeile)
        except ValueError:
            continue
        if isinstance(e, dict) and e.get("type") == "result":
            letzt = e
    zahl = lambda w: w if isinstance(w, (int, float)) and not isinstance(w, bool) else None  # noqa: E731
    return zahl(letzt.get("total_cost_usd")), zahl(letzt.get("duration_ms"))
