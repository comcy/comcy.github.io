# Plan: Timeline auf der Startseite und zweisprachiger Blog

Stand: 2026-10-04 (nach Grilling, alle offenen Fragen entschieden). Beides bleibt bei POSIX-Shell + pandoc, keine neuen Abhängigkeiten, kein JS-Framework.

## Reihenfolge

1. **PR 1: Timeline**, nur Deutsch. Kein Umbau der Struktur.
2. **PR 2: Zweisprachigkeit**, eigener PR, weil er die Struktur anfasst. Zieht die Timeline mit.

Beide PRs bekommen Screenshots (Desktop und Mobil, mehrere Themes).

## 1. Timeline (PR 1)

### Idee

Senkrechte Linie von oben nach unten, chronologisch, neueste zuerst. Je Eintrag Datum + Titel, später optional eine Zusatz-Property. Punkte in der Akzentfarbe des aktuellen Themes.

### Quellen

- **Automatisch:** jede Markdown-Datei mit `date:` im Frontmatter (Posts, Seiten, später mehr). Ohne `date:` kein Eintrag, `draft` bleibt draußen (wie beim Blog). `pages/about.md` erscheint also erst, wenn ein Datum gesetzt wird.
- **Manuell ("Bookmarks"):** Ordner `timeline/`, eine Datei je Eintrag. Keine öffentliche Seite.
- Galerie-Bilder sind vorerst keine Quelle (kein Datum). Später optional über `gallery/<bild>.txt`.

```
timeline/2024-05-vortrag.md          Bookmark
timeline/2024-05-vortrag/            optional: Bilder, Slides zum Eintrag
```

Der Ordner neben der Datei wird wie bei Posts (`posts/<name>/`) mitkopiert. Ein Eintrag hat immer ein Datum.

```yaml
title: Titel
date: 2024-05            # YYYY, YYYY-MM oder YYYY-MM-DD
end: 2024-11             # optional, siehe unten
description: Text für den Aufklapp-Teil.
```

Fehlende Datumsteile gelten als Monats- bzw. Jahresanfang.

### Darstellung

- **Startseite:** zweite Spalte neben Willkommen/Profil, mobil darunter. Die 8 neuesten Einträge stehen direkt im HTML (SEO, ohne JS lesbar).
- **Container mit fester Höhe** (Höhe des Profilblocks, mobil z. B. 60vh) und eigenem Scroll, damit die Startseite nicht länger wird.
- **Nachladen:** `build.sh` rendert den Rest als Fragmente `/timeline/chunk-2.html`, `chunk-3.html` … (je 10 Einträge). Ein `IntersectionObserver` am Listenende holt den nächsten Chunk per `fetch` (ca. 20 Zeilen JS).
- **Ohne JS:** Link "Alles ansehen" führt auf `/timeline/` mit der vollen Liste, gleiche Daten.
- **Einträge mit Seite** (Posts): Titel ist Link, Beschreibung steht als Zeile darunter.
- **Bookmarks ohne Seite:** Titel ist `<summary>`, Text/Bild/Link im aufgeklappten `<details>`. Eine Mechanik für Maus und Touch, kein JS, kein Hover-Popover.

### Zeiträume (`end:`)

- Das Datenmodell kennt `end:` von Anfang an. **Phase 1 zeigt es nur als "Datum – Datum" im Aufklapp-Teil.**
- **Später:** Git-Graph-Optik (Branch am Start, Merge am Ende, eigene Spur, greedy erste freie Spalte, max. 3 bis 4 Spuren). Erst bauen, wenn tatsächlich Zeiträume gepflegt werden. Kosten: Spurenlogik, Mobilbreite, Touch, alle acht Farbvarianten.
- `end: now` = laufend, Branch bleibt offen.

### Inhalt

- Themen und Projekte ja, **Arbeitgebernamen standardmäßig nein**, kein `company`-Feld. Das Repo ist öffentlich, die Git-History bleibt dauerhaft nachlesbar. Wer einen Arbeitgeber nennen will, schreibt es bewusst in die Beschreibung.
- Lebenslauf bleibt eigene Seite (`pages/about.md`), nicht Teil der Timeline.

