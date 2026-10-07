## Why

Der Workflow steht in Prosa und Skill-Texten. Agenten und Menschen befolgen ihn wahrscheinlich, aber nicht garantiert (#11). Die mechanischen Regeln (Commit-Format, keine Secrets, Branch- und Label-Wechsel) sollen von Werkzeugen erzwungen werden, die für jede Person und jeden Agenten gelten und auf Linux, macOS und Windows laufen.

## What Changes

- Neu: Prüfungen `commit-gates` als Python-Skript (nur Standardbibliothek): Conventional-Commit-Lint und Secret-Scan. Dieselbe Logik läuft lokal als Git-Hook (`.githooks/commit-msg`, `.githooks/pre-commit`, dünne `sh`-Hüllen) und in der CI (alle Commits eines PR, Diff des PR).
- Neu: `flow start <issue>` und `flow review` als Zustandswechsel (Branch `feature/<id>-<slug>`, Label `status:*` nach `workflow/transitions.tsv`), sodass der Übergang nicht frei improvisiert wird.
- `setup` setzt `core.hooksPath` bereits, `setup --check` meldet, wenn die Hooks fehlen oder nicht aktiv sind.
- Nicht in diesem Change: Evals, Metriken (#28), Maintain-Phase (#60), Orchestrierung (LangGraph o. Ä.), Agenten-Hooks im Repo.
- Entscheidung für Agenten-Hooks: harte Regeln liegen nur in Git-Hooks und CI. Agenten-Hooks (`settings.json`) bleiben persönlich (Teil C von `docs/workflow.md`), nie Voraussetzung.

## Capabilities

### New Capabilities
- `commit-gates`: Commit-Lint und Secret-Scan, lokal als Git-Hook und in der CI.
- `flow-transitions`: Zustandswechsel `flow start` und `flow review` aus den Prozessdaten.

### Modified Capabilities
- `repo-setup`: `setup --check` prüft zusätzlich, dass die Hooks aktiv sind.

## Impact

- Neu: `scripts/gate.py`, `scripts/lib/gates.py`, `.githooks/`, Muster-Datei und Allowlist für den Secret-Scan, Erweiterung von `scripts/flow.py`, `.github/workflows/test.yml` (Job `gates`).
- Branch-Schutz: Job `gates` als Pflicht-Check hinzufügen (Einstellung auf GitHub, nur mit Freigabe des Repo-Eigners).
- Keine neue Abhängigkeit. Optionale Beschleunigung durch gitleaks ist nicht Teil der Pflicht.
