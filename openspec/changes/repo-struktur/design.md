# Design

## Context

Siehe proposal.md. Ist-Zustand der Kopplungen:

- `workflow/*.tsv` ist ein Vertrag mit kvasir (feste Pfade in `repo_file.py`, `metrics.py`).
- `scripts/lib/workflow.py` kennt `WORKFLOW_DIR = "workflow"`; `evals/run.py` hat `FIXTURE` mit festen Pfaden; `.githooks/*` rufen `scripts/gate.py` über relativen Pfad; `setup.py` setzt `core.hooksPath`.
- Projektspezifisches steckt im Werkzeug: `pandoc` in `scripts/setup.d/tools.tsv`, `scripts/gate.d/allow.tsv` und `commit-types.tsv`, `evals/tasks/`, `evals/reports/`.
- Generisch (bleibt im Werkzeug): `gate.d/secrets.tsv` (Muster), `setup.d/agents.tsv` (Adapter-Definitionen), Eval-Runner, Adapter, Stub-`gh`.
- CI ruft `build.sh`, `tests/run.sh` und `python -m unittest discover -s tests` auf; die Namen der Jobs sind in der Branch Protection hinterlegt.

## Goals / Non-Goals

**Goals:**
- Vier klare Bereiche (`content/`, `site/`, `workflow/`, `devflow/`); `devflow/` ist als Ordner abspaltbar.
- Ein Konfigurationsordner, den das Werkzeug an einer Stelle benennt.
- `public/` bleibt byte-gleich, CI-Namen bleiben.

**Non-Goals:**
- Kein `devflow init`, keine Standardwerte im Werkzeug, keine Überlagerung (erst bei einem zweiten Projekt; Vorlagen sauber zu trennen genügt).
- Kein eigenes Repo, kein Paket, kein Umbenennen von `workflow/` (kvasir).
- Keine Änderung am Inhalt der Blogbeiträge, an Timeline-Verhalten oder an kvasir selbst.

## Decisions

1. **Reihenfolge: erst Konfiguration herauslösen, dann verschieben.** Slice 2 trennt Konfiguration und Werkzeug am Ort (`scripts/` bleibt), Slice 3 verschiebt nur noch Dateien. So bricht ein Schritt nicht zwei Dinge gleichzeitig. Alternative: alles in einem PR → schwer zu prüfen, großer Diff.
2. **`devflow/` als Arbeitsname.** Er steht in einer Konstante und in der Doku; Umbenennen vor dem Abspalten ist ein Suchen-und-Ersetzen. Alternative `tools/` oder `process/` → zu allgemein, kollidiert mit Projektordnern anderer Projekte.
3. **Unterordner in `workflow/` für Gate- und Eval-Daten** (`workflow/gate/`, `workflow/evals/`), die TSVs für kvasir bleiben flach. kvasir liest nur seine Dateien, Unterordner stören nicht. Alternative: alles flach → Namenskollisionen (`allow.tsv` ohne Kontext).
4. **Generisches bleibt im Werkzeug**: `secrets.tsv` und `agents.tsv` liegen in `devflow/`. Ein Projekt kann Muster über die Allowlist ausnehmen, aber nicht ersetzen. Alternative: alles in `workflow/` → jedes Projekt müsste Muster pflegen.
5. **Tests folgen ihrem Bereich**: Python-Tests nach `devflow/tests/`, Shell- und Browser-Tests nach `site/tests/`. `tests/run.sh` wird zu `site/tests/run.sh`; die Jobs `test` und `python (…)` behalten Namen und Befehle mit neuem Pfad.
6. **Hooks bleiben Hüllen im Wurzelverzeichnis** und rufen `devflow/scripts/gate.py`. `core.hooksPath` bleibt `.githooks`.
7. **Doku trennen**: Allgemeines (Workflow-Beschreibung, Anleitung, Playbook-Abgleich, Diagramm) nach `devflow/docs/`; Projektbezogenes (`docs/agents/`, `docs/plans/`, `docs/metriken/`) bleibt in `docs/`. Die Anleitung nutzt den Blog als Beispiel, Verweise bleiben gültig.
8. **Prüfung der Gleichheit** der Seite über `diff -r` zweier Builds mit festem `SITE_URL` und festem Datum, einmal vor Slice 1 aufgenommen (Referenz im Scratchpad, nicht im Git).

## Risks / Trade-offs

- [Pfade übersehen, CI rot] → Slice für Slice mergen, nach jedem Slice alle drei Betriebssysteme grün; `grep` nach alten Pfaden als Abschlussprüfung.
- [Branch Protection verlangt Jobnamen] → Namen unverändert lassen; im PR prüfen, dass sie gemeldet werden.
- [Offene Branches/Worktrees brechen bei großen Moves] → vorher offene PRs mergen oder rebasen lassen (derzeit #122, #30, #23: reine Doku/Blog, `git mv` wird beim Rebase erkannt).
- [Eval-Wegwerf-Repo ohne `devflow/`] → `FIXTURE` und Spec-Szenario; ein Eval-Test baut das Repo und führt `flow validate` darin aus.
- [Werkzeug und Konfiguration entkoppeln, aber nicht ganz sauber] → Test mit Beispielprojekt ohne `pandoc` und `content/` (Spec "Werkzeug ohne Projektwissen").
- [kvasir kennt nur `workflow/`] → bleibt so; Ticket für `workflow_dir` in kvasir.

## Migration Plan

1. Referenz-Build ablegen (`public/` vor dem Umzug).
2. Slices 1 bis 3 als eigene PRs nach `master`, jeweils mit grüner CI.
3. Rollback je Slice: Revert des PR; kein Slice ändert Daten außerhalb des Repos.
4. Vault-Doku und Blog-Hinweise nach Slice 4 aktualisieren.

## Open Questions

- Endgültiger Name von `devflow/` (erst vor dem Abspalten nötig).
- Ob `docs/metriken/` und Eval-Berichte ins Werkzeugrepo wandern oder beim Beispielprojekt bleiben (erst beim Abspalten).
