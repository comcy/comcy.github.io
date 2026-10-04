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

Offene Frage: Claude Code liest Projekt-Skills aus `.claude/skills/`. Ob `.agents/skills/` ohne lokalen Symlink erkannt wird, ist noch zu prüfen.

## Workflow definieren

Entscheidung: OpenSpec hält fest, *was* gelten soll, GitHub-Issues, `tdd` und `code-review` erledigen das Bauen. Beschrieben in `docs/workflow.md`: Teil A generisch mit Voraussetzungen (später Basis für ein Setup-Skript), Teil B repo-spezifisch; persönliche Anpassungen sind als Haken vorgesehen, stehen aber nicht im Dokument. Verdrahtet über `rules` und `operations.*.guidance` in `openspec/config.yaml`.

## Das Modell

![Workflow: links der Ablauf, rechts was wir weglassen und womit es ersetzt wird, unten die Erweiterungspunkte](workflow.svg)

## Skills einbinden

- Die Matt-Pocock-Skills waren schon installiert, aber umbenannt: `to-issues` -> `to-tickets`, `to-prd` -> `to-spec`. Die meisten sind nur per Eingabe aufrufbar und tauchen deshalb in der Skill-Liste des Modells nicht auf.
- Abgrenzung: OpenSpec ist die Spec, `/to-spec` entfällt. `/to-tickets` schneidet den Change in Tickets, `/implement` baut (tdd + code-review), `/triage` ist der Eingang.
- Das Phasenmodell ist bewusst ein Gerüst. Erweiterungspunkte (UI/UX-Prototypen, früher Tester, Rückfragen an einen PO, mehrere Personen) stehen in der Doku, aber noch nicht ausgebaut.

## Noch zu dokumentieren

- Erster Change von der Idee bis zum Archive.
- Was hat gut funktioniert, was war Overhead?
