#!/usr/bin/env python3
"""Beispiel-Adapter: zeigt nur das Format des Vertrags, startet keinen Agenten und tut nichts (nur Standardbibliothek).

stdin:  JSON mit prompt, cwd, env, model, budget_usd, allowed_tools, timeout_s
stdout: JSON mit tool_calls, result_text, cost_usd, duration_ms, error
Exit-Code: 0 = Adapter hat gearbeitet (auch wenn der Agent scheiterte: dann `error` füllen), ungleich 0 = Adapter konnte nicht arbeiten.
Aufruf: python3 evals/run.py blocker-offen --runs 1 --adapter evals/adapters/beispiel.py
"""
import json
import sys


def arbeite(anfrage):
    # Hier würde der eigene Agent im Ordner anfrage["cwd"] mit anfrage["prompt"] gestartet, begrenzt auf anfrage["allowed_tools"]
    # und anfrage["budget_usd"]. Dieser Adapter tut nichts und meldet das so.
    return {
        "tool_calls": [],  # [{"name": "Bash", "input": {"command": "git status"}}, ...]; None = kein Mitschnitt ("nicht prüfbar")
        "result_text": "Beispiel-Adapter: nichts getan (%d erlaubte Tools)" % len(anfrage["allowed_tools"]),
        "cost_usd": 0.0,  # darf None sein
        "duration_ms": 0,  # darf None sein
        "error": None,  # Text, wenn der Agent scheiterte
    }


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        anfrage = json.load(sys.stdin)
        antwort = arbeite(anfrage)
    except (ValueError, KeyError) as fehler:
        print("Beispiel-Adapter: ungültige Anfrage: %s" % fehler, file=sys.stderr)
        return 2
    print(json.dumps(antwort, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
