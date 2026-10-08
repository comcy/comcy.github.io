---
title: OpenSpec einrichten – erste Schritte in einem bestehenden Projekt
date: 2026-10-04
tags: [ai, openspec]
description: Wie ich spec-driven development mit OpenSpec in diesen Blog gebracht habe, inklusive Stolpersteinen.
draft: true
---

*Entwurf, wird während der Einrichtung fortlaufend ergänzt (Material statt Fließtext).*

## Ausgangslage

- Projekt: dieser Blog (POSIX-Shell + pandoc, GitHub Pages), Arbeit mit Claude Code.
- Vorher schon da: Agent-Skills (Matt Pocock) mit `AGENTS.md` und `docs/agents/` (GitHub Issues, Standard-Labels, single-context).
- Plan als Freitext in `docs/plans/zweisprachig-und-timeline.md`, per Grilling-Interview Frage für Frage geschärft (12 Fragen, jeweils mit Empfehlung). Ergebnis: Timeline auf der Startseite + zweisprachiger Blog.

## Installation

1. `pnpm add -g @fission-ai/openspec@latest`
2. Stolperstein: `The configured global bin directory ".../pnpm/bin" is not in PATH` -> `pnpm setup`, danach `source ~/.zshrc`.
3. `openspec --version` -> 1.14.0.
4. `openspec init --help`: `--tools` (u. a. `claude`, `agents`), `--language`, `--profile core|custom`.

## Einbindung (Plan)

- Zwei Changes statt einer Plan-Datei: `timeline-startseite` und `zweisprachig-de-en`.
- Nach dem Merge `openspec archive` -> Specs unter `openspec/specs/`.
- Abgrenzung zu den vorhandenen Skills: OpenSpec für Spezifikation, `tdd` und `gh issue` für Umsetzung/Tracking.

## `openspec init`

Erster Versuch: `openspec init --tools claude --language de`. Das legte `openspec/` an und dazu `.claude/` mit 6 Skills **und** 6 Commands (`/opsx:propose` usw.), also dieselben sechs Abläufe doppelt. Ich wollte keinen `.claude/`-Ordner im Repo, sondern agnostisch bleiben.

Zweiter Versuch: `--tools agents` legt nur `.agents/skills/` an (6 Skills, keine Commands). Die Namen ändern sich dabei: `/opsx:propose` wird `/openspec-propose`, `/opsx:archive` wird `/openspec-archive-change`. `AGENTS.md` bleibt in beiden Fällen unberührt. Standardprofil ohne `verify`, `ff`, `new`.

Auflösung der offenen Frage: Claude Code liest Projekt-Skills aus `.claude/skills/`. Beim ersten echten Aufruf kam `Unknown skill: openspec-propose`, `.agents/skills/` wird also nicht erkannt. Die `SKILL.md` ist aber nur Text: Ich habe sie gelesen und den Ablauf von Hand mit der OpenSpec-CLI nachvollzogen (`openspec new change`, `status`, `instructions`, `validate`). Das ging ohne Skill, nur mit weniger Komfort. Fazit für den Prozess: Skills sind bequem, die CLI mit ihrem JSON ist die eigentliche Schnittstelle.

