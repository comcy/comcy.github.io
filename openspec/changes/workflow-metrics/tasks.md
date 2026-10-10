## 1. Daten und Prüfung (Workflow-Repo, Tracer)
- [x] 1.1 `workflow/metrics.tsv` und `metric-sources.tsv` mit den fünf Metriken, `flow validate` prüft (Ids, `art`, `target`, Quellen), Tests, Doku

## 2. kvasir: Ereignismodell und erste Metrik (kvasir-Repo)
- [x] 2.1 Ereignismodell, GitHub-Übersetzung der Ticket-Ereignisse, `ticket_cycle_time`, `kvasir metrics` (text), liest `metrics.tsv`

## 3. kvasir: PR- und CI-Metriken
- [x] 3.1 `pr_duration` und `ci_red_before_merge` (GitHub)

## 4. kvasir: Nacharbeit und Eval-Quote
- [x] 4.1 `rework_fixes_per_change` und `eval_pass_rate` (`--evals`)

## 5. kvasir: Azure DevOps
- [x] 5.1 Übersetzung der Work-Item-Revisionen, PRs und Pipeline-Läufe in Ereignisse (gegen Fakes), Handprüfung dokumentiert

## 6. kvasir: Formate und Zeitraum
- [x] 6.1 `--format json|markdown`, `--since`, "zu klein", "unbekannt", `doctor`

## 7. Doku
- [x] 7.1 `docs/workflow.md`, `docs/anleitung/04` und 03 (kvasir), erster echter Bericht für dieses Repo eingecheckt
