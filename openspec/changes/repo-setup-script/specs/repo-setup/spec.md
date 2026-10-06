# Spec Delta

## Purpose

Legt fest, was der Befehl `setup` nach dem Klonen tut: Voraussetzungen prüfen, den lokalen Klon für die gewählten Agenten einrichten, auf Wunsch die Labels des Prozesses anlegen und mit `--check` melden, was fehlt, ohne etwas zu ändern.

## ADDED Requirements

### Requirement: Voraussetzungen prüfen
`setup` SHALL die Programme aus `scripts/setup.d/tools.tsv` prüfen (Name, Mindestversion, Stufe `required` oder `recommended`, Hinweis). Ein fehlendes oder zu altes Pflichtprogramm MUST einen Fehler mit dem Hinweis und einen Exit-Code ungleich 0 ergeben. Ein fehlendes empfohlenes Programm ist nur ein Hinweis. Ohne Mindestversion (`-`) genügt, dass das Programm vorhanden ist.

#### Scenario: Pflichtprogramm fehlt
- **WHEN** `git` oder `gh` nicht gefunden wird
- **THEN** meldet `setup` den Namen und den Hinweis und endet mit Exit-Code ungleich 0

#### Scenario: Version zu alt
- **WHEN** die installierte Version eines Programms unter der Mindestversion liegt
- **THEN** nennt `setup` installierte und geforderte Version und endet mit Exit-Code ungleich 0

#### Scenario: Empfohlenes Programm fehlt
- **WHEN** nur ein Programm der Stufe `recommended` fehlt
- **THEN** zeigt `setup` einen Hinweis und der Exit-Code bleibt 0

### Requirement: Standardlauf wirkt nur lokal
Ohne Schalter SHALL `setup` ausschließlich Dinge im lokalen Klon ändern und MUST keine Daten auf GitHub schreiben. Es setzt `core.hooksPath` auf `.githooks`, wenn dieser Ordner existiert, richtet die Agenten-Adapter ein und trägt deren Ordner in `.git/info/exclude` ein.

#### Scenario: Kein Zugriff auf GitHub
- **WHEN** `setup` ohne Schalter läuft
- **THEN** werden keine Labels angelegt oder geändert

#### Scenario: Hooks-Ordner vorhanden
- **WHEN** `.githooks/` existiert
- **THEN** ist danach `core.hooksPath` auf `.githooks` gesetzt

#### Scenario: Kein Hooks-Ordner
- **WHEN** `.githooks/` nicht existiert
- **THEN** bleibt `core.hooksPath` unverändert

### Requirement: Agenten-Adapter
`setup` SHALL die Adapter für die Agenten einrichten, die als Argumente genannt werden, sonst die in `git config --local setup.agents` gespeicherten, sonst nur `agents`. Es MUST dazu `openspec init --tools agents[,<agent>…]` aufrufen und die Wahl in `setup.agents` speichern. Die Ordner der Adapterdateien stehen in `scripts/setup.d/agents.tsv`, ein unbekannter Agent MUST einen Fehler mit dem Hinweis auf diese Datei ergeben.

#### Scenario: Agent als Argument
- **WHEN** `setup claude` läuft
- **THEN** ruft `setup` `openspec init --tools agents,claude` auf und speichert `claude` in `setup.agents`

#### Scenario: Gespeicherte Wahl
- **WHEN** `setup` ohne Argument läuft und `setup.agents` ist `claude`
- **THEN** wird `claude` wieder verwendet

#### Scenario: Keine Wahl
- **WHEN** weder Argument noch gespeicherte Wahl vorhanden sind
- **THEN** richtet `setup` nur `agents` ein und weist auf das Argument für den eigenen Agenten hin

#### Scenario: Unbekannter Agent
- **WHEN** ein Agent nicht in `agents.tsv` steht
- **THEN** endet `setup` mit einem Fehler und ändert nichts

### Requirement: Ausschlüsse in .git/info/exclude
`setup` SHALL die Ordner der gewählten Agenten (nicht `agents`) einmalig in `.git/info/exclude` eintragen und MUST bestehende Einträge dort unverändert lassen. Wiederholte Läufe erzeugen keine doppelten Einträge.

