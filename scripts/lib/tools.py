"""Prüfung der Programme aus scripts/setup.d/tools.tsv (nur Standardbibliothek)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import proc
from workflow import Finding, Row, missing_columns, read_table

TOOLS_FILE = "scripts/setup.d/tools.tsv"
TOOL_REQUIRED = ("name", "min_version", "level", "version_cmd", "hint")
TOOL_LEVELS = ("required", "recommended")


@dataclass(frozen=True)
class Result:
    status: str  # "ok", "error" oder "hint"
    message: str


def read_tools(root: Path, findings: list[Finding]) -> list[Row]:
    """Liest tools.tsv und meldet Formatfehler (Spalten, Stufe, Mindestversion); liefert nur gültige Zeilen."""
    table = read_table(root / TOOLS_FILE, TOOLS_FILE, findings)
    if table is None or not missing_columns(table, TOOL_REQUIRED, findings):
        return []
    gueltig = []
    for zeile in table.rows:
        v = zeile.values
        fehler = False
        if v["level"] not in TOOL_LEVELS:
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"ungültige Stufe '{v['level']}', erlaubt: {', '.join(TOOL_LEVELS)}"))
            fehler = True
        if v["min_version"] != "-" and not re.fullmatch(r"\d+(\.\d+)*", v["min_version"]):
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"ungültige Mindestversion '{v['min_version']}', erwartet Zahlen mit Punkten oder -"))
            fehler = True
        if not v["version_cmd"].split():
            findings.append(Finding(table.file, zeile.line, "error", "version_cmd ist leer"))
            fehler = True
        if not fehler:
            gueltig.append(zeile)
    return gueltig


def parse_version(text: str) -> tuple[int, ...] | None:
    """Erste Versionsnummer mit mindestens einem Punkt, zum Beispiel aus 'v22.4.0' oder 'git version 2.45.1'."""
    m = re.search(r"\d+(?:\.\d+)+", text)
    return tuple(int(teil) for teil in m.group(0).split(".")) if m else None


def at_least(installiert: tuple[int, ...], minimum: tuple[int, ...]) -> bool:
    """Numerischer Vergleich mit aufgefüllten Stellen: 20.19 und 20.19.0 sind gleich, 20.2 ist älter als 20.19."""
    laenge = max(len(installiert), len(minimum))
    return installiert + (0,) * (laenge - len(installiert)) >= minimum + (0,) * (laenge - len(minimum))


def version_text(version: tuple[int, ...]) -> str:
    return ".".join(map(str, version))


def check_tool(zeile: Row) -> Result:
    v = zeile.values
    name, minimum = v["name"], v["min_version"]
    kommando = v["version_cmd"].split()  # ponytail: einfache Aufrufe, Pfade mit Leerzeichen bräuchten Anführungszeichen
    fehlt = "fehlt (erforderlich)" if v["level"] == "required" else "fehlt (empfohlen)"
    status = "error" if v["level"] == "required" else "hint"
    if proc.find(kommando[0]) is None:
        return Result(status, f"{name} {fehlt}: {v['hint']}")
    try:
        lauf = proc.run(kommando[0], kommando[1:])
    except proc.SetupError as fehler:
        return Result(status, f"{name}: {fehler}: {v['hint']}")
    version = parse_version(lauf.stdout + "\n" + lauf.stderr)
    if minimum == "-":
        return Result("ok", f"{name} {version_text(version) if version else 'vorhanden'}")
    if version is None:
        return Result(status, f"{name}: Version nicht erkennbar, {minimum} oder neuer erwartet: {v['hint']}")
    mindest = tuple(int(t) for t in minimum.split("."))
    if not at_least(version, mindest):
        return Result(status, f"{name} {version_text(version)} ist zu alt, {minimum} oder neuer nötig: {v['hint']}")
    return Result("ok", f"{name} {version_text(version)}")
