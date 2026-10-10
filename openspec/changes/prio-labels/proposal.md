## Why

Die Statusansicht (kvasir) braucht Prioritäten am Ticket. Sie sind weder Triage-Rolle noch Fluss-Status und gehören als eigene Art in `workflow/states.tsv`, damit `flow validate` und `setup --labels` sie kennen (#136).

## What Changes

- `states.tsv` kennt die dritte Art `prio` (`prio:1` bis `prio:4`); `id` ist der Labelname, `setup --labels` legt sie an.
- Prio-Labels sind keine Zustände: Als `from` oder `to` in `transitions.tsv` ist ein Prio-Label ein Fehler; die Graph-Warnungen (kein Ein- oder Ausgang) gelten für sie nicht.

## Capabilities

### Modified Capabilities
- `workflow-definition`: Requirement Zustände und Übergänge.

## Impact

- `scripts/lib/workflow.py`, `scripts/lib/labels.py`, `workflow/states.tsv`, Doku (`docs/workflow.md`, `docs/agents/`, Anleitung 04).
- Die Regel "höchstens ein Prio-Label je Issue" ist Anweisung in `docs/agents/flow-labels.md`; `flow validate` sieht keine Issues, die Warnung bei zwei Labels gehört in die Statusansicht (kvasir).
