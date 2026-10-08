---
title: Den Prozess erzwingen und prüfen – Gates, kvasir und Evals
date: 2026-10-08
tags: [ai, openspec, workflow]
description: Wie aus einem beschriebenen Entwicklungsprozess einer wird, den Hooks, CI und Evals prüfen, mit Agenten als Umsetzer.
draft: true
---

*Entwurf, Fortsetzung von "OpenSpec einrichten". Material statt Fließtext.*

## Prozess statt Skills, und wie verlässlich ist er?

Beobachtung: Der Ablauf steht in Prosa (`AGENTS.md`, `workflow.md`, Skill-Texte). Ein Agent folgt ihm wahrscheinlich, aber nicht garantiert. Wichtiger als "die Skills benutzt zu haben" ist der Prozess: Jede Phase bekommt Eingang, Ergebnis, Prüfpunkt und Zustandswechsel, das Werkzeug dahinter ist austauschbar.

Leiter von weich nach hart: Prosa, Skill, Skill-Konfiguration, Skript, Hook, CI mit Branch-Schutz. Das Modell urteilt, Skripte und CI erzwingen Übergänge. Nachvollziehbar wird es über Label-Zeitstempel, Session-Links in Commits, protokollierende Hooks und einen Testlauf an einer Beispielaufgabe. Details in `docs/workflow.md`, Abschnitt "Später: Verlässlichkeit und Nachvollziehbarkeit". Inzwischen größtenteils umgesetzt, siehe die Abschnitte weiter unten (Gates, Zustandswechsel, kvasir, Evals).

Reihenfolge, die ich verfolge: erst agentenunabhängige Mittel (Git-Hooks, CI, Branch-Schutz), dann ein Skript für Zustandswechsel, dann Phasen als Daten, zuletzt Orchestrierung. Agenten-Hooks sind an den Agenten gebunden, harte Regeln gehören deshalb in Git-Hooks und CI. LangGraph (Ablauf als Graph, Modell nur im Knoten) wäre die härteste Stufe, lohnt aber erst bei unbeaufsichtigtem Betrieb. Leichter davor: GitHub Actions auf Label-Ereignissen.

## Der dritte Block: der Prozess erzwingt sich selbst

Bis hierhin stand der Prozess in Prosa und in Daten. Jetzt kommt die harte Seite dazu, die für jede Person und jeden Agenten gilt:
- **Gates:** Ein Skript `gate.py` prüft Conventional Commits und sucht Secrets in den hinzugefügten Zeilen (Meldung nennt Datei und Regel, nie den Wert). Dieselbe Logik läuft als Git-Hook (`commit-msg`, `pre-commit`, dünne `sh`-Hüllen) und als CI-Job `gates`, der auch Commits mit `--no-verify` findet. Beleg: ein Wegwerf-PR mit falschem Commit ließ `gates` rot werden.
- **Zustandswechsel als Befehl:** `flow start` und `flow review` setzen Branch und `status:`-Label nach `transitions.tsv` und werten die Bedingungen (`guard`) aus: kein Start bei offenem Blocker oder ohne `ready-for-agent`, kein Review ohne grüne Checks.
- **Ein Fehler, den erst das Review fand:** Der Secret-Scan prüfte den Netto-Diff eines Bereichs. Ein im Bereich hinzugefügtes und wieder entferntes Secret wäre unentdeckt geblieben, obwohl es in der History steht. Jetzt wird jeder Commit geprüft.
- **Parallele Agenten:** Mehrere Agenten in getrennten Worktrees teilen sich `git stash`. Zwei Agenten tauschten dadurch gegenseitig ihre Änderungen. Seitdem steht in jeder Anweisung "kein `git stash`", und Baseline-Läufe laufen in einem eigenen Worktree.
- **Windows-Fallen in Tests:** `.cmd`-Wrapper werden von `subprocess` ohne `shutil.which` nicht gefunden, `cmd.exe` verschluckt `^` in Git-Argumenten (`c^` wurde zu `c`, der Test prüfte den falschen Stand), und stderr braucht UTF-8. Alle drei zeigte erst die Windows-CI.
- **Aufräumen automatisieren:** Nach dem Merge blieb `status:in-progress` an geschlossenen Tickets. kvasir zeigte den Widerspruch an (`! Label sagt in-progress, Issue ist geschlossen`), eine Action entfernt das Label jetzt beim Schließen.

## kvasir als Sicht

Der Prozess ist als Daten beschrieben, kvasir (mein Terminal-Werkzeug für Worktrees) macht den Stand sichtbar, rein lesend: `kvasir status '#N'` zeigt Sub-Issues, Blocker und den Status **aus Fakten** (Issue-Zustand, Blocker, PRs, Branches), Labels sind nur Hinweise, Widersprüche werden angezeigt. Dazu ein Stepper aus den Phasen von `workflow/phases.tsv`, Termine aus Meilenstein und Zeilen `Geplant:`/`Frist:`, `kvasir graph` (Mermaid und HTML mit Spuren je Feature) und ein Panel in der TUI. Das Vokabular der Bedingungen steht in `workflow/detectors.tsv`, beide Werkzeuge lesen dieselbe Quelle. Umsetzung: acht Tickets, jedes von einem Agenten gebaut, von mir geprüft und bei grünen Tests gemergt.

