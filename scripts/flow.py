"""Befehle für den Prozess: `python3 scripts/flow.py validate` prüft die Dateien unter workflow/.

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
import workflow  # noqa: E402


def cmd_validate(args: argparse.Namespace) -> int:
    funde = workflow.validate(args.root)
    for fund in funde:
        print(fund.format())
    fehler = sum(f.level == "error" for f in funde)
    warnungen = sum(f.level == "warning" for f in funde)
    print(f"{fehler} Fehler, {warnungen} Warnungen")
    return 1 if fehler or (args.strict and warnungen) else 0


def main(argv: list[str] | None = None) -> int:
    proc.utf8_output()
    parser = argparse.ArgumentParser(prog="flow", description="Befehle für die Prozessdaten")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="Dateien unter workflow/ auf Konsistenz prüfen")
    v.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                   help="Wurzel des Repos (Ordner mit workflow/)")
    v.add_argument("--strict", action="store_true", help="Warnungen wie Fehler behandeln")
    v.set_defaults(func=cmd_validate)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
