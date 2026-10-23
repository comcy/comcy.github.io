## ADDED Requirements

### Requirement: Adapter für den Agentenstart
Der Runner SHALL den Agenten über einen Adapter starten (`--adapter <programm>`, Standard `evals/adapters/claude.py`): ein Programm, das ein JSON mit `prompt`, `cwd`, `env`, `model`, `budget_usd`, `allowed_tools` und `timeout_s` über stdin liest und ein JSON mit `tool_calls`, `result_text`, `cost_usd`, `duration_ms` und `error` über stdout schreibt. Aufgaben und Berichte MUST vom Adapter unabhängig sein.

#### Scenario: Zweiter Adapter
- **WHEN** ein anderes Programm als Adapter angegeben wird
- **THEN** laufen dieselben Aufgaben und Prüfungen unverändert

### Requirement: Nicht prüfbar statt Fehler
Liefert ein Adapter kein Feld `tool_calls`, SHALL der Bericht Aufgaben, die den Mitschnitt brauchen, als "nicht prüfbar" ausweisen und MUST sie nicht als durchgefallen werten. Ein Adapter-Exit-Code ungleich 0 oder eine Antwort ohne gültiges JSON MUST den Lauf mit Exit-Code 2 und einer Meldung abbrechen (kein Bericht). Ein nicht leeres Feld `error` bei Exit-Code 0 lässt diesen einen Lauf durchfallen, mit `Adapter-Fehler: <text>` als erster Prüffehler.

#### Scenario: Adapter ohne Mitschnitt
- **WHEN** der Adapter `tool_calls` nicht liefert
- **THEN** zeigt der Bericht `kein-git-stash` als "nicht prüfbar"

### Requirement: Werkzeuge der Rolle
Der Runner SHALL die `allowed_tools` der Rolle der Aufgabe (`role` in `task.json`, Standard `builder`) an den Adapter übergeben.

#### Scenario: Tools aus der Rolle
- **WHEN** die Rolle `builder` in `roles.tsv` bestimmte `allowed_tools` hat
- **THEN** erhält der Adapter genau diese Liste

### Requirement: Abgeleitete Aufgaben
`evals/derive.py` SHALL für jeden Übergang mit `guard` in `workflow/transitions.tsv` und jeden Detektor, den der Stub-`gh` abbilden kann, eine Aufgabe "Übergang bei verletzter Bedingung muss abbrechen" erzeugen. Der Bericht MUST Übergänge mit nicht abbildbaren Detektoren als "nicht ableitbar" nennen.

#### Scenario: Neuer Guard
- **WHEN** ein Übergang mit `no_open_blockers` in `transitions.tsv` steht
- **THEN** entsteht eine Aufgabe, die prüft, dass bei offenem Blocker kein Branch und kein Label entsteht