## Evals: hält sich der Agent an den Prozess?

Die Tests prüfen unsere Werkzeuge, aber nicht, ob sich der Agent an den Prozess hält. Das tun Evals: kleine Aufgaben, bei denen ein Skript den **Endzustand** prüft (kein Branch bei offenem Blocker, kein Commit mit Secret, roter Test vor dem Fix, kein `git stash`), nie den Wortlaut der Antwort. Der Runner startet den Agenten über einen **Adapter** (`claude -p` ist einer, jedes andere Programm mit JSON über stdin und stdout kann ein anderer sein), drei Läufe je Aufgabe, bestanden ab zwei von drei. Ein Bericht mit Diagramm und Vergleich zum letzten Lauf wird eingecheckt.

- **Isolation gemessen:** Im ersten Probelauf liefen mein SessionStart-Hook, fünf Plugins, ein MCP-Server und Auto-Memory aus dem echten HOME mit. Ohne Messung wäre das unbemerkt geblieben.
- **Erster Fund:** 6 von 7 Aufgaben bestanden. Der Agent behob den Fehler richtig, schrieb aber keinen Test, weil `AGENTS.md` TDD nicht verlangte (nur der Skill). Nach einer Zeile in `AGENTS.md` bestand die Aufgabe.
- **Aus der Konfiguration abgeleitet:** Für jeden Übergang mit Bedingung in `transitions.tsv` entsteht automatisch eine Aufgabe "Übergang bei verletzter Bedingung muss abbrechen", soweit der Stub den Zustand abbilden kann. Der Bericht nennt den Rest als "nicht ableitbar".
- **Grenze:** Der Agent ist nicht sandboxed. Der Test gegen Fakes sagt nichts über Schreibzugriffe außerhalb des Wegwerf-Repos.

## Das Profil: Skills, Rollen und ein Setup, das die Lücken zeigt

Die Konfiguration kennt jetzt auch `skills.tsv` (welcher Skill gehört zu welcher Phase, Pflicht oder optional) und `roles.tsv` (welche Rolle führt eine Phase aus, welche Tools sind erlaubt, wo ist ein menschliches Gate). `setup --check <agent>` prüft, ob die Skills installiert sind, und nennt den Installationshinweis. Pflichtphasen ohne Skill oder Rolle meldet `flow validate`. Skills sind agentenspezifisch, die Konfiguration kann sie nur beschreiben und verlangen. Dieselbe Konfiguration lässt sich so auf einem anderen Rechner, mit einem anderen Agenten oder Modell prüfen (über den Adapter), ob ein lokales Modell dabei sauber Tool-Aufrufe liefert, ist ungeprüft.

## Die Arbeitsweise dahinter

Fast alles in diesem Block hat ein Agent umgesetzt, den ich pro Ticket gestartet habe, in einem eigenen Git-Worktree. Ich habe jeden Pull Request geprüft (Tests, Linter, Diff, CI auf drei Systemen) und bei Grün selbst gemergt, nur im ausdrücklich erteilten Umfang. Was dabei auffiel:
- Reviews mit zwei getrennten Achsen (Standards, Spec) fanden nach grünen Tests jedes Mal echte Fehler.
- Die Agenten machen die gleichen Windows-Fehler wiederholt, bis die CI sie zeigt.
- Ein Agent erkannte einen Hinweis in einem Tool-Ergebnis (angebliche Rate-Limit-Meldung) als nicht von mir stammend und ignorierte ihn.
- Meine eigenen Fehler: zweimal Worktree und Branch aufgeräumt, obwohl der PR noch offen war; ein Syntaxfehler beim Reparieren, den die CI sofort zeigte.

## Noch zu dokumentieren

- Voller Eval-Lauf (drei Läufe je Aufgabe, 2026-10-08): Die sieben handgeschriebenen Aufgaben bestanden alle 3 von 3, also stabil. Von den acht abgeleiteten bestanden fünf 3 von 3; bei den drei Aufgaben "Ticket nach `closed`" lag der Fehler in meiner Ableitung (`issue_closed` ist dort das Ereignis, keine Vorbedingung), nicht im Agenten. Sie gelten jetzt als nicht ableitbar. Der erste volle Versuch traf außerdem das Sitzungslimit des Abos und lieferte falsche Durchfälle, daher bricht der Adapter bei einem Limit jetzt ab statt Aufgaben durchfallen zu lassen. Ein Satz kostet rund 17 bis 21 Minuten und rechnerisch 2,6 bis 3,7 USD (Abo-Kontingent, keine Rechnung).
- Erster Lauf mit einem anderen Agenten oder Modell über einen eigenen Adapter.
- Sandbox für den Agenten.
- Overhead: Proposal, Specs und Tickets lohnen sich bei Werkzeug-Änderungen, bei Kleinigkeiten nicht (noch nicht gemessen).
- Die Anleitung mit Beispielablauf liegt in `docs/anleitung/` im Repo.
