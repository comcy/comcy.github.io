# Spec Delta

## Purpose

Legt fest, aus welchen Quellen Timeline-Einträge entstehen und welche Daten ein Eintrag hat: automatische Einträge aus datierten Inhalten und manuelle Bookmarks aus dem Ordner `timeline/`.

## ADDED Requirements

### Requirement: Datierte Inhalte werden automatisch Einträge
Jeder veröffentlichte Markdown-Inhalt mit `date:` im Frontmatter SHALL einen Timeline-Eintrag erzeugen. Der Eintrag zeigt Datum und Titel und verweist auf die Seite des Inhalts. Inhalte ohne `date:` MUST NOT erscheinen. Entwürfe (`draft: true`) von Beiträgen, Seiten und Bookmarks erscheinen nur, wenn der Build Entwürfe einschließt.

#### Scenario: Beitrag mit Datum
- **WHEN** ein veröffentlichter Beitrag `date: 2026-10-03` und einen Titel hat
- **THEN** enthält die Timeline einen Eintrag mit diesem Datum und Titel, der auf die Seite des Beitrags verweist

#### Scenario: Seite ohne Datum
- **WHEN** eine Seite kein `date:` im Frontmatter hat
- **THEN** erzeugt sie keinen Timeline-Eintrag

#### Scenario: Entwurf
- **WHEN** ein Beitrag `draft: true` hat und der Build ohne Entwürfe läuft
- **THEN** erscheint er nicht in der Timeline
- **AND** erscheint er, wenn der Build Entwürfe einschließt, wie im Blog

#### Scenario: Entwurf bei Bookmark und Seite
- **WHEN** ein Bookmark oder eine Seite `draft: true` hat und der Build ohne Entwürfe läuft
- **THEN** erscheint der Eintrag nicht in der Timeline

### Requirement: Manuelle Einträge im Ordner timeline
Jede Markdown-Datei in `timeline/` SHALL einen Timeline-Eintrag ("Bookmark") erzeugen. Ein Bookmark hat Titel, Datum und eine Beschreibung. Er MUST NOT eine eigene öffentliche Seite erzeugen.

#### Scenario: Bookmark anlegen
- **WHEN** `timeline/2024-05-vortrag.md` mit Titel, `date: 2024-05` und Beschreibung existiert
- **THEN** enthält die Timeline einen Eintrag mit Titel und Beschreibung
- **AND** existiert keine Seite unter einer eigenen URL für diesen Eintrag

#### Scenario: Bookmark ohne Datum oder Titel
- **WHEN** eine Datei in `timeline/` kein `date:` oder keinen Titel hat
- **THEN** bricht der Build mit einer Fehlermeldung ab, die die Datei benennt

### Requirement: Datumsformate
Als Datum SHALL `YYYY`, `YYYY-MM` und `YYYY-MM-DD` gültig sein. Für die Sortierung gilt ein fehlender Monat oder Tag als der erste. Die Anzeige MUST das Datum so zeigen, wie es geschrieben wurde.

#### Scenario: Nur Monat angegeben
- **WHEN** ein Bookmark `date: 2024-05` hat
- **THEN** wird es wie der 1. Mai 2024 einsortiert
- **AND** zeigt die Timeline "2024-05"

#### Scenario: Ungültiges Datum
- **WHEN** `date:` nicht einem der drei Formate entspricht
- **THEN** bricht der Build mit einer Fehlermeldung ab, die die Datei benennt

### Requirement: Reihenfolge
Einträge SHALL nach Datum absteigend sortiert sein, neueste zuerst. Bei gleichem normalisierten Datum (fehlender Monat oder Tag zählt als der erste) entscheiden die Art (Beitrag vor Seite vor Bookmark) und dann der Slug absteigend, bei jedem Build gleich und unabhängig von Dateisystem und Locale.

#### Scenario: Gemischte Quellen
- **WHEN** ein Beitrag vom 2026-10-03 und ein Bookmark mit `date: 2026-10` existieren
- **THEN** steht der Beitrag vor dem Bookmark, weil der Bookmark wie der 1. Oktober zählt

#### Scenario: Gleiches Datum
- **WHEN** zwei Einträge dasselbe Datum haben
- **THEN** ist ihre Reihenfolge bei wiederholten Builds identisch

#### Scenario: Gleichstand in unterschiedlicher Schreibweise
- **WHEN** ein Beitrag `2026-10-01` und zwei Bookmarks mit `2026-10-01` und `2026-10` existieren
- **THEN** steht der Beitrag zuerst
- **AND** die Bookmarks folgen nach Slug absteigend, nicht nach der Länge der Schreibweise

### Requirement: Optionales Enddatum
Ein Bookmark MAY ein `end:` in einem der drei Datumsformate oder den Wert `now` haben. Das Enddatum SHALL den Eintrag nicht umsortieren, sondern nur als Zeitraum angezeigt werden. Ein Enddatum vor dem Startdatum (nach Normalisierung) MUST den Build abbrechen, ein gleiches Datum nicht.

#### Scenario: Zeitraum
- **WHEN** ein Bookmark `date: 2024-05` und `end: 2024-11` hat
- **THEN** zeigt der Eintrag den Zeitraum "2024-05 – 2024-11"
- **AND** bleibt seine Position durch `date` bestimmt

#### Scenario: Laufender Zeitraum
- **WHEN** ein Bookmark `end: now` hat
- **THEN** zeigt der Eintrag den Zeitraum als laufend

#### Scenario: Ende gleich Start
- **WHEN** `date: 2024-05-01` und `end: 2024-05` gesetzt sind
- **THEN** baut die Seite und zeigt den Zeitraum

#### Scenario: Ende vor Start
- **WHEN** `end:` liegt vor `date:`
- **THEN** bricht der Build mit einer Fehlermeldung ab, die die Datei benennt
