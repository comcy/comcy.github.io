# Blog

Statische Seite aus Markdown, gebaut mit einer POSIX-Shell und [pandoc](https://pandoc.org),
veröffentlicht über GitHub Actions auf GitHub Pages.

## Schreiben

Neuer Post: `posts/JJJJ-MM-TT-slug.md`

```markdown
---
title: Titel des Posts
date: 2026-10-03
tags: [agile, ai, angular, scrum]
description: Ein Satz für Übersicht, Feed und Suchmaschinen.
draft: true   # weglassen, sobald der Post online gehen soll
---

Text in Markdown …
```

Bilder zu einem Post kommen in einen gleichnamigen Ordner (`posts/JJJJ-MM-TT-slug/bild.jpg`)
und werden im Text als `![Beschreibung](bild.jpg)` eingebunden.
Galeriebilder kommen nach `gallery/`, eine Bildunterschrift optional in `gallery/<bild>.txt`.

## Timeline

Die Startseite zeigt eine Timeline mit den `TL_MAX` neuesten Einträgen (Wert in `build.sh`, derzeit 8): alle Beiträge und Seiten mit `date:` im
Frontmatter (nicht Startseite und Galerie, Entwürfe nur mit `DRAFTS=1`) sowie manuelle Bookmarks aus `timeline/`.
Ein Bookmark ist eine Datei `timeline/JJJJ-MM-TT-slug.md` (Datum im Namen nur zur Sortierung im Ordner) ohne eigene Seite, die Beschreibung klappt auf:

```markdown
---
title: Entwicklungsprozess mit OpenSpec aufgesetzt
date: 2026-10-04      # JJJJ, JJJJ-MM oder JJJJ-MM-TT (fehlender Teil zählt als der erste)
end: now              # optional: Datum im selben Format oder now = laufend
description: Ein Satz, der beim Aufklappen erscheint.
---
```

Weitere Einträge lädt die Startseite beim Scrollen im Container nach (Fragmente `/timeline/chunk-N.html` mit je 10 Einträgen, `static/timeline.js`). Ohne JavaScript führt "Alles ansehen" auf `/timeline/`. Die Browser-Prüfung dazu steht in `tests/browser/timeline-nachladen.mjs` (manuell, mit Chromium).

Fehlendes oder ungültiges Datum, fehlender Titel und ein Ende vor dem Start brechen den Build mit dem Dateinamen ab.

## Lokal ansehen

```sh
SITE_URL=http://localhost:8000 DRAFTS=1 ./build.sh
python3 -m http.server -d public 8000
```

## Prozess einrichten

Nach dem Klonen (Python ab 3.11, nur Standardbibliothek; unter Windows `py -3` statt `python3`):

```sh
python3 scripts/setup.py --check           # prüft Programme, Adapter, Labels und workflow/, ändert nichts
python3 scripts/setup.py claude            # richtet den lokalen Klon für Claude Code ein
python3 scripts/setup.py --labels claude   # legt zusätzlich fehlende Labels auf GitHub an
python3 scripts/flow.py validate           # prüft die Dateien unter workflow/
```

Details und Hintergründe: `docs/workflow.md` (Abschnitte "Setup nach dem Klonen" und "Prozessdaten"). Die Dateien unter
`workflow/` und `scripts/setup.d/` sind tabulatorgetrennt (Tabs, keine Leerzeichen); `flow validate` meldet Spaltenzahl
und Zeile.

## Prüfen

```sh
sh tests/run.sh
```

`tests/run.sh` führt alle `tests/*-check.sh` (Blog, Shell) und die Python-Tests `tests/test_*.py` (Prozess) aus (Fehlercode bei einem roten Fall). Die Python-Tests allein: `python3 -m unittest discover -s tests -p "test_*.py"`. In der CI läuft er auf jedem
Pull Request (`.github/workflows/test.yml`) und vor dem Veröffentlichen (`deploy.yml`).

Baut die Seite in temporären Klonen mit eigenen Beiträgen und prüft die Timeline auf der Startseite
(Anzahl, Reihenfolge, Datumsformate, Entwürfe, leere Seite). Kein Framework, nur `sh`, `pandoc`, `grep`.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `build.sh` | Build-Skript (POSIX sh) |
| `site.conf` | Titel, Autor, URL |
| `templates/page.html` | HTML-Template für pandoc |
| `timeline/` | Manuelle Timeline-Einträge (Bookmarks), eine Datei je Eintrag |
| `templates/timeline-meta.txt` | Metadaten-Vorlage für Seiten und Bookmarks der Timeline |
| `workflow/` | Prozessdaten (Zustände, Übergänge, Phasen, Detektoren), Quelle der Labels |
| `scripts/` | `setup.py`, `flow.py` und `lib/` (Python), `setup.d/` mit `tools.tsv` und `agents.tsv` |
| `tests/` | Shell-Checks, z. B. `timeline-check.sh` |
| `static/` | CSS und andere Dateien, werden 1:1 kopiert |
| `pages/` | Startseite, Über mich, Galerie-Text und weitere Seiten |
| `.github/workflows/deploy.yml` | Baut und veröffentlicht bei jedem Push auf `master` |

## Einmalig in GitHub einstellen

*Settings → Pages → Build and deployment → Source: GitHub Actions*

## Theme und JavaScript

Das Theme "Modern Glass" steckt komplett in `static/style.css`, Dunkel ist der Standard, Hell wird über `data-theme="light"` am `<html>`-Element gesteuert.
`static/site.js` wird auf jeder Seite geladen (Umschalter, Kopieren-Button). In einzelnen Posts kannst du zusätzlich
rohes HTML mit Script-Blöcken direkt in die Markdown-Datei schreiben, pandoc reicht es unverändert durch.

## Farbschemata

Es gibt vier Farbschemata: "Modern Glass" (Standard), "Nord" (Farbpalette von
[insanum/obsidian_nord](https://github.com/insanum/obsidian_nord)), "Neon" (Dunkelblau zu Lila mit Neon-Pink, -Gelb, -Grün und Lila)
und "Pastell" (dieselben Akzente in Pastell). Der Knopf mit der Palette (🎨) in der Kopfleiste öffnet eine Auswahl mit allen Schemata, jeweils in Dunkel und Hell (acht Varianten).
Der Sonne/Mond-Knopf wechselt wie gehabt schnell zwischen Hell und Dunkel. Beides wird im Browser gemerkt. Die Liste der Schemata steht in `static/site.js`.
Ein weiteres Schema ergänzt du in `static/style.css` mit einem Block `:root[data-palette="name"]`.
