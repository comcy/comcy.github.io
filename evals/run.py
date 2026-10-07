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
    vorbereiten = getattr(lade_modul(aufgabe), "vorbereiten", None)  # optional: Aufgabe richtet das Repo weiter ein
    if vorbereiten:
        vorbereiten(repo, env)
    return repo, env


def starte_agent(prompt, cwd, env, model=None, budget=1.0):
    """Einzige Stelle, die `claude` aufruft; ein anderer Runner (SDK) ersetzt nur diese Funktion."""
    args = ["-p", prompt, "--max-budget-usd", str(budget), "--allowedTools", TOOLS,
            "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose"]
    if model:
        args += ["--model", model]
    return proc.run("claude", args, cwd=cwd, env=env, timeout=AGENT_TIMEOUT)


def lade_modul(aufgabe):
    spec = importlib.util.spec_from_file_location("check_" + aufgabe.name.replace("-", "_"), aufgabe / "check.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def lauf(aufgabe, work, args, base_env):
    """Ein Lauf; Rückgabe: Liste der Prüffehler (leer = bestanden)."""
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
    return lade_modul(aufgabe).check(ctx)


def bericht(ergebnisse, runs, commit):
    zeilen = [f"# Eval-Bericht {datetime.now():%Y-%m-%d %H:%M}", "",
              f"Commit {commit}, {runs} Läufe je Aufgabe, bestanden ab {runs // 2 + 1}.", "",
              "| Aufgabe | Läufe | Ergebnis | Erste fehlgeschlagene Prüfung |", "| --- | --- | --- | --- |"]
    for name, fehlerlisten in ergebnisse.items():
        ok = sum(1 for f in fehlerlisten if not f)
        erste = next((f[0] for f in fehlerlisten if f), "")
        zeilen.append(f"| {name} | {ok}/{runs} | {'bestanden' if ok >= runs // 2 + 1 else 'durchgefallen'} | {erste} |")
    return "\n".join(zeilen) + "\n"


def main(argv=None):
    proc.utf8_output()
    p = argparse.ArgumentParser(description="Evals gegen den Agenten laufen lassen")
    p.add_argument("aufgaben", nargs="*")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--model")
    p.add_argument("--budget", type=float, default=1.0, help="USD je Lauf (--max-budget-usd)")
    p.add_argument("--out", type=Path, default=HIER, help="Ausgabeordner für reports/ und runs/")
    args = p.parse_args(argv)
    try:
        if proc.find("claude") is None:
            raise SetupError("claude nicht gefunden: Claude Code installieren und anmelden")
        ergebnisse = {}
        stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
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
        text = bericht(ergebnisse, args.runs, commit)
        ziel = args.out / "reports" / f"{stamp[:-2]}.md"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text, encoding="utf-8")
        print(text)
        print("Bericht:", ziel)
        return 0 if all(sum(1 for f in fl if not f) >= args.runs // 2 + 1 for fl in ergebnisse.values()) else 1
    except SetupError as fehler:
        print("Fehler:", fehler, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
