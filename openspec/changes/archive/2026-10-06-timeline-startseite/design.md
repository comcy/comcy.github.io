# Design

## Context

- Der Build ist `build.sh` (POSIX-Shell + pandoc). Beiträge laufen durch einen Index mit Feldtrenner `$US` (Datum, Slug, Titel, Tags, Beschreibung). Startseite und Übersichten werden als temporäre Markdown-Dateien erzeugt und mit `templates/page.html` gerendert.
- `main`, Kopf und Fuß teilen sich eine Breite von 48 rem. Die Startseite ist heute einspaltig: Profil aus `pages/index.md`, darunter "Neueste Beiträge".
- Anforderungen: siehe `specs/timeline-entries` und `specs/timeline-view`. Motivation: siehe `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Ein einziger Timeline-Index im Build, aus dem Startseite, Fragmente und `/timeline/` erzeugt werden, ohne doppelte Logik.
- Die Seite bleibt ohne JavaScript vollständig nutzbar.
- Keine neuen Abhängigkeiten, kein Framework.

**Non-Goals:**
- Kein clientseitiges Rendering aus JSON.
- Keine Vorbereitung der Zweisprachigkeit über das hinaus, was `.en.md` später braucht (der Index ist pro Lauf, eine Sprachschleife kann ihn später umschließen).
- Keine Branch/Merge-Darstellung.

## Decisions

**1. Ein gemeinsamer Index, gleiche Mechanik wie Posts.**
Neue Datei `$TMP/timeline` mit Feldern Sortierschlüssel, Anzeige-Datum, Ende, Art (`post`/`page`/`bookmark`), Slug, Titel, Beschreibung. Beiträge liefern ihre Daten aus dem bestehenden Post-Index (keine zweite pandoc-Abfrage), Seiten und Bookmarks bekommen eine kleine Metadaten-Vorlage `templates/timeline-meta.txt` (`$date$`, `$end$`, `$title$`, `$description$`).
*Alternative:* Jede Quelle erzeugt eigenes HTML. Verworfen, weil Sortierung und Chunking dann an mehreren Stellen stehen.

**2. Datumsprüfung zentral per `grep -E`.**
Eine Funktion normalisiert `YYYY`, `YYYY-MM`, `YYYY-MM-DD` auf `YYYY-MM-DD` (fehlender Teil = `01`) und bricht mit Dateinamen ab, wenn das Format nicht passt. `end` nutzt dieselbe Funktion, `now` ist erlaubt, `end < date` bricht ab. Sortierung per `LC_ALL=C sort -r` auf `Schlüssel + Art + Slug`, damit gleiche Daten reproduzierbar bleiben.
*Alternative:* `date -d`. Verworfen, nicht portabel (BSD/macOS) und akzeptiert Teilformate nicht.

**3. HTML der Einträge per Shell, nicht per pandoc.**
Eine Funktion schreibt `<li>` je Eintrag mit vorhandenem `xml_escape` für Text. Bookmarks sind `<details>`, Einträge mit Seite ein Link. Gleiche Funktion für Startseite, Fragmente und `/timeline/`.
*Alternative:* pandoc je Eintrag. Verworfen, bei vielen Einträgen unnötig langsam und ohne Gewinn, die Beschreibung ist ein Satz Klartext.

**4. Ausgabe in drei Formen aus demselben Index.**
- Startseite: erste 8 Einträge als rohes HTML (pandoc `raw_attribute`) in der Timeline-Spalte, daneben das bisherige Markdown.
- Fragmente `/timeline/chunk-1.html`, `chunk-2.html`, … je 10 Einträge ab Eintrag 9, nur `<li>`-Elemente.
- `/timeline/index.html`: alle Einträge, normale Seite mit Titel "Timeline", ohne Container.
Die Zahl der Fragmente steht als `data-chunks` im Container, damit das Skript nach dem letzten stoppt und keinen Abruf ins Leere macht. Ist die Gesamtzahl höchstens 8, gibt es weder Fragmente noch "Alles ansehen", bei 0 keine Spalte.

**5. Nachladen mit `IntersectionObserver` im Container.**
Ein Sentinel am Listenende, `root` ist der Scroll-Container. Das Skript holt `chunk-N.html` per `fetch`, hängt die `<li>` an und zählt hoch. Bei Fehler hört es auf, der Link "Alles ansehen" bleibt sichtbar. Fallback ohne `IntersectionObserver`: nichts nachladen, nur der Link.
*Alternative:* Scroll-Event. Verworfen, teurer und fehleranfälliger.

**6. Layout: Startseite breiter, Spalten per Grid.**
Das Template setzt `class="home"` am `body` (Metadatum `home` nur für die Startseite). Dann gilt eine Breite von etwa 62 rem für Kopf, Hauptbereich und Fuß, im Hauptbereich ein Grid (Profil und Beiträge links, Timeline rechts). Ab 640 px abwärts eine Spalte. Container: `max-height` etwa `min(36rem, 70vh)`, mobil `60vh`.
*Alternative:* bei 48 rem bleiben und die Timeline eng quetschen. Verworfen, zu schmale Textspalte beim langen Profiltext.

**7. Linie und Punkte rein per CSS.**
`li::before` für den Punkt, ein Randstreifen für die Linie, Farben aus den vorhandenen Variablen (`--accent`, `--line`). Dadurch gelten alle Farbschemata ohne eigenen Code. Änderungen an `style.css` und `site.js` erneuern über die vorhandene Prüfsumme (`ASSET_V`) automatisch den Cache.

**8. Test: ein Shell-Check, kein Framework.**
`tests/timeline-check.sh` kopiert das Repo in ein temporäres Verzeichnis, legt Fixtures an (25 Einträge, ungültige Daten) und prüft Ausgabedateien per `grep`/`wc`. Deckt die Szenarien der Specs ab, soweit sie ohne Browser prüfbar sind. Layout und Nachladen werden im Browser mit Screenshots geprüft.

## Risks / Trade-offs

- [Pandoc formatiert `date:` unerwartet um] → Beim ersten Task die Ausgabe von `$date$` für `2024`, `2024-05`, `2024-05-17` prüfen und gegebenenfalls das Frontmatter-Feld im Check mit Anführungszeichen vorsehen.
- [Ungültiges Datum in einem bestehenden Beitrag lässt jetzt den Build scheitern] → Gewollt (Spec), die zwei vorhandenen Beiträge sind gültig; die Fehlermeldung nennt die Datei.
- [Shell-Escaping von Titeln und Beschreibungen] → Nur `xml_escape` für Text, Slugs werden aus Dateinamen abgeleitet und enthalten keine Sonderzeichen. Check mit `&` und `<` im Titel.
- [Breitere Startseite wirkt gegenüber den anderen Seiten uneinheitlich] → Kopf und Fuß werden auf der Startseite mitverbreitert, damit nichts versetzt aussieht. Beim Screenshot-Review prüfen.
- [Containerhöhe passt nicht zur Höhe des Profils] → Feste obere Grenze statt exaktem Angleichen, einfacher und robust. Nachjustieren nach dem Review.
- [Spätere Zweisprachigkeit] → Der Index entsteht pro Build-Lauf, die Sprachschleife kann ihn später umschließen. Fragmente liegen dann je Sprache unter `/en/timeline/`.

## Annahmen (bewusst offen für Review)

- `end: now` wird als "laufend" angezeigt.
- Seiten mit `date:` (außer Startseite und Galerie) erzeugen ebenfalls einen Eintrag, `pages/about.md` bleibt ohne Datum und damit draußen.
- Die Spalte heißt "Timeline", Titel der Gesamtseite ebenfalls. Texte können später in die Sprachdateien wandern.

## Migration Plan

Reiner Seitenbau, keine Daten und keine Umleitungen. Rollback: Änderung zurücknehmen und neu bauen. Bestehende URLs ändern sich nicht, neu sind `/timeline/` und `/timeline/chunk-N.html`.
