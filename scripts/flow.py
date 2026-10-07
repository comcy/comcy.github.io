"""Befehle für den Prozess: `flow.py validate` prüft die Dateien unter workflow/, `flow.py start <issue>` startet ein Ticket, `flow.py review [<issue>]` gibt es zum Review.

Aufruf unter Windows: `py -3 scripts\\flow.py validate`. Nur Standardbibliothek, Python 3.11 oder neuer.
"""
from __future__ import annotations

import pycheck  # liegt neben dieser Datei und läuft auch auf älterem Python

pycheck.require_python()

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import proc  # noqa: E402
import transition  # noqa: E402
import workflow  # noqa: E402


def cmd_validate(args: argparse.Namespace) -> int:
    funde = workflow.validate(args.root)
    for fund in funde:
        print(fund.format())
    fehler = sum(f.level == "error" for f in funde)
    warnungen = sum(f.level == "warning" for f in funde)
    print(f"{fehler} Fehler, {warnungen} Warnungen")
    return 1 if fehler or (args.strict and warnungen) else 0


def cmd_start(args: argparse.Namespace) -> int:
    return _wechsel(transition.start, args)


def cmd_review(args: argparse.Namespace) -> int:
    return _wechsel(transition.review, args)


def _wechsel(funktion, args: argparse.Namespace) -> int:
    try:
        schritte = funktion(args.root, args.issue, args.dry_run)
    except proc.SetupError as fehler:
        print(f"Fehler: {fehler}")
        return 1
    for schritt in schritte:
        print(("würde ausführen: " if args.dry_run else "ausgeführt: ") + schritt)
    return 0


def main(argv: list[str] | None = None) -> int:
    proc.utf8_output()
    parser = argparse.ArgumentParser(prog="flow", description="Befehle für die Prozessdaten")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="Dateien unter workflow/ auf Konsistenz prüfen")
    v.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                   help="Wurzel des Repos (Ordner mit workflow/)")
    v.add_argument("--strict", action="store_true", help="Warnungen wie Fehler behandeln")
    v.set_defaults(func=cmd_validate)
    s = sub.add_parser("start", help="Branch feature/<id>-<slug> anlegen, status:in-progress setzen")
    s.add_argument("issue", help="Nummer des Issues")
    s.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                   help="Wurzel des Git-Repos (Ordner mit workflow/)")
    s.add_argument("--dry-run", action="store_true", help="Schritte zeigen, nichts ändern")
    s.set_defaults(func=cmd_start)
    r = sub.add_parser("review", help="status:in-progress -> status:in-review; Issue ggf. aus dem Branchnamen")
    r.add_argument("issue", nargs="?", help="Nummer des Issues (Standard: aus feature/<nr>-…)")
    r.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                   help="Wurzel des Git-Repos (Ordner mit workflow/)")
    r.add_argument("--dry-run", action="store_true", help="Schritt zeigen, nichts ändern")
    r.set_defaults(func=cmd_review)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
