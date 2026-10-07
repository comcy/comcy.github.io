# Entwicklungs-Workflow (v0)

Stand: 2026-10-04. **v0, noch nicht an einem echten Change erprobt.** Wird nach dem ersten Change (Timeline) korrigiert.

Aufbau:
- **Teil A** ist projektunabhängig und generisch. Er soll später in ein eigenes Entwickler-Repo wandern (Setup-Skript wie `setup-matt-pocock-skills`).
- **Teil B** sind die Eigenheiten dieses Repos.
- **Teil C** sind persönliche Anpassungen ("user custom"). Sie hängen als Haken an Phasen aus Teil A, gehören aber nie in Teil A selbst.

## Teil A: Generischer Ablauf

### Voraussetzungen

Was jede Person installiert haben muss, bevor der Ablauf funktioniert:

| Voraussetzung | Wofür | Installation | Prüfen |
| --- | --- | --- | --- |
| `git` und ein GitHub-Repo | Versionsverwaltung, Remote | Paketmanager | `git --version` |
| GitHub CLI `gh`, eingeloggt | Issues, PRs, `/triage`, `/to-tickets` | <https://cli.github.com>, dann `gh auth login` | `gh auth status` |
| Python ab 3.11 | Setup und Prüfung des Prozesses (`scripts/`, nur Standardbibliothek) | <https://www.python.org> oder Paketmanager | `python3 --version` (Windows: `py -3 --version`) |
| Node.js ab 20.19 | Laufzeit für OpenSpec | <https://nodejs.org> oder Paketmanager | `node --version` |
| `pnpm` (oder `npm`) | installiert OpenSpec | Paketmanager; `pnpm` einmalig `pnpm setup` | `pnpm --version` |
| OpenSpec CLI | Specs und Changes | `pnpm add -g @fission-ai/openspec@latest` (oder `npm i -g`) | `openspec --version` (hier 1.14.0) |
| KI-Agent mit Skill-Unterstützung | führt die Skills aus (hier Claude Code) | siehe Agent-Doku | |
| Matt-Pocock-Skills | `grilling`, `triage`, `to-tickets`, `implement`, `tdd`, `code-review` u. a. | Plugin über den Marketplace: `/plugin install mattpocock-skills@claude-plugins-official` (hier 1.2.3) | `/plugin` |

Die Tabelle spiegelt `scripts/setup.d/tools.tsv`, `python3 scripts/setup.py --check` prüft sie (Mindestversionen, Pflicht oder empfohlen). Projektspezifische Werkzeuge (z. B. Build-Tools) stehen in Teil B.

### Ablauf

![Workflow-Modell: Ablauf, ersetzte Skills, Erweiterungspunkte](workflow.svg)

Leitidee: **OpenSpec hält fest, *was* gelten soll (Anforderungen als Specs). Issues, TDD und Review erledigen *das Bauen*.** Zwei Quellen der Wahrheit vermeiden: Specs beschreiben Verhalten, Issues beschreiben Arbeit.

| Phase | Werkzeug | Ergebnis |
| --- | --- | --- |
| S. Setup (einmalig je Klon) | `python3 scripts/setup.py [agent]` (`--check`, `--labels`), danach `python3 scripts/flow.py validate` | Voraussetzungen erfüllt, Adapter lokal eingerichtet, Labels angelegt, Prozessdaten konsistent |
| 0. Eingang | Issue anlegen, `/triage` | Triage-Zustand (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) |
| 1. Idee schärfen | `/grilling` oder `/openspec-explore` | Entscheidungen, Rest-Fragen |
| 2. Anforderungen festhalten | `/openspec-propose <name>` | `openspec/changes/<name>/`: proposal, Delta-Specs, design, tasks |
| 3. Arbeit schneiden | `/to-tickets` aus dem Change | Tracer-Bullet-Tickets mit Blockern auf GitHub |
| 4. Bauen und prüfen | `/implement` je Ticket (treibt `tdd`, endet mit `code-review`) | Code + Tests, ein PR je Ticket, `tasks.md` abhaken |
| 5. Abschließen | `/openspec-archive-change` | Delta-Specs fließen in `openspec/specs/` |
| 6. Wissen sichern | Entscheidungen als ADR in `docs/adr/` (`/domain-modeling`), Verlauf in einem Log, Ort frei wählbar | Entscheidungen, Stolpersteine nachlesbar |

