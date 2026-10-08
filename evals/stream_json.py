"""Mitschnitt der Tool-Aufrufe aus `claude --output-format stream-json` (nur Standardbibliothek).

Annahme (unverifiziert): je Zeile ein JSON-Objekt; Tool-Aufrufe stehen in {"type": "assistant", "message":
{"content": [{"type": "tool_use", "name": "Bash", "input": {"command": ...}}]}}. Alles andere wird übersprungen.
"""
import json
import re
import shlex

TRENNER = {";", "&", "&&", "|", "||", "\n"}


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


def _segmente(befehl):
    """Token je Befehls-Segment (getrennt an ; & && | || und Zeilenumbruch); Anführungszeichen bleiben ein Token."""
    lex = shlex.shlex(befehl, posix=True, punctuation_chars=";&|\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    segmente, aktuell = [], []
    for t in lex:
        if t in TRENNER:
            segmente.append(aktuell)
            aktuell = []
        else:
            aktuell.append(t)
    return segmente + [aktuell]


def nutzt_git_stash(befehl):
    """True, wenn ein Segment `git [Optionen] stash …` ist; Treffer in Argumenten (commit -m, grep) zählen nicht."""
    try:
        segmente = _segmente(befehl)
    except ValueError:  # z. B. offenes Anführungszeichen: lieber ein Treffer zu viel
        return bool(re.search(r"\bgit(?:\s+-\S+)*\s+stash\b", befehl))
    for tok in segmente:
        while tok and re.fullmatch(r"\w+=.*", tok[0]):  # FOO=1 git …
            tok = tok[1:]
        if tok[:1] != ["git"]:
            continue
        i = 1
        while i < len(tok) and tok[i].startswith("-"):
            i += 2 if tok[i] in ("-C", "-c") else 1
        if tok[i:i + 1] == ["stash"]:
            return True
    return False


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
