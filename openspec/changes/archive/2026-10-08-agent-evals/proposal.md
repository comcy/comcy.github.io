## Why

Der Prozess hängt an weichen Dingen: Skill-Texten, `AGENTS.md`, `openspec/config.yaml`. Ändert man eine davon, merkt niemand, ob sich der Agent danach noch an den Prozess hält. Die Tests prüfen unsere Werkzeuge (`gate.py`, `flow.py`), nicht das Verhalten des Agenten. Das Playbook nennt laufende Evals als größte offene Lücke der Stufe Test (#86, Teil von #11).

## What Changes

- Neu: ein Eval-Runner `evals/run.py` (Python, nur Standardbibliothek) und ein Satz Aufgaben unter `evals/tasks/`. Jede Aufgabe ist Startzustand, Auftrag und maschinelle Endzustand-Prüfung.
- Der Runner startet den Agenten headless (`claude -p`) in einem Wegwerf-Repo mit Stub-`gh`, begrenzt Modell, Budget und Rechte, und führt jede Aufgabe dreimal aus. Bestanden ab zwei von drei.
- Erster Satz mit sieben Aufgaben: Blocker offen, kein `ready-for-agent`, Secret im Commit, Commit-Nachricht und Autor, roter Test zuerst, kein `git stash`, kein Merge bei roten Checks.
- Der Runner schreibt einen kurzen Bericht `evals/reports/<datum>-<uhrzeit>.md` (Tabelle, Mermaid-Diagramm, Vergleich zum letzten Bericht, Auffälligkeiten). Berichte werden eingecheckt, Rohdaten (`evals/runs/`) sind ignoriert.
- Start manuell. Nicht in diesem Change: CI-Gate bei Änderungen an Skills und `AGENTS.md`, LLM als Bewerter (Aufgabe "vertikale Scheiben"), SDK-Runner, Maintain-Phase.

## Capabilities

### New Capabilities
- `agent-evals`: Aufgaben, Runner, Bestehensregel und Bericht für die Prüfung der Prozess-Treue des Agenten.

### Modified Capabilities
<!-- keine -->

## Impact

- Neu: `evals/` (Runner, Aufgaben, Basis-Fixture, Berichte), `.gitignore` (`evals/runs/`), Doku in `docs/workflow.md` und `docs/anleitung/05`.
- Kosten: echte Agentenläufe (Modell und Budget je Lauf einstellbar). Keine neue Abhängigkeit; `claude` muss installiert und angemeldet sein.
- Der Runner schreibt nie auf GitHub: `gh` ist ein Stub mit Schreibschutz auf sein Arbeitsverzeichnis.
