## MODIFIED Requirements

### Requirement: Isolierter Lauf
Der Runner SHALL jede Aufgabe in einem frischen Wegwerf-Repo ausführen, das aus dem aktuellen Arbeitsstand von `AGENTS.md`, `docs/agents/`, `workflow/`, `scripts/`, `.githooks/`, `openspec/config.yaml` und `.agents/skills/` gebaut wird, mit einem Stub-`gh` vor dem PATH, der nur unter seinem Arbeitsverzeichnis schreibt. Der Agent MUST ohne Nutzer-Einstellungen laufen (keine Hooks, Plugins, MCP-Server und kein Auto-Memory aus dem echten HOME) und SHALL Modell, Budget und erlaubte Tools je Lauf begrenzen. Der Runner SHALL den Adapter in einer Sandbox starten, die Schreibzugriffe außerhalb des Arbeitsverzeichnisses des Laufs und der Claude-Konfiguration verhindert (`--sandbox auto|bwrap|none`, Standard `auto`). Fehlt die Sandbox, MUST der Runner mit klarer Meldung abbrechen, außer `--sandbox none` ist angegeben.

#### Scenario: Keine Nutzer-Einstellungen
- **WHEN** der Agent gestartet wird
- **THEN** erhält `claude` `--setting-sources project,local`, `--strict-mcp-config` und `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`

#### Scenario: Stub schreibt nur in sein Verzeichnis
- **WHEN** der Stub-`gh` außerhalb seines Arbeitsverzeichnisses schreiben soll
- **THEN** bricht er ab und das echte Repo bleibt unverändert

#### Scenario: Schreiben außerhalb der Sandbox
- **WHEN** der Agent unter `bwrap` versucht, eine Datei außerhalb des Arbeitsverzeichnisses zu schreiben
- **THEN** scheitert der Schreibzugriff und die Datei existiert nicht

#### Scenario: Keine Sandbox verfügbar
- **WHEN** `bwrap` fehlt und `--sandbox none` nicht angegeben ist
- **THEN** bricht der Runner mit Exit-Code 2 und einer Meldung ab

## ADDED Requirements

### Requirement: Sandbox-Modus im Bericht
Der Bericht SHALL im Kopf den Sandbox-Modus nennen (`bwrap` oder `keine`).

#### Scenario: Lauf ohne Sandbox
- **WHEN** mit `--sandbox none` gelaufen wurde
- **THEN** steht im Kopf `Sandbox: keine`
