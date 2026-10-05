---
title: kvasir als Helfer im Entwicklungsprozess
date: 2026-10-05
tags: [ai, kvasir, prozess]
description: Wie aus einem Worktree-Manager ein Werkzeug wird, das Abhängigkeiten, Status, Zeitplan und Prozessstand sichtbar macht, deterministisch und ohne Modell.
draft: true
---

*Entwurf, Material zum Ausformulieren. Noch nichts davon ist gebaut, Stand der Planung: 2026-10-05.*

## Ausgangslage

kvasir ist mein Terminal-Tool für Git-Worktrees: Python mit Textual, eine TUI mit drei Spalten (Repos, Worktrees und Branches, Details), Bare-Layout mit einem Worktree pro Branch, Notizen, Fetch im Intervall. Dazu gibt es eine Plattformschicht für GitHub (über `gh`) und Azure DevOps (über `az`): Pull Requests, Pipelines und Work Items zum Branch, rein lesend und ohne Token in kvasir.

Was fehlt, merkt man erst, wenn ein Prozess mit Tickets läuft: Ich habe Sub-Issues, `blocked_by`-Beziehungen und Status-Labels, aber keine Sicht darauf.

## Was ich sehen will

- Welche Work Items hängen voneinander ab?
- Was ist offen, in Arbeit, in Review oder erledigt?
- Gibt es einen Zeitplan, wenn Items Termine haben (Frist, Quartalsende, Sprintende)?
- Wo stehe ich selbst im Prozess: was war davor, was kommt noch, in welchem Schritt bin ich?

GitHub Projects kann Spalten und eine Roadmap, zeigt aber keinen Abhängigkeitsgraphen und braucht zusätzliche Token-Rechte. Und ich will es später auch für Azure DevOps.

## Die Entscheidungen (aus einer Grilling-Runde, elf Fragen)

- **kvasir ist der Motor, deterministisch und ohne Modell.** Es liest, rechnet und zeigt an. Gleiche Eingabe, gleiche Ausgabe. Ein Skill ist nur eine dünne Hülle ("Wo stehe ich? Rufe `kvasir status --json` auf und erkläre den nächsten Schritt"), er enthält keine Logik.
- **Rein lesend.** Die Ausgabe geht nach stdout oder in eine Datei. Wer sie im Tracker haben will, kopiert sie oder lässt es einen CI-Schritt tun.
- **Fakten vor Labels.** Der Status kommt aus Tatsachen: Issue geschlossen, offene Blocker, PR als Draft oder bereit, Branch mit Issue-Nummer. Ein `status:*`-Label ist ein Hinweis. Widersprüche werden angezeigt, nicht still korrigiert.
- **Große Ansicht:** eine Spur je Feature, Kanten für Abhängigkeiten, der Status als Farbe, waagerecht Abhängigkeitstiefe oder, wo Termine gesetzt sind, die Zeit. Ein eigener **Stepper** zeigt als Kontext, was erledigt ist, wo ich bin und was fehlt.
- **Termine:** Meilenstein für Fristen und Sprints, eine feste Zeile im Issue für Zeiträume und Quartalsende (`Geplant: …`, `Frist: Ende Q4 2026`). Ohne Termine gibt es nur eine Reihenfolge nach Abhängigkeit, keine erfundene Zeit.
- **Konfiguration als Daten:** eine `kvasir.toml` im Repo mit den Phasen des Prozesses und weiteren Einstellungen. Die Datei wählt nur aus einem festen Vokabular von Detektoren (`pr_state:draft`, `issue_closed` …), sie enthält keinen ausführbaren Code. `kvasir init` legt sie an, `kvasir doctor` prüft sie.
- **kvasir ist empfohlen, aber nicht zwingend.** Der Prozess läuft auch ohne, nur ohne diese Sicht. Das Setup-Skript im Repo bleibt der unabhängige Einstieg.

## Vom Plan zu Tickets

Aus den Entscheidungen wurden acht Tickets als vertikale Scheiben (jede einzeln nutzbar), verknüpft über Sub-Issues und `blocked_by`:

| Ticket | Inhalt | Blockiert von |
| --- | --- | --- |
| 1 | `kvasir status`: Status und Beziehungen aus Fakten | – |
| 2 | Prozess-Stepper | 1 |
| 3 | Termine (Meilenstein, `Geplant:`, `Frist:`) | 1 |
| 4 | Mermaid-Graph mit Spuren, Statusfarben, Gantt | 1, 3 |
| 5 | `kvasir.toml`, `init`, `doctor` | 2 |
| 6 | TUI-Panel | 2 |
| 7 | HTML-/SVG-Ansicht mit Spuren und Zeitachse | 4 |
| 8 | Azure DevOps | 1 |

Nach Ticket 1 laufen 2, 3 und 8 parallel. Das Schöne: Der Graph, den ich bauen will, ist genau dieser. Die acht Tickets sind sein erstes Testbild.

## Noch offen

- Wie gut trägt der Stepper, wenn Belege fehlen? Er soll nichts behaupten, was er nicht sieht.
- Reicht die Zeile im Issue für Termine, oder kommen am Ende doch die Projects-Felder dazu?
- Lohnt die HTML-Ansicht gegenüber Mermaid, oder reicht Mermaid für fast alles?
- Messen: Wie viel Zeit spart die Sicht tatsächlich, verglichen mit dem Durchklicken der Issues?

*Zu ergänzen, sobald Ticket 1 und 2 laufen: Screenshots der Ausgabe, ein Beispiel für den Stepper, die Erfahrung mit Fakten gegen Labels.*
