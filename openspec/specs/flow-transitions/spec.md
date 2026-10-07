# flow-transitions Specification

## Purpose
Legt fest, wie `flow start` und `flow review` Zustandswechsel gemäß `workflow/transitions.tsv` ausführen: Branch und `status:`-Label, nur erlaubte Übergänge, mit `--dry-run`.

## Requirements

### Requirement: Zustandswechsel als Befehl
`flow start <issue>` SHALL einen Branch `feature/<id>-<slug>` anlegen und das Label der Dimension `status` gemäß `workflow/transitions.tsv` setzen. `flow review` SHALL analog in den Review-Zustand wechseln. Ein nicht erlaubter Übergang MUST mit Exit-Code ungleich 0 abbrechen, ohne etwas zu ändern.

#### Scenario: Start eines Tickets
- **WHEN** `flow start 42` für ein offenes Issue ohne `status`-Label läuft
- **THEN** existiert Branch `feature/42-<slug>` und das Issue trägt `status:in-progress`

#### Scenario: Nicht erlaubter Übergang
- **WHEN** `flow review 42` für ein Issue ohne `status:in-progress` läuft
- **THEN** bricht der Befehl ab, nennt den Übergang und ändert weder Branch noch Label

#### Scenario: Probelauf
- **WHEN** `--dry-run` angegeben ist
- **THEN** werden die Schritte angezeigt und nichts geändert
