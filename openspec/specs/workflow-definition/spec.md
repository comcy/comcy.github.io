# workflow-definition Specification

## Purpose
Legt fest, wie der Prozess als Daten unter `workflow/` beschrieben ist (Zustände, Übergänge, Phasen, Detektoren) und wie `flow validate` diese Dateien auf Konsistenz prüft.

## Requirements

### Requirement: Dateiformat mit Kopfzeile
Jede Datei unter `workflow/` SHALL tabulatorgetrennt sein, Zeilen mit `#` am Anfang und leere Zeilen MUST ignoriert werden. Die erste übrige Zeile benennt die Spalten, Werte werden über diese Namen zugeordnet, nicht über die Position. Unbekannte zusätzliche Spalten MUST ignoriert werden, fehlende Pflichtspalten sind ein Fehler.

#### Scenario: Spalten in anderer Reihenfolge
- **WHEN** die Spalten einer Datei in anderer Reihenfolge stehen als in der Beschreibung
- **THEN** wird die Datei richtig gelesen

#### Scenario: Zusätzliche Spalte
- **WHEN** eine Datei eine unbekannte Spalte enthält
- **THEN** meldet `flow validate` keinen Fehler und die Spalte bleibt unbenutzt

#### Scenario: Fehlende Pflichtspalte
- **WHEN** eine Pflichtspalte fehlt
- **THEN** meldet `flow validate` einen Fehler mit Dateiname und Spaltenname

#### Scenario: Zeilenenden
- **WHEN** eine Datei Windows-Zeilenenden (CRLF) hat
- **THEN** werden die Werte ohne das Zeilenende-Zeichen gelesen

#### Scenario: Sonderzeichen
- **WHEN** ein Wert ein Formfeed- oder Zeilentabulator-Zeichen enthält
- **THEN** trennt es keine Zeile, nur `\n`, `\r\n` und `\r` tun das

### Requirement: Zustände
`workflow/states.tsv` SHALL die Zustände mit `id`, `kind` (`triage`, `status` oder `terminal`), `color` und `description` enthalten, optional `enabled` (`yes` oder `no`, Standard `yes`). Die `id` MUST in der Datei eindeutig sein und ist bei `triage` und `status` der Name des Labels. Die Farbe MUST aus sechs Hex-Zeichen bestehen, bei `terminal` darf sie `-` sein. Es MUST genau einen Zustand der Art `terminal` geben.

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

### Requirement: Übergänge
`workflow/transitions.tsv` SHALL Übergänge mit `from`, `to`, `trigger` und `guard` enthalten, optional `enabled`. `from` und `to` MUST auf Zustände aus `states.tsv` verweisen, `from` darf `-` (Start) sein. Ein Übergang bleibt innerhalb einer Dimension (gleiche `kind`), außer bei `-` als Start oder `terminal` als Ziel. `guard` ist eine mit Komma getrennte UND-Liste von Detektoren oder `-`.

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

### Requirement: Phasen
`workflow/phases.tsv` SHALL Phasen mit `id`, `name`, `tool`, `done_when` und `level` (`required` oder `optional`) enthalten, optional `enabled`. Die `id` MUST eindeutig sein. `done_when` ist eine mit Komma getrennte UND-Liste von Detektoren oder `-`.

#### Scenario: Doppelte Phase
- **WHEN** zwei Phasen dieselbe `id` haben
- **THEN** meldet `flow validate` einen Fehler

#### Scenario: Ungültige Stufe
- **WHEN** `level` weder `required` noch `optional` ist
- **THEN** meldet `flow validate` einen Fehler

### Requirement: Detektoren als festes Vokabular
`workflow/detectors.tsv` SHALL die erlaubten Detektoren mit `name`, `arg` und `description` enthalten. `arg` ist `-` (kein Argument), `text`, `path` oder `enum:a|b|c`. Jeder Detektor in `guard` und `done_when` MUST in dieser Datei stehen und die passende Argumentform haben (`name` oder `name:argument`). Es wird nie Code aus den Dateien ausgeführt.

#### Scenario: Unbekannter Detektor
- **WHEN** eine Bedingung `pr_open:draft` nennt, der Name aber nicht in `detectors.tsv` steht
- **THEN** meldet `flow validate` einen Fehler mit Datei, Zeile und Namen

#### Scenario: Falsches Argument
- **WHEN** ein Detektor mit `enum:draft|ready|merged` mit dem Argument `open` verwendet wird
- **THEN** meldet `flow validate` einen Fehler mit der erlaubten Liste

#### Scenario: Fehlendes oder überzähliges Argument
- **WHEN** ein Detektor ohne Argument ein Argument bekommt oder ein Detektor mit Argument keines
- **THEN** meldet `flow validate` einen Fehler

### Requirement: Warnungen
`flow validate` SHALL Auffälligkeiten als Warnung melden, die keinen Fehlercode erzeugen: Verweise auf Zustände mit `enabled=no` (Phasen werden von nichts referenziert), ein aktivierter Zustand ohne eingehenden Übergang oder, außer bei `terminal`, ohne ausgehenden Übergang und Phasen-IDs, die nicht in aufsteigender Reihenfolge stehen. Mit `--strict` MUST jede Warnung zu einem Fehler werden.

#### Scenario: Verweis auf deaktivierten Zustand
- **WHEN** ein aktivierter Übergang auf einen Zustand mit `enabled=no` zeigt
- **THEN** meldet `flow validate` eine Warnung und der Exit-Code bleibt 0

#### Scenario: Strikter Modus
- **WHEN** `flow validate --strict` eine Warnung findet
- **THEN** ist der Exit-Code ungleich 0

### Requirement: Befehl flow validate
`flow validate` SHALL alle Dateien unter `workflow/` prüfen, ohne Netzzugriff und ohne etwas zu ändern. Jeden Fund MUST es als `datei:zeile: Stufe: meldung` ausgeben (Stufe ist Fehler oder Warnung), danach eine Zusammenfassung mit Zahl der Fehler und Warnungen. Bei mindestens einem Fehler MUST der Exit-Code ungleich 0 sein.

#### Scenario: Gültige Daten
- **WHEN** alle Dateien gültig sind
- **THEN** endet `flow validate` mit Exit-Code 0 und meldet 0 Fehler

#### Scenario: Mehrere Funde
- **WHEN** zwei Dateien Fehler enthalten
- **THEN** werden alle Funde ausgegeben, nicht nur der erste, und der Exit-Code ist ungleich 0

#### Scenario: Fehlende Datei
- **WHEN** eine der vier Dateien fehlt
- **THEN** meldet `flow validate` einen Fehler mit dem Dateinamen

### Requirement: Skills und Rollen im Prozessverzeichnis
`flow validate` SHALL `workflow/skills.tsv` und `workflow/roles.tsv` wie die übrigen Dateien lesen (Kopfzeile, Spalten nach Namen, `enabled`), Verweise auf Phasen gegen `phases.tsv` prüfen und fehlende Pflichtspalten mit Datei und Spalte melden.

#### Scenario: Verweis auf unbekannte Phase
- **WHEN** `skills.tsv` eine Phase nennt, die in `phases.tsv` fehlt
- **THEN** meldet `flow validate` Datei, Zeile und Phase
