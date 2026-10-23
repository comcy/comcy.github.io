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
TRANSITIONS_FILE = "transitions.tsv"
PHASES_FILE = "phases.tsv"
DETECTORS_FILE = "detectors.tsv"
SKILLS_FILE = "skills.tsv"
ROLES_FILE = "roles.tsv"
METRICS_FILE = "metrics.tsv"
METRIC_SOURCES_FILE = "metric-sources.tsv"

STATE_KINDS = ("triage", "status", "prio", "terminal")
STATE_REQUIRED = ("id", "kind", "color", "description")
TRANSITION_REQUIRED = ("from", "to", "trigger", "guard")
PHASE_REQUIRED = ("id", "name", "tool", "done_when", "level")
PHASE_LEVELS = ("required", "optional")
SKILL_REQUIRED = ("skill", "phase", "level", "source", "hint", "manual")
ROLE_REQUIRED = ("role", "phases", "allowed_tools", "human_gate", "description")
DETECTOR_REQUIRED = ("name", "arg", "description")
METRIC_REQUIRED = ("id", "art", "name", "unit", "source", "target", "enabled")
METRIC_SOURCE_REQUIRED = ("name", "arg", "description")
METRIC_ARTS = ("leading", "lagging")
METRIC_UNITS = ("h", "d", "%", "n")


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
    # nur \n, \r\n und \r trennen Zeilen (str.splitlines trennt auch an \x0b, \x0c und Unicode-Zeichen)
    for nummer, zeile in enumerate(re.split(r"\r\n|\n|\r", text), start=1):
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


def is_enabled(row: Row) -> bool:
    return row.values.get("enabled", "yes") != "no"


def check_detectors(table: Table, findings: list[Finding]) -> dict[str, str] | None:
    """Das feste Vokabular: name eindeutig, arg ist '-', 'text', 'path' oder 'enum:a|b|c'. Liefert name -> arg."""
    if not missing_columns(table, DETECTOR_REQUIRED, findings):
        return None
    vokabular: dict[str, str] = {}
    for zeile in table.rows:
        name, arg = zeile.values["name"], zeile.values["arg"]
        if not name:
            findings.append(Finding(table.file, zeile.line, "error", "name ist leer"))
            continue
        if name in vokabular:
            findings.append(Finding(table.file, zeile.line, "error", f"doppelter Detektor '{name}'"))
            continue
        werte = arg[len("enum:"):].split("|") if arg.startswith("enum:") else None
        if arg not in ("-", "text", "path") and (werte is None or not all(werte)):
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"ungültige Argumentform '{arg}' für '{name}', erlaubt: -, text, path, enum:a|b|c"))
            continue
        vokabular[name] = arg
    return vokabular


def check_expression(table: Table, zeile: Row, spalte: str, vokabular: dict[str, str],
                     findings: list[Finding]) -> None:
    """Eine UND-Liste von Detektoren ('-' = keine): jeder Name muss im Vokabular stehen, das Argument zur Form passen.

    ponytail: Argumente dürfen kein Komma enthalten (Trenner der Liste), bei Bedarf Anführungszeichen einführen.
    """
    ausdruck = zeile.values[spalte]
    if ausdruck == "-":
        return
    if not ausdruck:
        findings.append(Finding(table.file, zeile.line, "error", f"{spalte} ist leer, '-' steht für keine Bedingung"))
        return
    for teil in (t.strip() for t in ausdruck.split(",")):
        name, trenner, arg = teil.partition(":")
        form = vokabular.get(name)
        if form is None:
            findings.append(Finding(table.file, zeile.line, "error", f"unbekannter Detektor '{name}' in {spalte}"))
        elif form == "-" and trenner:
            findings.append(Finding(table.file, zeile.line, "error", f"Detektor '{name}' erwartet kein Argument"))
        elif form in ("text", "path") and not arg:
            findings.append(Finding(table.file, zeile.line, "error", f"Detektor '{name}' braucht ein Argument ({form})"))
        elif form.startswith("enum:"):
            erlaubt = form[len("enum:"):]
            if not trenner or arg not in erlaubt.split("|"):
                findings.append(Finding(table.file, zeile.line, "error",
                                        f"Argument '{arg}' für '{name}' ungültig, erlaubt: {erlaubt}"))