Status am Issue (zweite Label-Dimension, `status:ready-for-refinement`, `status:in-refinement`, `status:in-progress`, `status:in-review`): `docs/agents/flow-labels.md`. Die Skills setzen sie nicht, sie gelten als Anweisung.

Rollen der Skills: **OpenSpec ist die Spec** (Verhalten, dauerhaft in `openspec/specs/`). `/to-spec` wird deshalb **nicht** benutzt, es würde eine zweite Spec als Issue anlegen. `/to-tickets` ist das Bindeglied: Es schneidet den Change in Arbeit, die Issues referenzieren den Change-Namen.

Regeln:
- Ändert sich ein Verhalten während des Bauens, zuerst den Change aktualisieren (`/openspec-update-change`), dann Code. Sonst driftet die Spec.
- `/openspec-propose` plant nur und stoppt. Bauen startet immer eine neue, ausdrückliche Anfrage.
- Bei sehr großem Vorhaben (mehr als eine Session) vorher `/wayfinder`: Karte aus Entscheidungs-Tickets, danach je Entscheidung ein Change.
- Unsicher, welcher Skill passt: `/ask-matt`.
- Reiner Bugfix ohne Verhaltensänderung braucht keinen Change: `diagnosing-bugs` + `tdd` + Issue.
- Commit-Konvention und Secret-Scan vor dem Staging festlegen (Teil B/C).

### Eigene Anpassungen

Jede Person darf Phasen um eigene Schritte ergänzen (Haken), ohne den generischen Ablauf zu ändern. Regel: Der Haken benennt die Phase, nach der er läuft, und beschreibt den Schritt. Beispiele für Haken: Verlauf in ein persönliches Wissenssystem schreiben (nach Phase 6), eigene Branch-Regeln (Phase 4), Benachrichtigungen. Die konkreten Haken stehen in Teil C.

### Setup nach dem Klonen

```
python3 scripts/setup.py --check            # prüft, ändert nichts (Exit-Code 1, wenn etwas fehlt)
python3 scripts/setup.py claude             # richtet den lokalen Klon für Claude Code ein
python3 scripts/setup.py --labels claude    # dasselbe, legt zusätzlich fehlende Labels an (einmal je Repo)
python3 scripts/flow.py validate            # prüft die Prozessdaten unter workflow/
python3 scripts/flow.py start 42            # Ticket starten (siehe "Zustandswechsel")
```
Unter Windows `py -3 scripts\setup.py …`. Das Setup tut Folgendes (Details in der Spec `repo-setup`):

1. **Voraussetzungen** aus `scripts/setup.d/tools.tsv` prüfen; ein fehlendes Pflichtprogramm bricht ab, ohne etwas zu ändern.
2. **Adapter:** `openspec init --tools agents[,<agent>]` (nur wenn ein Adapterordner fehlt), die gewählten Agenten stehen in `git config --local setup.agents` und werden beim nächsten Aufruf ohne Argument wieder genutzt. Bei abweichender `openspec`-Version (`generatedBy` in den Skills) ruft ein Lauf `openspec update` auf. Agenten und ihre Ordner stehen in `scripts/setup.d/agents.tsv`.
3. **Ausschlüsse:** Die Ordner der Agenten (`.claude/` usw.) kommen einmalig in `.git/info/exclude`, nicht in die `.gitignore`. `.agents/` bleibt eingecheckt (agentenneutrale Basis).
4. **Hooks:** `core.hooksPath` auf `.githooks`, sobald dieser Ordner existiert.
5. **Labels** nur mit `--labels`: fehlende Labels der Zustände aus `workflow/states.tsv`, vorhandene bleiben unberührt. Ohne den Schalter nennt `setup` nur die Zahl der fehlenden Labels.

Ein zweiter Lauf meldet "nichts zu tun". Von Hand bleibt: `/setup-matt-pocock-skills` (`AGENTS.md`, `docs/agents/*.md`), in `openspec/config.yaml` die Regeln `rules.tasks` und `operations.*.guidance` (Beispiel: Teil B), dieses Dokument ins Projekt legen und optional eigene Haken (siehe "Eigene Anpassungen").

Warum lokal: Claude Code sucht Projekt-Skills nur in `.claude/skills/`, nicht in `.agents/skills/`. Die agentenspezifischen Dateien sind abgeleitet (`openspec update` erzeugt sie neu), jede Person braucht nur den Adapter für ihren Agenten. Ein Klon-Hook ist in Git nicht möglich (Hooks werden nicht mitgeklont), deshalb ist `scripts/setup.py` der feste erste Schritt.

### Prozessdaten (`workflow/`)

