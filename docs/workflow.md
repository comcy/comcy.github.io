# Entwicklungs-Workflow (v0)

Stand: 2026-10-04. **v0, noch nicht an einem echten Change erprobt.** Wird nach dem ersten Change (Timeline) korrigiert. Gedacht als Vorlage: Teil A ist projektunabhängig und soll später in ein eigenes Entwickler-Repo (Setup-Skript wie `setup-matt-pocock-skills`) wandern, Teil B sind die Eigenheiten dieses Repos.

## Teil A: Generischer Ablauf

![Workflow-Modell: Ablauf, ersetzte Skills, Erweiterungspunkte](workflow.svg)

Leitidee: **OpenSpec hält fest, *was* gelten soll (Anforderungen als Specs). Issues, TDD und Review erledigen *das Bauen*.** Zwei Quellen der Wahrheit vermeiden: Specs beschreiben Verhalten, Issues beschreiben Arbeit.

| Phase | Werkzeug | Ergebnis |
| --- | --- | --- |
| 0. Eingang | Issue anlegen, `/triage` | Label-Zustand (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) |
| 1. Idee schärfen | `/grilling` oder `/opsx:explore` | Entscheidungen, Rest-Fragen |
| 2. Anforderungen festhalten | `/opsx:propose <name>` | `openspec/changes/<name>/`: proposal, Delta-Specs, design, tasks |
| 3. Arbeit schneiden | `/to-tickets` aus dem Change | Tracer-Bullet-Tickets mit Blockern auf GitHub |
| 4. Bauen und prüfen | `/implement` je Ticket (treibt `tdd`, endet mit `code-review`) | Code + Tests, ein PR je Ticket, `tasks.md` abhaken |
| 5. Abschließen | `/opsx:archive` | Delta-Specs fließen in `openspec/specs/` |
| 6. Festhalten | Projektlog (Vault) | Entscheidungen, Stolpersteine |

Rollen der Skills: **OpenSpec ist die Spec** (Verhalten, dauerhaft in `openspec/specs/`). `/to-spec` wird deshalb **nicht** benutzt, es würde eine zweite Spec als Issue anlegen. `/to-tickets` ist das Bindeglied: Es schneidet den Change in Arbeit, die Issues referenzieren den Change-Namen.

Regeln:
- Ändert sich ein Verhalten während des Bauens, zuerst den Change aktualisieren (`/opsx:update`), dann Code. Sonst driftet die Spec.
- `/opsx:propose` plant nur und stoppt. Bauen startet immer eine neue, ausdrückliche Anfrage.
- Bei sehr großem Vorhaben (mehr als eine Session) vorher `/wayfinder`: Karte aus Entscheidungs-Tickets, danach je Entscheidung ein Change.
- Unsicher, welcher Skill passt: `/ask-matt`.
- Reiner Bugfix ohne Verhaltensänderung braucht keinen Change: `diagnosing-bugs` + `tdd` + Issue.
- Commits: Conventional Commits, Autor aus der globalen Konfiguration, Secret-Scan vor dem Staging.

### Setup-Checkliste (Basis für ein späteres Skript)

1. Git-Repo, Remote auf GitHub, `gh` eingeloggt.
2. Bare-Repo + Worktrees, falls aktive Arbeit (siehe Vault-Konzeptseite).
3. Plugin `mattpocock-skills` installiert, dann `/setup-matt-pocock-skills`: `AGENTS.md` (oder `CLAUDE.md`), `docs/agents/{issue-tracker,triage-labels,domain}.md`.
4. OpenSpec installieren: `pnpm add -g @fission-ai/openspec@latest` (einmalig `pnpm setup`, falls PATH fehlt).
5. `openspec init --tools claude --language <de|en>` -> `openspec/` und `.claude/{skills,commands}`.
6. `openspec/config.yaml`: `rules.tasks` und `operations.apply|archive.guidance` auf den Workflow zeigen lassen (siehe Teil B).
7. Dieses Dokument ins Projekt legen, Vault-Projektordner anlegen (Plan + Log).

## Teil B: Dieses Repo

- Stack: POSIX-Shell + pandoc, kein Testframework. "Test" heißt hier: `./build.sh` läuft sauber, erwartete Dateien in `public/` existieren, Stichproben per `grep`. Ein Check pro Logik, kein Framework (ponytail).
- Sprache der Specs: Deutsch, Strukturüberschriften und SHALL/MUST englisch (`openspec/config.yaml`).
- Geplante Changes: `timeline-startseite` (PR 1), `zweisprachig-de-en` (PR 2). Vorlage: `docs/plans/zweisprachig-und-timeline.md`.
- Beobachtungen zur Einrichtung:
  - `openspec init` hat `AGENTS.md` nicht verändert, legt nur `openspec/` und `.claude/` an (6 Skills, 6 Commands).
  - Im Standardprofil sind `new`, `continue`, `ff`, `bulk-archive`, `verify`, `onboard` nicht aktiv (`openspec config profile`). `verify` wäre die OpenSpec-eigene Variante von Phase 4.
  - Plugin `mattpocock-skills` 1.2.3 enthält alles nötige. Umbenannt: `to-issues` -> `to-tickets`, `to-prd` -> `to-spec`. `triage`, `to-tickets`, `to-spec`, `implement`, `wayfinder`, `ask-matt` sind nur per Eingabe aufrufbar (`disable-model-invocation`) und stehen deshalb nicht in der Skill-Liste des Modells.
  - Die Kopie von `setup-matt-pocock-skills` unter `~/.claude/skills/` ist älter und spricht noch von `to-issues`/`to-prd`.

## Erweiterungspunkte (bewusst noch nicht ausgebaut)

Das Phasenmodell ist ein Gerüst, keine Vollständigkeit. Wo Lücken später gefüllt werden:

- **UI/UX klären:** vor Phase 2 `prototype` (HTML-Varianten zum Anschauen), Ergebnis in `design.md` des Changes. Heute für die Timeline nicht nötig, Screenshots im PR genügen.
- **Tester früh einbinden:** Prototyp oder Preview-Link an den Issue hängen, Feedback als Kommentar, Zustand `needs-info`. Eigene Phase "Abnahme" zwischen 4 und 5, wenn es echte Tester gibt.
- **Rückfragen an einen PO:** Schleife Phase 1 <-> 2. Frage als Kommentar am Issue, Label `needs-info` (Triage wartet auf den Fragesteller), Antwort fließt per `/opsx:update` in den Change. Der Change bleibt offen, bis die Fragen geklärt sind.
- **Mehrere Personen:** Eingang über Issues + `/triage` (Rollen und Labels stehen bereits in `docs/agents/`). Später feiner: Zuständigkeit je Phase, Review-Pflicht, Branch-Schutz, Change-Eigentümer, PR-Vorlage, Labels für UX/Test.
- **Bugs:** eigener Pfad ohne Change (`diagnosing-bugs` + `tdd`), siehe Regeln.

## Offen / zu erproben

- Taugt `tasks.md` als Eingabe für `/to-tickets`, oder schneidet der Skill besser aus `proposal` + Specs?
- Brauchen wir Phase 3 bei einem Ein-Personen-Repo, oder reicht `tasks.md` + `/implement`?
- Lohnt OpenSpecs `verify` zusätzlich zu `code-review`?
- Wie viel Overhead ist ein Change für eine kleine Änderung? (Schwelle definieren.)
