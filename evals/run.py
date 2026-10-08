#!/usr/bin/env python3
"""Eval-Runner: Aufgaben aus evals/tasks/ gegen einen echten Agenten laufen lassen (nur Standardbibliothek).

python3 evals/run.py [aufgabe …] [--runs 3] [--model M] [--budget USD] [--adapter PROGRAMM] [--sandbox auto|bwrap|none] [--out ORDNER]

Je Lauf: Wegwerf-Repo aus dem Arbeitsstand, Stub-gh vor dem PATH, Agent über einen Adapter (starte_agent(), JSON-Vertrag), dann check(ctx) der Aufgabe.
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

sys.path.insert(0, str(REPO / "scripts"))
import gate  # noqa: E402
import derive  # noqa: E402
import workflow  # noqa: E402

FIXTURE = ["AGENTS.md", "docs/agents", "workflow", "scripts", ".githooks", "openspec/config.yaml", ".agents/skills"]
STANDARD_ROLLE = "builder"
AGENT_TIMEOUT = 900  # Sekunden je Lauf
STANDARD_ADAPTER = HIER / "adapters" / "claude.py"


@dataclasses.dataclass
class Ctx:
    """Was check(ctx) sieht. tool_calls: Mitschnitt des Adapters (leer, wenn er keinen liefert; solche Aufgaben laufen dann gar nicht)."""
    repo: Path              # Wegwerf-Repo, in dem der Agent gearbeitet hat
    basis_branch: str       # Ausgangsbranch des Repos
    state: dict             # Endzustand des Stub-gh (state.json nach dem Lauf)
    gh_writes: list         # Protokoll der Schreibaufrufe des Stub-gh: [{"args": [...]}, ...]
    tool_calls: list        # Tool-Aufrufe: [{"name": "Bash", "input": {"command": ...}}, ...]
    agent: dict             # normalisierte Antwort des Adapters


def aufgaben(namen, ordner=HIER / "tasks", abgeleitet=()):
    """Aufgabenordner (mit prompt.md) unter `ordner` plus abgeleitete; ohne Namen alle, sortiert."""
    alle = {p.name: p for p in sorted(ordner.iterdir()) if (p / "prompt.md").is_file()}
    alle.update((p.name, p) for p in abgeleitet)
    unbekannt = [n for n in namen if n not in alle]
    if unbekannt:
        raise SetupError("Unbekannte Aufgabe: %s (vorhanden: %s)" % (", ".join(unbekannt), ", ".join(alle)))
    return [alle[n] for n in namen] if namen else list(alle.values())


def rollen_tools(aufgabe):
    """allowed_tools (Liste) der Rolle aus task.json (optional, Feld `role`, Standard builder) laut workflow/roles.tsv; `-` = keine."""
    datei = aufgabe / "task.json"
    rolle = (json.loads(datei.read_text(encoding="utf-8")) if datei.is_file() else {}).get("role", STANDARD_ROLLE)
    findings = []
    tabelle = workflow.read_table(REPO / workflow.WORKFLOW_DIR / workflow.ROLES_FILE, "workflow/roles.tsv", findings)
    if tabelle is None:
        raise SetupError("; ".join(f.format() for f in findings))
    for zeile in tabelle.rows:
        if zeile.values.get("role") == rolle and workflow.is_enabled(zeile):
            return [] if zeile.values["allowed_tools"] == "-" else zeile.values["allowed_tools"].split()
    raise SetupError("Aufgabe %s: Rolle '%s' fehlt in %s (vorhanden: %s)" % (
        aufgabe.name, rolle, tabelle.file, ", ".join(z.values.get("role", "") for z in tabelle.rows)))


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


def sandbox_befehl(work, home=None):
    """bwrap-Aufruf (Liste, Programm zuerst) vor dem Adapter: alles schreibgeschützt, beschreibbar nur `work` und die Claude-Konfiguration (nur vorhandene Pfade)."""
    home = Path(home) if home else Path.home()
    # /tmp ist ein privates tmpfs: das Bash-Tool von claude braucht dort ein Arbeitsverzeichnis (im Probelauf gemessen: ohne lief Bash nicht)
    cmd = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--bind", str(work), str(work)]
    for p in (home / ".claude", home / ".claude.json"):
        if p.exists():
            cmd += ["--bind", str(p), str(p)]
    return cmd + ["--unshare-pid", "--die-with-parent", "--"]


def sandbox_modus(wahl):
    """'bwrap' oder 'keine' aus --sandbox auto|bwrap|none; ohne bwrap (und nicht none) Abbruch mit SetupError."""
    if wahl == "none":
        return "keine"
    if proc.find("bwrap") is None:
        raise SetupError("bwrap (Bubblewrap) nicht gefunden: installieren (nur Linux) oder mit --sandbox none ausdrücklich ohne Sandbox laufen lassen")
    return "bwrap"


def starte_agent(adapter, prompt, cwd, env, model=None, budget=1.0, tools=(), sandbox=()):
    """Einzige Stelle, die den Agenten startet: ruft den Adapter (Python-Skript über sys.executable, sonst das Programm direkt)
    mit dem JSON-Vertrag auf stdin und gibt dessen JSON von stdout als dict zurück."""
    anfrage = {"prompt": prompt, "cwd": str(cwd), "env": env, "model": model, "budget_usd": budget,
               "allowed_tools": list(tools), "timeout_s": AGENT_TIMEOUT}
    pfad = str(adapter)
    if os.sep in pfad or "/" in pfad:  # Pfad statt PATH-Name: absolut machen, der Adapter läuft im Wegwerf-Repo
        pfad = str(Path(pfad).resolve())
    exe, args = (sys.executable, [pfad]) if pfad.lower().endswith(".py") else (pfad, [])
    if sandbox:  # Sandbox-Befehl davor; der Adapter bleibt unverändert und läuft weiter über proc.run
        sichtbar = []  # /tmp ist in der Sandbox ein leeres tmpfs: ein Adapter dort bliebe unsichtbar, also schreibgeschützt einbinden
        if Path(pfad).is_absolute() and Path(pfad).exists() and Path(pfad).resolve().is_relative_to("/tmp"):
            sichtbar = ["--ro-bind", pfad, pfad]
        i = sandbox.index("--unshare-pid") if "--unshare-pid" in sandbox else len(sandbox) - 1
        exe, args = sandbox[0], [*sandbox[1:i], *sichtbar, *sandbox[i:], exe, *args]
    r = proc.run(exe, args, cwd=cwd, env=env, timeout=AGENT_TIMEOUT + 30, input=json.dumps(anfrage, ensure_ascii=False))
    name = Path(pfad).name
    if r.returncode != 0:
        raise SetupError("Adapter %s endete mit Exit-Code %d: %s" % (name, r.returncode, (r.stderr.strip() or r.stdout.strip())[-500:]))
    try:
        antwort = json.loads(r.stdout)
    except ValueError:
        antwort = None
    if not isinstance(antwort, dict) or not (antwort.get("tool_calls") is None or isinstance(antwort["tool_calls"], list)):
        raise SetupError("Adapter %s lieferte kein gültiges JSON-Objekt (tool_calls als Liste) auf stdout: %s" % (name, r.stdout.strip()[:200]))
    return antwort


def lade_modul(aufgabe):
    spec = importlib.util.spec_from_file_location("check_" + aufgabe.name.replace("-", "_"), aufgabe / "check.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def lauf(aufgabe, work, args, base_env):
    """Ein Lauf; Rückgabe: (Prüffehler (leer = bestanden, None = nicht prüfbar), Kosten USD oder None, Dauer ms oder None)."""
    tools = rollen_tools(aufgabe)  # vor dem Aufbau: unbekannte Rolle bricht ab, bevor ein Agent startet
    repo, env = baue_lauf(aufgabe, work, base_env)
    prompt = (aufgabe / "prompt.md").read_text(encoding="utf-8").strip()
    sandbox = sandbox_befehl(work) if getattr(args, "sandbox", "keine") == "bwrap" else ()
    agent = starte_agent(args.adapter, prompt, repo, env, args.model, args.budget, tools, sandbox)
    (work / "agent.out").write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")
    protokoll = work / "gh-writes.jsonl"
    modul = lade_modul(aufgabe)
    kosten, dauer = agent.get("cost_usd"), agent.get("duration_ms")
    if agent.get("tool_calls") is None and getattr(modul, "BRAUCHT_MITSCHNITT", False):
        return (None, kosten, dauer)  # nicht prüfbar: Adapter liefert keinen Mitschnitt
    ctx = Ctx(repo, "master", json.loads((work / "state.json").read_text(encoding="utf-8")),
              [json.loads(z) for z in protokoll.read_text(encoding="utf-8").splitlines()] if protokoll.exists() else [],
              agent.get("tool_calls") or [], agent)
    fehler = modul.check(ctx)
    if agent.get("tool_calls") is not None and not zustand_gelesen(agent["tool_calls"]):
        # "nichts getan" darf nicht als bestanden zählen (im Sandbox-Probelauf bestand eine Aufgabe, obwohl Bash nicht lief)
        fehler = [*fehler, "Zustand nicht gelesen: kein gh-, git- oder flow-Aufruf im Mitschnitt"]
    if agent.get("error"):
        fehler = [f"Adapter-Fehler: {agent['error']}", *fehler]
    return (fehler, kosten, dauer)


ZUSTAND_BEFEHLE = re.compile(r"(^|[\s;&|(])(gh|git|flow(\.py)?)(\s|$)|scripts/flow\.py")


def zustand_gelesen(tool_calls):
    """Hat der Agent den Zustand abgefragt? Mindestens ein Bash-Aufruf mit gh, git oder flow im Mitschnitt."""
    return any(t.get("name") == "Bash" and ZUSTAND_BEFEHLE.search(str(t.get("input", {}).get("command", ""))) for t in tool_calls)


def commit_angabe(repo):
    """Kurz-Hash von HEAD; die Läufe nutzen den Arbeitsstand, daher Zusatz bei Änderungen an den kopierten Pfaden."""
    sha = git(repo, "rev-parse", "--short", "HEAD").strip()
    return sha + (" (+ lokale Änderungen)" if git(repo, "status", "--porcelain", "--", *FIXTURE).strip() else "")


def bestanden(ok, runs):
    return ok >= runs // 2 + 1


def ok_laeufe(laeufe):
    return sum(1 for l in laeufe if l[0] is not None and not l[0])


def nicht_pruefbar(laeufe):
    """Alle Läufe ohne Prüfung (Adapter lieferte den nötigen Mitschnitt nicht): weder bestanden noch durchgefallen."""
    return all(l[0] is None for l in laeufe)


def frueherer(ordner, ohne):
    """(Dateiname, Text) des letzten Berichts im Ordner außer `ohne`, sonst None."""
    # Namensreihenfolge reicht auch für alte Minutennamen (…-HHMM.md): "." sortiert vor Ziffern, also vor …-HHMMSS.md
    alt = [p for p in sorted(ordner.glob("*.md")) if p.name != ohne] if ordner.is_dir() else []
    return (alt[-1].name, alt[-1].read_text(encoding="utf-8")) if alt else None


def bericht(ergebnisse, runs, commit, modell, jetzt, vorher=None, nicht_ableitbar=(), sandbox="keine"):
    """Markdown-Bericht. ergebnisse: {aufgabe: [(fehler (None = nicht prüfbar), kosten, dauer_ms), …]}; vorher: (dateiname, text) des letzten Berichts."""
    usd = lambda w: "$%.4f" % w if w else "-"  # noqa: E731
    kosten = [l[1] for ls in ergebnisse.values() for l in ls if l[1] is not None]
    dauer = [l[2] for ls in ergebnisse.values() for l in ls if l[2] is not None]
    zeilen = [f"# Eval-Bericht {jetzt:%Y-%m-%d %H:%M}", "", f"- Commit: {commit}", f"- Modell: {modell or 'Standard'}", f"- Sandbox: {sandbox}",
              f"- Läufe: {runs} je Aufgabe, bestanden ab {runs // 2 + 1}",
              f"- Kosten: {'$%.4f' % sum(kosten) if kosten else 'unbekannt'}",
              f"- Dauer: {'%d s' % round(sum(dauer) / 1000) if dauer else 'unbekannt'}"]
    leer = [n for n, ls in ergebnisse.items() if nicht_pruefbar(ls)]
    if leer:
        zeilen.append(f"- Nicht prüfbar: {len(leer)} von {len(ergebnisse)} Aufgaben ({', '.join(leer)})")
    zeilen += ["", "| Aufgabe | Läufe | Ergebnis | Kosten | Erste fehlgeschlagene Prüfung |", "| --- | --- | --- | --- | --- |"]
    jetzt_ok, auffaellig = {}, []
    for name, laeufe in ergebnisse.items():
        if name in leer:
            zeilen.append(f"| {name} | - | nicht prüfbar | {usd(sum(l[1] or 0 for l in laeufe))} | - |")
            auffaellig.append(f"- {name}: nicht prüfbar, der Adapter lieferte keine `tool_calls`")
            continue
        ok = ok_laeufe(laeufe)
        erste = next((l[0][0] for l in laeufe if l[0]), "")
        jetzt_ok[name] = bestanden(ok, runs)
        zeilen.append(f"| {name} | {ok}/{runs} | {'bestanden' if jetzt_ok[name] else 'durchgefallen'} | "
                      f"{usd(sum(l[1] or 0 for l in laeufe))} | {erste or '-'} |")
        if erste:
            auffaellig.append(f"- {name}: {runs - ok} von {runs} Läufen fehlgeschlagen, erste Prüfung: {erste}")
    quoten = ", ".join(str(round(100 * ok_laeufe(ls) / runs)) for n, ls in ergebnisse.items() if n not in leer)
    namen = ", ".join('"%s"' % n for n in ergebnisse if n not in leer)
    if namen:
        zeilen += ["", "## Bestehensquote", "", "```mermaid", "xychart-beta", '    title "Bestehensquote je Aufgabe (%)"',
                   f"    x-axis [{namen}]", '    y-axis "Prozent" 0 --> 100', f"    bar [{quoten}]", "```"]
    if vorher:
        alt = dict(re.findall(r"^\| (\S+) \| \d+/\d+ \| (bestanden|durchgefallen) \|", vorher[1], re.M))
        rot = [n for n, b in jetzt_ok.items() if not b and alt.get(n) == "bestanden"]
        gruen = [n for n, b in jetzt_ok.items() if b and alt.get(n) == "durchgefallen"]
        zeilen += ["", f"## Vergleich zum letzten Bericht ({vorher[0]})", "",
                   f"- Neu rot: {', '.join(rot) or 'keine'}", f"- Neu grün: {', '.join(gruen) or 'keine'}"]
    if nicht_ableitbar:
        zeilen += ["", "## Nicht ableitbar", ""] + [f"- {'(Start)' if v == '-' else v} -> {n}: Detektor `{d}`" for v, n, d in nicht_ableitbar]
    zeilen += ["", "## Auffälligkeiten", ""] + (auffaellig or ["- keine"])
    return "\n".join(zeilen) + "\n"


def main(argv=None):
    proc.utf8_output()
    p = argparse.ArgumentParser(description="Evals gegen den Agenten laufen lassen")
    p.add_argument("aufgaben", nargs="*")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--model")
    p.add_argument("--budget", type=float, default=1.0, help="USD je Lauf (--max-budget-usd)")
    p.add_argument("--adapter", default=str(STANDARD_ADAPTER), help="Programm, das den Agenten startet (JSON über stdin/stdout, siehe docs/workflow.md)")
    p.add_argument("--ohne-abgeleitete", action="store_true", help="keine Aufgaben aus workflow/transitions.tsv ableiten (evals/derive.py)")
    p.add_argument("--tasks", type=Path, default=HIER / "tasks", help="Ordner mit den Aufgaben (Standard evals/tasks)")
    p.add_argument("--zeit", type=datetime.fromisoformat, default=None, help="Zeitstempel fixieren (für Tests), z. B. 2026-03-04T05:06")
    p.add_argument("--sandbox", choices=["auto", "bwrap", "none"], default="auto", help="Adapter unter bwrap starten (auto/bwrap) oder ohne Sandbox (none)")
    p.add_argument("--out", type=Path, default=HIER, help="Ausgabeordner für reports/ und runs/")
    args = p.parse_args(argv)
    try:
        if args.runs < 1:
            raise SetupError("--runs muss mindestens 1 sein (angegeben: %d)" % args.runs)
        if args.adapter == str(STANDARD_ADAPTER) and proc.find("claude") is None:
            raise SetupError("claude nicht gefunden: Claude Code installieren und anmelden")
        args.sandbox = sandbox_modus(args.sandbox)  # danach 'bwrap' oder 'keine'
        ergebnisse = {}
        jetzt = args.zeit or datetime.now()
        stamp = jetzt.strftime("%Y-%m-%d-%H%M%S")
        abgeleitet, nicht_ableitbar = ([], []) if args.ohne_abgeleitete else derive.ableiten(REPO / "workflow", args.out / "tasks-derived")
        with tempfile.TemporaryDirectory(prefix="evals-") as tmp:
            for aufgabe in aufgaben(args.aufgaben, args.tasks, abgeleitet):
                ergebnisse[aufgabe.name] = []
                for n in range(1, args.runs + 1):
                    work = Path(tmp) / f"{aufgabe.name}-{n}"
                    work.mkdir()
                    ergebnisse[aufgabe.name].append(lauf(aufgabe, work, args, dict(os.environ)))
                    roh = args.out / "runs" / stamp / f"{aufgabe.name}-{n}"
                    roh.mkdir(parents=True)
                    shutil.copy2(work / "agent.out", roh / "agent.out")
        commit = commit_angabe(REPO)
        ziel = args.out / "reports" / f"{stamp}.md"
        text = bericht(ergebnisse, args.runs, commit, args.model, jetzt, frueherer(ziel.parent, ziel.name), nicht_ableitbar, args.sandbox)
        if gate.check_text(REPO, text, ziel.relative_to(args.out).as_posix()):
            raise SetupError("Bericht enthält ein mögliches Secret und wurde nicht geschrieben (Rohdaten: %s)" % (args.out / "runs" / stamp))
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text, encoding="utf-8")
        print(text)
        print("Bericht:", ziel)
        return 0 if all(bestanden(ok_laeufe(ls), args.runs) for ls in ergebnisse.values() if not nicht_pruefbar(ls)) else 1
    except SetupError as fehler:
        print("Fehler:", fehler, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