Zustände, Übergänge, Phasen und das Vokabular der Bedingungen stehen als Dateien neben dem Werkzeug, tabulatorgetrennt mit Kopfzeile (Spalten nach Namen, `#` für Kommentare, `enabled` zum Abschalten eines Schritts). Sie sind die Quelle der Labels und später für kvasir und das Diagramm.

| Datei | Inhalt |
| --- | --- |
| `states.tsv` | Zustände: `id` (= Label), `kind` (`triage`, `status`, `terminal`), `color`, `description` |
| `transitions.tsv` | Übergänge: `from` (oder `-` für den Start), `to`, `trigger`, `guard` (Detektoren, Komma = UND) |
| `phases.tsv` | Phasen S, 0 bis 6, 4b: `id`, `name`, `tool`, `done_when`, `level` |
| `detectors.tsv` | das feste Vokabular der Bedingungen mit Argumentform (`-`, `text`, `path`, `enum:a|b|c`) |

`python3 scripts/flow.py validate` prüft Spalten, Eindeutigkeit, Verweise, Dimensionen (Übergänge nur innerhalb einer Dimension, außer vom Start oder zu `closed`) und das Vokabular; Warnungen (abgeschaltete Verweise, Sackgassen, Phasenreihenfolge) werden mit `--strict` zu Fehlern. Es läuft in jedem Pull Request. Die Dateien enthalten nie Code, ausgewertet wird im Werkzeug. Ein Wechsel auf JSON oder YAML wäre lokal im Leser (`scripts/lib/workflow.py`) möglich, sobald ODER-Bedingungen, mehr als etwa acht Eigenschaften je Schritt oder Tab-Fehler es nötig machen.

### Zustandswechsel (`flow start`)

`python3 scripts/flow.py start <issue> [--dry-run]` (Windows: `py -3 scripts\flow.py start …`) liest Titel, Zustand und Labels per `gh`, legt den Branch `feature/<id>-<slug>` an (`git branch`, ohne Wechsel des Arbeitsordners) und setzt `status:in-progress`. Das alte `status:`-Label wird entfernt.
- Erlaubt ist nur ein Übergang nach `status:in-progress` mit Auslöser `branch_created` (kein `status`-Label) oder `work_started` (von `status:in-refinement`) aus `workflow/transitions.tsv`. Sonst Exit-Code 1 mit Nennung des Übergangs, ohne Branch- oder Label-Änderung. Ebenso bei geschlossenem Issue oder vorhandenem Branch.
- Die Bedingungen (`guard`, z. B. `no_open_blockers`) wertet der Befehl noch nicht aus.
- `--dry-run` zeigt die Schritte (`git branch …`, `gh issue edit …`) und ändert nichts.
- Slug: Kleinbuchstaben, Umlaute und `ß` als `ae oe ue ss`, Akzente entfernt, Sonderzeichen werden zu `-`, höchstens 40 Zeichen an einer Wortgrenze; ohne verwertbare Zeichen `issue`.
- Fehlt `gh`, der GitHub-Remote oder die Anmeldung, gibt es eine Fehlermeldung ohne Traceback. Scheitert das Label, wird der neue Branch wieder gelöscht.
- `flow review` ist noch nicht umgesetzt.

## Teil B: Dieses Repo

- Stack: POSIX-Shell + pandoc, kein Testframework. "Test" heißt hier: `sh build.sh` läuft sauber, erwartete Dateien in `public/` existieren, Stichproben per `grep`. Ein Check pro Logik, kein Framework (ponytail).
- Zusätzliche Voraussetzung: `pandoc` (Arch: `sudo pacman -Syu pandoc-cli`).
- Sprache der Specs: Deutsch, Strukturüberschriften und SHALL/MUST englisch (`openspec/config.yaml`).
- Commits: Conventional Commits, Secret-Scan vor dem Staging.
- Geplante Changes: `timeline-startseite` (PR 1), `zweisprachig-de-en` (PR 2). Vorlage: `docs/plans/zweisprachig-und-timeline.md`.
- Beobachtungen zur Einrichtung:
  - `openspec init --tools claude` legte `.claude/skills/` (6 Skills) **und** `.claude/commands/opsx/` (6 Commands) an, dieselben sechs Abläufe doppelt. `--tools agents` legt nur `.agents/skills/` an (6 Skills, keine Commands). Wir nutzen `agents` im Repo und den Claude-Adapter nur lokal.
  - Die Skill-Namen ändern sich damit: `/opsx:propose` wird zu `/openspec-propose`, `/opsx:archive` zu `/openspec-archive-change` usw.
  - `openspec init` hat `AGENTS.md` nicht verändert.
  - Im Standardprofil sind `new`, `continue`, `ff`, `bulk-archive`, `verify`, `onboard` nicht aktiv (`openspec config profile`). `verify` wäre die OpenSpec-eigene Variante von Phase 4.
  - Plugin `mattpocock-skills` 1.2.3 enthält alles nötige. Umbenannt: `to-issues` -> `to-tickets`, `to-prd` -> `to-spec`. `triage`, `to-tickets`, `to-spec`, `implement`, `wayfinder`, `ask-matt` sind nur per Eingabe aufrufbar (`disable-model-invocation`) und stehen deshalb nicht in der Skill-Liste des Modells.
  - Die Kopie von `setup-matt-pocock-skills` unter `~/.claude/skills/` ist älter und spricht noch von `to-issues`/`to-prd`.

