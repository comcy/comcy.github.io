"""Labels des Prozesses: Soll aus workflow/states.tsv, Ist per gh, fehlende anlegen (nur Standardbibliothek)."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from local import SetupError
from workflow import Finding, STATES_FILE, WORKFLOW_DIR, is_enabled, read_table


@dataclass(frozen=True)
class Label:
    name: str
    color: str
    description: str


def wanted_labels(root: Path) -> list[Label]:
    """Aktivierte Zustände der Art triage und status in der Reihenfolge der Datei (terminale haben kein Label)."""
    table = read_table(root / WORKFLOW_DIR / STATES_FILE, f"{WORKFLOW_DIR}/{STATES_FILE}", [])
    if table is None or not all(c in table.header for c in ("id", "kind", "color", "description")):
        return []
    return [Label(z.values["id"], z.values["color"], z.values["description"]) for z in table.rows
            if z.values["kind"] in ("triage", "status") and is_enabled(z)]


def gh(root: Path, *args: str) -> subprocess.CompletedProcess:
    """gh im Repo aufrufen (der Tracker ergibt sich aus dem Remote), ohne Shell."""
    exe = shutil.which("gh")
    if exe is None:
        raise SetupError("gh nicht gefunden")
    return subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root)


def logged_in(root: Path) -> bool:
    return gh(root, "auth", "status").returncode == 0


def existing_labels(root: Path) -> set[str]:
    antwort = gh(root, "label", "list", "--limit", "500", "--json", "name")
    try:
        if antwort.returncode != 0:
            raise ValueError(antwort.stderr.strip() or f"Exit-Code {antwort.returncode}")
        return {eintrag["name"] for eintrag in json.loads(antwort.stdout)}
    except (ValueError, KeyError, TypeError) as fehler:
        raise SetupError(f"gh label list ist nicht lesbar: {fehler}") from fehler


def missing_labels(root: Path) -> list[Label]:
    vorhanden = existing_labels(root)
    return [label for label in wanted_labels(root) if label.name not in vorhanden]


def create_label(root: Path, label: Label) -> None:
    antwort = gh(root, "label", "create", label.name, "--color", label.color, "--description", label.description)
    if antwort.returncode != 0:
        raise SetupError(f"gh label create {label.name} ist fehlgeschlagen: {antwort.stderr.strip()}")
