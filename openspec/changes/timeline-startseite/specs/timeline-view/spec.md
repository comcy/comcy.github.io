# Spec Delta

## Purpose

Legt fest, wie die Timeline auf der Startseite und auf der Seite `/timeline/` erscheint: Layout, Scroll-Container, Aufklappen, Nachladen, Verhalten ohne JavaScript und Zugänglichkeit.

## ADDED Requirements

### Requirement: Timeline auf der Startseite
Die Startseite SHALL die Timeline als zweite Spalte neben Profil und neuesten Beiträgen zeigen. Auf schmalen Bildschirmen (bis 640 px) MUST die Timeline unter dem übrigen Inhalt stehen.

#### Scenario: Breiter Bildschirm
- **WHEN** die Startseite auf einem breiten Bildschirm geöffnet wird
- **THEN** steht die Timeline neben dem Profil

#### Scenario: Schmaler Bildschirm
- **WHEN** die Startseite auf 375 px Breite geöffnet wird
- **THEN** steht die Timeline unter dem übrigen Inhalt, ohne horizontales Scrollen

#### Scenario: Keine Einträge
- **WHEN** es keinen einzigen Timeline-Eintrag gibt
- **THEN** zeigt die Startseite keine Timeline und keine leere Fläche

### Requirement: Container mit fester Höhe
Die Startseite SHALL die 8 neuesten Einträge direkt im ausgelieferten HTML enthalten, in einem Container mit begrenzter Höhe und eigenem Scrollen. Die Seite selbst MUST dadurch nicht länger werden.

#### Scenario: Mehr Einträge als sichtbar
- **WHEN** es 20 Einträge gibt
- **THEN** enthält das HTML der Startseite genau die 8 neuesten
- **AND** scrollt der Inhalt der Timeline im Container, nicht die Seite

### Requirement: Linie und Punkte
Die Timeline SHALL als senkrechte Linie mit je einem Punkt pro Eintrag dargestellt werden. Die Punkte MUST die Akzentfarbe des aktiven Farbschemas verwenden, in allen Schemata, hell und dunkel.

#### Scenario: Farbschema wechseln
- **WHEN** der Nutzer Farbschema oder Hell/Dunkel umschaltet
- **THEN** übernehmen die Punkte die Akzentfarbe des neuen Schemas ohne Neuladen

### Requirement: Darstellung eines Eintrags
Jeder Eintrag SHALL Datum und Titel zeigen. Ein Eintrag mit Seite zeigt den Titel als Link, ein Bookmark zeigt den Titel als aufklappbare Zeile. Aufgeklappt zeigt ein Bookmark Beschreibung und, falls vorhanden, den Zeitraum.

#### Scenario: Eintrag mit Seite
- **WHEN** ein Beitrag in der Timeline steht
- **THEN** ist sein Titel ein Link auf die Beitragsseite

#### Scenario: Bookmark aufklappen
- **WHEN** der Nutzer den Titel eines Bookmarks anklickt oder antippt
- **THEN** erscheint darunter die Beschreibung
- **AND** erscheint der Zeitraum, falls ein Enddatum gesetzt ist

### Requirement: Nachladen
Wenn der Nutzer das Ende der Timeline im Container erreicht und weitere Einträge existieren, SHALL die Seite die nächsten 10 Einträge anhängen. Das MUST sich wiederholen, bis alle Einträge geladen sind, ohne Doppelungen. Danach MUST kein weiterer Abruf erfolgen.

#### Scenario: 25 Einträge
- **WHEN** es 25 Einträge gibt und der Nutzer bis zum Ende scrollt
- **THEN** werden zuerst 10 weitere Einträge angehängt (Einträge 9 bis 18)
- **AND** bei erneutem Erreichen des Endes die letzten 7 (Einträge 19 bis 25)
- **AND** danach erfolgt kein weiterer Abruf

#### Scenario: Höchstens 8 Einträge
- **WHEN** es höchstens 8 Einträge gibt
- **THEN** erfolgt kein Nachladen und es erscheint kein Link "Alles ansehen"

#### Scenario: Nachladen schlägt fehl
- **WHEN** der Abruf weiterer Einträge fehlschlägt
- **THEN** zeigt die Timeline stattdessen den Link "Alles ansehen" und bleibt benutzbar

### Requirement: Vollständige Seite
Es SHALL eine Seite `/timeline/` geben, die alle Einträge ohne Scroll-Container zeigt, mit derselben Darstellung der Einträge. Sie MUST von der Startseite über "Alles ansehen" erreichbar sein, wenn mehr Einträge existieren als dort stehen.

#### Scenario: Ohne JavaScript
- **WHEN** JavaScript deaktiviert ist und es 20 Einträge gibt
- **THEN** zeigt die Startseite 8 Einträge und einen Link "Alles ansehen"
- **AND** zeigt `/timeline/` alle 20 Einträge

### Requirement: Zugänglichkeit
Die Timeline SHALL als Liste in Reihenfolge der Zeit ausgeliefert werden. Aufklappen MUST per Tastatur bedienbar sein, der Zustand MUST für Hilfstechnologien erkennbar sein und der Fokus sichtbar. Bei eingestellter reduzierter Bewegung MUST Animation entfallen.

#### Scenario: Tastaturbedienung
- **WHEN** der Nutzer mit Tab zu einem Bookmark navigiert und Enter oder Leertaste drückt
- **THEN** klappt die Beschreibung auf und der Fokus bleibt sichtbar
