## Context

Die Werkzeuge des Prozesses (`flow`, `gate`, `setup`) sind getestet. Ungeprüft ist, ob ein Agent sie einhält. Vorfälle aus dem Betrieb (Stash-Tausch zwischen Worktrees, Stub schrieb ins echte Repo, Merge-Versuch vor Berechnung der Mergbarkeit) zeigen, dass Prosa nicht reicht. `claude -p` (headless) mit `--max-budget-usd`, `--model`, `--allowedTools`, `--permission-mode` und `--output-format stream-json` ist verfügbar.

## Goals / Non-Goals

- Goals: Prozess-Treue deterministisch am Endzustand prüfen; planbare Kosten; ein kurzer, verständlicher Bericht; Aufgabe und Prüfung als Daten, damit der Agentenstart austauschbar bleibt (später SDK).
- Non-Goals: Bewertung von Texten durch ein Modell, CI-Gate, Leistungsvergleich zwischen Modellen.

## Decisions

- **Aufgabe als Ordner** `evals/tasks/<id>/`: `prompt.md` (Auftrag), `state.json` (Zustand des `gh`-Stubs: Issues, Labels, Blocker, Checks), optional `files/` (Zusatzdateien im Wegwerf-Repo), `check.py` (Funktion `check(ctx) -> list[str]`, leere Liste = bestanden). `ctx` enthält Repo-Pfad, Stub-Protokoll und den Mitschnitt der Tool-Aufrufe. Keine Prüfung bewertet Wortlaut.
- **Basis-Fixture** `evals/fixture/`: Kopie der relevanten Teile des Repos zum geprüften Stand (`AGENTS.md`, `docs/agents/`, `workflow/`, `scripts/`, `.githooks/`, `openspec/config.yaml`, `.agents/skills/`). Der Runner baut sie bei jedem Lauf frisch aus dem **aktuellen Arbeitsstand**, damit Änderungen an Skills und `AGENTS.md` geprüft werden und die Fixture nicht veraltet.
- **Runner** `evals/run.py [aufgabe …] [--runs 3] [--model M] [--budget USD]`: je Lauf Temp-Verzeichnis, `git init`, Fixture kopieren, Stub-`gh` (Wiederverwendung von `tests/stubs.py`) vor den PATH, `claude -p` mit Auftrag. Das Starten des Agenten steht in einer Funktion `starte_agent(...)`, damit ein SDK-Runner sie ersetzen kann.
- **Mitschnitt**: `--output-format stream-json`, Tool-Aufrufe werden geparst. Damit prüft Aufgabe 6 (kein `git stash`) und die Reihenfolge roter Test vor Fix (Aufgabe 5 zusätzlich aus der Git-History).
- **Bestehensregel**: drei Läufe, bestanden ab zwei von drei. Der Bericht zeigt `3/3`, `2/3` usw.
- **Bericht**: `evals/reports/<datum>-<uhrzeit>.md`: Kopf (Commit, Modell, Läufe, Kosten, Dauer), Tabelle je Aufgabe (Läufe, Ergebnis, Kosten, erste fehlgeschlagene Prüfung), Mermaid-Balkendiagramm der Bestehensquote, Vergleich zum letzten Bericht (neu rot, neu grün), Auffälligkeiten aus den Fehlschlägen. Rohdaten nach `evals/runs/<lauf>/` (ignoriert). Vor dem Schreiben läuft `gate.py secrets` über den Bericht.
- **Sicherheit**: Der Agent arbeitet nur im Wegwerf-Verzeichnis; `gh` ist ein Stub mit Schreibschutz (`STUB_ROOT`), kein Netz außer dem Modellzugriff; Rechte über `--allowedTools` und `--permission-mode` begrenzt; `--max-budget-usd` je Lauf.
- **Start**: manuell. Ein späteres Gate (Pfade `.agents/`, `AGENTS.md`, `openspec/config.yaml`, `workflow/`, `.githooks/`) setzt einen stabilen Satz voraus (zwei Wochen) und ist ein eigener Change.

## Risks / Trade-offs

- Nicht deterministisch: drei Läufe mit Schwelle glätten, aber Ausreißer bleiben; der Bericht zeigt Instabilität.
- Kosten wachsen mit Aufgaben mal Läufe: Budget je Lauf und `--runs` einstellbar, Standard klein.
- Die Fixture kann vom echten Repo abweichen: sie wird aus dem Arbeitsstand erzeugt, nicht gepflegt.
- Aufgaben prüfen nur, was Werkzeuge beobachten können; Stilfragen bleiben Review.

## Open Questions

- Welches Modell als Standard? Vorschlag: das, mit dem gearbeitet wird, per `--model` überschreibbar.
