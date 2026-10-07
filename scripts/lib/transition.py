"""Zustandswechsel als Befehl: `flow start <issue>` (nur Standardbibliothek).

Erlaubt ist nur, was workflow/transitions.tsv für die Dimension status vorsieht. Die Bedingungen (guard) wertet
dieser Befehl nicht aus.
ponytail: guard (z. B. no_open_blockers, subissues_exist) bleibt ungeprüft, bei Bedarf Detektoren hier auswerten.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import proc
from labels import gh
from proc import SetupError
from workflow import STATES_FILE, TRANSITIONS_FILE, WORKFLOW_DIR, is_enabled, read_table

START_TARGET = "status:in-progress"
START_TRIGGERS = ("branch_created", "work_started")  # Ereignisse, die ein Start auslösen darf
SLUG_MAX = 40
UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ẞ": "ss"})


def slugify(titel: str) -> str:
    text = unicodedata.normalize("NFKD", titel.translate(UMLAUTE))
    text = text.encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > SLUG_MAX:  # an der letzten Wortgrenze kürzen, sonst hart
        gekuerzt = text[:SLUG_MAX + 1].rsplit("-", 1)[0]
        text = gekuerzt if "-" in text[:SLUG_MAX + 1] else text[:SLUG_MAX]
    return text.strip("-") or "issue"


def status_ids(root: Path) -> set[str]:
    table = read_table(root / WORKFLOW_DIR / STATES_FILE, f"{WORKFLOW_DIR}/{STATES_FILE}", [])
    return {z.values["id"] for z in table.rows if z.values.get("kind") == "status"} if table else set()


def allowed(root: Path, von: str, nach: str, ausloeser: tuple[str, ...]) -> bool:
    table = read_table(root / WORKFLOW_DIR / TRANSITIONS_FILE, f"{WORKFLOW_DIR}/{TRANSITIONS_FILE}", [])
    return table is not None and any(
        z.values["from"] == von and z.values["to"] == nach and z.values["trigger"] in ausloeser and is_enabled(z)
        for z in table.rows)


def git(root: Path, *args: str):
    return proc.run("git", args, cwd=root)


def start(root: Path, issue: str, dry_run: bool = False) -> list[str]:
    """Plant (und führt ohne dry_run aus) Branch und Label; gibt die Schritte als Text zurück. Fehler: SetupError."""
    antwort = gh(root, "issue", "view", issue, "--json", "title,state,labels")
    if antwort.returncode != 0:
        raise SetupError(f"gh issue view {issue} ist fehlgeschlagen: {antwort.stderr.strip()}")
    try:
        daten = json.loads(antwort.stdout)
        titel, offen = daten["title"], daten["state"].upper() == "OPEN"
        labels = [eintrag["name"] for eintrag in daten["labels"]]
    except (ValueError, KeyError, TypeError, AttributeError) as fehler:
        raise SetupError(f"gh issue view {issue} ist nicht lesbar: {fehler}") from fehler
    if not offen:
        raise SetupError(f"Issue {issue} ist nicht offen")
    alt = [n for n in labels if n in status_ids(root)]
    if len(alt) > 1:
        raise SetupError(f"Issue {issue} trägt mehrere status-Labels: {', '.join(alt)}")
    von = alt[0] if alt else "-"
    if not allowed(root, von, START_TARGET, START_TRIGGERS):
        raise SetupError(f"Übergang {von} -> {START_TARGET} ist in {WORKFLOW_DIR}/{TRANSITIONS_FILE} nicht erlaubt")
    branch = f"feature/{issue}-{slugify(titel)}"
    if git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0:
        raise SetupError(f"Branch {branch} existiert schon")
    edit = ["issue", "edit", issue, "--add-label", START_TARGET] + (["--remove-label", alt[0]] if alt else [])
    schritte = [f"git branch {branch}", "gh " + " ".join(edit)]
    if not dry_run:
        angelegt = git(root, "branch", branch)
        if angelegt.returncode != 0:
            raise SetupError(f"git branch {branch} ist fehlgeschlagen: {angelegt.stderr.strip()}")
        gesetzt = gh(root, *edit)
        if gesetzt.returncode != 0:
            git(root, "branch", "-D", branch)  # zurückrollen: kein Branch ohne Label
            raise SetupError(f"gh issue edit {issue} ist fehlgeschlagen: {gesetzt.stderr.strip()}")
    return schritte
