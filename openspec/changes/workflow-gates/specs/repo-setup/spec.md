## ADDED Requirements

### Requirement: Hooks im Prüflauf
`setup --check` SHALL melden, wenn `core.hooksPath` nicht auf `.githooks` zeigt oder `python` für die Hooks nicht im PATH ist, und MUST dabei nichts ändern.

#### Scenario: Hooks nicht aktiv
- **WHEN** `core.hooksPath` nicht gesetzt ist
- **THEN** nennt `setup --check` den Befund und den Befehl `setup`, ohne zu ändern
