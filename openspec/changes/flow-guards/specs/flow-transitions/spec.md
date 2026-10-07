## ADDED Requirements

### Requirement: Bedingungen der Übergänge
`flow start` und `flow review` SHALL die `guard`-Detektoren des Übergangs aus `workflow/transitions.tsv` auswerten, soweit sie sich per `gh` (lesend) oder Git ermitteln lassen. Ein nicht erfüllter Detektor MUST mit Exit-Code ungleich 0 abbrechen, den Detektor nennen und nichts ändern. Ein nicht auswertbarer Detektor SHALL eine Warnung ausgeben und den Übergang nicht blockieren.

#### Scenario: Bedingung nicht erfüllt
- **WHEN** `flow start 42` für ein Issue ohne Label `ready-for-agent` läuft
- **THEN** bricht der Befehl ab, nennt `label:ready-for-agent` und ändert weder Branch noch Label

#### Scenario: Offener Blocker
- **WHEN** `flow start 42` für ein Issue mit einem offenen Blocker läuft
- **THEN** bricht der Befehl ab und nennt `no_open_blockers`

#### Scenario: Checks nicht grün
- **WHEN** `flow review 42` läuft und die Checks des Pull Requests nicht erfolgreich sind oder kein Pull Request existiert
- **THEN** bricht der Befehl ab und nennt `checks:success`

#### Scenario: Detektor nicht auswertbar
- **WHEN** ein Detektor sich nicht auswerten lässt (z. B. `gh api` schlägt fehl)
- **THEN** erscheint eine Warnung mit dem Detektor und der Übergang läuft weiter
