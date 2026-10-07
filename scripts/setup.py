"""Richtet den lokalen Klon für den Prozess ein: `python3 scripts/setup.py --check` prüft, was fehlt.

Aufruf unter Windows: `py -3 scripts\\setup.py --check`. Nur Standardbibliothek, Python 3.11 oder neuer.
"""
from __future__ import annotations

import pycheck  # liegt neben dieser Datei und läuft auch auf älterem Python

pycheck.require_python()

import argparse  # noqa: E402
import sys  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import labels  # noqa: E402
import local  # noqa: E402
import proc  # noqa: E402
import tools  # noqa: E402
import workflow  # noqa: E402


def plural(n: int, eins: str, mehr: str) -> str:
    return f"{n} {eins if n == 1 else mehr}"


def summary(fehler: int, warnungen: int, hinweise: int) -> None:
    print(f"{fehler} Fehler, {plural(warnungen, 'Warnung', 'Warnungen')}, {plural(hinweise, 'Hinweis', 'Hinweise')}")


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


def resolve_agents(root: Path, gewuenscht: list[str], funde: list[workflow.Finding]) -> tuple[list[str], dict[str, str], bool]:
    """Agenten aus Argumenten, sonst aus der gespeicherten Wahl, sonst keine; unbekannte werden als Fehler gemeldet."""
    ordner = local.read_agents(root, funde)
    explizit = any(name != local.BASE_TOOLS for name in gewuenscht)  # "agents" allein ändert die gespeicherte Wahl nicht
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


@dataclass
class LabelState:
    """Was über die Labels bekannt ist: angemeldet, welche fehlen, und warum sie nicht prüfbar waren."""
    angemeldet: bool
    fehlende: list = field(default_factory=list)
    hinweis: str | None = None

    def not_checked(self) -> str | None:
        """Meldung "Labels nicht geprüft: …" oder None, wenn die Labels geprüft wurden."""
        if self.angemeldet and self.hinweis is None:
            return None
        return "HINWEIS Labels nicht geprüft: " + (self.hinweis or "gh nicht angemeldet (gh auth login)")


def label_state(root: Path, mit_labels: bool, nur_pruefen: bool) -> LabelState:
    if not labels.logged_in(root):
        return LabelState(False)
    try:
        return LabelState(True, labels.missing_labels(root))
    except proc.SetupError as problem:
        if mit_labels and not nur_pruefen:
            raise
        # ohne --labels kein Fehler, zum Beispiel in einem Klon ohne GitHub-Remote
        return LabelState(True, hinweis=str(problem))


def report(schritte: list, state: LabelState, warnungen: int, hinweise: int) -> int:
    """--check: fehlende Schritte und Labels melden, nichts ändern."""
    for schritt in schritte:
        print(f"FEHLT   {schritt.label}" + (f" (Abhilfe: {schritt.hint})" if schritt.hint else ""))
    for label in state.fehlende:
        print(f"FEHLT   Label {label.name} (anlegen mit setup --labels)")
    if (meldung := state.not_checked()):
        print(meldung)
        hinweise += 1
    summary(len(schritte) + len(state.fehlende), warnungen, hinweise)
    return 1 if schritte or state.fehlende else 0


def apply(root: Path, schritte: list, state: LabelState, mit_labels: bool) -> tuple[int, int]:
    """Normaler Lauf: Schritte ausführen, Labels nur mit --labels anlegen; liefert (erledigt, neue Hinweise)."""
    for schritt in schritte:
        schritt.apply()
        print(f"erledigt {schritt.label}")
    erledigt, hinweise = len(schritte), 0
    if mit_labels:
        for label in state.fehlende:
            labels.create_label(root, label)
            print(f"erledigt Label {label.name} angelegt")
            erledigt += 1
    elif state.fehlende:
        namen = ", ".join(label.name for label in state.fehlende)
        print(f"HINWEIS {plural(len(state.fehlende), 'Label fehlt', 'Labels fehlen')} ({namen}): mit setup --labels anlegen")
        hinweise = 1
    elif (meldung := state.not_checked()):
        print(meldung)
        hinweise = 1
    return erledigt, hinweise


def run(root: Path, gewuenscht: list[str], nur_pruefen: bool, mit_labels: bool = False) -> int:
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
        state = label_state(root, mit_labels, nur_pruefen)
        if mit_labels and not nur_pruefen and not state.angemeldet:
            raise proc.SetupError("gh ist nicht angemeldet: gh auth login")  # vor jeder Änderung
        schritte = local.plan(root, agenten, ordner, explizit)
        if nur_pruefen and local.hooks_python_missing(root):
            schritte.append(local.Step("python für die Hooks nicht im PATH", lambda: None,
                                       "python3, python oder py installieren und in den PATH legen"))
        if nur_pruefen:
            return report(schritte, state, warnungen, hinweise)
        erledigt, neue = apply(root, schritte, state, mit_labels)
    except proc.SetupError as fehlermeldung:
        print(f"FEHLER  {fehlermeldung}")
        summary(1, warnungen, hinweise)
        return 1
    if not erledigt:
        print("nichts zu tun")
    if not gewuenscht and not agenten:
        print("Hinweis: kein Agent gewählt, eingerichtet ist nur die agentenneutrale Basis (agents). "
              "Für deinen Agenten: setup claude (zum Beispiel python3 scripts/setup.py claude)")
    summary(0, warnungen, hinweise + neue)
    return 0


def main(argv: list[str] | None = None) -> int:
    proc.utf8_output()
    parser = argparse.ArgumentParser(prog="setup", description="Lokalen Klon für den Prozess einrichten")
    parser.add_argument("agents", nargs="*", help="Agenten für den lokalen Adapter, zum Beispiel claude")
    parser.add_argument("--check", action="store_true", help="nur melden, was fehlt, nichts ändern")
    parser.add_argument("--labels", action="store_true", help="fehlende Labels des Prozesses auf GitHub anlegen")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Wurzel des Repos (mit workflow/ und scripts/setup.d/)")
    args = parser.parse_args(argv)
    return run(args.root, args.agents, args.check, args.labels)


if __name__ == "__main__":
    sys.exit(main())
