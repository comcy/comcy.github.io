"""Skill-Prüfung von `setup --check`: liegen die Skills aus workflow/skills.tsv bei den gewählten Agenten?

Orte stehen in der Spalte `skill_paths` von agents.tsv (`;` getrennt, `~` wird aufgelöst, relativ = zum Repo) und
werden nie geraten. Gesucht wird `<ort>/<skill>/SKILL.md`, darunter auch verschachtelt unter einem `skills`-Ordner
(Plugin-Cache: `.../skills/<gruppe>/<skill>/SKILL.md`).
"""
from __future__ import annotations

from pathlib import Path

import workflow
from local import AGENTS_FILE
from workflow import missing_columns, read_table


def read_skill_paths(root: Path) -> dict[str, list[str]]:
    """Agent -> Orte aus agents.tsv; fehlt die Spalte oder ist sie leer, ist die Liste leer."""
    table = read_table(root / AGENTS_FILE, AGENTS_FILE, [])
    if table is None:
        return {}
    return {z.values["agent"]: [p.strip() for p in z.values.get("skill_paths", "").split(";") if p.strip()]
            for z in table.rows}


def required_skills(root: Path) -> list[dict[str, str]]:
    """Aktive Zeilen mit Skill (nicht '-'), Stufe aufgelöst (leer = Stufe der Phase); je Skill und Phase einmal."""
    funde: list[workflow.Finding] = []  # Fehler in den Daten meldet `flow validate`
    d = root / workflow.WORKFLOW_DIR
    phasen = read_table(d / workflow.PHASES_FILE, workflow.PHASES_FILE, funde)
    skills = read_table(d / workflow.SKILLS_FILE, workflow.SKILLS_FILE, funde)
    if phasen is None or skills is None or not missing_columns(phasen, workflow.PHASE_REQUIRED, funde) \
            or not missing_columns(skills, workflow.SKILL_REQUIRED, funde):
        return []
    aktiv = {z.values["id"]: z.values["level"] for z in phasen.rows if workflow.is_enabled(z)}
    ergebnis: list[dict[str, str]] = []
    gesehen: set[tuple[str, str]] = set()
    for z in skills.rows:
        v = z.values
        if not workflow.is_enabled(z) or v["skill"] in ("", "-") or v["phase"] not in aktiv:
            continue
        if (v["skill"], v["phase"]) in gesehen:
            continue
        gesehen.add((v["skill"], v["phase"]))
        ergebnis.append({**v, "level": v["level"] or aktiv[v["phase"]]})
    return ergebnis


def found(root: Path, orte: list[str], skill: str) -> bool:
    for ort in orte:
        basis = Path(ort).expanduser()
        basis = basis if basis.is_absolute() else root / basis
        if any("skills" in p.relative_to(basis).parts or p.parent.parent == basis
               for p in basis.glob(f"**/{skill}/SKILL.md")):
            return True
    return False


def check(root: Path, agenten: list[str]) -> tuple[list[str], int, int]:
    """Meldezeilen für die gewählten Agenten; liefert (Zeilen, Fehler, Hinweise)."""
    zeilen: list[str] = []
    fehler = hinweise = 0
    benoetigt = required_skills(root)
    if not benoetigt:
        return zeilen, 0, 0
    orte = read_skill_paths(root)
    for agent in agenten:
        if not orte.get(agent):
            namen = ", ".join(dict.fromkeys(s["skill"] for s in benoetigt))
            zeilen.append(f"HINWEIS Skills für {agent} nicht prüfbar (keine skill_paths in {AGENTS_FILE}): {namen}")
            hinweise += 1
            continue
        for s in benoetigt:
            wo = f"{agent}: Skill {s['skill']} (Phase {s['phase']})"
            if found(root, orte[agent], s["skill"]):
                zeilen.append(f"ok      {wo}")
            elif s["level"] == "required":
                zeilen.append(f"FEHLT   {wo}" + (f", Abhilfe: {s['hint']}" if s["hint"] else ""))
                fehler += 1
            else:
                zeilen.append(f"HINWEIS {wo} fehlt, optional" + (f" ({s['hint']})" if s["hint"] else ""))
                hinweise += 1
    return zeilen, fehler, hinweise
