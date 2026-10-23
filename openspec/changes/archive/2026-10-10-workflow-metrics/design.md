## Context

kvasir hat schon die Trennung nach Providern (GitHub über `gh`, Azure DevOps über `az`) für `status`, `graph` und den Stepper und liest `workflow/*.tsv` (Phasen, Detektoren). Metriken brauchen Zeitpunkte, die diese Funktionen bisher nicht liefern: Zustandswechsel, PR-Zeiten, CI-Ergebnisse.

## Goals / Non-Goals

- Goals: aus Fakten rechnen, nichts erfinden; GitHub und Azure DevOps gleich behandeln; Definition als Daten im Workflow-Repo; Ausgabe, die ein Mensch und ein Skript lesen können.
- Non-Goals: Warnungen, Dashboards, Metriken aus Modellbewertung.

## Decisions

- **`metrics.tsv`** (Kopfzeile, Spalten nach Namen, `#` Kommentare, `enabled`): `id`, `art` (`leading|lagging`), `name`, `unit` (`h`, `d`, `%`, `n`), `source` (Name aus `metric-sources.tsv`), `target` (optional, Zahl). **`metric-sources.tsv`**: `name`, `arg`, `description`; eine Quelle wird in kvasir ausgewertet, die Datei enthält nie Code (wie `detectors.tsv`). Ein Name, den kvasir nicht kennt, erscheint im Bericht als "unbekannt", `doctor` meldet ihn.
- **Quellen (erste Fassung)**: `ticket_cycle_time` (erstes Ereignis `in_arbeit` bis `geschlossen`, Median und Anzahl), `pr_duration` (`pr_erstellt` bis `pr_gemergt`, Median), `ci_red_before_merge` (Anteil der PRs mit mindestens einem roten Lauf vor dem Merge), `rework_fixes_per_change` (Fix-PRs `fix(...)` mit Bezug auf dasselbe Feature-Issue je Feature, Mittel), `eval_pass_rate` (Bestehensquote der letzten Berichte aus `--evals <pfad>`, Standard `evals/reports/`).
- **Neutrales Ereignismodell** in kvasir: `Event(item, art, zeit)` mit Arten `in_arbeit`, `in_review`, `geschlossen`, `pr_erstellt`, `pr_gemergt`, `ci_rot`, `ci_gruen`. Metriken rechnen nur darauf.
- **Provider**: Methode `events(zeitraum)` je Provider. GitHub: `gh api .../issues/N/timeline` (Label-Ereignisse `labeled` mit `status:in-progress`, `closed`), PRs (`created_at`, `merged_at`), Läufe (`gh run list`). Azure DevOps: Revisionen des Work Items (`System.State`, `System.Tags` mit Zeitstempel; unser Status liegt in Tags), PRs und Pipeline-Läufe (`az repos pr list`, `az pipelines runs list`). Welche Tag-Namen "in Arbeit" bedeuten, steht wie bei den Labels in `workflow/states.tsv`.
- **Ausgabe**: `kvasir metrics [--since 30d] [--repo ...] [--format text|json|markdown] [--evals PFAD]`; je Metrik Wert, Einheit, Stichprobengröße, Ziel (falls gesetzt); zu kleine Stichproben (n < 3) werden als solche gekennzeichnet statt als Wert gezeigt.
- **Nichts erfinden**: Fehlt eine Quelle (z. B. keine Berichte, kein CI), steht "keine Daten" statt 0.

## Risks / Trade-offs

- Ein Ein-Personen-Repo liefert kleine Stichproben: der Bericht zeigt n und warnt, Trends sind nur grob.
- ADO ist gegen Fakes getestet, nicht gegen eine echte Organisation; die Form der Revisionen muss einmal von Hand geprüft werden.
- Nacharbeit über Titel und Bezug ist eine Heuristik (Konvention `fix(...)`, `Refs #N` auf dasselbe Feature).

## Open Questions

- Soll `ziel` später Warnungen erzeugen (eigener Change)?