def check_transitions(table: Table, states: dict[str, tuple[str, bool]], vokabular: dict[str, str] | None,
                      findings: list[Finding]) -> None:
    """Übergänge: from (oder '-') und to verweisen auf Zustände, gleiche Dimension außer Start und terminalem Ziel."""
    if not missing_columns(table, TRANSITION_REQUIRED, findings):
        return
    for zeile in table.rows:
        v = zeile.values
        von, nach = v["from"], v["to"]
        if von != "-" and von not in states:
            findings.append(Finding(table.file, zeile.line, "error", f"unbekannter Zustand '{von}' in from"))
        if nach not in states:
            findings.append(Finding(table.file, zeile.line, "error",
                                    "Ziel darf nicht '-' sein" if nach == "-" else f"unbekannter Zustand '{nach}' in to"))
        for zustand in (von, nach):
            if states.get(zustand, ("",))[0] == "prio":
                findings.append(Finding(table.file, zeile.line, "error",
                                        f"Prio-Label '{zustand}' ist kein Zustand und darf an keinem Übergang teilnehmen"))
        if von in states and nach in states:
            kind_von, kind_nach = states[von][0], states[nach][0]
            if kind_von == "terminal":
                findings.append(Finding(table.file, zeile.line, "error", f"kein Übergang aus dem terminalen Zustand '{von}'"))
            elif kind_nach != "terminal" and kind_von != kind_nach:
                findings.append(Finding(table.file, zeile.line, "error",
                                        f"Übergang über Dimensionen ({kind_von} -> {kind_nach}), erlaubt nur innerhalb "
                                        "einer Dimension, vom Start '-' oder zu einem terminalen Zustand"))
        if not v["trigger"]:
            findings.append(Finding(table.file, zeile.line, "error", "trigger ist leer"))
        if vokabular is not None:
            check_expression(table, zeile, "guard", vokabular, findings)
        if is_enabled(zeile):
            for zustand in (von, nach):
                if zustand in states and not states[zustand][1]:
                    findings.append(Finding(table.file, zeile.line, "warning",
                                            f"verweist auf Zustand '{zustand}' mit enabled=no"))


def phase_key(phase_id: str) -> tuple[int, int, str]:
    """Sortierschlüssel der Phasen-IDs: S vor 0, dann Zahl, dann Buchstabensuffix (4 vor 4b vor 5)."""
    if phase_id == "S":
        return (-1, 0, "")
    m = re.fullmatch(r"(\d+)([a-z]*)", phase_id)
    return (0, int(m.group(1)), m.group(2)) if m else (1, 0, phase_id)


def check_phases(table: Table, vokabular: dict[str, str] | None, findings: list[Finding]) -> None:
    if not missing_columns(table, PHASE_REQUIRED, findings):
        return
    gesehen: dict[str, int] = {}
    vorher: Row | None = None
    for zeile in table.rows:
        v = zeile.values
        if not v["id"]:
            findings.append(Finding(table.file, zeile.line, "error", "id ist leer"))
        elif v["id"] in gesehen:
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"doppelte id '{v['id']}' (erste in Zeile {gesehen[v['id']]})"))
        else:
            gesehen[v["id"]] = zeile.line
        if v["level"] not in PHASE_LEVELS:
            findings.append(Finding(table.file, zeile.line, "error",
                                    f"ungültige Stufe '{v['level']}', erlaubt: {', '.join(PHASE_LEVELS)}"))
        if v.get("enabled", "yes") not in ("yes", "no", ""):
            findings.append(Finding(table.file, zeile.line, "error", f"enabled muss yes oder no sein, nicht '{v['enabled']}'"))
        if vokabular is not None:
            check_expression(table, zeile, "done_when", vokabular, findings)
        if vorher is not None and phase_key(v["id"]) <= phase_key(vorher.values["id"]):
            findings.append(Finding(table.file, zeile.line, "warning",
                                    f"Phasen-IDs nicht aufsteigend: '{v['id']}' nach '{vorher.values['id']}'"))
        vorher = zeile


