# 5. Gates, optionale Teile, Fehlersuche

## Gates: wer prüft was, wo

Ein **Gate** ist ein Prüfpunkt, der einen Übergang verhindert, solange etwas fehlt. Die härteren stehen rechts. Jede Regel gilt für Menschen und Agenten gleich, wenn sie in Git-Hooks, CI oder Branch-Schutz liegt.

| Regel | Prosa (AGENTS.md) | Skill-Konfig | `flow`-Guard | Git-Hook | CI | Branch-Schutz |
| --- | --- | --- | --- | --- | --- | --- |
| Conventional Commits | ✓ | | | `commit-msg` | `gates` | über `gates` |
| keine Secrets | ✓ | | | `pre-commit` | `gates` | über `gates` |
| Ticket nur starten, wenn bereit und unblockiert | ✓ | | `flow start` | | | |
| Review erst bei grünen Checks | ✓ | | `flow review` | | | |
| Spec gültig | | `openspec/config.yaml` | | | (`openspec validate` manuell) | |
| Prozessdaten konsistent | | | | | `python (…)`: `flow validate` | ✓ |
| Seite baut, Tests grün | ✓ | | | | `test` | ✓ |
| Tests auf 3 Systemen | ✓ | | | | `python (…)` | ✓ |
| Merge nur bei Grün | | | | | | ✓ |
| Freigabe von Change und Tickets | ✓ | | | | | (Mensch) |

