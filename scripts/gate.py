"""Prüfungen für Commits: `python3 scripts/gate.py commits <bereich>`, `commit-msg <datei>` und `secrets [--range a..b]` (Hooks).

Eine Logik für Hook und CI. Nur Standardbibliothek, Python 3.11 oder neuer.
"""
from __future__ import annotations

import pycheck  # liegt neben dieser Datei und läuft auch auf älterem Python

pycheck.require_python()

import argparse  # noqa: E402
import fnmatch  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import proc  # noqa: E402
import workflow  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TYPES_FILE = "scripts/gate.d/commit-types.tsv"
RULE = "type(scope)!: Betreff"
SECRETS_FILE = "scripts/gate.d/secrets.tsv"
ALLOW_FILE = "scripts/gate.d/allow.tsv"


def commit_types(root: Path) -> list[str]:
    funde: list[workflow.Finding] = []
    tabelle = workflow.read_table(root / TYPES_FILE, TYPES_FILE, funde)
    if funde or tabelle is None or not workflow.missing_columns(tabelle, ("type",), funde):
        raise proc.SetupError("; ".join(f.format() for f in funde) or f"{TYPES_FILE}: Spalte 'type' fehlt")
    return [zeile.values["type"] for zeile in tabelle.rows]


def subject_ok(betreff: str, typen: list[str], merge_erlaubt: bool = True) -> bool:
    """Gültig: type(scope)!: Betreff; Reverts ('Revert "…"') und Merge-Commits sind erlaubt."""
    if betreff.startswith('Revert "') or (merge_erlaubt and betreff.startswith("Merge ")):
        return True
    return re.fullmatch(rf"({'|'.join(map(re.escape, typen))})(\([^()\s][^()]*\))?!?: \S.*", betreff) is not None


def report(fehler: list[tuple[str, str]], typen: list[str]) -> int:
    for wer, betreff in fehler:
        print(f"FEHLER  {wer}: '{betreff}' verletzt die Regel {RULE} (Typen: {', '.join(typen)})")
    return 1 if fehler else 0


def check_range(root: Path, bereich: str, typen: list[str]) -> int:
    lauf = proc.run("git", ["log", "--format=%h%x1f%P%x1f%s", bereich, "--"], cwd=root)
    if lauf.returncode:
        raise proc.SetupError(f"git log {bereich}: {lauf.stderr.strip()}")
    fehler = []
    for zeile in lauf.stdout.split("\n"):
        if not zeile:
            continue
        sha, eltern, betreff = zeile.split("\x1f", 2)
        if len(eltern.split()) < 2 and not subject_ok(betreff, typen, merge_erlaubt=False):  # Merge: mehrere Eltern
            fehler.append((sha, betreff))
    return report(fehler, typen)


def check_message(datei: Path, typen: list[str]) -> int:
    zeilen = [z for z in datei.read_text(encoding="utf-8", errors="replace").splitlines() if not z.startswith("#")]
    betreff = next((z.strip() for z in zeilen if z.strip()), "")
    return report([] if subject_ok(betreff, typen) else [("Commit-Nachricht", betreff)], typen)


def load_rules(root: Path) -> tuple[list[tuple[str, str, re.Pattern]], list[tuple[str, re.Pattern]]]:
    """(Regeln als (id, kind, Regex), Ausnahmen als (Pfad-Glob, Regex)); Fehler in den Tabellen ergeben einen SetupError."""
    funde: list[workflow.Finding] = []
    regeln, ausnahmen = [], []
    tabelle = workflow.read_table(root / SECRETS_FILE, SECRETS_FILE, funde)
    if tabelle and workflow.missing_columns(tabelle, ("id", "kind", "pattern", "description"), funde):
        for z in tabelle.rows:
            if z.values["kind"] not in ("line", "file"):
                funde.append(workflow.Finding(SECRETS_FILE, z.line, "error", "kind muss line oder file sein"))
            try:
                regeln.append((z.values["id"], z.values["kind"], re.compile(z.values["pattern"])))
            except re.error as fehler:
                funde.append(workflow.Finding(SECRETS_FILE, z.line, "error", f"ungültiges Muster: {fehler}"))
    tabelle = workflow.read_table(root / ALLOW_FILE, ALLOW_FILE, funde)
    if tabelle and workflow.missing_columns(tabelle, ("path", "pattern", "reason"), funde):
        for z in tabelle.rows:
            if not z.values["reason"].strip():
                funde.append(workflow.Finding(ALLOW_FILE, z.line, "error", "Grund fehlt (Ausnahmen brauchen eine Begründung)"))
            try:
                ausnahmen.append((z.values["path"], re.compile(z.values["pattern"])))
            except re.error as fehler:
                funde.append(workflow.Finding(ALLOW_FILE, z.line, "error", f"ungültiges Muster: {fehler}"))
    if funde:
        raise proc.SetupError("\n".join(f.format() for f in funde))
    return regeln, ausnahmen


