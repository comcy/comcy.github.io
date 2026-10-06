"""Einrichtung des lokalen Klons: Agenten-Adapter, Ausschlüsse, Hooks-Pfad (nur Standardbibliothek).

Jeder Schritt ist ein `Step` mit Beschriftung und Ausführung. `plan` liefert nur die Schritte, die fehlen. Der normale
Lauf führt sie aus, `--check` meldet sie nur. So gibt es für beide Modi dieselbe Prüfung.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import proc
from proc import SetupError
from tools import parse_version
from workflow import Finding, missing_columns, read_table

AGENTS_FILE = "scripts/setup.d/agents.tsv"
AGENTS_REQUIRED = ("agent", "folder")
BASE_TOOLS = "agents"          # agentenneutrale Basis (.agents/), eingecheckt
BASE_FOLDER = ".agents/skills"  # dort liegen die Skills der Basis
HOOKS_DIR = ".githooks"


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


def git(root: Path, *args: str):
    return proc.run("git", ["-C", str(root), *args])


def git_config_set(root: Path, schluessel: str, wert: str) -> None:
    antwort = git(root, "config", "--local", schluessel, wert)
    if antwort.returncode != 0:
        raise SetupError(f"git config {schluessel} ist fehlgeschlagen: {antwort.stderr.strip()}")


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


def adapter_present(root: Path, ordner: str) -> bool:
    """Ein Adapter gilt als vorhanden, wenn openspec dort Skills erzeugt hat; ein bloßer Ordner (zum Beispiel
    .claude/ mit Einstellungen von Claude Code) genügt nicht."""
    return any((root / ordner / "skills").glob("openspec-*/SKILL.md"))


def generated_by(root: Path) -> str | None:
    """Version von openspec, mit der die Skills der Basis erzeugt wurden (generatedBy im Kopf der SKILL.md)."""
    for skill in sorted((root / BASE_FOLDER).glob("*/SKILL.md")):
        m = re.search(r'generatedBy:\s*"?(\d+(?:\.\d+)*)"?', skill.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return None


def installed_openspec() -> str | None:
    if proc.find("openspec") is None:
        return None
    lauf = proc.run("openspec", ["--version"])
    version = parse_version(lauf.stdout + "\n" + lauf.stderr)
    return ".".join(map(str, version)) if version else None


def run_openspec(root: Path, *args: str) -> None:
    """Ruft openspec im Repo auf (init und update arbeiten im Arbeitsordner)."""
    lauf = proc.run("openspec", args, cwd=root)
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
    fehlend = [] if adapter_present(root, ".agents") else [BASE_TOOLS]
    fehlend += [a for a in agenten if not adapter_present(root, ordner[a])]
    if fehlend:
        schritte.append(Step(f"openspec init --tools {werkzeuge} (fehlt: {', '.join(fehlend)})",
                             lambda: run_openspec(root, "init", "--tools", werkzeuge, "--no-animation")))
    else:
        neu, alt = installed_openspec(), generated_by(root)
        # nur ein neueres openspec frischt auf; ein älteres würde die Skills zurücksetzen, das tut kein Lauf von setup
        if neu and alt and parse_version(neu) > parse_version(alt):
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
                                 lambda: git_config_set(root, "core.hooksPath", HOOKS_DIR)))
    if explizit and stored_agents(root) != agenten:
        wert = " ".join(agenten)
        schritte.append(Step(f"Agentenwahl speichern (setup.agents = {wert})",
                             lambda: git_config_set(root, "setup.agents", wert)))
    return schritte
