## ADDED Requirements

### Requirement: Conventional Commits prüfen
Der Befehl `gate commits` SHALL die Betreffzeile jedes übergebenen Commits gegen `type(scope)!: Betreff` mit den erlaubten Typen prüfen und bei Verstoß mit Exit-Code ungleich 0 enden. Merge-Commits MUST erlaubt sein.

#### Scenario: Gültiger Betreff
- **WHEN** der Betreff `feat(setup): Labels anlegen` lautet
- **THEN** endet die Prüfung mit Exit-Code 0

#### Scenario: Ungültiger Betreff
- **WHEN** der Betreff `Labels angelegt` lautet
- **THEN** nennt die Prüfung Commit und Regel und endet mit Exit-Code ungleich 0

### Requirement: Secrets nicht einchecken
Der Befehl `gate secrets` SHALL hinzugefügte Zeilen und Dateinamen eines Bereichs oder des Index gegen die Regelliste prüfen und bei Treffern ohne passenden Allowlist-Eintrag mit Exit-Code ungleich 0 enden. Die Meldung MUST Datei und Regel nennen und DARF den gefundenen Wert nicht ausgeben.

#### Scenario: Token im Diff
- **WHEN** eine hinzugefügte Zeile einen Token mit bekanntem Präfix enthält
- **THEN** endet die Prüfung mit Exit-Code ungleich 0 und nennt Datei und Regel, nicht den Wert

#### Scenario: Allowlist
- **WHEN** ein Treffer durch einen Allowlist-Eintrag (Pfad, Muster, Grund) abgedeckt ist
- **THEN** wird er nicht gemeldet

### Requirement: Eine Logik für Hook und CI
Die Git-Hooks `commit-msg` und `pre-commit` SHALL dieselben Prüfungen wie die CI aufrufen. Der CI-Job `gates` MUST alle Commits und den Diff eines Pull Requests prüfen und auf Ubuntu laufen.

#### Scenario: Hook umgangen
- **WHEN** ein Commit mit `--no-verify` entstanden ist und gegen die Regeln verstößt
- **THEN** schlägt der CI-Job `gates` für den Pull Request fehl
