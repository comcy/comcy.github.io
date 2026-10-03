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

## Aufbau

| Pfad | Inhalt |
|---|---|
| `build.sh` | Build-Skript (POSIX sh) |
| `site.conf` | Titel, Autor, URL |
| `templates/page.html` | HTML-Template für pandoc |
| `static/` | CSS und andere Dateien, werden 1:1 kopiert |
| `pages/` | Startseite, Über mich, Galerie-Text und weitere Seiten |
| `.github/workflows/deploy.yml` | Baut und veröffentlicht bei jedem Push auf `master` |

## Einmalig in GitHub einstellen

*Settings → Pages → Build and deployment → Source: GitHub Actions*

## Theme und JavaScript

Das Theme "Modern Glass" steckt komplett in `static/style.css`, Hell/Dunkel wird über `data-theme` am `<html>`-Element gesteuert.
`static/site.js` wird auf jeder Seite geladen (Umschalter, Kopieren-Button). In einzelnen Posts kannst du zusätzlich
rohes HTML mit Script-Blöcken direkt in die Markdown-Datei schreiben, pandoc reicht es unverändert durch.
