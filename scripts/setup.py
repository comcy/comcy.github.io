"""Richtet den lokalen Klon für den Prozess ein: `python3 scripts/setup.py --check` prüft, was fehlt.

Aufruf unter Windows: `py -3 scripts\\setup.py --check`. Nur Standardbibliothek, Python 3.11 oder neuer.
"""
from __future__ import annotations

import pycheck  # liegt neben dieser Datei und läuft auch auf älterem Python

pycheck.require_python()

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import tools  # noqa: E402
import workflow  # noqa: E402


def plural(n: int, eins: str, mehr: str) -> str:
    return f"{n} {eins if n == 1 else mehr}"


def run_check(root: Path) -> int:
    """Meldet Voraussetzungen und die Konsistenz der Prozessdaten, ohne etwas zu ändern."""
    fehler = hinweise = 0
    funde: list[workflow.Finding] = []
    for zeile in tools.read_tools(root, funde):
        ergebnis = tools.check_tool(zeile)
        marke = {"ok": "ok     ", "error": "FEHLER ", "hint": "HINWEIS"}[ergebnis.status]
        print(f"{marke} {ergebnis.message}")
        fehler += ergebnis.status == "error"
        hinweise += ergebnis.status == "hint"
    funde += workflow.validate(root)
    for fund in sorted(funde, key=lambda f: (f.file, f.line, f.level, f.message)):
        print(fund.format())
    fehler += sum(f.level == "error" for f in funde)
    warnungen = sum(f.level == "warning" for f in funde)
    print(f"{plural(fehler, 'Fehler', 'Fehler')}, {plural(warnungen, 'Warnung', 'Warnungen')}, "
          f"{plural(hinweise, 'Hinweis', 'Hinweise')}")
    return 1 if fehler else 0


def main(argv: list[str] | None = None) -> int:
    # Ausgabe immer als UTF-8, damit sie unter Windows (Umleitung, CI) nicht von der Konsolenkodierung abhängt
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="setup", description="Lokalen Klon für den Prozess einrichten")
    parser.add_argument("--check", action="store_true", help="nur melden, was fehlt, nichts ändern")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Wurzel des Repos (mit workflow/ und scripts/setup.d/)")
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("ohne --check noch nicht umgesetzt (Ticket #50)")
    return run_check(args.root)


if __name__ == "__main__":
    sys.exit(main())