## Teil C: Eigene Anpassungen (Chris)

Haken an den generischen Phasen. Nur persönlich, nicht Teil des generischen Ablaufs:

| Nach Phase | Haken |
| --- | --- |
| Setup | Repo als Bare-Repo mit Git-Worktrees auschecken (ein Worktree je Branch) |
| 4 (Commit) | Commits als Conventional Commits mit festem Autor, Secret-Scan vor dem Staging (globale Regeln) |
| 6 | Verlauf und Referenz zusätzlich ins persönliche Wissenssystem (Vault, `Projects/<name>/`: Plan, Log) schreiben |

## Teststrategie

- **Szenario heißt Testfall:** Jedes Szenario einer OpenSpec-Spec ist ein Testfall. Die Shell-Tests unter `tests/<fähigkeit>-check.sh` sind die ausführbare Form des Verhaltens und bleiben im Repo. `<fähigkeit>` ist der Name der Fähigkeit (z. B. `timeline`), nicht der Name des Changes (`timeline-startseite`).
- **Teststelle ist der Build-Aufruf:** `sh build.sh` in einem temporären Klon mit eigenen Fixtures, geprüft wird `public/` und der Fehlercode (Black-Box, keine internen Funktionen). Vor dem ersten Test werden die Teststellen bestätigt (`/tdd`).
- **Layout per Screenshot:** Optik ist im Build-Output nicht sinnvoll prüfbar. Screenshots dienen als Beleg am PR (Branch `pr-screenshots`) und sind nicht persistent.
- **Wo es läuft:** lokal mit `sh tests/run.sh`, in der CI auf jedem Pull Request und vor dem Veröffentlichen. Ein verbindlicher Branch-Schutz ("Status check erforderlich") ist eine GitHub-Einstellung und bewusst noch nicht gesetzt.
- **Mutationscheck:** Bei einem Test, der etwas Unsichtbares schützen soll (z. B. feste Reihenfolge), den Code kurz verschlechtern und prüfen, dass der Test rot wird.

Abgleich mit dem Anthropic-Playbook: [playbook-abgleich.md](playbook-abgleich.md).

## Erweiterungspunkte (bewusst noch nicht ausgebaut)

Das Phasenmodell ist ein Gerüst, keine Vollständigkeit. Wo Lücken später gefüllt werden:

- **UI/UX klären:** vor Phase 2 `prototype` (HTML-Varianten zum Anschauen), Ergebnis in `design.md` des Changes. Heute für die Timeline nicht nötig, Screenshots im PR genügen.
- **Tester früh einbinden:** Prototyp oder Preview-Link an den Issue hängen, Feedback als Kommentar, Zustand `needs-info`. Eigene Phase "Abnahme" zwischen 4 und 5, wenn es echte Tester gibt.
- **Rückfragen an einen PO:** Schleife Phase 1 <-> 2. Frage als Kommentar am Issue, Label `needs-info` (Triage wartet auf den Fragesteller), Antwort fließt per `/openspec-update-change` in den Change. Der Change bleibt offen, bis die Fragen geklärt sind.
- **Mehrere Personen:** Eingang über Issues + `/triage` (Rollen und Labels stehen bereits in `docs/agents/`). Später feiner: Zuständigkeit je Phase, Review-Pflicht, Branch-Schutz, Change-Eigentümer, PR-Vorlage, Labels für UX/Test.
- **Bugs:** eigener Pfad ohne Change (`diagnosing-bugs` + `tdd`), siehe Regeln.

## Später: Verlässlichkeit und Nachvollziehbarkeit