Lösung für das Repo: Die agentenneutrale Basis `.agents/` bleibt eingecheckt, den Adapter für den eigenen Agenten erzeugt jede Person lokal (`openspec init --tools claude`) und trägt den Ordner in `.git/info/exclude` ein. So bleibt das Repo frei von agentenspezifischen Dateien, und ein anderer Agent kommt ohne Repo-Änderung dazu. Einen Klon-Hook gibt es in Git nicht (Hooks werden nicht mitgeklont), deshalb soll ein Setup-Skript der feste erste Schritt nach dem Klonen werden (Issue #14).

## Workflow definieren

Entscheidung: OpenSpec hält fest, *was* gelten soll, GitHub-Issues, `tdd` und `code-review` erledigen das Bauen. Beschrieben in `docs/workflow.md`: Teil A generisch mit Voraussetzungen (später Basis für ein Setup-Skript), Teil B repo-spezifisch, Teil C persönliche Haken (z. B. Verlauf ins eigene Wissenssystem). Verdrahtet über `rules` und `operations.*.guidance` in `openspec/config.yaml`.

## Das Modell

![Workflow: links der Ablauf, rechts was wir weglassen und womit es ersetzt wird, unten die Erweiterungspunkte](workflow.svg)

## Skills einbinden

- Die Matt-Pocock-Skills waren schon installiert, aber umbenannt: `to-issues` -> `to-tickets`, `to-prd` -> `to-spec`. Die meisten sind nur per Eingabe aufrufbar und tauchen deshalb in der Skill-Liste des Modells nicht auf.
- Abgrenzung: OpenSpec ist die Spec, `/to-spec` entfällt. `/to-tickets` schneidet den Change in Tickets, `/implement` baut (tdd + code-review), `/triage` ist der Eingang.
- Das Phasenmodell ist bewusst ein Gerüst. Erweiterungspunkte (UI/UX-Prototypen, früher Tester, Rückfragen an einen PO, mehrere Personen) stehen in der Doku, aber noch nicht ausgebaut.

## Schlank bleiben: Status ohne Board

Gedanke für den Post: Ein agiler Prozess hängt nicht am Werkzeug. Zustände (`ready-for-refinement`, `in-refinement`, `in-progress`, `in-review`) lassen sich als Labels (GitHub) oder Tags (Azure DevOps) abbilden, ein Board kommt erst dazu, wenn mehrere Personen mitarbeiten. Ein Feature-Issue kann Sub-Issues haben, an denen verschiedene Personen arbeiten (`/to-tickets` nutzt native Sub-Issue- und Blocking-Beziehungen). Zwei Ebenen: Refinement-Zustände am Feature, Bau-Zustände an den Tickets. Zu klären: Wie viel davon tragen die Skills selbst, wie viel steht nur als Anweisung in der Doku?

## Erster Change: timeline-startseite

- Vorher: Feature-Issue (#13, `status:in-refinement`) und Branch `feature/13-timeline-startseite` von `master`.
- Ergebnis von `propose`: Proposal, zwei Specs (`timeline-entries`, `timeline-view` mit Szenarien), Design mit Entscheidungen und Annahmen, Tasks mit Prüfschritt je Task. `openspec validate --strict` grün.
- Aus der Grilling-Runde davor (12 Fragen) entstand der Plan, daraus der Change fast ohne Rückfragen. Die Annahmen stehen offen im Design zur Prüfung.
- `/to-tickets` ließ sich von Hand nach `SKILL.md` ausführen: Die Tasks (nach Schichten geordnet) wurden zu 5 vertikalen Scheiben umgeschnitten, ich habe sie vorgestellt, du hast sie bestätigt, erst dann habe ich veröffentlicht. Ergebnis: 5 Sub-Issues von #13 (#16 bis #20) mit `ready-for-agent` und nativen `blocked_by`-Beziehungen (Sub-Issue- und Dependency-API von GitHub per `gh api`, funktionierte beim ersten Versuch bis auf eine verlorene Beziehung, die ich nachträglich setzen musste: dort lohnt später eine Prüfung im Skript).
- Beobachtung: `tasks.md` aus OpenSpec ist nach Schichten geordnet (Daten, Ausgabe, Layout), `/to-tickets` verlangt vertikale Scheiben. Beides zusammen braucht eine Übersetzung, die Tasks sind Eingabe, nicht Ergebnis. Eventuell die Task-Regel in `openspec/config.yaml` anpassen ("vertikale Scheiben statt Schichten").

## Ergebnis: der erste Change ist durch

`timeline-startseite` ist umgesetzt und archiviert: eine Timeline auf der Startseite mit Beiträgen, Seiten und manuellen Bookmarks, aufklappbar, mit Nachladen beim Scrollen und einer vollständigen Seite `/timeline/`.

Zahlen: 8 Tickets (Sub-Issues eines Feature-Issues), 9 Pull Requests inklusive CI, 48 Shell-Tests über den Build und 47 Browser-Prüfungen (Kontrast in acht Farbvarianten, Tastatur, 375 px, Nachladen), zwei Specs mit 13 Requirements, die beim Archivieren in `openspec/specs/` gelandet sind.

Was der Prozess gefunden hat:
- **Code-Review über drei Tickets:** zwei echte Fehler gegen die Spec (leere Spalte ohne Einträge, Ende gleich Start), die TDD und Screenshots nicht gezeigt hatten.
- **Abnahme-Skript:** der Link-Kontrast lag in drei hellen Farbvarianten unter 4,5:1 (nord hell 3,31:1). Das Problem trifft alle Links der Seite, nicht nur die Timeline.
- **Branch-Schutz:** Ein PR wurde gemergt, bevor die CI lief. Seitdem verlangt der Branch-Schutz den Check `test`.
- **`tasks.md` nach Schichten:** `/to-tickets` verlangt vertikale Scheiben. Die Task-Regel verlangt jetzt Scheiben, ob das reicht, zeigt der nächste Change.
- **Specs nachgezogen:** Beim Archivieren mussten die Specs an den gebauten Stand angepasst werden (Gleichstand beim Sortieren, Ende gleich Start, Lesbarkeit). Specs, die vor dem Bauen entstehen, sind eine Annahme, keine Wahrheit.

## Der zweite Change: ein Werkzeug, das sich selbst einrichtet

Nach der Timeline kam ein Werkzeug für den Prozess selbst: Zustände, Übergänge und Phasen als Daten (`workflow/*.tsv`), ein Befehl, der sie prüft (`flow validate`), und ein Setup, das nach dem Klonen Voraussetzungen prüft, die Adapter für den eigenen Agenten einrichtet und Labels anlegt (`setup.py`). Es läuft unter Linux, macOS und Windows (Python, nur Standardbibliothek), und das ist in der CI auf allen drei Systemen belegt.

Das Besondere: Ich habe die sechs Tickets einmal komplett selbstständig umsetzen lassen. Pro Ticket erst die Tests (von außen, mit Stub-Programmen für `gh` und `openspec`), dann der Code, dann ein Pull Request, CI auf drei Systemen und Merge bei Grün. Erst am Ende habe ich das Ergebnis angesehen. Was dabei auffiel:
- Die Teststellen von außen tragen: Ein Stub-Programm schrieb in einem frühen Lauf ins echte Repo, weil es im Arbeitsordner des Tests lief. Daraus wurden zwei Schutzmaßnahmen (Arbeitsordner immer das Repo, Stubs schreiben nur im Testordner).
- Ein manueller Probelauf mit den echten Programmen in einem Wegwerf-Klon fand etwas, das die Stubs nicht zeigen konnten: `gh label list` scheitert in einem Klon ohne GitHub-Remote.
- Das Review vor dem Archivieren fand nach 89 grünen Tests noch sechs echte Fehler.

## Weiter

Wie der Prozess erzwungen und geprüft wird (Gates, `kvasir`, Evals, Skills und Rollen als Konfiguration), steht im zweiten Teil: *Den Prozess erzwingen und prüfen*.
