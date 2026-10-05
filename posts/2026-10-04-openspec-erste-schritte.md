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

## Prozess statt Skills, und wie verlässlich ist er?

Beobachtung: Der Ablauf steht in Prosa (`AGENTS.md`, `workflow.md`, Skill-Texte). Ein Agent folgt ihm wahrscheinlich, aber nicht garantiert. Wichtiger als "die Skills benutzt zu haben" ist der Prozess: Jede Phase bekommt Eingang, Ergebnis, Prüfpunkt und Zustandswechsel, das Werkzeug dahinter ist austauschbar.

Leiter von weich nach hart: Prosa, Skill, Skill-Konfiguration, Skript, Hook, CI mit Branch-Schutz. Das Modell urteilt, Skripte und CI erzwingen Übergänge. Nachvollziehbar wird es über Label-Zeitstempel, Session-Links in Commits, protokollierende Hooks und einen Testlauf an einer Beispielaufgabe. Details in `docs/workflow.md`, Abschnitt "Später: Verlässlichkeit und Nachvollziehbarkeit". Noch nicht umgesetzt.

Reihenfolge, die ich verfolge: erst agentenunabhängige Mittel (Git-Hooks, CI, Branch-Schutz), dann ein Skript für Zustandswechsel, dann Phasen als Daten, zuletzt Orchestrierung. Agenten-Hooks sind an den Agenten gebunden, harte Regeln gehören deshalb in Git-Hooks und CI. LangGraph (Ablauf als Graph, Modell nur im Knoten) wäre die härteste Stufe, lohnt aber erst bei unbeaufsichtigtem Betrieb. Leichter davor: GitHub Actions auf Label-Ereignissen.

## Erster Change: timeline-startseite

- Vorher: Feature-Issue (#13, `status:in-refinement`) und Branch `feature/13-timeline-startseite` von `master`.
- Ergebnis von `propose`: Proposal, zwei Specs (`timeline-entries`, `timeline-view` mit Szenarien), Design mit Entscheidungen und Annahmen, Tasks mit Prüfschritt je Task. `openspec validate --strict` grün.
- Aus der Grilling-Runde davor (12 Fragen) entstand der Plan, daraus der Change fast ohne Rückfragen. Die Annahmen stehen offen im Design zur Prüfung.
- `/to-tickets` ließ sich von Hand nach `SKILL.md` ausführen: Die Tasks (nach Schichten geordnet) wurden zu 5 vertikalen Scheiben umgeschnitten, ich habe sie vorgestellt, du hast sie bestätigt, erst dann habe ich veröffentlicht. Ergebnis: 5 Sub-Issues von #13 (#16 bis #20) mit `ready-for-agent` und nativen `blocked_by`-Beziehungen (Sub-Issue- und Dependency-API von GitHub per `gh api`, funktionierte beim ersten Versuch bis auf eine verlorene Beziehung, die ich nachträglich setzen musste: dort lohnt später eine Prüfung im Skript).
- Beobachtung: `tasks.md` aus OpenSpec ist nach Schichten geordnet (Daten, Ausgabe, Layout), `/to-tickets` verlangt vertikale Scheiben. Beides zusammen braucht eine Übersetzung, die Tasks sind Eingabe, nicht Ergebnis. Eventuell die Task-Regel in `openspec/config.yaml` anpassen ("vertikale Scheiben statt Schichten").

## Ein Gate vor der Freigabe: lokale Abnahme

Beim ersten Umsetzungs-PR (Timeline, Ticket #16) kam ein optionaler Schritt dazu: Der PR bleibt Draft, bis ich den Branch lokal ausgecheckt und angesehen habe. Der PR-Text enthält die Befehle (`git switch`, Shell-Check, Seite bauen und starten) und eine Prüfliste, bei sichtbaren Änderungen Screenshots in allen Farbvarianten und auf dem Handy. Ablauf: TDD für alles, was der Build ausgibt (sieben Fälle, jeweils erst rot, dann grün, ein Mutationscheck bestätigt, dass der Test wirklich etwas prüft), Screenshots für alles Optische, danach der Mensch. Das Gate ergänzt die automatischen Prüfungen, ersetzt sie nicht, und entfällt bei reiner Doku.

## Noch zu dokumentieren

- Erster Change von der Idee bis zum Archive.
- Was hat gut funktioniert, was war Overhead?
