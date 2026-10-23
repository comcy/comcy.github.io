# Spec Delta

## MODIFIED Requirements

### Requirement: Voraussetzungen prüfen
`setup` SHALL die Programme aus `workflow/tools.tsv` prüfen (Name, Mindestversion, Stufe `required` oder `recommended`, Hinweis). Ein fehlendes oder zu altes Pflichtprogramm MUST einen Fehler mit dem Hinweis und einen Exit-Code ungleich 0 ergeben. Ein fehlendes empfohlenes Programm ist nur ein Hinweis. Ohne Mindestversion (`-`) genügt, dass das Programm vorhanden ist.

#### Scenario: Pflichtprogramm fehlt
- **WHEN** `git` oder `gh` nicht gefunden wird
- **THEN** meldet `setup` den Namen und den Hinweis und endet mit Exit-Code ungleich 0

#### Scenario: Version zu alt
- **WHEN** die installierte Version eines Programms unter der Mindestversion liegt
- **THEN** nennt `setup` installierte und geforderte Version und endet mit Exit-Code ungleich 0

#### Scenario: Empfohlenes Programm fehlt
- **WHEN** nur ein Programm der Stufe `recommended` fehlt
- **THEN** zeigt `setup` einen Hinweis und der Exit-Code bleibt 0

#### Scenario: Normaler Lauf bricht vor jeder Änderung ab
- **WHEN** ein Pflichtprogramm fehlt und `setup claude` ohne `--check` läuft
- **THEN** endet `setup` mit Exit-Code ungleich 0, ruft `openspec init` nicht auf und ändert weder Git-Konfiguration noch `.git/info/exclude`

#### Scenario: Programmliste gehört dem Projekt
- **WHEN** ein Projekt ein anderes Bauprogramm als `pandoc` braucht
- **THEN** genügt eine geänderte Zeile in `workflow/tools.tsv`, ohne das Werkzeug zu ändern
