# Proposal

## Why

Die Startseite zeigt nur Profiltext und die fünf neuesten Beiträge. Wer die Seite besucht, sieht nicht, was über die Zeit passiert ist: Beiträge, Projekte, Vorträge. Eine chronologische Timeline macht den Verlauf auf einen Blick sichtbar, ohne dass dafür jedes Ereignis eine eigene Seite braucht. Sie ist außerdem die Grundlage für die spätere zweisprachige Fassung, die auf denselben Einträgen aufbaut.

## What Changes

- Neue Timeline auf der Startseite: senkrechte Linie, neueste Einträge oben, Punkte in der Akzentfarbe des aktuellen Themes (alle Farbschemata, hell und dunkel).
- Einträge entstehen automatisch aus allen veröffentlichten Markdown-Inhalten mit `date:` im Frontmatter (Beiträge, später Seiten). Entwürfe bleiben draußen.
- Neuer Ordner `timeline/` für manuelle Einträge ("Bookmarks"). Ein Bookmark hat Titel, Datum, optionales Enddatum und eine Beschreibung. Er erzeugt keine eigene Seite, die Beschreibung klappt per `<details>` auf.
- Startseite zeigt die 8 neuesten Einträge in einem Container mit fester Höhe. Weitere Einträge werden beim Scrollen aus vorgerenderten Fragmenten nachgeladen (je 10 Einträge, kein Framework).
- Eigene Seite `/timeline/` mit der vollständigen Liste, erreichbar über "Alles ansehen". Sie dient auch als Rückfall ohne JavaScript.
- Zeiträume: `end:` ist im Frontmatter erlaubt und erscheint als "Datum – Datum" im aufgeklappten Teil. Eine Darstellung als Branch/Merge ist nicht Teil dieser Änderung.
- Layout der Startseite: Timeline als zweite Spalte neben Profil und neuesten Beiträgen, mobil untereinander.

## Capabilities

### New Capabilities

- `timeline-entries`: Woher Einträge kommen und wie sie aussehen als Daten: Quellen, Frontmatter-Felder, Datumsformate, Sortierung, Ausschluss von Entwürfen, Bookmarks im Ordner `timeline/`.
- `timeline-view`: Wie die Timeline erscheint: Startseiten-Spalte mit Scroll-Container, Aufklapp-Bookmarks, Nachladen in Fragmenten, vollständige Seite `/timeline/`, Verhalten ohne JavaScript, Barrierefreiheit und Themes.

### Modified Capabilities

<!-- Keine: es gibt noch keine bestehenden Specs. -->

## Impact

- `build.sh`: Index über Inhalte und `timeline/` aufbauen, Startseite, Fragmente und `/timeline/` erzeugen.
- Neu: `templates/timeline-meta.txt` (Metadaten der Bookmarks), Ordner `timeline/` mit Beispieleinträgen.
- `pages/index.md` bzw. der Startseitenaufbau in `build.sh`: zweispaltiger Aufbau.
- `static/style.css`: Timeline, Container, Punkte, Aufklappen, Startseitenlayout, alle Farbvarianten.
- `static/site.js`: Nachladen per `IntersectionObserver`.
- `README.md`: Beschreibung der Bookmark-Dateien.
- Keine neuen Abhängigkeiten, weiterhin POSIX-Shell und pandoc.

## Out of Scope

- Zweisprachigkeit (eigener Change `zweisprachig-de-en`, nutzt danach `.en.md`-Schwesterdateien).
- Branch/Merge-Darstellung für Zeiträume.
- Bilder und Slides zu einem Bookmark (Ordner neben der Datei).
- Galerie-Bilder als Quelle, Suche, Filter, Navigationslink "Timeline".
