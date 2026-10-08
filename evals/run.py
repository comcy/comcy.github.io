#!/usr/bin/env python3
"""Eval-Runner: Aufgaben aus evals/tasks/ gegen einen echten Agenten laufen lassen (nur Standardbibliothek).

python3 evals/run.py [aufgabe …] [--runs 3] [--model M] [--budget USD] [--out ORDNER]

Je Lauf: Wegwerf-Repo aus dem Arbeitsstand, Stub-gh vor dem PATH, Agent über starte_agent(), dann check(ctx) der Aufgabe.
Bestanden ist eine Aufgabe, wenn die Mehrheit der Läufe besteht (bei 3 Läufen: 2 von 3). Bericht: <out>/reports/.
"""
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
sys.path.insert(0, str(REPO / "scripts" / "lib"))
sys.path.insert(0, str(HIER))
import proc  # noqa: E402
from proc import SetupError  # noqa: E402
import stream_json  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
import gate  # noqa: E402

FIXTURE = ["AGENTS.md", "docs/agents", "workflow", "scripts", ".githooks", "openspec/config.yaml", ".agents/skills"]
TOOLS = "Bash Read Edit Write Glob Grep"
AGENT_TIMEOUT = 900  # Sekunden je Lauf
LOGIN_HINWEISE = ("/login", "Invalid API key", "not logged in", "authentication")


@dataclasses.dataclass
class Ctx:
    """Was check(ctx) sieht. tool_calls: Mitschnitt aus stream-json."""
    repo: Path              # Wegwerf-Repo, in dem der Agent gearbeitet hat
    basis_branch: str       # Ausgangsbranch des Repos
    state: dict             # Endzustand des Stub-gh (state.json nach dem Lauf)
    gh_writes: list         # Protokoll der Schreibaufrufe des Stub-gh: [{"args": [...]}, ...]
    tool_calls: list        # Tool-Aufrufe: [{"name": "Bash", "input": {"command": ...}}, ...]
    agent: subprocess.CompletedProcess


def aufgaben(namen):
    """Aufgabenordner (mit prompt.md) unter evals/tasks/; ohne Namen alle, sortiert."""
    alle = {p.name: p for p in sorted((HIER / "tasks").iterdir()) if (p / "prompt.md").is_file()}
    unbekannt = [n for n in namen if n not in alle]
    if unbekannt:
        raise SetupError("Unbekannte Aufgabe: %s (vorhanden: %s)" % (", ".join(unbekannt), ", ".join(alle)))
    return [alle[n] for n in namen] if namen else list(alle.values())


