## ADDED Requirements

### Requirement: Skills je Phase
`workflow/skills.tsv` SHALL je Zeile `skill`, `phase`, optional `level` (`required` oder `optional`, Standard: `level` der Phase), `source`, `hint` und `manual` beschreiben. Eine Phase MAY mehrere Zeilen haben.

#### Scenario: Skill einer Phase
- **WHEN** die Zeile `to-tickets` mit `phase` `3` und `level` `required` steht
- **THEN** gilt `/to-tickets` als Pflicht-Skill der Phase 3

### Requirement: Rollen
`workflow/roles.tsv` SHALL je Zeile `role`, `phases`, `allowed_tools`, `human_gate` (`yes` oder `no`) und `description` beschreiben. Rollen SHALL beschreiben und prüfbar sein, MUST aber im Alltag nicht erzwungen werden.

#### Scenario: Rolle mit menschlichem Gate
- **WHEN** eine Rolle `human_gate` `yes` trägt
- **THEN** benennt die Konfiguration, dass vor der nächsten Phase eine menschliche Freigabe nötig ist

### Requirement: Abdeckung
`flow validate` SHALL einen Fehler melden, wenn eine Phase mit `level` `required` keinen Skill und kein `manual` hat oder keiner Rolle zugeordnet ist, und SHALL warnen bei Rollen ohne Phase sowie bei Skills, deren Phase fehlt oder abgeschaltet ist.

#### Scenario: Unbedeckte Pflichtphase
- **WHEN** die Pflichtphase `3` weder Skill noch `manual` hat
- **THEN** meldet `flow validate` einen Fehler mit Datei und Phase und endet mit Exit-Code ungleich 0