def git_out(root: Path, *args: str) -> str:
    lauf = proc.run("git", ["-c", "core.quotepath=off", *args], cwd=root)
    if lauf.returncode:
        raise proc.SetupError(f"git {' '.join(args)}: {lauf.stderr.strip()}")
    return lauf.stdout


def check_secrets(root: Path, bereich: str | None) -> int:
    """Prüft hinzugefügte Zeilen und Dateinamen (Index oder Bereich); meldet Datei, Zeile und Regel, nie den Wert."""
    regeln, ausnahmen = load_rules(root)
    basis = ["diff", "--cached"] if bereich is None else ["diff", bereich]
    basis += ["--no-color", "--no-ext-diff", "--no-renames", "--diff-filter=AM"]

    def erlaubt(pfad: str, text: str) -> bool:
        return any(fnmatch.fnmatchcase(pfad, g) and m.search(text) for g, m in ausnahmen)

    treffer: list[str] = []
    for pfad in filter(None, git_out(root, *basis, "--name-only", "-z").split("\x00")):
        for rid, art, muster in regeln:
            if art == "file" and muster.search(pfad) and not erlaubt(pfad, pfad):
                treffer.append(f"{pfad}: Regel {rid}")
    pfad, nr = "", 0
    for zeile in git_out(root, *basis, "-U0").split("\n"):
        if zeile.startswith("+++ "):
            pfad = zeile[6:].split("\t")[0] if zeile.startswith("+++ b/") else ""
        elif zeile.startswith("@@"):
            nr = int(re.search(r"\+(\d+)", zeile).group(1)) - 1
        elif zeile.startswith("+") and pfad:
            nr += 1
            for rid, art, muster in regeln:
                if art == "line" and muster.search(zeile[1:]) and not erlaubt(pfad, zeile[1:]):
                    treffer.append(f"{pfad}:{nr}: Regel {rid}")
    for t in dict.fromkeys(treffer):
        print(f"FEHLER  {t} (mögliches Secret; Wert wird nicht ausgegeben; Ausnahme nur mit Grund in {ALLOW_FILE})")
    return 1 if treffer else 0


def main(argv: list[str] | None = None) -> int:
    proc.utf8_output()
    parser = argparse.ArgumentParser(prog="gate", description="Prüfungen für Commits")
    teil = parser.add_subparsers(dest="befehl", required=True)
    teil.add_parser("commits", help="Betreffzeilen eines Bereichs prüfen").add_argument("bereich", help="z. B. origin/master..HEAD")
    teil.add_parser("commit-msg", help="Nachrichtendatei prüfen (Git-Hook)").add_argument("datei", type=Path)
    teil.add_parser("secrets", help="hinzugefügte Zeilen auf Secrets prüfen (Index oder --range)").add_argument(
        "--range", dest="bereich", help="z. B. origin/master..HEAD; ohne Angabe: Index")
    parser.add_argument("--root", type=Path, default=ROOT, help="Wurzel des Repos")
    args = parser.parse_args(argv)
    try:
        if args.befehl == "secrets":
            return check_secrets(args.root, args.bereich)
        typen = commit_types(args.root)
        return check_range(args.root, args.bereich, typen) if args.befehl == "commits" else check_message(args.datei, typen)
    except proc.SetupError as fehler:
        print(f"FEHLER  {fehler}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