### Betrifft

`build.sh` (Index-Schleife, Chunks, `/timeline/`), `templates/page.html`, `static/style.css` (alle acht Farbvarianten), `static/site.js`, README.

**Aufwand:** mittel.

## 2. Zweisprachig DE/EN (PR 2)

### URLs und Inhalte

Deutsch bleibt unter `/`, Englisch unter `/en/`. Bestehende Links ändern sich nicht. Eine Übersetzung ist eine Schwesterdatei mit Suffix `.en.md`, gleicher Name paart die Sprachen, kein Extra-Frontmatter.

```
posts/2026-10-03-warum-dieser-blog.md      (DE)
posts/2026-10-03-warum-dieser-blog.en.md   (EN, optional)
pages/about.md / pages/about.en.md
pages/index.md / pages/index.en.md
timeline/2024-05-vortrag.md / timeline/2024-05-vortrag.en.md
```

- **Fehlende Übersetzung:** Der Eintrag erscheint nur in der Sprache, in der er existiert. Kein Fallback, keine halben Seiten, keine toten Links, kein Build-Warnen.
- **Single Source:** Datum, `end` und Anhänge-Ordner stammen aus der DE-Datei. Die EN-Datei überschreibt nur Texte.
- **Glob-Falle:** Die Globs `posts/*.md`, `pages/*.md`, `timeline/*.md` in `build.sh` müssen `*.en.md` ausschließen und je Sprache filtern. Sonst entsteht aus `x.en.md` der Slug `x.en`. Das ist der Kern des Umbaus.

### Oberflächentexte und Build

- Menü, "Weiterlesen", Tags, Footer, Datumsformat: `i18n/de.conf` und `i18n/en.conf` mit Variablen, von `build.sh` per `. ./i18n/$LANG.conf` eingelesen und an das Template übergeben.
- `build.sh` läuft in einer Schleife `for LANG in de en`. Je Sprache: Blogindex, Tags, Galerie, Seiten, Timeline samt Chunks und ein eigener Feed (`feed.xml`, `en/feed.xml`).

### Umschalter

- `DE | EN` im Header, **nicht** im 🎨-Panel (Sprache ist Inhalt und URL, nicht Aussehen). Mobil als letzte Zeile im Dropdown-Menü.
- Echte `<a href>` auf die Übersetzung der aktuellen Seite, sonst auf die Startseite der anderen Sprache.
- **Gespeicherte Wahl:** nur durch expliziten Klick gesetzt, in `localStorage` (kein Cookie, der Server liest ihn nie). Ein kurzes Script macht bei abweichender gespeicherter Sprache und vorhandener Übersetzung (`<link rel=alternate hreflang>` im Head) `location.replace(alternate)`. `replace` verhindert Zurück-Schleifen. Ohne Übersetzung bleibt die Seite stehen.
- **Nie** Umleitung nach Browsersprache. Crawler und Nutzer ohne JS sehen keinen Redirect.

### SEO und Technik

`<html lang>`, `hreflang`-Alternates, Sprache im Atom-Feed. Sitemap später.

### Übersetzen

Ich entwerfe die englischen Fassungen des Bestands, Chris prüft vor dem Merge (Ton: nah am Original, keine Glättung).

- Umfang PR 2: `i18n/en.conf`, `index`, `about`, `slides`, Galerie-Intro, beide Posts.
- Neue Posts: EN optional, Entscheidung je Post.
- Timeline-Bookmarks: nur bei Bedarf.

### Betrifft

`build.sh`, `templates/page.html`, Header (mobil beachten), `static/site.js`, README.

**Aufwand:** mittel.

## Entschiedene Fragen (zuvor offen)

| Frage | Entscheidung |
| --- | --- |
| Was in die Timeline? | Alles mit `date:` plus manuelle Bookmarks aus `timeline/` |
| Firmennamen? | Standardmäßig nein, kein `company`-Feld |
| Sprachumschalter wo? | Header, mobil im Dropdown; Wahl in `localStorage` |
| Wer übersetzt? | Claude entwirft, Chris reviewt; neue Posts optional |
| Git-Graph? | Später, erst wenn Zeiträume gepflegt werden |
