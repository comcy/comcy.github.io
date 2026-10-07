# Abgleich mit dem AI-native SDLC Playbook

Quelle: https://claude.com/blog/the-ai-native-sdlc-playbook (gelesen 2026-10-07). Vergleich mit `docs/workflow.md`. Ticket #45.

**Maßstab ist der generische Workflow (Teil A), nicht dieses Repo.** Eine Stufe fällt nicht weg, weil die Blog-Seite sie nicht braucht. Teil A soll jede Stufe abdecken (Phase, Skill oder Ablauf); ob ein Projekt sie aktiviert, entscheidet Teil B bzw. die `enabled`-Spalte in `workflow/*.tsv`.

## Stufen

| Playbook | Artefakt dort | Bei uns | Status |
| --- | --- | --- | --- |
| Plan | `intent.md` | Issue + Grilling-Zusammenfassung (`/grilling`, `/to-tickets`) | OK, anderes Format |
| Design | `spec.md` | OpenSpec-Change (proposal, specs, design) | OK |
| Build | `plan.md`, CLAUDE.md, Skills, Hooks, Worktrees, Subagents | `tasks.md` + Tickets mit `blocked_by`, `AGENTS.md`, `.agents/skills/`, `/implement`, Worktrees, Agents | OK, Hooks fehlen (#11) |
| Test | Feedback-Loops, laufende Evals | TDD an äußeren Nähten, `tests/run.sh`, CI inkl. 3-OS-Matrix, Abnahme-Gate lokal | Evals fehlen |
| Deploy | AI-PR-Review mit `REVIEW.md`, Hooks als Gates, Managed Settings, CI/CD-Stufen | `/code-review` (Standards + Spec), Branch Protection (Check `test`), `deploy.yml` test → build → deploy | OK; Review-Kriterien nicht in eigener Datei |
| Maintain | Monitoring-Bänder, wiederkehrende Scans, On-Call | keine Phase, kein Skill | Lücke im generischen Ablauf; in diesem Repo nicht aktiviert |

## Menschliche Gates

| Playbook | Bei uns |
| --- | --- |
| PO gibt Intent/Spec frei | Chris beantwortet Grilling, gibt Change frei (Phase 1) |
| Engineer gibt Plan frei | Ticketliste vor Anlage (`/to-tickets`) |
| Code Owner gibt PR frei | Merge nur im ausdrücklich erteilten Umfang, sonst Chris |

## Bewusste Abweichungen

- **Source of Truth:** GitHub Issues + Repo (OpenSpec, `workflow/*.tsv`). Kein zweites System. Entspricht der Playbook-Empfehlung "ein System benennen".
- **Audit Trail:** Kette aus Issue → Change → PR → Archiv, alles committet bzw. verlinkt.
- **`AGENTS.md` kurz:** Details in `docs/`, nicht im Einstiegsfile.

## Lücken

| Lücke | Playbook | Plan |
| --- | --- | --- |
| Hooks als Gates (Secret-Scan, Commit-Lint, Freigabe) | Deploy | #11 |
| Evals (20–50 Aufgaben, Gate bei Änderung an Skills/Hooks/AGENTS.md, Incident → Eval) | Test | #11 |
| Metriken (Durchlaufzeit, Nacharbeit, Fehlerquote) | Metriken je Play | #28, Daten aus Label-Zeitstempeln |
| Maintain als generische Phase (Monitoring, wiederkehrende Scans, Incident → Ticket/Eval) | Maintain | neue Phase in `phases.tsv` (optional, `enabled` je Projekt), Skill/Ablauf dazu; Ticket anlegen. Hier standardmäßig aus (statische Seite), der Mechanismus muss trotzdem existieren |
| `REVIEW.md` | Deploy | prüfen: reicht `/code-review` mit Verweis auf AGENTS.md/Teststrategie? |

## Erste Messwerte (Stand 2026-10-07)

Aus `gh`, nur grob:

- 29 gemergte PRs.
- `test.yml`: 16 grün, 3 rot, 1 abgebrochen.
- `deploy.yml`: 29 grün, 1 abgebrochen.
- PRs mit Nacharbeit nach dem ersten Push (mehr als 1 Commit): #53, #58 von 13 geprüften.
- Durchlaufzeit PR → Merge der letzten acht (#53–#58, #46, #44): Median unter 5 Minuten, Ausreißer #44 (86 Min., Nutzerfreigabe).

Zeigt: Leading-Indikator "rote CI vor Merge" ist messbar, ohne neue Technik. Systematisch erst mit #28.

## Optional: `intent.md`

Idee: lokale Arbeit ohne Tracker beginnt mit einer kurzen `intent.md` (Ziel, Grenzen, Abnahme). Mit Tracker ersetzt das Issue sie. Nicht einführen, solange jede Arbeit ein Issue hat. Wieder aufgreifen, falls Arbeit ohne GitHub-Anbindung dazukommt.

## Reihenfolge

Plan/Design/Build/Test/Deploy-Review sind abgedeckt. Nächster Schritt mit größtem Hebel: Hooks + Evals (#11), danach Metriken (#28), dann Maintain als optionale generische Phase.
