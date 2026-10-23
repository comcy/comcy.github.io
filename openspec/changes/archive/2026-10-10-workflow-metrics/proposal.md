## Why

Der Prozess ist beschrieben, erzwungen und geprüft, aber ob er etwas bringt, misst niemand. Das Playbook verlangt je Stufe vorlaufende und nachlaufende Kennzahlen. Die Daten liegen schon vor (Label-Ereignisse, PRs, CI-Läufe, Eval-Berichte), werden aber nicht ausgewertet. Außerdem soll der Prozess nicht nur auf GitHub, sondern auch auf Azure DevOps laufen.

## What Changes

- Neu: `workflow/metrics.tsv` beschreibt die Metriken als Daten (`id`, `art` vorlaufend oder nachlaufend, `name`, `einheit`, `quelle`, optional `ziel`, optional `enabled`) und `workflow/metric-sources.tsv` das feste Vokabular der Quellen. `flow validate` prüft beide (Spalten, eindeutige Ids, bekannte Quellen, Werte).
- Erste Quellen und Metriken: Durchlaufzeit je Ticket, PR-Dauer, rote CI vor Merge (Anteil), Nacharbeit (Fix-PRs je Change), Eval-Bestehensquote.
- Die Berechnung liegt in kvasir (`kvasir metrics`, rein lesend, `--since`, `--format text|json|markdown`) auf einem **providerneutralen Ereignismodell** (Item, Art, Zeitpunkt). Je Provider eine Übersetzung: GitHub (Timeline, PRs, Läufe) und Azure DevOps (Work-Item-Revisionen mit Zustand und Tags, PRs, Pipeline-Läufe). Die Eval-Quote liest `evals/reports/`.
- Nicht in diesem Change: Warnungen bei Überschreitung von `ziel` (nur die Spalte ist vorgesehen), Dashboard, Berechnung außerhalb von kvasir, weitere Metriken (z. B. Review-Funde je Change).

## Capabilities

### New Capabilities
- `workflow-metrics`: Metriken als Daten (`metrics.tsv`, `metric-sources.tsv`) und der Bericht, den kvasir daraus erzeugt.

### Modified Capabilities
- `workflow-definition`: `flow validate` kennt die neuen Dateien.

## Impact

- Workflow-Repo: `workflow/metrics.tsv`, `workflow/metric-sources.tsv`, Erweiterung von `scripts/lib/workflow.py` und `flow validate`, Doku (`docs/workflow.md`, `docs/anleitung`).
- kvasir-Repo (eigene Tickets): Ereignismodell, GitHub- und Azure-Übersetzung, `kvasir metrics`.
- Keine neue Abhängigkeit. Azure ist nur gegen Fakes testbar, die echte Prüfung geschieht von Hand.
