# Tasks

## 1. Daten: Index und Prüfung

- [ ] 1.1 `templates/timeline-meta.txt` und Datumsfunktion in `build.sh` (drei Formate, `end`, `now`, Abbruch mit Dateiname) anlegen; `tests/timeline-check.sh` mit Fällen für gültige und ungültige Daten, Ende vor Start, fehlenden Titel; Check läuft grün und die Fehlerfälle brechen mit Dateiname ab
- [ ] 1.2 Bookmarks aus `timeline/*.md` in einen Timeline-Index lesen, zwei Beispieleinträge unter `timeline/` anlegen; Index enthält beide und es entsteht keine Seite unter `/blog/` oder einer eigenen URL für sie
- [ ] 1.3 Beiträge (aus dem bestehenden Index) und Seiten mit `date:` in den Timeline-Index aufnehmen, Entwürfe wie im Blog behandeln, deterministisch absteigend sortieren; Check prüft Reihenfolge (Beitrag vor Bookmark im selben Monat), gleiche Reihenfolge bei zwei Builds, Entwurf nur mit `DRAFTS=1`

## 2. Ausgabe: HTML aus dem Index

- [ ] 2.1 Funktion für ein Listenelement (Datum, Titel, Link oder `<details>`, Zeitraum, Escaping) schreiben; Check mit `&` und `<` im Titel findet escapte Ausgabe, `end: now` zeigt "laufend"
- [ ] 2.2 `/timeline/index.html` mit allen Einträgen und Fragmente `chunk-N.html` (10 je, ab Eintrag 9) erzeugen; Check mit 25 Fixture-Einträgen: Gesamtseite 25, Fragmente 10 und 7, bei höchstens 8 Einträgen keine Fragmente
- [ ] 2.3 Startseite: erste 8 Einträge im HTML, `data-chunks`, "Alles ansehen" nur bei mehr als 8, keine Spalte bei 0; Check prüft alle drei Fälle

## 3. Layout und Stil

- [ ] 3.1 `templates/page.html` und Startseitenaufbau: `home`-Klasse, zweispaltiges Grid, breitere Startseite, mobil untereinander bis 640 px; Screenshots bei 375 px und 1280 px zeigen die Anordnung ohne horizontales Scrollen
- [ ] 3.2 CSS für Linie, Punkte, aufklappbare Bookmarks und Container mit fester Höhe in `static/style.css`; Screenshots in allen vier Farbschemata, hell und dunkel, zeigen Punkte in der Akzentfarbe
- [ ] 3.3 Fokus sichtbar und reduzierte Bewegung respektiert; Tabulator-Durchlauf im Browser erreicht jedes Bookmark, Enter/Leertaste klappt auf

## 4. Nachladen

- [ ] 4.1 `IntersectionObserver` in `static/site.js` (Sentinel, `fetch` der Fragmente, Stopp nach dem letzten, Fehlerfall); im Browser mit 25 Einträgen: 8 sichtbar, zwei Abrufe im Netzwerk-Tab, 25 Einträge ohne Doppelungen, danach keine weiteren Abrufe, mit blockiertem Fragment bleibt "Alles ansehen" benutzbar

## 5. Dokumentation und Abschluss

- [ ] 5.1 README: Abschnitt zu Bookmarks (Frontmatter-Felder, Datumsformate, `end`) und Check-Aufruf; der dort beschriebene Beispieleintrag baut wie dokumentiert
- [ ] 5.2 Integrationscheck: `sh build.sh` ohne Fehler, `sh tests/timeline-check.sh` grün, Screenshots (Desktop, Mobil, mehrere Themes) im PR
