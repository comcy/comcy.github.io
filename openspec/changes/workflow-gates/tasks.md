## 1. Commit-Lint (vertikale Scheibe)
- [x] 1.1 `gate commits <bereich>` plus Hook `commit-msg`, Tests am Prozessaufruf, Doku in `docs/workflow.md`

## 2. Secret-Scan
- [x] 2.1 `gate secrets` (Index und Bereich) plus Hook `pre-commit`, Regelliste, Allowlist, Tests (kein Wert in der Ausgabe), Doku

## 3. CI-Job
- [ ] 3.1 Job `gates` in `test.yml` (Commits und Diff des PR), Hinweis zum Branch-Schutz an Repo-Eigner

## 4. Setup-Prüfung
- [ ] 4.1 `setup --check` meldet inaktive Hooks bzw. fehlendes `python`, Tests

## 5. Zustandswechsel
- [ ] 5.1 `flow start <issue>` mit `--dry-run`, Tests mit `gh`-Stub
- [x] 5.2 `flow review` mit erlaubten Übergängen, Tests