def check_profile(phases: Table, skills: Table | None, roles: Table | None, findings: list[Finding]) -> None:
    """skills.tsv und roles.tsv: Spalten, Werte, Verweise auf Phasen und die Abdeckung der aktiven Pflichtphasen."""
    phasen = {r.values["id"]: r for r in phases.rows}
    gedeckt: set[str] = set()
    mit_rolle: set[str] = set()
    if skills is not None and missing_columns(skills, SKILL_REQUIRED, findings):
        for z in skills.rows:
            v = z.values
            if not v["skill"]:
                findings.append(Finding(skills.file, z.line, "error", "skill ist leer, '-' steht für keinen"))
            if v["level"] not in ("", *PHASE_LEVELS):
                findings.append(Finding(skills.file, z.line, "error", f"ungültige Stufe '{v['level']}'"))
            if v["manual"] not in ("", "yes", "no"):
                findings.append(Finding(skills.file, z.line, "error", f"manual muss yes oder no sein, nicht '{v['manual']}'"))
            if v.get("enabled", "yes") not in ("yes", "no", ""):
                findings.append(Finding(skills.file, z.line, "error", f"enabled muss yes oder no sein, nicht '{v['enabled']}'"))
            if v["phase"] not in phasen:
                findings.append(Finding(skills.file, z.line, "error", f"unbekannte Phase '{v['phase']}'"))
            elif not is_enabled(phasen[v["phase"]]):
                findings.append(Finding(skills.file, z.line, "warning", f"Phase '{v['phase']}' ist abgeschaltet"))
            elif is_enabled(z) and (v["manual"] == "yes" or v["skill"] not in ("", "-")):
                gedeckt.add(v["phase"])
    if roles is not None and missing_columns(roles, ROLE_REQUIRED, findings):
        for z in roles.rows:
            v = z.values
            if not v["role"]:
                findings.append(Finding(roles.file, z.line, "error", "role ist leer"))
            if v.get("enabled", "yes") not in ("yes", "no", ""):
                findings.append(Finding(roles.file, z.line, "error", f"enabled muss yes oder no sein, nicht '{v['enabled']}'"))
            if v["human_gate"] not in ("yes", "no"):
                findings.append(Finding(roles.file, z.line, "error", f"human_gate muss yes oder no sein, nicht '{v['human_gate']}'"))
            ids = [p.strip() for p in v["phases"].split(",") if p.strip()]
            for p in ids:
                if p not in phasen:
                    findings.append(Finding(roles.file, z.line, "error", f"unbekannte Phase '{p}'"))
            if is_enabled(z):
                if not ids:
                    findings.append(Finding(roles.file, z.line, "warning", f"Rolle '{v['role']}' ohne Phase"))
                mit_rolle.update(ids)
    for z in phases.rows:
        v = z.values
        if v["level"] != "required" or not is_enabled(z):
            continue
        if skills is not None and v["id"] not in gedeckt:
            findings.append(Finding(phases.file, z.line, "error", f"Phase {v['id']} hat weder Skill noch manual in {SKILLS_FILE}"))
        if roles is not None and v["id"] not in mit_rolle:
            findings.append(Finding(phases.file, z.line, "error", f"Phase {v['id']} ist keiner Rolle in {ROLES_FILE} zugeordnet"))


