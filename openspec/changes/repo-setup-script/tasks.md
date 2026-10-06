# Tasks

## 1. Tracer: `flow validate` für Zustände, Leser und CI-Matrix

- [ ] 1.1 `.gitattributes`, `workflow/states.tsv` mit den heutigen neun Labels und `closed`, `scripts/lib/workflow.py` (Leser mit Kopfzeile, Kommentaren, CRLF) und `scripts/flow.py validate` für `states.tsv` (Spalten, Eindeutigkeit, Farbe, Beschreibung, genau ein terminaler Zustand); Tests per `unittest` gegen Kopien mit je einem Defekt und gegen die echte Datei; `python3 -m unittest` grün
- [ ] 1.2 CI-Job mit Matrix Ubuntu, macOS und Windows für die Python-Tests und `flow validate`, `tests/run.sh` ruft die Python-Tests mit auf; der Job ist auf allen drei Systemen grün (Nachweis im PR, Windows-Zeilenenden geprüft)

## 2. Übergänge, Phasen und Detektoren

- [ ] 2.1 `workflow/detectors.tsv`, `workflow/transitions.tsv`, `workflow/phases.tsv` mit dem heutigen Prozess füllen und `flow validate` um die Prüfungen für Verweise, Dimensionen, Vokabular, Argumentformen und Phasen erweitern; je Prüfung ein Fehlerfall im Test, die echten Dateien sind ohne Fehler
- [ ] 2.2 Warnungen (deaktivierte Verweise, unerreichbare Zustände, Reihenfolge) und `--strict`, Ausgabe `datei:zeile: meldung` mit Zusammenfassung und Exit-Code; Tests für Warnung ohne Fehlercode und `--strict` mit Fehlercode

## 3. `setup --check`: Voraussetzungen

- [ ] 3.1 `scripts/setup.d/tools.tsv`, `scripts/setup.py --check` mit Programmsuche (`shutil.which`), Versionsvergleich, Pflicht und empfohlen; Tests im temporären Repo mit Stub-Programmen (fehlt, zu alt, empfohlen fehlt), Exit-Codes; Stubs laufen auf allen drei Systemen

## 4. `setup`: lokaler Klon

- [ ] 4.1 Agenten-Adapter (`scripts/setup.d/agents.tsv`, Argumente, `git config --local setup.agents`, `openspec init --tools agents,<agent>`) und `.git/info/exclude` ohne Dopplung, `core.hooksPath` nur mit vorhandenem `.githooks/`; Tests für Argument, gespeicherte Wahl, keine Wahl, unbekannten Agenten, wiederholten Lauf (Idempotenz) und unveränderte vorhandene Ausschlüsse
- [ ] 4.2 Adapter aktuell halten: Vergleich der `openspec`-Version mit `generatedBy` in den Skills, `openspec update` im normalen Lauf, "Adapter veraltet" in `--check` ohne Änderung; Tests mit abweichender Version

## 5. `setup --labels`

- [ ] 5.1 Labels aus `states.tsv` anlegen (`gh label list`, `gh label create` mit Farbe und Beschreibung), nur fehlende, nur mit `--labels`, Hinweis ohne Schalter, Fehler ohne angemeldetes `gh`; Tests mit Stub-`gh` (zwei fehlen, alle da, nicht angemeldet); manueller Probelauf gegen das echte Repo als Beleg im PR

## 6. Doku und Abschluss

- [ ] 6.1 `docs/workflow.md` (Setup-Checkliste und Phase S im Diagramm) auf den Aufruf umstellen, README (Aufrufe unter Linux, macOS und Windows, Python 3.11, Tab-Hinweis), `docs/agents/triage-labels.md` und `flow-labels.md` verweisen auf `workflow/states.tsv` als Quelle; `flow validate` und `setup --check` laufen auf dem Repo ohne Fehler, Matrix grün
