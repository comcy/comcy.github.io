## MODIFIED Requirements

### Requirement: Zustände
`workflow/states.tsv` SHALL die Zustände mit `id`, `kind` (`triage`, `status`, `prio` oder `terminal`), `color` und `description` enthalten, optional `enabled` (`yes` oder `no`, Standard `yes`). Die `id` MUST in der Datei eindeutig sein und ist bei `triage`, `status` und `prio` der Name des Labels. Die Farbe MUST aus sechs Hex-Zeichen bestehen, bei `terminal` darf sie `-` sein. Es MUST genau einen Zustand der Art `terminal` geben.

#### Scenario: Gültige Zustände
- **WHEN** alle Zustände vollständig und eindeutig sind
- **THEN** meldet `flow validate` für die Datei keinen Fehler

#### Scenario: Doppelte Kennung
- **WHEN** zwei Zeilen dieselbe `id` haben
- **THEN** meldet `flow validate` einen Fehler mit Datei und Zeile

#### Scenario: Ungültiger Wert für enabled
- **WHEN** `enabled` weder `yes` noch `no` ist
- **THEN** meldet `flow validate` einen Fehler mit Datei und Zeile

#### Scenario: Ungültige Farbe oder fehlende Beschreibung
- **WHEN** die Farbe keine sechs Hex-Zeichen hat oder die Beschreibung leer ist
- **THEN** meldet `flow validate` einen Fehler mit Datei und Zeile

#### Scenario: Terminaler Zustand
- **WHEN** es keinen oder mehr als einen Zustand der Art `terminal` gibt
- **THEN** meldet `flow validate` einen Fehler

#### Scenario: Prioritäten
- **WHEN** Zustände der Art `prio` (`prio:1` bis `prio:4`) mit Farbe und Beschreibung vollständig sind
- **THEN** meldet `flow validate` keinen Fehler und keine Warnung wegen fehlender Übergänge

### Requirement: Übergänge
`workflow/transitions.tsv` SHALL Übergänge mit `from`, `to`, `trigger` und `guard` enthalten, optional `enabled`. `from` und `to` MUST auf Zustände aus `states.tsv` verweisen, `from` darf `-` (Start) sein. Ein Übergang bleibt innerhalb einer Dimension (gleiche `kind`), außer bei `-` als Start oder `terminal` als Ziel. Ein Zustand der Art `prio` MUST an keinem Übergang als `from` oder `to` stehen. `guard` ist eine mit Komma getrennte UND-Liste von Detektoren oder `-`.

#### Scenario: Verweis auf unbekannten Zustand
- **WHEN** `from` oder `to` eine unbekannte `id` nennt
- **THEN** meldet `flow validate` einen Fehler mit Datei, Zeile und der unbekannten `id`

#### Scenario: Übergang über Dimensionen
- **WHEN** ein Übergang von einem `triage`-Zustand zu einem `status`-Zustand führt und `from` nicht `-` ist
- **THEN** meldet `flow validate` einen Fehler

#### Scenario: Aus dem terminalen Zustand
- **WHEN** ein Übergang von einem Zustand der Art `terminal` ausgeht
- **THEN** meldet `flow validate` einen Fehler

#### Scenario: Leerer Auslöser
- **WHEN** `trigger` leer ist
- **THEN** meldet `flow validate` einen Fehler

#### Scenario: Start und terminaler Zustand
- **WHEN** ein Übergang von `-` zu einem Zustand oder von einem `status`-Zustand zu `closed` führt
- **THEN** meldet `flow validate` keinen Fehler

#### Scenario: Prio-Label im Übergang
- **WHEN** `from` oder `to` ein Label der Art `prio` nennt
- **THEN** meldet `flow validate` einen Fehler mit Datei und Zeile