Aktuell steht der Prozess in Prosa (`AGENTS.md`, diese Datei, Skill-Texte, `openspec/config.yaml`). Ein Agent befolgt das wahrscheinlich, aber nicht garantiert. Idee für später, nicht jetzt: Texte erklären, Werkzeuge erzwingen.

Durchsetzungsstufen, von weich nach hart:

| Stufe | Beispiel | Verlässlichkeit |
| --- | --- | --- |
| Prosa | `AGENTS.md`, `workflow.md` | Agent kann sie überlesen |
| Skill | ein Skill je Phase mit festem Ein-/Ausgang | folgt der Skill-Anweisung, aber noch Modellverhalten |
| Skill-Konfiguration | `openspec/config.yaml` (rules, guidance) | wird beim Skill-Lauf eingelesen |
| Skript | Zustandswechsel als Befehl (`gh` + Label + Branch-Name) statt freier Improvisation | deterministisch für das Mechanische |
| Hook | Harness-Hooks (z. B. vor `git commit`: Secret-Scan, Branch-Name) | wird vom Harness ausgeführt, nicht vom Modell |
| CI / Branch-Schutz | Pflicht-Checks: Build, `openspec validate`, Commit-Lint, Label-Prüfung | gilt für jede Person und jeden Agenten |

Prinzip: Das Modell urteilt (Spezifikation, Code, Review), Skripte und CI erzwingen Übergänge und Prüfpunkte.

Idee: Phasen als Daten beschreiben (Eingang, Ergebnis, Prüfpunkt, Zustandswechsel je Phase), daraus Tabelle, Diagramm, Labels und Setup-Skript erzeugen. Dann ist der Prozess unabhängig von einzelnen Skills austauschbar.

### Umsetzungsreihenfolge (später, jeweils nur bei echtem Bedarf)

