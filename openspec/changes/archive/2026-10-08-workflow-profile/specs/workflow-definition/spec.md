## ADDED Requirements

### Requirement: Skills und Rollen im Prozessverzeichnis
`flow validate` SHALL `workflow/skills.tsv` und `workflow/roles.tsv` wie die übrigen Dateien lesen (Kopfzeile, Spalten nach Namen, `enabled`), Verweise auf Phasen gegen `phases.tsv` prüfen und fehlende Pflichtspalten mit Datei und Spalte melden.

#### Scenario: Verweis auf unbekannte Phase
- **WHEN** `skills.tsv` eine Phase nennt, die in `phases.tsv` fehlt
- **THEN** meldet `flow validate` Datei, Zeile und Phase
