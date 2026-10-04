# Entwicklungs-Workflow (v0)

Stand: 2026-10-04. **v0, noch nicht an einem echten Change erprobt.** Wird nach dem ersten Change (Timeline) korrigiert.

Aufbau:
- **Teil A** ist projektunabhängig und generisch. Er soll später in ein eigenes Entwickler-Repo wandern (Setup-Skript wie `setup-matt-pocock-skills`).
- **Teil B** sind die Eigenheiten dieses Repos.

Persönliche Anpassungen gehören nicht in dieses Dokument, siehe "Eigene Anpassungen".

## Teil A: Generischer Ablauf

### Voraussetzungen

Was jede Person installiert haben muss, bevor der Ablauf funktioniert:

| Voraussetzung | Wofür | Installation | Prüfen |
| --- | --- | --- | --- |
| `git` und ein GitHub-Repo | Versionsverwaltung, Remote | Paketmanager | `git --version` |
| GitHub CLI `gh`, eingeloggt | Issues, PRs, `/triage`, `/to-tickets` | <https://cli.github.com>, dann `gh auth login` | `gh auth status` |
| Node.js ab 20.19 | Laufzeit für OpenSpec | <https://nodejs.org> oder Paketmanager | `node --version` |
| `pnpm` (oder `npm`) | installiert OpenSpec | Paketmanager; `pnpm` einmalig `pnpm setup` | `pnpm --version` |
| OpenSpec CLI | Specs und Changes | `pnpm add -g @fission-ai/openspec@latest` (oder `npm i -g`) | `openspec --version` (hier 1.14.0) |
| KI-Agent mit Skill-Unterstützung | führt die Skills aus (hier Claude Code) | siehe Agent-Doku | |
| Matt-Pocock-Skills | `grilling`, `triage`, `to-tickets`, `implement`, `tdd`, `code-review` u. a. | Plugin über den Marketplace: `/plugin install mattpocock-skills@claude-plugins-official` (hier 1.2.3) | `/plugin` |

Projektspezifische Werkzeuge (z. B. Build-Tools) stehen in Teil B.

### Ablauf

![Workflow-Modell: Ablauf, ersetzte Skills, Erweiterungspunkte](workflow.svg)

Leitidee: **OpenSpec hält fest, *was* gelten soll (Anforderungen als Specs). Issues, TDD und Review erledigen *das Bauen*.** Zwei Quellen der Wahrheit vermeiden: Specs beschreiben Verhalten, Issues beschreiben Arbeit.

| Phase | Werkzeug | Ergebnis |
| --- | --- | --- |
| 0. Eingang | Issue anlegen, `/triage` | Label-Zustand (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) |
| 1. Idee schärfen | `/grilling` oder `/openspec-explore` | Entscheidungen, Rest-Fragen |
| 2. Anforderungen festhalten | `/openspec-propose <name>` | `openspec/changes/<name>/`: proposal, Delta-Specs, design, tasks |
| 3. Arbeit schneiden | `/to-tickets` aus dem Change | Tracer-Bullet-Tickets mit Blockern auf GitHub |
| 4. Bauen und prüfen | `/implement` je Ticket (treibt `tdd`, endet mit `code-review`) | Code + Tests, ein PR je Ticket, `tasks.md` abhaken |
| 5. Abschließen | `/openspec-archive-change` | Delta-Specs fließen in `openspec/specs/` |
| 6. Wissen sichern | Entscheidungen als ADR in `docs/adr/` (`/domain-modeling`), Verlauf in einem Log, Ort frei wählbar | Entscheidungen, Stolpersteine nachlesbar |

Rollen der Skills: **OpenSpec ist die Spec** (Verhalten, dauerhaft in `openspec/specs/`). `/to-spec` wird deshalb **nicht** benutzt, es würde eine zweite Spec als Issue anlegen. `/to-tickets` ist das Bindeglied: Es schneidet den Change in Arbeit, die Issues referenzieren den Change-Namen.

Regeln:
- Ändert sich ein Verhalten während des Bauens, zuerst den Change aktualisieren (`/openspec-update-change`), dann Code. Sonst driftet die Spec.
- `/openspec-propose` plant nur und stoppt. Bauen startet immer eine neue, ausdrückliche Anfrage.
- Bei sehr großem Vorhaben (mehr als eine Session) vorher `/wayfinder`: Karte aus Entscheidungs-Tickets, danach je Entscheidung ein Change.
- Unsicher, welcher Skill passt: `/ask-matt`.
- Reiner Bugfix ohne Verhaltensänderung braucht keinen Change: `diagnosing-bugs` + `tdd` + Issue.
- Commit-Konvention und Secret-Scan vor dem Staging festlegen (Beispiel: Teil B).

### Eigene Anpassungen

Jede Person darf Phasen um eigene Schritte ergänzen (Haken), ohne den generischen Ablauf zu ändern. Ein Haken benennt die Phase, nach der er läuft, und beschreibt den Schritt. Beispiele: Verlauf in ein persönliches Wissenssystem schreiben (nach Phase 6), eigene Branch-Regeln (Phase 4), Benachrichtigungen. Die konkreten Haken pflegt jede Person außerhalb dieses Dokuments, es ist nur die Stelle dafür vorgesehen.

### Setup-Checkliste (Basis für ein späteres Skript)

