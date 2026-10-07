## Why

`flow start` und `flow review` prüfen Quelle, Ziel und Auslöser, aber nicht die `guard`-Spalte aus `workflow/transitions.tsv` (z. B. `label:ready-for-agent,no_open_blockers`). Damit sind die Bedingungen nur Prosa (#75).

## What Changes

- `flow start` und `flow review` werten die `guard`-Detektoren des Übergangs aus, soweit sie sich per `gh` (nur lesend) oder Git ermitteln lassen: `label`, `has_label_kind`, `issue_open`, `issue_closed`, `issue_exists`, `no_open_blockers`, `subissues_exist`, `checks:success`, `file_exists`.
- Nicht erfüllter Detektor: Abbruch mit Exit-Code 1, Meldung nennt den Detektor, nichts geändert (auch bei `--dry-run`).
- Nicht auswertbarer Detektor (unbekannt, gh-Fehler): Warnung, kein Abbruch, nie stilles Durchwinken.
- Kein `--force`: die Spec sieht keinen Weg um einen Übergang vor.
- Kein neues Design-Dokument: kleine Änderung in `scripts/lib/transition.py`.

## Capabilities

### Modified Capabilities
- `flow-transitions`: Bedingungen (`guard`) werden ausgewertet.

## Impact

- `scripts/lib/transition.py`, `tests/test_flow_guards.py`, `docs/workflow.md`. Keine neue Abhängigkeit.
