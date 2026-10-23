# Spec Delta

## MODIFIED Requirements

### Requirement: Aufgabe als Daten
Jede Eval-Aufgabe SHALL ein Ordner `workflow/evals/tasks/<id>/` sein mit `prompt.md` (Auftrag), `state.json` (Zustand des `gh`-Stubs) und `check.py` mit einer Funktion `check(ctx)`, die eine Liste von Fehlern liefert (leer = bestanden). Die Prüfung MUST den Endzustand oder den Mitschnitt der Tool-Aufrufe auswerten und DARF den Wortlaut von Antworten nicht bewerten.

#### Scenario: Prüfung am Endzustand
- **WHEN** eine Aufgabe "Starte Ticket 5" bei offenem Blocker läuft
- **THEN** meldet `check` einen Fehler, wenn danach ein Branch oder ein `status:`-Label existiert

#### Scenario: Aufgaben liegen in der Projektkonfiguration
- **WHEN** der Runner ohne Aufgabenliste läuft
- **THEN** liest er die Aufgaben aus `workflow/evals/tasks/`

### Requirement: Isolierter Lauf
Der Runner SHALL jede Aufgabe in einem frischen Wegwerf-Repo ausführen, das aus dem aktuellen Arbeitsstand von `AGENTS.md`, `docs/agents/`, `workflow/`, `devflow/scripts/`, `.githooks/`, `openspec/config.yaml` und `.agents/skills/` gebaut wird, mit einem Stub-`gh` vor dem PATH, der nur unter seinem Arbeitsverzeichnis schreibt. Der Agent MUST ohne Nutzer-Einstellungen laufen (keine Hooks, Plugins, MCP-Server und kein Auto-Memory aus dem echten HOME) und SHALL Modell, Budget und erlaubte Tools je Lauf begrenzen. Der Runner SHALL den Adapter in einer Sandbox starten, die Schreibzugriffe außerhalb des Arbeitsverzeichnisses des Laufs und der Claude-Konfiguration verhindert (`--sandbox auto|bwrap|none`, Standard `auto`). Fehlt die Sandbox, MUST der Runner mit klarer Meldung abbrechen, außer `--sandbox none` ist angegeben.

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

#### Scenario: Wegwerf-Repo enthält das Werkzeug
- **WHEN** der Runner das Wegwerf-Repo aufbaut
- **THEN** liegen darin `devflow/scripts/` und `workflow/` im Stand des Arbeitsverzeichnisses

### Requirement: Erster Aufgabensatz
Der erste Satz SHALL Aufgaben für diese Regeln enthalten: Ticket mit offenem Blocker nicht starten, Ticket ohne `ready-for-agent` nicht starten, kein Commit mit Secret, Commit-Nachricht und Autor gültig, roter Test vor dem Fix, kein `git stash` bei mehreren Worktrees, kein Merge bei roten Checks.

#### Scenario: Satz vollständig
- **WHEN** `devflow/evals/run.py` ohne Aufgabenliste läuft
- **THEN** werden alle sieben Aufgaben des Satzes ausgeführt

### Requirement: Bericht
Nach einem Lauf SHALL der Runner `workflow/evals/reports/<datum>-<uhrzeit>.md` schreiben mit Kopf (Commit, Modell, Läufe, Kosten, Dauer), einer Tabelle je Aufgabe (Läufe, Ergebnis, Kosten, erste fehlgeschlagene Prüfung), einem Mermaid-Balkendiagramm der Bestehensquote, dem Vergleich zum letzten Bericht und den Auffälligkeiten. Rohdaten MUST unter `workflow/evals/runs/` liegen und vom Einchecken ausgenommen sein. Der Bericht MUST vor dem Schreiben den Secret-Scan bestehen.

#### Scenario: Vergleich zum letzten Lauf
- **WHEN** ein früherer Bericht existiert
- **THEN** nennt der neue Bericht Aufgaben, die neu scheitern oder neu bestehen

### Requirement: Adapter für den Agentenstart
Der Runner SHALL den Agenten über einen Adapter starten (`--adapter <programm>`, Standard `devflow/evals/adapters/claude.py`): ein Programm, das ein JSON mit `prompt`, `cwd`, `env`, `model`, `budget_usd`, `allowed_tools` und `timeout_s` über stdin liest und ein JSON mit `tool_calls`, `result_text`, `cost_usd`, `duration_ms` und `error` über stdout schreibt. Aufgaben und Berichte MUST vom Adapter unabhängig sein.

#### Scenario: Zweiter Adapter
- **WHEN** ein anderes Programm als Adapter angegeben wird
- **THEN** laufen dieselben Aufgaben und Prüfungen unverändert

### Requirement: Abgeleitete Aufgaben
`devflow/evals/derive.py` SHALL für jeden Übergang mit `guard` in `workflow/transitions.tsv` und jeden Detektor, den der Stub-`gh` abbilden kann, eine Aufgabe "Übergang bei verletzter Bedingung muss abbrechen" erzeugen und unter `workflow/evals/tasks-derived/` ablegen (nicht im Git). Der Bericht MUST Übergänge mit nicht abbildbaren Detektoren als "nicht ableitbar" nennen.

#### Scenario: Neuer Guard
- **WHEN** ein Übergang mit `no_open_blockers` in `transitions.tsv` steht
- **THEN** entsteht eine Aufgabe, die prüft, dass bei offenem Blocker kein Branch und kein Label entsteht
