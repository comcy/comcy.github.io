# Spec Delta

## Purpose
Legt fest, welche Verzeichnisse im Repo welche Aufgabe haben (Inhalt, Bauwerkzeug, Projektkonfiguration, Werkzeug), damit das Werkzeug aus dem Repo abgespalten und in anderen Projekten mit eigener Konfiguration genutzt werden kann.

## ADDED Requirements

### Requirement: Vier Bereiche
Das Repo SHALL seine Dateien in vier Bereiche teilen: Inhalt (`content/`), Bauwerkzeug (`site/`), Projektkonfiguration (`workflow/`) und Werkzeug (`devflow/`). Im Wurzelverzeichnis MUST nur liegen, was Git, GitHub, OpenSpec oder die Agenten dort erwarten.

#### Scenario: Neuer Beitrag
- **WHEN** ein Beitrag geschrieben wird
- **THEN** liegt die Datei unter `content/posts/` und keine Datei außerhalb von `content/` ändert sich

#### Scenario: Wurzelverzeichnis
- **WHEN** das Wurzelverzeichnis aufgelistet wird
- **THEN** enthält es neben den vier Bereichen nur `README.md`, `AGENTS.md`, `docs/`, `openspec/`, `.github/`, `.githooks/`, `.claude/`, `.agents/` und Git-Dateien

### Requirement: Werkzeug ohne Projektwissen
Der Ordner `devflow/` SHALL keine Pfade, Namen oder Programme des Blogs enthalten (kein `pandoc`, kein `content/`, keine Eval-Aufgabe). Alles Projektspezifische MUST in `workflow/` oder in den Bereichen Inhalt und Bauwerkzeug liegen.

#### Scenario: Projektspezifisches im Werkzeug
- **WHEN** in `devflow/` nach `pandoc`, `content/` oder `posts/` gesucht wird
- **THEN** gibt es keinen Treffer außerhalb von Tests, die ein Beispielprojekt aufbauen

### Requirement: Ein Konfigurationsordner
Das Werkzeug SHALL seine Konfiguration ausschließlich aus `workflow/` im Wurzelverzeichnis des Projekts lesen. Dazu gehören die Prozess-Tabellen, `tools.tsv`, die Gate-Listen (`gate/allow.tsv`, `gate/commit-types.tsv`) und die Eval-Aufgaben (`evals/tasks/`). Der Ordnername MUST an einer Stelle im Werkzeug stehen.

#### Scenario: Pflichtprogramm ergänzen
- **WHEN** eine Zeile in `workflow/tools.tsv` ergänzt wird
- **THEN** prüft `setup --check` das Programm, ohne dass Dateien in `devflow/` geändert werden

#### Scenario: Eval-Aufgabe ergänzen
- **WHEN** ein Ordner unter `workflow/evals/tasks/` angelegt wird
- **THEN** nimmt der Runner die Aufgabe beim nächsten Lauf auf

### Requirement: Gebaute Seite bleibt gleich
Die Umstellung SHALL die gebaute Seite nicht verändern: Dieselben Eingaben ergeben unter `public/` dieselben Dateien mit demselben Inhalt, dieselben URLs und dieselben Namen der CI-Prüfungen.

#### Scenario: Vergleich vor und nach dem Umzug
- **WHEN** die Seite mit demselben `SITE_URL` und demselben Datum vor und nach dem Umzug gebaut wird
- **THEN** unterscheiden sich die beiden `public/`-Ordner nicht (`diff -r`)

#### Scenario: Branch Protection
- **WHEN** ein PR nach dem Umzug geöffnet wird
- **THEN** melden die Prüfungen `test`, `gates` und `python (ubuntu/macos/windows)` unter denselben Namen

### Requirement: Dateien für kvasir
Die Dateien `workflow/phases.tsv`, `detectors.tsv`, `states.tsv`, `metrics.tsv` und `metric-sources.tsv` SHALL an ihrem Ort mit unverändertem Format bleiben, solange kvasir keinen anderen Ordner kennt.

#### Scenario: kvasir nach dem Umzug
- **WHEN** `kvasir status` und `kvasir metrics` nach dem Umzug laufen
- **THEN** lesen sie die Phasen, Zustände und Metriken ohne Warnung über fehlende Dateien