def check_metrics(metrics: Table | None, sources: Table | None, findings: list[Finding]) -> None:
    """metrics.tsv: eindeutige id, art, unit, target (leer oder Zahl), source aus metric-sources.tsv (abgeschaltet = Warnung)."""
    quellen: dict[str, bool] = {}
    if sources is not None and missing_columns(sources, METRIC_SOURCE_REQUIRED, findings):
        for z in sources.rows:
            name = z.values["name"]
            if not name:
                findings.append(Finding(sources.file, z.line, "error", "name ist leer"))
            elif name in quellen:
                findings.append(Finding(sources.file, z.line, "error", f"doppelte Quelle '{name}'"))
            else:
                quellen[name] = is_enabled(z)
    if metrics is None or not missing_columns(metrics, METRIC_REQUIRED, findings):
        return
    gesehen: dict[str, int] = {}
    for z in metrics.rows:
        v = z.values
        if not v["id"]:
            findings.append(Finding(metrics.file, z.line, "error", "id ist leer"))
        elif v["id"] in gesehen:
            findings.append(Finding(metrics.file, z.line, "error", f"doppelte id '{v['id']}' (erste in Zeile {gesehen[v['id']]})"))
        else:
            gesehen[v["id"]] = z.line
        if v["art"] not in METRIC_ARTS:
            findings.append(Finding(metrics.file, z.line, "error", f"ungültige art '{v['art']}', erlaubt: {', '.join(METRIC_ARTS)}"))
        if v["unit"] not in METRIC_UNITS:
            findings.append(Finding(metrics.file, z.line, "error", f"ungültige unit '{v['unit']}', erlaubt: {', '.join(METRIC_UNITS)}"))
        if v["target"]:
            try:
                float(v["target"])
            except ValueError:
                findings.append(Finding(metrics.file, z.line, "error", f"target muss eine Zahl sein, nicht '{v['target']}'"))
        if v["enabled"] not in ("yes", "no", ""):
            findings.append(Finding(metrics.file, z.line, "error", f"enabled muss yes oder no sein, nicht '{v['enabled']}'"))
        if sources is None or not all(c in sources.header for c in METRIC_SOURCE_REQUIRED):
            continue
        if v["source"] not in quellen:
            findings.append(Finding(metrics.file, z.line, "error", f"unbekannte source '{v['source']}' (nicht in {METRIC_SOURCES_FILE})"))
        elif not quellen[v["source"]] and is_enabled(z):
            findings.append(Finding(metrics.file, z.line, "warning", f"source '{v['source']}' ist abgeschaltet"))


def check_graph(states_table: Table, transitions_table: Table, findings: list[Finding]) -> None:
    """Warnungen: aktivierte Zustände ohne eingehenden Übergang (unerreichbar) oder ohne ausgehenden (Sackgasse)."""
    aktiv = [r for r in transitions_table.rows if is_enabled(r)]
    eingang = {r.values["to"] for r in aktiv}
    ausgang = {r.values["from"] for r in aktiv}
    for zeile in states_table.rows:
        v = zeile.values
        if not is_enabled(zeile) or v["kind"] == "prio":  # Prio-Labels nehmen an keinem Übergang teil
            continue
        if v["id"] not in eingang:
            findings.append(Finding(states_table.file, zeile.line, "warning", f"kein eingehender Übergang für '{v['id']}'"))
        if v["kind"] != "terminal" and v["id"] not in ausgang:
            findings.append(Finding(states_table.file, zeile.line, "warning", f"kein ausgehender Übergang für '{v['id']}'"))


def validate(root: Path) -> list[Finding]:
    """Prüft alle Dateien unter <root>/workflow und liefert die Funde sortiert nach Datei und Zeile."""
    findings: list[Finding] = []

    def laden(name: str) -> Table | None:
        return read_table(root / WORKFLOW_DIR / name, f"{WORKFLOW_DIR}/{name}", findings)

    states_table, transitions_table = laden(STATES_FILE), laden(TRANSITIONS_FILE)
    phases_table, detectors_table = laden(PHASES_FILE), laden(DETECTORS_FILE)
    skills_table, roles_table = laden(SKILLS_FILE), laden(ROLES_FILE)
    vokabular = check_detectors(detectors_table, findings) if detectors_table else None
    states_ok = False
    if states_table is not None:
        before = len(findings)
        check_states(states_table, findings)
        states_ok = len(findings) == before
    zustaende: dict[str, tuple[str, bool]] = {}
    if states_table is not None and all(c in states_table.header for c in STATE_REQUIRED):
        zustaende = {r.values["id"]: (r.values["kind"], is_enabled(r)) for r in states_table.rows if r.values["id"]}
    if transitions_table is not None:
        check_transitions(transitions_table, zustaende, vokabular, findings)
        if states_table is not None and states_ok and all(c in transitions_table.header for c in TRANSITION_REQUIRED):
            check_graph(states_table, transitions_table, findings)
    if phases_table is not None:
        check_phases(phases_table, vokabular, findings)
        if all(c in phases_table.header for c in PHASE_REQUIRED):
            check_profile(phases_table, skills_table, roles_table, findings)
    check_metrics(laden(METRICS_FILE), laden(METRIC_SOURCES_FILE), findings)
    return sorted(findings, key=lambda f: (f.file, f.line, f.level, f.message))