1. Voraussetzungen (Tabelle oben) erfüllen.
2. Git-Repo mit GitHub-Remote.
3. `/setup-matt-pocock-skills`: `AGENTS.md` (oder `CLAUDE.md`), `docs/agents/{issue-tracker,triage-labels,domain}.md`.
4. `openspec init --tools agents --language <de|en>` -> `openspec/` und `.agents/skills/` (6 OpenSpec-Skills, keine Commands).
5. `openspec/config.yaml`: `rules.tasks` und `operations.apply|archive.guidance` auf den Workflow zeigen lassen (Beispiel: Teil B).
6. Dieses Dokument ins Projekt legen.
7. Optional: eigene Haken einrichten (siehe "Eigene Anpassungen").

Hinweis zur Skill-Erkennung: Claude Code sucht Projekt-Skills in `.claude/skills/`, nicht in `.agents/skills/`. Tauchen die `/openspec-*`-Skills nicht auf, lokal verlinken, ohne `.claude/` einzuchecken (**nicht getestet**):

```
mkdir -p .claude/skills && for d in .agents/skills/openspec-*; do ln -s ../../$d .claude/skills/$(basename $d); done
echo '.claude/' >> .git/info/exclude
```

## Teil B: Dieses Repo

- Stack: POSIX-Shell + pandoc, kein Testframework. "Test" heißt hier: `sh build.sh` läuft sauber, erwartete Dateien in `public/` existieren, Stichproben per `grep`. Ein Check pro Logik, kein Framework (ponytail).
- Zusätzliche Voraussetzung: `pandoc` (Arch: `sudo pacman -Syu pandoc-cli`).
- Sprache der Specs: Deutsch, Strukturüberschriften und SHALL/MUST englisch (`openspec/config.yaml`).
- Commits: Conventional Commits, Secret-Scan vor dem Staging.
- Geplante Changes: `timeline-startseite` (PR 1), `zweisprachig-de-en` (PR 2). Vorlage: `docs/plans/zweisprachig-und-timeline.md`.
- Beobachtungen zur Einrichtung:
  - `openspec init --tools claude` legte `.claude/skills/` (6 Skills) **und** `.claude/commands/opsx/` (6 Commands) an, dieselben sechs Abläufe doppelt. `--tools agents` legt nur `.agents/skills/` an (6 Skills, keine Commands). Wir nutzen `agents`, `.claude/` ist entfernt.
  - Die Skill-Namen ändern sich damit: `/opsx:propose` wird zu `/openspec-propose`, `/opsx:archive` zu `/openspec-archive-change` usw.
  - `openspec init` hat `AGENTS.md` nicht verändert.
  - Im Standardprofil sind `new`, `continue`, `ff`, `bulk-archive`, `verify`, `onboard` nicht aktiv (`openspec config profile`). `verify` wäre die OpenSpec-eigene Variante von Phase 4.
  - Plugin `mattpocock-skills` 1.2.3 enthält alles nötige. Umbenannt: `to-issues` -> `to-tickets`, `to-prd` -> `to-spec`. `triage`, `to-tickets`, `to-spec`, `implement`, `wayfinder`, `ask-matt` sind nur per Eingabe aufrufbar (`disable-model-invocation`) und stehen deshalb nicht in der Skill-Liste des Modells.
  - Die Kopie von `setup-matt-pocock-skills` unter `~/.claude/skills/` ist älter und spricht noch von `to-issues`/`to-prd`.

## Erweiterungspunkte (bewusst noch nicht ausgebaut)

Das Phasenmodell ist ein Gerüst, keine Vollständigkeit. Wo Lücken später gefüllt werden:

- **UI/UX klären:** vor Phase 2 `prototype` (HTML-Varianten zum Anschauen), Ergebnis in `design.md` des Changes. Heute für die Timeline nicht nötig, Screenshots im PR genügen.
- **Tester früh einbinden:** Prototyp oder Preview-Link an den Issue hängen, Feedback als Kommentar, Zustand `needs-info`. Eigene Phase "Abnahme" zwischen 4 und 5, wenn es echte Tester gibt.
- **Rückfragen an einen PO:** Schleife Phase 1 <-> 2. Frage als Kommentar am Issue, Label `needs-info` (Triage wartet auf den Fragesteller), Antwort fließt per `/openspec-update-change` in den Change. Der Change bleibt offen, bis die Fragen geklärt sind.
- **Mehrere Personen:** Eingang über Issues + `/triage` (Rollen und Labels stehen bereits in `docs/agents/`). Später feiner: Zuständigkeit je Phase, Review-Pflicht, Branch-Schutz, Change-Eigentümer, PR-Vorlage, Labels für UX/Test.
- **Bugs:** eigener Pfad ohne Change (`diagnosing-bugs` + `tdd`), siehe Regeln.

## Offen / zu erproben

- Taugt `tasks.md` als Eingabe für `/to-tickets`, oder schneidet der Skill besser aus `proposal` + Specs?
- Brauchen wir Phase 3 bei einem Ein-Personen-Repo, oder reicht `tasks.md` + `/implement`?
- Lohnt OpenSpecs `verify` zusätzlich zu `code-review`?
- Erkennt Claude Code die Skills aus `.agents/skills/` ohne Symlink?
- Wie viel Overhead ist ein Change für eine kleine Änderung? (Schwelle definieren.)
