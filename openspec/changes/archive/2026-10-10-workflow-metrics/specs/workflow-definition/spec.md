## ADDED Requirements

### Requirement: Metriken im Prozessverzeichnis
`flow validate` SHALL `workflow/metrics.tsv` und `workflow/metric-sources.tsv` wie die übrigen Dateien lesen (Kopfzeile, Spalten nach Namen, `enabled`), doppelte Ids, ungültige Werte für `art` und `target` sowie unbekannte `source` mit Datei, Zeile und Meldung melden und Metriken abgeschalteter oder fehlender Quellen als Warnung führen.

#### Scenario: Unbekannte Quelle
- **WHEN** `metrics.tsv` eine `source` nennt, die in `metric-sources.tsv` fehlt
- **THEN** meldet `flow validate` Datei, Zeile und Quelle und endet mit Exit-Code ungleich 0