Lesehilfe:
- Der **Hook** ist frühe Rückmeldung und lässt sich mit `--no-verify` umgehen. Die **CI** (`gates`) fängt das ab (belegt mit einem Wegwerf-PR, PR #74).
- `flow start`/`flow review` stehen nicht in der CI. Sie schützen vor Fehlbedienung, nicht vor Umgehen. Wer von Hand brancht und labelt, umgeht sie. Das ist gewollt: Die Datei steuert, aber niemand wird eingesperrt.
- **Menschliche Gates** (Freigabe des Changes, der Tickets, Merge außerhalb eines erteilten Umfangs) hat kein Werkzeug. Sie hängen an der Vereinbarung.

## Optionale und noch fehlende Teile

| Teil | Status | Hinweis |
| --- | --- | --- |
| kvasir | optional, empfohlen | reine Sicht, nichts hängt davon ab |
| Agent und Skills | optional | jeder Schritt geht von Hand; die Skills sind Abkürzungen mit festen Ein- und Ausgängen |
| Phase 4b Abnahme | optional (`level=optional`) | Draft-PR, Screenshots, Prüfliste; Entwurf in PR #23 / Ticket #22 |
| `/wayfinder` | optional | nur bei sehr großen Vorhaben (mehr als eine Session) |
| `--labels` bei `setup` | optional | schreibt auf GitHub, einmal je Repo |
| `kvasir.toml` | optional | nur für geteilte Überschreibungen |
| Evals: Prozess-Treue des Agenten (Runner `evals/run.py`, sieben Aufgaben, Bericht mit Diagramm) | **gebaut, erster echter Lauf 2026-10-08** | 6 von 7 bestanden, eine Lücke in `AGENTS.md` gefunden und geschlossen; kein CI-Gate (manueller Start), mehr Läufe und Aufgaben später |
| Maintain-Phase (Monitoring, wiederkehrende Scans) | **fehlt** | Ticket #60, als optionale generische Phase geplant |
| Metriken (Durchlaufzeit, Nacharbeit, rote CI vor Merge) | **fehlt** | Daten vorhanden (Label-Zeitstempel, PRs), keine Auswertung |
| Protokoll der Skill-Aufrufe und `gh`-Schreibzugriffe | **fehlt** | Teil von Ticket #11 (Nachvollziehbarkeit) |
| Orchestrierung (LangGraph, Agent SDK) | bewusst vertagt | erst bei unbeaufsichtigtem Betrieb sinnvoll |

## Typische Probleme

Alle aus echtem Betrieb dieses Repos.

| Symptom | Ursache | Lösung |
| --- | --- | --- |
| `setup --check`: `FEHLT core.hooksPath` | Hooks sind im Klon nicht aktiv | `python3 scripts/setup.py` |
| Commit abgelehnt: `verletzt die Regel type(scope)!: Betreff` | Nachricht ohne Typ | `feat(bereich): Betreff`, erlaubte Typen in `commit-types.tsv` |
| Commit abgelehnt: `Regel github-token (mögliches Secret…)` | Muster getroffen, der Wert wird nie ausgegeben | Wert entfernen; Fehlalarm → Zeile mit Grund in `allow.tsv` |
| `flow start`: `Bedingung label:ready-for-agent ist nicht erfüllt` | Ticket ist nicht bereit (oder Blocker offen) | triagieren (`/triage`) bzw. Blocker abwarten; `--dry-run` zeigt es ohne Änderung |
| `flow review` bricht ab | PR fehlt oder Checks noch nicht grün | PR anlegen, CI abwarten |
| kvasir: `! Label sagt in-progress, Issue ist geschlossen` | Status-Label nach dem Merge nicht entfernt | seit `close-labels.yml` automatisch beim Schließen; ältere Fälle von Hand: `gh issue edit N --remove-label status:in-progress` (Liste: `gh issue list --state closed --label status:in-progress`) |
| `gh pr merge` direkt nach `git push`: `Pull Request is not mergeable` | GitHub berechnet die Mergbarkeit noch | einige Sekunden warten, erneut versuchen |
| Windows-CI rot, lokal grün, `UnicodeDecodeError` | Ausgabe auf stderr in Konsolenkodierung statt UTF-8 | `proc.utf8_output()` stellt stdout **und** stderr um (behoben mit PR #78) |
| Zwei Agenten tauschen sich gegenseitig die Änderungen | `git stash` ist über alle Worktrees geteilt | in parallelen Worktrees nie `git stash`; Baseline-Läufe in einem eigenen Worktree |
| Ein CI-Lauf hängt, nach Neustart grün | unklar (Einzelfall, 16 Minuten) | Lauf abbrechen und neu starten; wiederholt sich das, Log lesen |
| Test schreibt ins echte Repo | Stub oder Prozess lief mit falschem Arbeitsordner | Tests laufen in Wegwerf-Repos, Stubs schreiben nur unter `STUB_ROOT`, `openspec` mit `cwd=<Repo>` |
| `openspec validate --specs` meldet `Purpose … TBD` | neue Capability archiviert, Purpose nicht ausgefüllt | `## Purpose` in `openspec/specs/<name>/spec.md` schreiben |
| `__pycache__` im Commit | fehlt in `.gitignore` | eingetragen; vor dem Commit `git status` lesen |

## Checkliste für neue Personen

1. `git`, `gh` (`gh auth login`), Python ≥ 3.11, Node ≥ 20.19, `openspec`, `pandoc` installieren.
2. Klonen. Optional im **Bare-Layout** mit kvasir (`kvasir setup <url>`), damit parallele Tickets getrennte Ordner haben.
3. `python3 scripts/setup.py --check`, dann `python3 scripts/setup.py <agent>` (Hooks, Adapter).
4. `python3 scripts/flow.py validate --strict` → `0 Fehler, 0 Warnungen`.
5. `sh tests/run.sh` → grün.
6. Git-Identität: `git config user.email christian.silfang@gmail.com` (bzw. die eigene Adresse), Autor der Commits.
7. Dokumente lesen: `docs/workflow.md` (Referenz), diese Anleitung (Ablauf), `docs/agents/*` (Regeln für Agenten).
8. Ein kleines Ticket nach Kapitel 2 durchspielen, bevor ein großes Feature beginnt.

## Varianten

| Variante | Was sich ändert |
| --- | --- |
| Ohne Agent | Skills durch Checklisten ersetzen: Fragen von Hand, `openspec` direkt, Tickets mit `gh`; Gates bleiben |
| Ohne OpenSpec bei Kleinigkeiten | Reiner Bugfix ohne Verhaltensänderung: `diagnosing-bugs` + `tdd` + Issue, kein Change (unter etwa einem Ticket lohnt der Change nicht) |
| Mehrere Personen | Branch-Schutz mit Pflichtreview ergänzen (`required_pull_request_reviews`), `ready-for-human` aktiv nutzen, `CODEOWNERS` |
| Anderes Repo | Teil A (generisch) übernehmen; Teil B (hier: pandoc, Seitenbau) ersetzen; `workflow/*.tsv`, `tools.tsv`, `gate.d/` anpassen |
| Azure DevOps statt GitHub | `kvasir status`/`graph`-Teile für Azure vorhanden (ungeprüft gegen ein echtes Repo); `gh`-gebundene Teile von `flow` und `setup --labels` sind GitHub-only |
| Nur lokal, ohne Tracker | Issue durch eine kurze `intent.md` ersetzen (Ziel, Grenzen, Abnahme); `flow` und kvasir brauchen einen Tracker |

## Weiterführend

- Referenz mit allen Regeln und Spalten: [../workflow.md](../workflow.md)
- Abgleich mit dem Anthropic-Playbook (Lücken, Messwerte): [../playbook-abgleich.md](../playbook-abgleich.md)
- Spezifikationen des Werkzeugs: `openspec/specs/{workflow-definition,repo-setup,commit-gates,flow-transitions}`
- Pläne und Entscheidungen: `docs/plans/`
