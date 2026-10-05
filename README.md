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

## Lokal ansehen

```sh
SITE_URL=http://localhost:8000 DRAFTS=1 ./build.sh
python3 -m http.server -d public 8000
```

## Prüfen

```sh
sh tests/timeline-check.sh
```

Baut die Seite in temporären Klonen mit eigenen Beiträgen und prüft die Timeline auf der Startseite
(Anzahl, Reihenfolge, Datumsformate, Entwürfe, leere Seite). Kein Framework, nur `sh`, `pandoc`, `grep`.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `build.sh` | Build-Skript (POSIX sh) |
| `site.conf` | Titel, Autor, URL |
| `templates/page.html` | HTML-Template für pandoc |
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
