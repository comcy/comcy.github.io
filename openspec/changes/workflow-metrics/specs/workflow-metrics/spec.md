## ADDED Requirements

### Requirement: Metriken als Daten
`workflow/metrics.tsv` SHALL je Zeile `id`, `art` (`leading` oder `lagging`), `name`, `unit`, `source`, optional `target` und `enabled` beschreiben. `source` MUST ein Name aus `workflow/metric-sources.tsv` sein. Die Dateien dürfen keinen ausführbaren Code enthalten.

#### Scenario: Metrik mit Quelle
- **WHEN** die Zeile `cycle` mit `source` `ticket_cycle_time` und `art` `lagging` steht
- **THEN** gilt `ticket_cycle_time` als Quelle der nachlaufenden Metrik `cycle`

### Requirement: Providerneutrale Ereignisse
Die Berechnung SHALL ausschließlich auf einem neutralen Ereignismodell (Item, Art, Zeitpunkt) laufen. Jeder Provider (GitHub, Azure DevOps) MUST seine Daten in dieses Modell übersetzen. Fehlen Daten, SHALL der Bericht "keine Daten" zeigen und MUST keine Werte erfinden.

#### Scenario: Gleiche Metrik, zwei Provider
- **WHEN** dieselbe Metrik für ein GitHub- und ein Azure-DevOps-Repo berechnet wird
- **THEN** verwendet sie dieselben Ereignisarten und dieselbe Formel

### Requirement: Bericht
`kvasir metrics` SHALL je aktiver Metrik Wert, Einheit, Stichprobengröße und, falls gesetzt, das Ziel ausgeben, in den Formaten `text`, `json` und `markdown`, für den Zeitraum `--since` (Standard 30 Tage). Stichproben mit weniger als drei Einträgen SHALL als zu klein gekennzeichnet werden.

#### Scenario: Zu kleine Stichprobe
- **WHEN** nur zwei Tickets im Zeitraum geschlossen wurden
- **THEN** nennt der Bericht die Durchlaufzeit mit `n=2` und dem Hinweis "zu klein" statt eines Medians als Befund

### Requirement: Unbekannte Quelle
Eine `source`, die kvasir nicht auswerten kann, SHALL im Bericht als "unbekannt" erscheinen, und `kvasir doctor` MUST sie melden.

#### Scenario: Quelle nur in der Datei
- **WHEN** `metric-sources.tsv` einen Namen enthält, den kvasir nicht kennt
- **THEN** zeigt der Bericht die Metrik als "unbekannt"