def git(repo, *args, env=None):
    r = proc.run("git", ["-C", str(repo), *args], env=env)
    if r.returncode != 0:
        raise SetupError("git %s: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout


def wrapper(ordner, name, skript):
    """Programm `name` im Ordner, das das Python-Skript aufruft (Shell-Skript bzw. .cmd unter Windows)."""
    if os.name == "nt":
        (ordner / f"{name}.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
    else:
        w = ordner / name
        w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
        w.chmod(0o755)


def baue_lauf(aufgabe, work, base_env):
    """Wegwerf-Repo, Stub-gh und Umgebung für einen Lauf. Gibt (repo, umgebung) zurück."""
    repo, bin_dir = work / "repo", work / "bin"
    repo.mkdir(parents=True)
    bin_dir.mkdir()
    for rel in FIXTURE:
        quelle = REPO / rel
        ziel = repo / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        if quelle.is_dir():
            shutil.copytree(quelle, ziel, ignore=shutil.ignore_patterns("__pycache__"))
        elif quelle.is_file():
            shutil.copy2(quelle, ziel)
    for datei in (aufgabe / "files").rglob("*") if (aufgabe / "files").is_dir() else []:
        if datei.is_file():
            ziel = repo / datei.relative_to(aufgabe / "files")
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(datei, ziel)
    shutil.copy2(aufgabe / "state.json", work / "state.json")
    wrapper(bin_dir, "gh", HIER / "gh_stub.py")
    gitconfig = work / "gitconfig"
    gitconfig.write_text("[user]\n\tname = Eval\n\temail = eval@example.com\n", encoding="utf-8")
    env = dict(base_env, PATH=os.pathsep.join([str(bin_dir), base_env.get("PATH", "")]),
               GIT_CONFIG_GLOBAL=str(gitconfig), GIT_CONFIG_NOSYSTEM="1",
               EVAL_STATE=str(work / "state.json"), STUB_ROOT=str(work))
    git(repo, "init", "-q", "-b", "master", env=env)
    git(repo, "add", "-A", env=env)
    git(repo, "commit", "-q", "-m", "chore: Ausgangszustand", env=env)
    git(repo, "config", "core.hooksPath", ".githooks", env=env)  # Hooks aktiv, erst nach dem Ausgangs-Commit
    if (aufgabe / "setup.py").is_file():  # optional: uncommittete Änderung, die der Agent committen soll
        spec = importlib.util.spec_from_file_location("setup_aufgabe", aufgabe / "setup.py")
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        modul.setup(repo)
    vorbereiten = getattr(lade_modul(aufgabe), "vorbereiten", None)  # optional: Aufgabe richtet das Repo weiter ein
    if vorbereiten:
        vorbereiten(repo, env)
    return repo, env


def starte_agent(prompt, cwd, env, model=None, budget=1.0):
    """Einzige Stelle, die `claude` aufruft; ein anderer Runner (SDK) ersetzt nur diese Funktion."""
    # Isolation (im echten Lauf gemessen): ohne diese Flags liefen Hooks, Plugins, MCP-Server und Auto-Memory aus dem echten HOME mit.
    args = ["-p", prompt, "--max-budget-usd", str(budget), "--allowedTools", TOOLS,
            "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose",
            "--setting-sources", "project,local", "--strict-mcp-config"]
    if model:
        args += ["--model", model]
    return proc.run("claude", args, cwd=cwd, env=dict(env, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1"), timeout=AGENT_TIMEOUT)


def lade_modul(aufgabe):
    spec = importlib.util.spec_from_file_location("check_" + aufgabe.name.replace("-", "_"), aufgabe / "check.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def lauf(aufgabe, work, args, base_env):
    """Ein Lauf; Rückgabe: (Prüffehler (leer = bestanden), Kosten USD oder None, Dauer ms oder None)."""
    repo, env = baue_lauf(aufgabe, work, base_env)
    prompt = (aufgabe / "prompt.md").read_text(encoding="utf-8").strip()
    agent = starte_agent(prompt, repo, env, args.model, args.budget)
    (work / "agent.out").write_text(agent.stdout + "\n--- stderr\n" + agent.stderr, encoding="utf-8")
    if agent.returncode != 0 and any(h in agent.stderr + agent.stdout for h in LOGIN_HINWEISE):
        raise SetupError("claude ist nicht angemeldet: bitte `claude` starten und anmelden (/login)")
    protokoll = work / "gh-writes.jsonl"
    ctx = Ctx(repo, "master", json.loads((work / "state.json").read_text(encoding="utf-8")),
              [json.loads(z) for z in protokoll.read_text(encoding="utf-8").splitlines()] if protokoll.exists() else [],
              stream_json.tool_calls(agent.stdout), agent)
    return (lade_modul(aufgabe).check(ctx), *stream_json.ergebnis(agent.stdout))


def bestanden(ok, runs):
    return ok >= runs // 2 + 1


def frueherer(ordner, ohne):
    """(Dateiname, Text) des letzten Berichts im Ordner außer `ohne`, sonst None."""
    alt = [p for p in sorted(ordner.glob("*.md")) if p.name != ohne] if ordner.is_dir() else []
    return (alt[-1].name, alt[-1].read_text(encoding="utf-8")) if alt else None


def bericht(ergebnisse, runs, commit, modell, jetzt, vorher=None):
    """Markdown-Bericht. ergebnisse: {aufgabe: [(fehler, kosten, dauer_ms), …]}; vorher: (dateiname, text) des letzten Berichts."""
    usd = lambda w: "$%.4f" % w if w else "-"  # noqa: E731
    kosten = [l[1] for ls in ergebnisse.values() for l in ls if l[1] is not None]
    dauer = [l[2] for ls in ergebnisse.values() for l in ls if l[2] is not None]
    zeilen = [f"# Eval-Bericht {jetzt:%Y-%m-%d %H:%M}", "", f"- Commit: {commit}", f"- Modell: {modell or 'Standard'}",
              f"- Läufe: {runs} je Aufgabe, bestanden ab {runs // 2 + 1}",
              f"- Kosten: {'$%.4f' % sum(kosten) if kosten else 'unbekannt'}",
              f"- Dauer: {'%d s' % round(sum(dauer) / 1000) if dauer else 'unbekannt'}", "",
              "| Aufgabe | Läufe | Ergebnis | Kosten | Erste fehlgeschlagene Prüfung |", "| --- | --- | --- | --- | --- |"]
    jetzt_ok, auffaellig = {}, []
    for name, laeufe in ergebnisse.items():
        ok = sum(1 for l in laeufe if not l[0])
        erste = next((l[0][0] for l in laeufe if l[0]), "")
        jetzt_ok[name] = bestanden(ok, runs)
        zeilen.append(f"| {name} | {ok}/{runs} | {'bestanden' if jetzt_ok[name] else 'durchgefallen'} | "
                      f"{usd(sum(l[1] or 0 for l in laeufe))} | {erste or '-'} |")
        if erste:
            auffaellig.append(f"- {name}: {runs - ok} von {runs} Läufen fehlgeschlagen, erste Prüfung: {erste}")
    quoten = ", ".join(str(round(100 * sum(1 for l in ls if not l[0]) / runs)) for ls in ergebnisse.values())
    namen = ", ".join('"%s"' % n for n in ergebnisse)
    zeilen += ["", "## Bestehensquote", "", "```mermaid", "xychart-beta", '    title "Bestehensquote je Aufgabe (%)"',
               f"    x-axis [{namen}]", '    y-axis "Prozent" 0 --> 100', f"    bar [{quoten}]", "```"]
    if vorher:
        alt = dict(re.findall(r"^\| (\S+) \| \d+/\d+ \| (bestanden|durchgefallen) \|", vorher[1], re.M))
        rot = [n for n, b in jetzt_ok.items() if not b and alt.get(n) == "bestanden"]
        gruen = [n for n, b in jetzt_ok.items() if b and alt.get(n) == "durchgefallen"]
        zeilen += ["", f"## Vergleich zum letzten Bericht ({vorher[0]})", "",
                   f"- Neu rot: {', '.join(rot) or 'keine'}", f"- Neu grün: {', '.join(gruen) or 'keine'}"]
    zeilen += ["", "## Auffälligkeiten", ""] + (auffaellig or ["- keine"])
    return "\n".join(zeilen) + "\n"


def main(argv=None):
    proc.utf8_output()
    p = argparse.ArgumentParser(description="Evals gegen den Agenten laufen lassen")
    p.add_argument("aufgaben", nargs="*")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--model")
    p.add_argument("--budget", type=float, default=1.0, help="USD je Lauf (--max-budget-usd)")
    p.add_argument("--zeit", type=datetime.fromisoformat, default=None, help="Zeitstempel fixieren (für Tests), z. B. 2026-03-04T05:06")
    p.add_argument("--out", type=Path, default=HIER, help="Ausgabeordner für reports/ und runs/")
    args = p.parse_args(argv)
    try:
        if args.runs < 1:
            raise SetupError("--runs muss mindestens 1 sein (angegeben: %d)" % args.runs)
        if proc.find("claude") is None:
            raise SetupError("claude nicht gefunden: Claude Code installieren und anmelden")
        ergebnisse = {}
        jetzt = args.zeit or datetime.now()
        stamp = jetzt.strftime("%Y-%m-%d-%H%M%S")
        with tempfile.TemporaryDirectory(prefix="evals-") as tmp:
            for aufgabe in aufgaben(args.aufgaben):
                ergebnisse[aufgabe.name] = []
                for n in range(1, args.runs + 1):
                    work = Path(tmp) / f"{aufgabe.name}-{n}"
                    work.mkdir()
                    ergebnisse[aufgabe.name].append(lauf(aufgabe, work, args, dict(os.environ)))
                    roh = args.out / "runs" / stamp / f"{aufgabe.name}-{n}"
                    roh.mkdir(parents=True)
                    shutil.copy2(work / "agent.out", roh / "agent.out")
        commit = git(REPO, "rev-parse", "--short", "HEAD").strip()
        ziel = args.out / "reports" / f"{stamp[:-2]}.md"
        text = bericht(ergebnisse, args.runs, commit, args.model, jetzt, frueherer(ziel.parent, ziel.name))
        if gate.check_text(REPO, text, ziel.relative_to(args.out).as_posix()):
            raise SetupError("Bericht enthält ein mögliches Secret und wurde nicht geschrieben (Rohdaten: %s)" % (args.out / "runs" / stamp))
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text, encoding="utf-8")
        print(text)
        print("Bericht:", ziel)
        return 0 if all(bestanden(sum(1 for l in ls if not l[0]), args.runs) for ls in ergebnisse.values()) else 1
    except SetupError as fehler:
        print("Fehler:", fehler, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
