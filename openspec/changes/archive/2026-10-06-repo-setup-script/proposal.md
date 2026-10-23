# Proposal

## Why

Der Prozess steht heute als Prosa (`docs/workflow.md`, `docs/agents/*.md`) und als Handarbeit nach einer Checkliste. Das ist weder prüfbar noch wiederholbar: Labels, Agenten-Adapter und Voraussetzungen richtet jede Person von Hand ein, und niemand merkt, wenn Doku, Labels auf GitHub und Praxis auseinanderlaufen. Ein Klon-Hook ist in Git nicht möglich, also braucht es ein Skript als festen ersten Schritt. Zustände, Übergänge und Phasen als Daten schaffen die Grundlage für Diagramm, kvasir und spätere Automatisierung (siehe #11 und #28).

## What Changes

- Neuer Ordner `workflow/` mit den Daten des Prozesses als TSV-Dateien mit Kopfzeile: Zustände (`states.tsv`), Übergänge (`transitions.tsv`), Phasen (`phases.tsv`) und das Vokabular der Detektoren (`detectors.tsv`). Zwei Dimensionen von Zuständen (Triage-Rollen und Status), `closed` als terminaler Zustand ohne Label.
- Befehl `flow validate` prüft die Dateien auf Konsistenz (Spalten, Eindeutigkeit, Verweise, Vokabular) mit Fehlern und Warnungen, auch für die CI.
- Befehl `setup` prüft Voraussetzungen, richtet den lokalen Klon ein (Agenten-Adapter, Ausschlüsse, Git-Konfiguration) und legt auf Wunsch die Labels aus `states.tsv` an. `--check` zeigt, was fehlt, ohne etwas zu ändern.
- Daten für das Setup liegen neben dem Skript: `scripts/setup.d/tools.tsv` (Programme, Mindestversion, Pflicht oder empfohlen) und `scripts/setup.d/agents.tsv` (Agent, Ordner der Adapterdateien).
- Werkzeug in **Python 3.11 oder neuer, nur Standardbibliothek**, lauffähig unter Linux, macOS und Windows; Tests mit `unittest`, CI-Matrix auf allen drei Systemen.
- `docs/workflow.md` ersetzt die Setup-Checkliste durch den Aufruf.

## Capabilities

### New Capabilities

- `workflow-definition`: Format, Inhalt und Konsistenzprüfung der Prozessdaten unter `workflow/` und der Befehl `flow validate`.
- `repo-setup`: Der Befehl `setup`: Voraussetzungen, lokale Einrichtung des Klons, Agenten-Adapter, Labels, `--check`, Idempotenz, Plattformunabhängigkeit.

### Modified Capabilities

<!-- Keine. -->

## Impact

- Neu: `workflow/*.tsv`, `scripts/setup.py`, `scripts/flow.py`, `scripts/lib/workflow.py`, `scripts/setup.d/*.tsv`, Python-Tests unter `tests/`, ein CI-Job mit Matrix, `.gitattributes` (Zeilenenden).
- Geändert: `tests/run.sh` (ruft zusätzlich die Python-Tests auf), `.github/workflows/test.yml` und `deploy.yml`, `docs/workflow.md`, `README.md`, `docs/agents/*.md` (Verweis auf `workflow/states.tsv` als Quelle der Labels).
- Voraussetzung neu: Python ab 3.11 (kvasir braucht dasselbe). Keine Abhängigkeiten zur Laufzeit.

## Out of Scope

- Ausführen von Übergängen (`flow start`, `flow review`) und Auswerten der Detektoren gegen den Tracker (kommt mit #11 bzw. in kvasir, #48).
- Git-Hooks unter `.githooks/` und Commit-Lint (#11 Stufe 1); `setup` setzt `core.hooksPath` nur, wenn der Ordner existiert.
- Umstellung der Daten auf JSON oder YAML (Kriterien stehen im Design).
- Validierung gegen das SDLC-Playbook (#45).
