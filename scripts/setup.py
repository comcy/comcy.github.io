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
import local  # noqa: E402
import tools  # noqa: E402
import workflow  # noqa: E402


def plural(n: int, eins: str, mehr: str) -> str:
    return f"{n} {eins if n == 1 else mehr}"


def check_prerequisites(root: Path, funde: list[workflow.Finding]) -> tuple[int, int]:
    """Gibt die Prüfung der Programme aus und liefert (Fehler, Hinweise)."""
    fehler = hinweise = 0
    for zeile in tools.read_tools(root, funde):
        ergebnis = tools.check_tool(zeile)
        marke = {"ok": "ok     ", "error": "FEHLER ", "hint": "HINWEIS"}[ergebnis.status]
        print(f"{marke} {ergebnis.message}")
        fehler += ergebnis.status == "error"
        hinweise += ergebnis.status == "hint"
    return fehler, hinweise


def summary(fehler: int, warnungen: int, hinweise: int) -> None:
    print(f"{plural(fehler, 'Fehler', 'Fehler')}, {plural(warnungen, 'Warnung', 'Warnungen')}, "
          f"{plural(hinweise, 'Hinweis', 'Hinweise')}")


def resolve_agents(root: Path, gewuenscht: list[str], funde: list[workflow.Finding]) -> tuple[list[str], dict[str, str], bool]:
    """Agenten aus Argumenten, sonst aus der gespeicherten Wahl, sonst keine; unbekannte werden als Fehler gemeldet."""
    ordner = local.read_agents(root, funde)
    explizit = bool(gewuenscht)
    wahl = gewuenscht if explizit else local.stored_agents(root)
    agenten: list[str] = []
    for name in wahl:
        if name == local.BASE_TOOLS or name in agenten:
            continue
        if name not in ordner:
            funde.append(workflow.Finding(local.AGENTS_FILE, 1, "error",
                                          f"Agent '{name}' ist nicht in {local.AGENTS_FILE} eingetragen"))
            continue
        agenten.append(name)
    return agenten, ordner, explizit


def run(root: Path, gewuenscht: list[str], nur_pruefen: bool) -> int:
    """Voraussetzungen, Agentenwahl und lokale Schritte; mit nur_pruefen werden die Schritte nur gemeldet."""
    funde: list[workflow.Finding] = []
    fehler, hinweise = check_prerequisites(root, funde)
    agenten, ordner, explizit = resolve_agents(root, gewuenscht, funde)
    if nur_pruefen:
        funde += workflow.validate(root)
    for fund in sorted(funde, key=lambda f: (f.file, f.line, f.level, f.message)):
        print(fund.format())
    fehler += sum(f.level == "error" for f in funde)
    warnungen = sum(f.level == "warning" for f in funde)
    if fehler:
        summary(fehler, warnungen, hinweise)
        return 1
    try:
        schritte = local.plan(root, agenten, ordner, explizit)
        if nur_pruefen:
            for schritt in schritte:
                print(f"FEHLT   {schritt.label}")
            summary(len(schritte), warnungen, hinweise)
            return 1 if schritte else 0
        for schritt in schritte:
            schritt.apply()
            print(f"erledigt {schritt.label}")
    except local.SetupError as fehlermeldung:
        print(f"FEHLER  {fehlermeldung}")
        summary(1, warnungen, hinweise)
        return 1
    if not schritte:
        print("nichts zu tun")
    if not gewuenscht and not agenten:
        print("Hinweis: kein Agent gewählt, eingerichtet ist nur die agentenneutrale Basis (agents). "
              "Für deinen Agenten: setup claude (zum Beispiel python3 scripts/setup.py claude)")
    summary(0, warnungen, hinweise)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Ausgabe immer als UTF-8, damit sie unter Windows (Umleitung, CI) nicht von der Konsolenkodierung abhängt
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="setup", description="Lokalen Klon für den Prozess einrichten")
    parser.add_argument("agents", nargs="*", help="Agenten für den lokalen Adapter, zum Beispiel claude")
    parser.add_argument("--check", action="store_true", help="nur melden, was fehlt, nichts ändern")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Wurzel des Repos (mit workflow/ und scripts/setup.d/)")
    args = parser.parse_args(argv)
    return run(args.root, args.agents, args.check)


if __name__ == "__main__":
    sys.exit(main())
