# Anleitung: Entwickeln mit dem Workflow (mit und ohne kvasir)

Diese Anleitung zeigt den Entwicklungs-Workflow an einem durchgehenden Beispiel, einmal nur mit den Werkzeugen des Repos und einmal zusätzlich mit **kvasir** (Sicht auf Status, Abhängigkeiten, Termine). Sie ersetzt `docs/workflow.md` nicht: Die Referenz (Spalten, Regeln, Spezialfälle) bleibt dort, hier steht der Ablauf zum Mitmachen.

## Lesereihenfolge

| Datei | Inhalt | Wann lesen |
| --- | --- | --- |
| [01-landkarte.md](01-landkarte.md) | Bausteine, Rollen, Zustände, Phasen als Diagramme | zuerst |
| [02-beispiel-workflow.md](02-beispiel-workflow.md) | Beispiel von Setup bis Archivierung, nur mit Repo-Werkzeugen | zum Mitmachen |
| [03-beispiel-mit-kvasir.md](03-beispiel-mit-kvasir.md) | dasselbe Beispiel, mit kvasir als Sicht | wenn kvasir installiert ist |
| [04-konfiguration.md](04-konfiguration.md) | alle Konfigurationsdateien, was drinsteht, wie man sie ändert | beim Anpassen |
| [05-gates-und-fehlersuche.md](05-gates-und-fehlersuche.md) | Gates, optionale Teile, typische Probleme, Onboarding-Checkliste | bei Problemen |

## Legende

- **echt**: Ausgabe stammt aus einem Lauf in diesem Repo (Stand 2026-10-07).
- **illustrativ**: Das Beispiel (Feature "Tag-Übersicht", Tickets #101 bis #105) ist erfunden, damit die Nummern nicht mit echten Tickets kollidieren. Befehle und Dateiformate sind echt, die Ausgabe ist an das Beispiel angepasst.
- **Mensch** / **Agent** vor einem Schritt sagt, wer ihn tut. "Agent" ist ein KI-Agent mit Skill-Unterstützung (hier Claude Code). Jeder Schritt lässt sich auch von Hand tun, die Skills sind Abkürzungen.
- **Pflicht** / **optional**: Was ohne Funktion nicht fehlen darf und was man weglassen kann.

## Das Beispiel in einem Satz

Auf der Blog-Startseite soll eine Seite `/tags/` die Tags mit der Anzahl ihrer Beiträge zeigen. Das ist klein genug für eine Seite Anleitung und groß genug für alle Phasen: ein Feature-Issue, ein OpenSpec-Change, vier Tickets mit Abhängigkeiten, vier PRs.
