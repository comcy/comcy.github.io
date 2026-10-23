## Context

`flow validate` liest `workflow/*.tsv` (Spalten nach Namen, Kopfzeile, `enabled`). `setup --check` liest `tools.tsv` und `agents.tsv`. Die Evals rufen `claude` in `starte_agent` auf, der Mitschnitt kommt aus `stream-json`. Ein erster echter Lauf (6 von 7) zeigte, dass der Abgleich von Konfiguration und Agent-Verhalten Lücken findet.

## Goals / Non-Goals

- Goals: fehlende Skills vor dem Betrieb sichtbar machen; Rollen und Phasen als Daten; Evals auf anderen Rechnern, Agenten und Modellen gegen dieselbe Konfiguration; abgeleitete Aufgaben, damit Konfiguration und Prüfung nicht auseinanderlaufen.
- Non-Goals: Rollen im Alltag erzwingen; Skills transportieren (agentenspezifisch); weitere Agenten raten.

## Decisions

- **`skills.tsv`**: Spalten `skill`, `phase`, `level` (`required|optional`, Standard: `level` der Phase), `source` (Anzeige, z. B. `plugin mattpocock-skills`), `hint` (Installationsbefehl), `manual` (`yes` = Phase darf ohne Skill von Hand laufen). Mehrere Zeilen je Phase erlaubt. Eine Phase ohne Zeile und ohne `manual` ist unbedeckt.
- **`roles.tsv`**: Spalten `role`, `phases` (Komma), `allowed_tools`, `human_gate` (`yes|no`: Mensch muss freigeben, bevor die nächste Phase beginnt), `description`. Rollen sind Beschreibung und Prüfobjekt; Durchsetzung bleibt weich (`AGENTS.md`, Skill).
- **Skill-Prüfung in `setup --check`**: Für jeden gewählten Agenten (`agents.tsv`, Spalte `skill_paths`, durch `;` getrennt, `~` wird aufgelöst) wird je Skill `<pfad>/<skill>/SKILL.md` gesucht, für Plugins zusätzlich `**/skills/<skill>/SKILL.md` unter dem angegebenen Plugin-Cache. Gefunden: `ok`. Nicht gefunden: `FEHLT` (Phase `required`, Skill `required`) oder `HINWEIS`. Agent ohne `skill_paths`: `nicht prüfbar`, mit Liste. Orte werden aus der Datei gelesen, nie geraten.
- **Abdeckung in `flow validate`**: Fehler, wenn eine `required`-Phase weder Skill noch `manual` hat oder keine Rolle; Warnung für Rollen ohne Phase und für Skills, deren Phase fehlt oder `enabled=no` ist.
- **Adapter-Vertrag**: `evals/run.py --adapter <programm>` (Standard: `evals/adapters/claude.py`). Eingabe JSON über stdin: `prompt`, `cwd`, `env`, `model`, `budget_usd`, `allowed_tools`, `timeout_s`. Ausgabe JSON über stdout: `tool_calls` (Liste aus `name`, `input`), `result_text`, `cost_usd`, `duration_ms`, `error`. Fehlt `tool_calls` (Feld nicht vorhanden), sind Aufgaben, die sie brauchen, im Bericht "nicht prüfbar". Exit-Code des Adapters ungleich 0 ist ein Lauffehler (Bericht: Fehler beim Lauf, nicht "durchgefallen"). `starte_agent` ruft den Adapter auf; Aufgaben und Berichte bleiben unverändert.
- **Werkzeuge der Rolle**: Der Runner übergibt `allowed_tools` der Rolle der Aufgabe (Spalte `role` in `task.json`, Standard `builder`) an den Adapter.
- **Abgeleitete Aufgaben**: `evals/derive.py` erzeugt je Übergang mit `guard` aus `transitions.tsv` und je Detektor, den der Stub abbildet (`label`, `no_open_blockers`, `checks`, `issue_open`, `issue_closed`, `subissues_exist`, `has_label_kind`), eine Aufgabe im Ordner `evals/tasks-derived/` (nicht eingecheckt, bei jedem Lauf frisch). Prüfung: kein Branch, kein Label-Wechsel, kein schreibender `gh`-Aufruf (`issue edit/close/reopen`, `pr merge/ready`, `api`). Andere Detektoren: Bericht-Abschnitt "nicht ableitbar".
- **Reihenfolge der Umsetzung** (vertikale Scheiben): Dateien und Prüfung; Skill-Prüfung im Setup; Adapter-Vertrag; Rollen steuern Tools; Ableitung; Doku und Probelauf mit zweitem Adapter-Trockenlauf.

## Risks / Trade-offs

- Skill-Orte anderer Agenten sind Annahmen des Nutzers (geteilte Pfade); die Spalte `skill_paths` macht sie überprüfbar und änderbar.
- Ein Adapter für ein lokales Modell ist ungeprüft (Tool-Aufrufe, Format); der Vertrag fängt das mit "nicht prüfbar" ab.
- Abgeleitete Aufgaben sind nur so gut wie der Stub; der Bericht nennt, was nicht ableitbar ist.

## Open Questions

- Soll ein Skill mehrere Phasen bedienen können (Zeile je Phase) oder mit einer Liste? Vorschlag: Zeile je Phase.
