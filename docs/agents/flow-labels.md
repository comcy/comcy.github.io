# Flow Labels

Zweite Label-Dimension neben den Triage-Rollen (`docs/agents/triage-labels.md`). Die Skills von mattpocock/skills kennen sie nicht und setzen sie nicht von selbst, sie gelten als Anweisung für Agenten und Menschen. Eigene Datei, damit ein erneutes `/setup-matt-pocock-skills` sie nicht überschreibt.

Genau ein `status:`-Label je Issue. Beim Wechsel das alte entfernen (`gh issue edit <n> --remove-label ... --add-label ...`).

| Label | Bedeutung | Phase |
| --- | --- | --- |
| `status:ready-for-refinement` | Nach Triage sinnvoll, muss noch geschärft werden | 1 |
| `status:in-refinement` | `/grilling` und `/openspec-propose` laufen, Change existiert | 1 bis 2 |
| `ready-for-agent` / `ready-for-human` | Definition of Ready: Tickets aus `/to-tickets` sind geschnitten (Triage-Rolle, kein `status:`) | 3 |
| `status:in-progress` | Branch und PR offen | 4 |
| `status:in-review` | PR bereit, Review läuft | 4 |

Abschluss: Issue schließen (`/openspec-archive-change` abgeschlossen), kein Label.

Ebenen: Refinement-Status am Feature-Issue, Bau-Status an den Sub-Issues (Tickets). Branch-Name: `feature/<issue-id>-<slug>`.

Anweisung an Agenten: Wechselt die Arbeit in eine neue Phase, setze das passende `status:`-Label und sage es im Ergebnis. Entfernt der Agent kein altes Label, ist das ein Fehler, den der Mensch korrigiert.

Azure DevOps o. ä.: gleiche Namen als Tags verwenden.

**Quelle der Label-Namen, Farben und Beschreibungen** ist `workflow/states.tsv`; `python3 scripts/setup.py --labels` legt fehlende Labels an. Übergänge und Bedingungen stehen in `workflow/transitions.tsv`.
