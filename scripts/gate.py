"""Prüfungen für Commits: `python3 scripts/gate.py commits <bereich>` und `commit-msg <datei>` (Hook).

Eine Logik für Hook und CI. Nur Standardbibliothek, Python 3.11 oder neuer.
"""
from __future__ import annotations

import pycheck  # liegt neben dieser Datei und läuft auch auf älterem Python

pycheck.require_python()

import argparse  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import proc  # noqa: E402
import workflow  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TYPES_FILE = "scripts/gate.d/commit-types.tsv"
RULE = "type(scope)!: Betreff"


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


def main(argv: list[str] | None = None) -> int:
    proc.utf8_output()
    parser = argparse.ArgumentParser(prog="gate", description="Prüfungen für Commits")
    teil = parser.add_subparsers(dest="befehl", required=True)
    teil.add_parser("commits", help="Betreffzeilen eines Bereichs prüfen").add_argument("bereich", help="z. B. origin/master..HEAD")
    teil.add_parser("commit-msg", help="Nachrichtendatei prüfen (Git-Hook)").add_argument("datei", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT, help="Wurzel des Repos")
    args = parser.parse_args(argv)
    try:
        typen = commit_types(args.root)
        return check_range(args.root, args.bereich, typen) if args.befehl == "commits" else check_message(args.datei, typen)
    except proc.SetupError as fehler:
        print(f"FEHLER  {fehler}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
