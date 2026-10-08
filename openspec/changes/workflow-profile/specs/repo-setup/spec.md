## ADDED Requirements

### Requirement: Skills je Phase im Prüflauf
`setup --check` SHALL für jeden gewählten Agenten prüfen, ob die Skills aus `workflow/skills.tsv` unter den Orten der Spalte `skill_paths` von `scripts/setup.d/agents.tsv` liegen (`<ort>/<skill>/SKILL.md`). Ein fehlender Skill einer Phase mit `level` `required` MUST ein Fehler mit dem Installationshinweis sein, sonst ein Hinweis. Hat ein Agent keine `skill_paths`, SHALL die Ausgabe "nicht prüfbar" mit der Liste der benötigten Skills zeigen. Orte werden nie geraten.

#### Scenario: Pflicht-Skill fehlt
- **WHEN** `/to-tickets` (Phase 3, Pflicht) nirgends gefunden wird
- **THEN** meldet `setup --check` `FEHLT` mit Phase und Hinweis und endet mit Exit-Code 1

#### Scenario: Agent ohne bekannte Orte
- **WHEN** der gewählte Agent keine `skill_paths` hat
- **THEN** meldet `setup --check` "nicht prüfbar" und listet die Skills, endet aber nicht mit einem Fehler
