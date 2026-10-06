"""Leser und Prüfungen für die Prozessdaten unter workflow/ (nur Standardbibliothek).

Der Leser ist die einzige Zugriffsstelle auf die Dateien: Tabulatorgetrennt, Zeilen mit # und leere Zeilen werden
ignoriert, die erste übrige Zeile benennt die Spalten, Werte werden über diese Namen zugeordnet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

WORKFLOW_DIR = "workflow"
STATES_FILE = "states.tsv"

STATE_KINDS = ("triage", "status", "terminal")
STATE_REQUIRED = ("id", "kind", "color", "description")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    level: str  # "error" oder "warning"
    message: str

    def format(self) -> str:
        stufe = "Fehler" if self.level == "error" else "Warnung"
        return f"{self.file}:{self.line}: {stufe}: {self.message}"


@dataclass
class Row:
    line: int
    values: dict[str, str]


@dataclass
class Table:
    file: str
    header_line: int
    header: list[str]
    rows: list[Row] = field(default_factory=list)


def read_table(path: Path, rel: str, findings: list[Finding]) -> Table | None:
    """Liest eine Datei als Tabelle; fehlende Datei, fehlende Kopfzeile und falsche Spaltenzahl werden gemeldet."""
    if not path.is_file():
        findings.append(Finding(rel, 1, "error", "Datei fehlt"))
        return None
    text = path.read_bytes().decode("utf-8-sig")
    table: Table | None = None
    for nummer, zeile in enumerate(text.splitlines(), start=1):
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        zellen = zeile.split("\t")
        if table is None:
            table = Table(rel, nummer, [c.strip() for c in zellen])
            continue
        if len(zellen) != len(table.header):
            findings.append(Finding(rel, nummer, "error",
                                    f"{len(table.header)} Spalten erwartet, {len(zellen)} gefunden"))
            continue
        table.rows.append(Row(nummer, {name: wert.strip() for name, wert in zip(table.header, zellen)}))
    if table is None:
        findings.append(Finding(rel, 1, "error", "keine Kopfzeile gefunden"))
    return table


def missing_columns(table: Table, required: tuple[str, ...], findings: list[Finding]) -> bool:
    """Meldet fehlende Pflichtspalten; True, wenn alle da sind."""
    fehlen = [name for name in required if name not in table.header]
    for name in fehlen:
        findings.append(Finding(table.file, table.header_line, "error", f"Pflichtspalte '{name}' fehlt"))
    return not fehlen


def check_states(table: Table, findings: list[Finding]) -> None:
    """Zustände: eindeutige id, gültige Art, Farbe aus sechs Hex-Zeichen (bei terminal auch '-'), Beschreibung,
    genau ein terminaler Zustand, enabled nur yes oder no."""
    if not missing_columns(table, STATE_REQUIRED, findings):
        return
    gesehen: dict[str, int] = {}
    terminale = 0
    for zeile in table.rows:
        v = zeile.values
        if not v["id"]:
            findings.append(Finding(table.file, zeile.line, "error", "id ist leer"))
        elif v["id"] in gesehen:
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"doppelte id '{v['id']}' (erste in Zeile {gesehen[v['id']]})"))
        else:
            gesehen[v["id"]] = zeile.line
        if v["kind"] not in STATE_KINDS:
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"ungültige Art '{v['kind']}', erlaubt: {', '.join(STATE_KINDS)}"))
        terminal = v["kind"] == "terminal"
        terminale += terminal
        if not (re.fullmatch(r"[0-9a-fA-F]{6}", v["color"]) or (terminal and v["color"] == "-")):
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"ungültige Farbe '{v['color']}', erwartet sechs Hex-Zeichen"
                                    + (" oder '-'" if terminal else "")))
        if not v["description"]:
            findings.append(Finding(table.file, zeile.line, "error", "Beschreibung ist leer"))
        if v.get("enabled", "yes") not in ("yes", "no", ""):
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"enabled muss yes oder no sein, nicht '{v['enabled']}'"))
    if terminale != 1:
        findings.append(Finding(table.file, table.header_line, "error",
                                f"genau ein Zustand der Art 'terminal' erwartet, gefunden {terminale}"))


def validate(root: Path) -> list[Finding]:
    """Prüft alle Dateien unter <root>/workflow und liefert die Funde sortiert nach Datei und Zeile."""
    findings: list[Finding] = []
    rel = f"{WORKFLOW_DIR}/{STATES_FILE}"
    table = read_table(root / WORKFLOW_DIR / STATES_FILE, rel, findings)
    if table is not None:
        check_states(table, findings)
    return sorted(findings, key=lambda f: (f.file, f.line, f.level, f.message))