1. **Agentenunabhängig und billig:** Git-Hooks über `git config core.hooksPath .githooks` (`commit-msg`: Conventional Commits, `pre-commit`: Secret-Scan), dazu ein CI-Job (Build, Validierung) und Branch-Schutz auf `master`. Wirkt für jede Person und jeden Agenten.
2. **Skripte:** `scripts/setup.py` (erledigt mit #14, einmaliger Einstieg nach dem Klonen) und danach ein Skript für Zustandswechsel (`scripts/flow.py` kennt `validate` und `start` (#66), `review` folgt; gehört zu #11): z. B. `scripts/flow start <issue>` legt `feature/<id>-<slug>` an und setzt `status:in-progress`, `scripts/flow review` setzt `status:in-review`. POSIX-Shell mit `gh`, wie der Rest des Repos.
3. **Phasen als Daten:** erledigt als `workflow/*.tsv` (#14), die Labels entstehen daraus, Doku und Diagramm sollen noch daraus erzeugt werden.
4. **Nachvollziehbarkeit:** Protokoll der Skill-Aufrufe und `gh`-Schreibzugriffe, Testlauf des Prozesses an einer Beispielaufgabe.
5. **Orchestrierung (nur bei unbeaufsichtigtem Betrieb):** siehe unten.

Agenten-Hooks (Claude Code: `settings.json`, vom Harness ausgeführt) sind agentengebunden und liegen unter `.claude/`. Wer `.claude/` nicht einchecken will, legt sie in die Nutzer-Einstellungen oder in eine ignorierte `settings.local.json`. Harte Regeln gehören deshalb in Git-Hooks und CI, Agenten-Hooks nur für Komfort wie Protokollierung.

### Orchestrierung mit LangGraph oder Ähnlichem?

LangGraph beschreibt Abläufe als Graph aus Knoten (Schritte) und Kanten (Übergänge), mit gespeichertem Zustand und Stellen für menschliche Freigabe. Der Ablauf ist dann Code, das Modell arbeitet nur innerhalb eines Knotens. Das wäre die härteste Form von deterministisch.

Dagegen: Es ist ein eigener Agent-Runner (Python, neue Abhängigkeit), er ersetzt die interaktive Arbeit im Agenten statt sie zu ergänzen, und für ein Ein-Personen-Repo ist es zu viel. Sinnvoll wird es, wenn der Prozess unbeaufsichtigt läuft, z. B. wenn ein Label `ready-for-agent` eine Pipeline startet und mehrere Personen dem Ablauf vertrauen müssen. Leichtere Alternativen davor: GitHub Actions auf Label-Ereignissen (`issues: labeled`), das Agent SDK für programmatische Läufe, allgemeine Workflow-Engines. Empfehlung: erst Stufen 1 bis 3, LangGraph neu bewerten, wenn Unbeaufsichtigtheit gewollt ist.

## Offen / zu erproben

Erfahrungen aus dem ersten durchlaufenen Change (`timeline-startseite`, 2026-10-06, 8 Tickets, 9 PRs inklusive CI):

- **`tasks.md` und `/to-tickets`:** `tasks.md` war nach Schichten geordnet (Daten, Ausgabe, Layout), `/to-tickets` verlangt vertikale Scheiben. Die Tasks waren Eingabe, nicht Ergebnis. Die Task-Regel in `openspec/config.yaml` verlangt jetzt vertikale Scheiben. Ob das reicht, zeigt der nächste Change.
- **Phase 3 bei einem Ein-Personen-Repo:** Die Tickets mit Blockern haben sich getragen (ein PR je Ticket, klare Reihenfolge, Frontier sichtbar). Der Aufwand lag im Schneiden, nicht im Pflegen. Beibehalten.
- **`code-review` statt `verify`:** Das Review über drei Tickets fand zwei echte Spec-Fehler (leere Spalte ohne Einträge, Ende gleich Start) und mehrere Pflegepunkte, die der TDD-Lauf nicht gezeigt hatte. Lohnt sich nach jeder Gruppe von Tickets, nicht erst am Ende.
- **Overhead eines Changes:** Proposal, Specs, Design und Tasks waren schnell geschrieben (ein Zug), den Aufwand machten Umsetzung, Tests und Abnahme. Vermutung, noch nicht gemessen: Für Änderungen mit weniger als etwa einem Ticket Aufwand lohnt der Change nicht, dann reichen Issue, `/tdd` und PR.
- **Abnahme-Gate:** Die lokale Abnahme vor der Freigabe hat sich bewährt. Merges vor dem CI-Ergebnis verhindert jetzt der Branch-Schutz (Check `test`).
- **Skripte statt Prosa für Browser-Prüfungen:** Headless Chromium über das DevTools-Protokoll aus Node reicht für Nachladen, Tastatur, Kontrast und 375 px, ohne neue Abhängigkeit. Die Prüfungen laufen manuell, nicht in der CI.
- **Selbstständiger Lauf (#14, Tickets #47 bis #52, 2026-10-06):** Sechs Tickets nacheinander mit TDD, Pull Request, CI auf drei Systemen und Merge bei Grün, ohne Zwischenabnahme. Funktioniert, wenn die Teststellen von außen liegen (Prozessaufruf, Stub-Programme) und die Matrix auf Ubuntu, macOS und Windows sofort mitläuft: die Stubs mit `.cmd`-Wrapper liefen beim ersten Versuch. Was dabei schiefging: ein früher Testlauf ließ einen Stub mit dem Arbeitsordner des Tests Dateien im echten Repo überschreiben (Gegenmaßnahme: `openspec` läuft mit `cwd=<Repo>`, Stubs schreiben nur unter `STUB_ROOT`), `__pycache__` wurde einmal eingecheckt (`.gitignore`), und ein Probelauf in einem Klon ohne GitHub-Remote zeigte, dass `gh label list` dort scheitert (jetzt nur ein Hinweis, mit `--labels` ein Fehler). Der manuelle Probelauf mit den echten Programmen im Wegwerf-Klon hat damit Fehler gefunden, die die Stubs nicht zeigen konnten.
- **Code-Review vor dem Archivieren (#14):** Zwei parallele Agenten (Standards, Spec) fanden nach 89 grünen Tests noch sechs echte Fehler, die kein Test vorhergesehen hatte: fehlgeschlagenes `git config` wurde als erledigt gemeldet, ein von Claude Code selbst angelegter `.claude/`-Ordner galt als Adapter, `setup agents` löschte die gespeicherte Wahl, ein älteres `openspec` löste ein Update aus, Labelnamen wurden groß- und kleinschreibungsabhängig verglichen und `splitlines` trennte Dateien an Sonderzeichen. Dazu kamen Duplikate (fünfmal derselbe Programmaufruf), die in `scripts/lib/proc.py` zusammengeführt wurden. Das Review lohnt sich auch nach TDD und auch bei einem selbstständigen Lauf.
- **Testlaufzeit:** 48 Fälle brauchen lokal etwa 75 Sekunden und wachsen mit jedem Fall. Fixtures verkleinern oder Builds teilen, bevor es zu langsam wird.
