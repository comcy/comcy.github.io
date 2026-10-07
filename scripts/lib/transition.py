"""Zustandswechsel als Befehl: `flow start <issue>` und `flow review [<issue>]` (nur Standardbibliothek).

Erlaubt ist nur, was workflow/transitions.tsv für die Dimension status vorsieht, samt guard (Detektoren, Komma = UND).
Ausgewertet werden die Detektoren, die sich per gh (nur lesend) oder Git ermitteln lassen; die übrigen sind eine Warnung.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import proc
from labels import gh
from proc import SetupError
from workflow import STATES_FILE, TRANSITIONS_FILE, WORKFLOW_DIR, is_enabled, read_table

START_TARGET = "status:in-progress"
START_TRIGGERS = ("branch_created", "work_started")  # Ereignisse, die ein Start auslösen darf
REVIEW_FROM, REVIEW_TARGET, REVIEW_TRIGGERS = "status:in-progress", "status:in-review", ("pr_ready",)
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


def allowed(root: Path, von: str, nach: str, ausloeser: tuple[str, ...]) -> str | None:
    """guard des passenden Übergangs ("-" = keine Bedingung) oder None, wenn er nicht erlaubt ist."""
    table = read_table(root / WORKFLOW_DIR / TRANSITIONS_FILE, f"{WORKFLOW_DIR}/{TRANSITIONS_FILE}", [])
    for z in table.rows if table else []:
        if z.values["from"] == von and z.values["to"] == nach and z.values["trigger"] in ausloeser and is_enabled(z):
            return z.values["guard"]
    return None


def _api_liste(root: Path, issue: str, pfad: str) -> list:
    """Liste aus gh api (Blocker, Sub-Issues); ValueError, wenn nicht lesbar."""
    antwort = gh(root, "api", f"repos/{{owner}}/{{repo}}/issues/{issue}/{pfad}")
    if antwort.returncode != 0:
        raise ValueError(antwort.stderr.strip() or f"Exit-Code {antwort.returncode}")
    daten = json.loads(antwort.stdout)
    if not isinstance(daten, list):
        raise ValueError("keine Liste")
    return daten


def _checks_success(root: Path) -> bool:
    """Alle Checks des PR zum aktuellen Branch grün (gh pr checks); ValueError, wenn nicht ermittelbar."""
    antwort = gh(root, "pr", "checks", "--json", "bucket")
    try:
        buckets = [e["bucket"] for e in json.loads(antwort.stdout)]
    except (ValueError, KeyError, TypeError):
        if "no pull requests found" in antwort.stderr:
            return False  # kein PR: Bedingung nicht erfüllt
        raise ValueError(antwort.stderr.strip() or "Antwort nicht lesbar") from None
    return bool(buckets) and all(b in ("pass", "skipping") for b in buckets)


def ids_der_art(root: Path, art: str) -> set[str]:
    table = read_table(root / WORKFLOW_DIR / STATES_FILE, f"{WORKFLOW_DIR}/{STATES_FILE}", [])
    return {z.values["id"] for z in table.rows if z.values.get("kind") == art} if table else set()


def auswerten(root: Path, issue: str, labels: list[str], bedingung: str) -> bool:
    """Wertet einen Detektor aus. ValueError, wenn er sich nicht auswerten lässt (unbekannt oder gh/Git-Fehler)."""
    name, _, arg = bedingung.partition(":")
    try:
        if name == "label":
            return arg in labels
        if name == "has_label_kind":
            return any(n in labels for n in ids_der_art(root, arg))
        if name in ("issue_open", "issue_exists"):
            return True  # lade_issue hat ein offenes Issue geliefert
        if name == "issue_closed":
            return False
        if name == "no_open_blockers":
            return not any(str(e["state"]).lower() == "open" for e in _api_liste(root, issue, "dependencies/blocked_by"))
        if name == "subissues_exist":
            return bool(_api_liste(root, issue, "sub_issues"))
        if name == "checks" and arg == "success":
            return _checks_success(root)
        if name == "file_exists" and arg:
            return (root / arg).is_file()
    except (ValueError, KeyError, TypeError) as fehler:
        raise ValueError(f"{bedingung}: {fehler}") from fehler
    raise ValueError(f"{bedingung}: nicht auswertbar")


def pruefe_guard(root: Path, issue: str, labels: list[str], guard: str) -> None:
    """Nicht erfüllter Detektor: SetupError ohne Änderung; nicht auswertbarer: Warnung auf stderr, kein Abbruch."""
    for bedingung in (b.strip() for b in guard.split(",") if b.strip() and b.strip() != "-"):
        try:
            erfuellt = auswerten(root, issue, labels, bedingung)
        except ValueError as fehler:
            print(f"Warnung: Bedingung nicht prüfbar, übergangen ({fehler})", file=sys.stderr)
            continue
        if not erfuellt:
            raise SetupError(f"Bedingung {bedingung} ist nicht erfüllt (guard in {WORKFLOW_DIR}/{TRANSITIONS_FILE})")


def git(root: Path, *args: str):
    return proc.run("git", args, cwd=root)


def lade_issue(root: Path, issue: str) -> tuple[str, list[str], list[str]]:
    """Titel, status-Labels und alle Labels eines offenen Issues (per gh). Fehler: SetupError."""
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
    alt = [n for n in labels if n in ids_der_art(root, "status")]
    if len(alt) > 1:
        raise SetupError(f"Issue {issue} trägt mehrere status-Labels: {', '.join(alt)}")
    return titel, alt, labels


def start(root: Path, issue: str, dry_run: bool = False) -> list[str]:
    """Plant (und führt ohne dry_run aus) Branch und Label; gibt die Schritte als Text zurück. Fehler: SetupError."""
    titel, alt, labels = lade_issue(root, issue)
    von = alt[0] if alt else "-"
    guard = allowed(root, von, START_TARGET, START_TRIGGERS)
    if guard is None:
        raise SetupError(f"Übergang {von} -> {START_TARGET} ist in {WORKFLOW_DIR}/{TRANSITIONS_FILE} nicht erlaubt")
    pruefe_guard(root, issue, labels, guard)
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


def issue_aus_branch(root: Path) -> str:
    """Issue-Nummer aus dem aktuellen Branch (`<typ>/<nr>-<slug>`). Fehler: SetupError."""
    name = git(root, "branch", "--show-current").stdout.strip()
    treffer = re.match(r"[^/]+/(\d+)(?:-|$)", name)
    if not treffer:
        raise SetupError(f"Branch '{name or 'detached HEAD'}' enthält keine Issue-Nummer (erwartet z. B. feature/42-x): "
                         "bitte die Nummer angeben, `flow review <issue>`")
    return treffer.group(1)


def review(root: Path, issue: str | None = None, dry_run: bool = False) -> list[str]:
    """Wechselt von status:in-progress nach status:in-review; ohne issue aus dem Branchnamen. Fehler: SetupError."""
    issue = issue or issue_aus_branch(root)
    _, alt, labels = lade_issue(root, issue)
    von = alt[0] if alt else "-"
    guard = allowed(root, von, REVIEW_TARGET, REVIEW_TRIGGERS) if von == REVIEW_FROM else None
    if guard is None:
        raise SetupError(f"Übergang {von} -> {REVIEW_TARGET} ist nicht erlaubt (Issue {issue} braucht {REVIEW_FROM} "
                         f"und einen passenden Eintrag in {WORKFLOW_DIR}/{TRANSITIONS_FILE})")
    pruefe_guard(root, issue, labels, guard)
    edit = ["issue", "edit", issue, "--add-label", REVIEW_TARGET, "--remove-label", REVIEW_FROM]
    if not dry_run:
        gesetzt = gh(root, *edit)
        if gesetzt.returncode != 0:
            raise SetupError(f"gh issue edit {issue} ist fehlgeschlagen: {gesetzt.stderr.strip()}")
    return ["gh " + " ".join(edit)]
