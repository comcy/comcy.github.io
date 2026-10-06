"""Einrichtung des lokalen Klons: Agenten-Adapter, Ausschlüsse, Hooks-Pfad (nur Standardbibliothek).

Jeder Schritt ist ein `Step` mit Beschriftung und Ausführung. `plan` liefert nur die Schritte, die fehlen. Der normale
Lauf führt sie aus, `--check` meldet sie nur. So gibt es für beide Modi dieselbe Prüfung.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tools import parse_version
from workflow import Finding, missing_columns, read_table

AGENTS_FILE = "scripts/setup.d/agents.tsv"
AGENTS_REQUIRED = ("agent", "folder")
BASE_TOOLS = "agents"          # agentenneutrale Basis (.agents/), eingecheckt
BASE_FOLDER = ".agents/skills"  # dort liegen die Skills der Basis
HOOKS_DIR = ".githooks"


class SetupError(Exception):
    """Ein Schritt ist fehlgeschlagen; die Meldung geht unverändert an die Ausgabe."""


@dataclass
class Step:
    label: str
    apply: Callable[[], None]


def read_agents(root: Path, findings: list[Finding]) -> dict[str, str]:
    """Agent -> Ordner der Adapterdateien aus agents.tsv; ungültige Zeilen werden gemeldet."""
    table = read_table(root / AGENTS_FILE, AGENTS_FILE, findings)
    if table is None or not missing_columns(table, AGENTS_REQUIRED, findings):
        return {}
    agenten: dict[str, str] = {}
    for zeile in table.rows:
        name, ordner = zeile.values["agent"], zeile.values["folder"]
        if not re.fullmatch(r"\.[\w.-]+/", ordner):
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"ungültiger Ordner '{ordner}', erwartet zum Beispiel .claude/"))
        elif name in agenten or not name:
            findings.append(Finding(table.file, zeile.line, "error", f"doppelter oder leerer Agent '{name}'"))
        else:
            agenten[name] = ordner
    return agenten


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    exe = shutil.which("git")
    if exe is None:
        raise SetupError("git nicht gefunden")
    return subprocess.run([exe, "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def stored_agents(root: Path) -> list[str]:
    antwort = git(root, "config", "--local", "--get", "setup.agents")
    return antwort.stdout.split() if antwort.returncode == 0 else []


def exclude_path(root: Path) -> Path:
    """Pfad der Datei info/exclude (auch bei Worktrees und ausgelagertem .git)."""
    antwort = git(root, "rev-parse", "--git-path", "info/exclude")
    if antwort.returncode != 0:
        raise SetupError(f"kein Git-Repo unter {root}: {antwort.stderr.strip()}")
    pfad = Path(antwort.stdout.strip())
    return pfad if pfad.is_absolute() else root / pfad


def generated_by(root: Path) -> str | None:
    """Version von openspec, mit der die Skills der Basis erzeugt wurden (generatedBy im Kopf der SKILL.md)."""
    for skill in sorted((root / BASE_FOLDER).glob("*/SKILL.md")):
        m = re.search(r'generatedBy:\s*"?(\d+(?:\.\d+)*)"?', skill.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return None


def installed_openspec() -> str | None:
    exe = shutil.which("openspec")
    if exe is None:
        return None
    lauf = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    version = parse_version(lauf.stdout + "\n" + lauf.stderr)
    return ".".join(map(str, version)) if version else None


def run_openspec(root: Path, *args: str) -> None:
    """Ruft openspec im Repo auf (init und update arbeiten im Arbeitsordner)."""
    exe = shutil.which("openspec")
    if exe is None:
        raise SetupError("openspec nicht gefunden")
    lauf = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root)
    if lauf.returncode != 0:
        raise SetupError(f"openspec {' '.join(args)} ist fehlgeschlagen:\n{lauf.stdout}{lauf.stderr}".rstrip())


def add_exclude_line(root: Path, zeile: str) -> None:
    pfad = exclude_path(root)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    text = pfad.read_text(encoding="utf-8") if pfad.exists() else ""
    if zeile in (z.strip() for z in text.splitlines()):
        return
    if text and not text.endswith("\n"):
        text += "\n"
    pfad.write_text(text + zeile + "\n", encoding="utf-8", newline="\n")


def plan(root: Path, agenten: list[str], ordner: dict[str, str], explizit: bool) -> list[Step]:
    """Schritte, die für die gewählten Agenten fehlen (Reihenfolge: Adapter, Ausschlüsse, Hooks, Wahl speichern)."""
    schritte: list[Step] = []
    werkzeuge = ",".join([BASE_TOOLS, *agenten])
    fehlend = [] if (root / BASE_FOLDER).is_dir() else [BASE_TOOLS]
    fehlend += [a for a in agenten if not (root / ordner[a]).is_dir()]
    if fehlend:
        schritte.append(Step(f"openspec init --tools {werkzeuge} (fehlt: {', '.join(fehlend)})",
                             lambda: run_openspec(root, "init", "--tools", werkzeuge, "--no-animation")))
    else:
        neu, alt = installed_openspec(), generated_by(root)
        if neu and alt and parse_version(neu) != parse_version(alt):
            schritte.append(Step(f"Adapter veraltet (openspec {neu}, Skills {alt}): openspec update",
                                 lambda: run_openspec(root, "update")))
    lokal = exclude_path(root)
    vorhanden = {z.strip() for z in lokal.read_text(encoding="utf-8").splitlines()} if lokal.exists() else set()
    for agent in agenten:
        if ordner[agent] not in vorhanden:
            schritte.append(Step(f"Eintrag {ordner[agent]} in .git/info/exclude",
                                 lambda z=ordner[agent]: add_exclude_line(root, z)))
    if (root / HOOKS_DIR).is_dir():
        aktuell = git(root, "config", "--local", "--get", "core.hooksPath").stdout.strip()
        if aktuell != HOOKS_DIR:
            schritte.append(Step(f"core.hooksPath auf {HOOKS_DIR} setzen",
                                 lambda: git(root, "config", "--local", "core.hooksPath", HOOKS_DIR)))
    if explizit and stored_agents(root) != agenten:
        wert = " ".join(agenten)
        schritte.append(Step(f"Agentenwahl speichern (setup.agents = {wert})",
                             lambda: git(root, "config", "--local", "setup.agents", wert)))
    return schritte
