# Proposal

## Why

Blog-Inhalt, Bauwerkzeug und Prozess-Werkzeug liegen im Wurzelverzeichnis nebeneinander (`posts/`, `build.sh`, `scripts/`, `evals/`, `tests/` mit Shell- und Python-Tests gemischt). Der Prozess soll später als eigenes Werkzeug in anderen Projekten laufen, der Blog bleibt Beispielprojekt. Das geht nur, wenn klar ist, was Werkzeug, was Projektkonfiguration und was Projektinhalt ist.

## What Changes

- **Inhalt**: `posts/`, `pages/`, `timeline/`, `gallery/`, `site.conf` ziehen nach `content/`.
- **Bauwerkzeug**: `build.sh`, `templates/`, `static/` und die Shell-/Browser-Tests ziehen nach `site/`.
- **Projektkonfiguration**: `workflow/` bleibt (kvasir liest `workflow/*.tsv`) und nimmt auf, was heute im Werkzeug steckt, aber projektspezifisch ist: Pflichtprogramme (`tools.tsv`), Secret-Allowlist und Commit-Typen, Eval-Aufgaben und -Berichte.
- **Werkzeug**: `scripts/`, der Eval-Runner (`evals/run.py`, `derive.py`, Adapter), die Python-Tests und die allgemeine Doku (`docs/workflow.md`, `docs/anleitung/`, Playbook-Abgleich, Diagramm) ziehen nach `devflow/` (Arbeitsname), als Ordner später abspaltbar.
- Im Wurzelverzeichnis bleiben nur Dinge, die dort liegen müssen: `README.md`, `AGENTS.md`, `docs/agents/`, `openspec/`, `.github/`, `.githooks/`, `.claude/`, `.agents/`.
- Das Werkzeug kennt genau einen Konfigurationsordner (`workflow/` im Projektwurzelverzeichnis) statt fester Pfade an vielen Stellen.
- **BREAKING** für Aufrufer: Pfade von `scripts/*.py` und `build.sh` ändern sich (Hooks, CI, Doku werden mitgezogen). Das gebaute Ergebnis (`public/`) und die URLs bleiben gleich.

## Capabilities

### New Capabilities
- `repo-layout`: Aufteilung des Repos in Inhalt, Bauwerkzeug, Projektkonfiguration und Werkzeug; Konfiguration an genau einem Ort; Build-Ergebnis unverändert.

### Modified Capabilities
- `repo-setup`: Pflichtprogramme stehen in `workflow/tools.tsv` statt in `scripts/setup.d/tools.tsv`; Aufruf über den neuen Werkzeugpfad.
- `agent-evals`: Aufgaben liegen in `workflow/evals/tasks/<id>/`, Berichte in `workflow/evals/reports/`; das Wegwerf-Repo enthält das Werkzeug an seinem neuen Ort.

## Impact

- Code: `build.sh` (Pfade), `scripts/setup.py`, `scripts/lib/workflow.py`, `scripts/gate.py`, `evals/run.py` (`FIXTURE`, `REPO`), `.githooks/*`, `.github/workflows/{test,deploy,close-labels}.yml`, `tests/run.sh`, Aufrufe in der Doku.
- Nicht betroffen: Inhalt der Seite, URLs, Namen der CI-Checks (`test`, `gates`, `python (…)`), Branch Protection, `workflow/*.tsv` (Vertrag mit kvasir), Timeline-Specs.
- Außerhalb: kvasir bekommt ein eigenes Ticket für einen frei wählbaren Konfigurationsordner (`workflow_dir` in `kvasir.toml`); bis dahin gilt `workflow/`.
