#!/usr/bin/env python3
"""Adapter für `claude -p`: liest den Vertrag (JSON) von stdin, startet claude, schreibt das normalisierte JSON nach stdout.

stdin:  prompt, cwd, env, model, budget_usd, allowed_tools, timeout_s
stdout: tool_calls, result_text, cost_usd, duration_ms, error
Exit-Code ungleich 0 = Adapter konnte nicht arbeiten (claude fehlt, nicht angemeldet); ein Fehler des Agenten steht in `error`.
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent.parent / "scripts" / "lib"))
sys.path.insert(0, str(HIER.parent))
import proc  # noqa: E402
import stream_json  # noqa: E402

LOGIN_HINWEISE = ("/login", "Invalid API key", "not logged in")


def starte(anfrage):
    # Isolation (im echten Lauf gemessen): ohne diese Flags liefen Hooks, Plugins, MCP-Server und Auto-Memory aus dem echten HOME mit.
    args = ["-p", anfrage["prompt"], "--max-budget-usd", str(anfrage["budget_usd"]),
            "--allowedTools", " ".join(anfrage["allowed_tools"]), "--permission-mode", "acceptEdits",
            "--output-format", "stream-json", "--verbose", "--setting-sources", "project,local", "--strict-mcp-config"]
    if anfrage.get("model"):
        args += ["--model", anfrage["model"]]
    env = dict(anfrage["env"], CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
    r = proc.run("claude", args, cwd=anfrage["cwd"], env=env, timeout=anfrage["timeout_s"])
    if r.returncode != 0 and any(h in r.stderr + r.stdout for h in LOGIN_HINWEISE):
        raise proc.SetupError("claude ist nicht angemeldet: bitte `claude` starten und anmelden (/login)")
    kosten, dauer = stream_json.ergebnis(r.stdout)
    return {"tool_calls": stream_json.tool_calls(r.stdout), "result_text": stream_json.antwort(r.stdout),
            "cost_usd": kosten, "duration_ms": dauer,
            "error": None if r.returncode == 0 else "claude Exit-Code %d: %s" % (r.returncode, r.stderr.strip()[-500:])}


def main():
    proc.utf8_output()
    sys.stdin.reconfigure(encoding="utf-8")
    try:
        print(json.dumps(starte(json.load(sys.stdin)), ensure_ascii=False))
    except proc.SetupError as fehler:
        print(fehler, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
