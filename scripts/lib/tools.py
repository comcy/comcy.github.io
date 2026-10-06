"""Prüfung der Programme aus scripts/setup.d/tools.tsv (nur Standardbibliothek)."""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

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


def check_tool(zeile: Row) -> Result:
    v = zeile.values
    name, minimum = v["name"], v["min_version"]
    kommando = v["version_cmd"].split()
    fehlt = "fehlt (erforderlich)" if v["level"] == "required" else "fehlt (empfohlen)"
    status = "error" if v["level"] == "required" else "hint"
    exe = shutil.which(kommando[0])
    if exe is None:
        return Result(status, f"{name} {fehlt}: {v['hint']}")
    try:
        lauf = subprocess.run([exe, *kommando[1:]], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired) as fehler:
        return Result(status, f"{name} lässt sich nicht aufrufen ({fehler}): {v['hint']}")
    version = parse_version(lauf.stdout + "\n" + lauf.stderr)
    if minimum == "-":
        return Result("ok", f"{name} {'.'.join(map(str, version)) if version else 'vorhanden'}")
    if version is None:
        return Result(status, f"{name}: Version nicht erkennbar, {minimum} oder neuer erwartet: {v['hint']}")
    mindest = tuple(int(t) for t in minimum.split("."))
    if not at_least(version, mindest):
        return Result(status, f"{name} {'.'.join(map(str, version))} ist zu alt, {minimum} oder neuer nötig: {v['hint']}")
    return Result("ok", f"{name} {'.'.join(map(str, version))}")
