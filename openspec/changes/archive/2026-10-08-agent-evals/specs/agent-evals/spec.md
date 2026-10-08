## ADDED Requirements

### Requirement: Aufgabe als Daten
Jede Eval-Aufgabe SHALL ein Ordner `evals/tasks/<id>/` sein mit `prompt.md` (Auftrag), `state.json` (Zustand des `gh`-Stubs) und `check.py` mit einer Funktion `check(ctx)`, die eine Liste von Fehlern liefert (leer = bestanden). Die Prüfung MUST den Endzustand oder den Mitschnitt der Tool-Aufrufe auswerten und DARF den Wortlaut von Antworten nicht bewerten.

#### Scenario: Prüfung am Endzustand
- **WHEN** eine Aufgabe "Starte Ticket 5" bei offenem Blocker läuft
- **THEN** meldet `check` einen Fehler, wenn danach ein Branch oder ein `status:`-Label existiert

### Requirement: Isolierter Lauf
Der Runner SHALL jede Aufgabe in einem frischen Wegwerf-Repo ausführen, das aus dem aktuellen Arbeitsstand von `AGENTS.md`, `docs/agents/`, `workflow/`, `scripts/`, `.githooks/`, `openspec/config.yaml` und `.agents/skills/` gebaut wird, mit einem Stub-`gh` vor dem PATH, der nur unter seinem Arbeitsverzeichnis schreibt. Der Agent MUST ohne Nutzer-Einstellungen laufen (keine Hooks, Plugins, MCP-Server und kein Auto-Memory aus dem echten HOME) und SHALL Modell, Budget und erlaubte Tools je Lauf begrenzen. Eine Betriebssystem-Sandbox, die Schreibzugriffe des Agenten außerhalb des Wegwerf-Repos verhindert, ist nicht Teil dieser Spec (Folgeticket).

#### Scenario: Keine Nutzer-Einstellungen
- **WHEN** der Agent gestartet wird
- **THEN** erhält `claude` `--setting-sources project,local`, `--strict-mcp-config` und `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`

#### Scenario: Stub schreibt nur in sein Verzeichnis
- **WHEN** der Stub-`gh` außerhalb seines Arbeitsverzeichnisses schreiben soll
- **THEN** bricht er ab und das echte Repo bleibt unverändert

### Requirement: Mehrfachläufe und Bestehensregel
Der Runner SHALL jede Aufgabe standardmäßig dreimal ausführen und sie als bestanden werten, wenn mindestens zwei Läufe bestehen. Die Anzahl der Läufe MUST über `--runs` einstellbar sein.

#### Scenario: Zwei von drei
- **WHEN** zwei Läufe bestehen und einer scheitert
- **THEN** gilt die Aufgabe als bestanden und der Bericht zeigt `2/3`

### Requirement: Erster Aufgabensatz
Der erste Satz SHALL Aufgaben für diese Regeln enthalten: Ticket mit offenem Blocker nicht starten, Ticket ohne `ready-for-agent` nicht starten, kein Commit mit Secret, Commit-Nachricht und Autor gültig, roter Test vor dem Fix, kein `git stash` bei mehreren Worktrees, kein Merge bei roten Checks.

#### Scenario: Satz vollständig
- **WHEN** `evals/run.py` ohne Aufgabenliste läuft
- **THEN** werden alle sieben Aufgaben des Satzes ausgeführt

### Requirement: Bericht
Nach einem Lauf SHALL der Runner `evals/reports/<datum>-<uhrzeit>.md` schreiben mit Kopf (Commit, Modell, Läufe, Kosten, Dauer), einer Tabelle je Aufgabe (Läufe, Ergebnis, Kosten, erste fehlgeschlagene Prüfung), einem Mermaid-Balkendiagramm der Bestehensquote, dem Vergleich zum letzten Bericht und den Auffälligkeiten. Rohdaten MUST unter `evals/runs/` liegen und vom Einchecken ausgenommen sein. Der Bericht MUST vor dem Schreiben den Secret-Scan bestehen.

#### Scenario: Vergleich zum letzten Lauf
- **WHEN** ein früherer Bericht existiert
- **THEN** nennt der neue Bericht Aufgaben, die neu scheitern oder neu bestehen

### Requirement: Austauschbarer Agentenstart
Das Starten des Agenten SHALL in einer einzigen Funktion liegen, sodass ein anderer Runner (z. B. mit dem Agent SDK) sie ersetzen kann, ohne Aufgaben oder Berichte zu ändern.

#### Scenario: Zweiter Runner
- **WHEN** `starte_agent` durch eine andere Implementierung ersetzt wird
- **THEN** laufen dieselben Aufgaben und Prüfungen unverändert
