## Why

Der Prozess ist als Daten beschrieben (`workflow/*.tsv`: Zustände, Übergänge, Phasen, Detektoren), aber nicht, **welche Skills** eine Phase braucht, **welche Rolle** sie ausführt und **was erlaubt** ist. Wer das Repo auf einem anderen Rechner, mit einem anderen Agenten oder Modell nutzt, erfährt erst im Betrieb, dass ein Skill fehlt. Die Evals sind an `claude -p` und diesen Rechner gebunden und entstehen von Hand, ohne Zusammenhang zur Konfiguration.

## What Changes

- Neu: `workflow/skills.tsv` (Skills je Phase mit Pflicht oder optional, Quelle, Installationshinweis) und `workflow/roles.tsv` (Rollen mit Phasen, erlaubten Tools und menschlichem Gate).
- `setup --check` prüft die Skills je Phase gegen die Orte des Agenten (`skill_paths` in `scripts/setup.d/agents.tsv`; Standard: `.agents/skills/` im Repo, `~/.agents/skills/` und die Orte von Claude Code). Fehler nur bei Phasen mit `level=required`, sonst Hinweis. Agenten ohne bekannte Orte: "nicht prüfbar" mit Liste der benötigten Skills.
- `flow validate` prüft die Abdeckung: jede Phase hat eine Rolle, jede Rolle eine Phase, jede `required`-Phase mindestens einen Skill oder ausdrücklich "von Hand".
- Evals: Der Agentenstart wird ein **Adapter** (externes Programm, JSON über stdin und stdout, normalisierter Mitschnitt). `claude -p` wird der erste Adapter. Liefert ein Adapter keine Tool-Aufrufe, sind die betroffenen Aufgaben "nicht prüfbar", kein Fehler.
- Die erlaubten Tools der Rolle steuern `--allowedTools` im Eval-Lauf.
- Aus `transitions.tsv` werden Konformitäts-Aufgaben abgeleitet ("Übergang bei verletzter Bedingung muss abbrechen"), soweit der Stub-`gh` den Zustand abbilden kann. Der Rest erscheint im Bericht als "nicht ableitbar".
- Nicht in diesem Change: Durchsetzung der Rollen im Alltag (Agent-Hooks, Berechtigungsdateien), Skill-Orte weiterer Agenten über die Einträge in `agents.tsv` hinaus, Sandbox (#103).

## Capabilities

### New Capabilities
- `workflow-profile`: Skills und Rollen als Konfiguration (`skills.tsv`, `roles.tsv`) samt Abdeckungsprüfung.

### Modified Capabilities
- `workflow-definition`: `flow validate` kennt die neuen Dateien.
- `repo-setup`: `setup --check` prüft Skills je Phase.
- `agent-evals`: Adapter-Vertrag, abgeleitete Aufgaben, Werkzeuge der Rolle.

## Impact

- Neu: `workflow/skills.tsv`, `workflow/roles.tsv`, Spalte `skill_paths` in `agents.tsv`, `evals/adapters/` (`claude.py`), Ableitung in `evals/`, Erweiterungen in `scripts/flow.py`, `scripts/setup.py`, `scripts/lib/`.
- Doku: `docs/workflow.md`, `docs/anleitung/04`, Landkarte.
- Ein Profil (`workflow/` plus `evals/` plus Adapter) ist als Ganzes in ein anderes Repo oder auf einen anderen Rechner übertragbar.
- Keine neue Abhängigkeit.
