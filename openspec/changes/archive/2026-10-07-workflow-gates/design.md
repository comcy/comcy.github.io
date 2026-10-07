## Context

`setup.py` und `flow.py` sind Python (≥ 3.11, nur Standardbibliothek) und laufen in CI auf drei Systemen. Der Prozess ist als Daten in `workflow/*.tsv` beschrieben.

## Goals / Non-Goals

- Goals: deterministische Prüfungen mit einer Logik für Hook und CI; plattformneutral; keine neue Abhängigkeit.
- Non-Goals: perfekter Secret-Scanner (Allowlist statt Vollständigkeit), Evals, Orchestrierung.

## Decisions

- **Logik in Python, Hooks als Hülle.** `.githooks/*` sind drei Zeilen `sh`, die `python scripts/gate.py <check>` aufrufen (Git für Windows führt `sh`-Hooks aus). Alternative POSIX-`sh`-Logik verworfen: auf Windows-Runnern und in Tests unzuverlässig, widerspricht der Python-Linie von `setup`/`flow`.
- **Eine Logik, zwei Aufrufer.** CI ruft dieselben Befehle mit Bereichen auf (`gate.py commits <base>..<head>`, `gate.py secrets --range <base>..<head>`). Der Hook ist nur frühe Rückmeldung; die CI ist die verbindliche Stelle.
- **Secret-Scan:** Regelliste aus Mustern (private Schlüssel, bekannte Token-Präfixe, `KEY=`/`PASSWORD=`-Zuweisungen mit Wert, verbotene Dateinamen wie `.env`) in `scripts/gate.d/secrets.tsv`; Ausnahmen in `scripts/gate.d/allow.tsv` (Pfad + Muster + Grund). Es prüft nur hinzugefügte Zeilen. gitleaks ist nicht nötig.
- **Commit-Lint:** `type(scope)!: Betreff` mit den Typen aus einer Liste in `scripts/gate.d/`; Merge-Commits und `Revert` sind erlaubt. Die Autor-Mail wird nicht geprüft (Repo-Konfiguration, nicht Commit-Format).
- **Zustandswechsel:** `flow start <issue>` liest Titel per `gh`, legt `feature/<id>-<slug>` an, setzt das Label gemäß `transitions.tsv` (nur erlaubte Übergänge). `flow review` analog. `--dry-run` zeigt die Schritte; ohne `gh` oder Remote klare Fehlermeldung.
- **Branch-Schutz** wird nicht von Skripten verändert; Hinweis in `setup --check`.

## Risks / Trade-offs

- Muster erzeugen Fehlalarme → Allowlist mit Begründung statt Hook umgehen (`--no-verify` bleibt möglich, die CI fängt es).
- `sh`-Hüllen brauchen `python` im PATH → `setup --check` meldet das.

## Open Questions

- Soll `flow start/review` auch Draft-PRs anlegen? Vorschlag: nein, zunächst nur Branch und Label.
