## 1. Konfiguration und Abdeckung (Tracer)
- [x] 1.1 `workflow/skills.tsv` und `roles.tsv` mit dem heutigen Prozess, `flow validate` liest und prüft sie (Verweise, Abdeckung, Warnungen), Tests, Doku

## 2. Skill-Prüfung im Setup
- [ ] 2.1 Spalte `skill_paths` in `agents.tsv`, `setup --check` meldet Skills je Phase (`ok`, `FEHLT`, Hinweis, "nicht prüfbar"), Tests mit Wegwerf-HOME

## 3. Adapter-Vertrag
- [x] 3.1 `evals/adapters/claude.py` aus `starte_agent`, `--adapter`, JSON-Vertrag, "nicht prüfbar" bei fehlendem Mitschnitt, Test mit Fake-Adapter in anderer Sprache (Shell/Python)

## 4. Rollen steuern die Evals
- [x] 4.1 `role` in `task.json`, `allowed_tools` aus `roles.tsv` an den Adapter

## 5. Abgeleitete Aufgaben
- [x] 5.1 `evals/derive.py` für die abbildbaren Detektoren, Bericht-Abschnitt "nicht ableitbar", Tests

## 6. Doku und Probelauf
- [ ] 6.1 `docs/workflow.md`, `docs/anleitung/04` und Landkarte; Trockenlauf mit einem zweiten Adapter (Fake); echter Lauf nach Freigabe