#### Scenario: Eintrag wird ergänzt
- **WHEN** `setup claude` läuft und `.claude/` fehlt in `.git/info/exclude`
- **THEN** steht `.claude/` danach genau einmal in der Datei

#### Scenario: Wiederholter Lauf
- **WHEN** `setup claude` ein zweites Mal läuft
- **THEN** bleibt `.git/info/exclude` unverändert

### Requirement: Adapter aktuell halten
`setup` SHALL die installierte `openspec`-Version mit der Version in den erzeugten Skills (`generatedBy`) vergleichen. Weicht sie ab, MUST ein normaler Lauf `openspec update` aufrufen, `--check` MUST "Adapter veraltet" melden und nichts ändern.

#### Scenario: Version abweichend
- **WHEN** die Skills mit einer älteren `openspec`-Version erzeugt wurden
- **THEN** ruft ein normaler Lauf `openspec update` auf

#### Scenario: Prüfung ohne Änderung
- **WHEN** `--check` läuft und die Version abweicht
- **THEN** meldet es "Adapter veraltet" und ruft `openspec update` nicht auf

### Requirement: Labels nur mit Schalter
`setup --labels` SHALL die Labels für alle aktivierten Zustände der Art `triage` und `status` aus `workflow/states.tsv` anlegen, mit Farbe und Beschreibung, und MUST vorhandene Labels unverändert lassen. Ohne den Schalter meldet `setup` nur, wie viele Labels fehlen. Ohne angemeldetes `gh` ergibt `--labels` einen Fehler mit dem Hinweis `gh auth login`.

#### Scenario: Fehlende Labels anlegen
- **WHEN** `setup --labels` läuft und zwei Labels fehlen
- **THEN** werden genau diese zwei angelegt, mit Farbe und Beschreibung aus `states.tsv`

#### Scenario: Vorhandene Labels
- **WHEN** alle Labels existieren
- **THEN** legt `setup --labels` nichts an

#### Scenario: Hinweis ohne Schalter
- **WHEN** `setup` ohne `--labels` läuft und Labels fehlen
- **THEN** nennt es die Zahl der fehlenden Labels und den Schalter

#### Scenario: Nicht angemeldet
- **WHEN** `gh` nicht angemeldet ist und `--labels` gesetzt ist
- **THEN** endet `setup` mit einem Fehler und dem Hinweis auf `gh auth login`

### Requirement: Prüfmodus
`setup --check` SHALL nur melden, was fehlt oder abweicht (Voraussetzungen, Adapter, Ausschlüsse, Labels, Konsistenz der Dateien unter `workflow/` über dieselbe Prüfung wie `flow validate`), und MUST nichts ändern. Der Exit-Code ist ungleich 0, wenn etwas fehlt, das ein normaler Lauf beheben müsste oder nicht beheben kann.

#### Scenario: Alles vorhanden
- **WHEN** nichts fehlt
- **THEN** endet `setup --check` mit Exit-Code 0

#### Scenario: Etwas fehlt
- **WHEN** ein Ausschluss in `.git/info/exclude` fehlt
- **THEN** meldet `setup --check` ihn, ändert die Datei nicht und endet mit Exit-Code ungleich 0

### Requirement: Idempotenz
Ein zweiter Lauf von `setup` mit denselben Argumenten SHALL nichts verändern und MUST "nichts zu tun" melden.

#### Scenario: Zweiter Lauf
- **WHEN** `setup claude` zweimal hintereinander läuft
- **THEN** ruft der zweite Lauf `openspec init` nicht erneut auf und ändert weder die Git-Konfiguration noch `.git/info/exclude`

### Requirement: Plattformunabhängigkeit
`setup` und `flow` SHALL unter Linux, macOS und Windows dasselbe Ergebnis liefern. Sie nutzen nur die Python-Standardbibliothek ab Version 3.11, rufen Programme mit Argumentlisten auf (ohne Shell) und lesen Dateien unabhängig von den Zeilenenden.

#### Scenario: Aufruf unter Windows
- **WHEN** `py -3 scripts\setup.py --check` unter Windows läuft
- **THEN** verhält es sich wie `python3 scripts/setup.py --check` unter Linux

#### Scenario: Zu altes Python
- **WHEN** Python älter als 3.11 ist
- **THEN** nennt die Meldung die benötigte Version, statt mit einem Syntaxfehler abzubrechen
