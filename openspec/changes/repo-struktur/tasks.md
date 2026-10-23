# Tasks

## 1. Inhalt und Bauwerkzeug trennen

- [ ] 1.1 Referenz-Build mit festem `SITE_URL` und Datum im Scratchpad ablegen (`public/` vor dem Umzug). Prüfung: Ordner vorhanden, `sh build.sh` läuft grün.
- [ ] 1.2 `posts/`, `pages/`, `timeline/`, `gallery/`, `site.conf` nach `content/` und `build.sh`, `templates/`, `static/`, Shell- und Browser-Tests nach `site/` verschieben (`git mv`), Pfade in `build.sh` und Tests anpassen. Prüfung: `diff -r` zwischen Referenz und neuem `public/` ist leer; `sh site/tests/run.sh` grün.
- [ ] 1.3 `deploy.yml`, `test.yml` (Job `test`) und `.gitignore` auf die neuen Pfade stellen, README (Schreiben, Timeline, Lokal ansehen) anpassen. Prüfung: PR-CI grün, Jobnamen unverändert; Pages-Deploy nach dem Merge zeigt dieselben URLs.

## 2. Konfiguration aus dem Werkzeug lösen (am Ort)

- [ ] 2.1 `tools.tsv` nach `workflow/tools.tsv`, `allow.tsv` und `commit-types.tsv` nach `workflow/gate/`, Eval-Aufgaben und -Berichte nach `workflow/evals/`; Werkzeug liest über die eine Konstante für den Konfigurationsordner. Prüfung: roter Test zuerst (`setup --check` meldet fehlende Datei in `workflow/tools.tsv`), danach `python -m unittest discover -s tests` und `flow validate` grün.
- [ ] 2.2 Specs `repo-setup` und `agent-evals`: Pfade in Tests und Beispielen aktualisieren, `flow validate` kennt die neuen Dateien. Prüfung: Test mit Beispielprojekt, das ein anderes Bauprogramm in `workflow/tools.tsv` führt, ohne Änderung im Werkzeug.
- [ ] 2.3 `.gitignore` für `workflow/evals/runs/` und `workflow/evals/tasks-derived/`. Prüfung: `git status` nach einem Eval-Lauf (`--sandbox none`, Beispiel-Adapter) zeigt keine neuen Dateien außer dem Bericht.

## 3. Werkzeug nach devflow/ verschieben

- [ ] 3.1 `scripts/`, Runner/Adapter/Stub von `evals/`, `tests/test_*.py` und Hilfsdateien nach `devflow/{scripts,evals,tests}`; allgemeine Doku nach `devflow/docs/`. Prüfung: `python devflow/scripts/flow.py validate` und alle Python-Tests grün auf Linux, macOS, Windows (CI).
- [ ] 3.2 `.githooks/*`, `setup.py` (`core.hooksPath`, Adapter), `test.yml` (Job `python`, `gates`), `evals/run.py` (`FIXTURE`, Standard-Adapter) und `AGENTS.md` auf `devflow/` umstellen. Prüfung: Commit mit ungültiger Nachricht scheitert am Hook, PR-CI zeigt `test`, `gates`, `python (ubuntu/macos/windows)`.
- [ ] 3.3 Abschlussprüfung: kein `pandoc`, `content/`, `posts/` unter `devflow/` (Ausnahme: Tests mit Beispielprojekt); Eval-Test baut das Wegwerf-Repo und führt dort `flow validate` aus. Prüfung: `grep` und Test grün.

## 4. Doku und Anschluss

- [ ] 4.1 Verweise in `docs/`, `devflow/docs/anleitung/` und `README.md` auf neue Pfade, Kapitel 04 (Konfiguration) beschreibt `workflow/` als Projektkonfiguration und `devflow/` als Werkzeug. Prüfung: Link-Check per `grep` auf alte Pfade ohne Treffer.
- [ ] 4.2 kvasir: Ticket in `comcy/kvasir` für `workflow_dir` in `kvasir.toml` und Hinweis in der Anleitung 03 (`tools.tsv`-Zeile bleibt gültig). Prüfung: `kvasir status` und `kvasir metrics --since 7d` laufen im umgebauten Repo ohne Warnung.
- [ ] 4.3 Vault-Doku (Plan, Log, Workflow, Anleitung) auf den neuen Aufbau bringen. Prüfung: Log-Eintrag vorhanden, Verweise in den Notizen stimmen.
