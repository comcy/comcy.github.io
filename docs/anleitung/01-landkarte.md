# 1. Landkarte: Bausteine, Zustände, Phasen

## Bausteine

```mermaid
flowchart TB
    subgraph Menschen["Menschen und Agenten"]
        M["Mensch<br/>entscheidet, gibt frei"]
        A["KI-Agent<br/>führt Skills aus"]
    end
    subgraph Skills["Skills (Anweisungen für den Agenten)"]
        S1["/triage · /grilling · /to-tickets<br/>/implement · /tdd · /code-review<br/>(mattpocock-skills)"]
        S2["/openspec-propose · -apply-change<br/>-archive-change · -explore<br/>(OpenSpec, .agents/skills/)"]
    end
    subgraph Tools["Werkzeuge"]
        T1["git · gh · node · pandoc"]
        T2["openspec CLI"]
        T3["scripts/setup.py<br/>scripts/flow.py<br/>scripts/gate.py"]
        T4["kvasir (optional)<br/>status · graph · tui"]
        T5["evals/run.py<br/>derive.py"]
        T6["Adapter<br/>evals/adapters/"]
    end
    subgraph Daten["Daten im Repo"]
        D1["workflow/*.tsv<br/>Zustände, Übergänge,<br/>Phasen, Detektoren"]
        D5["workflow/skills.tsv<br/>roles.tsv<br/>(Skills und Rollen)"]
        D6["scripts/setup.d/<br/>agents.tsv (skill_paths)"]
        D2["openspec/<br/>specs/ und changes/"]
        D3["AGENTS.md · docs/agents/"]
        D4["scripts/gate.d/<br/>.githooks/"]
    end
    subgraph Gates["Gates (erzwingen Regeln)"]
        G1["Git-Hooks<br/>commit-msg · pre-commit"]
        G2["flow-Guards<br/>start · review"]
        G3["CI: test · python · gates"]
        G4["Branch-Schutz master"]
    end
    GH[("GitHub<br/>Issues · PRs · Labels")]
    M --> A --> S1 & S2
    S1 --> T1
    S2 --> T2
    T3 --> D1
    T3 --> D6
    D5 -. "Abdeckung (validate)<br/>Skill-Prüfung (setup --check)" .-> T3
    D1 -. "Übergänge → Aufgaben" .-> T5
    D5 -. "allowed_tools" .-> T5
    T5 -- "JSON-Vertrag" --> T6
    T6 -. "startet" .-> A
    T3 --> D4
    T4 -. liest .-> GH
    T4 -. liest .-> D1
    T1 --> GH
    D1 --> G2
    D4 --> G1
    D4 --> G3
    G3 --> G4
    G4 --> GH
```

Faustregel aus `docs/workflow.md`: **Das Modell urteilt** (Spezifikation, Code, Review), **Skripte und CI erzwingen** Übergänge und Prüfpunkte.

## Baustein-Tabelle

| Baustein | Zweck | Pflicht? | Wo / Aufruf |
| --- | --- | --- | --- |
| `git`, `gh` (angemeldet) | Versionsverwaltung, Issues, PRs | Pflicht | `gh auth status` |
| Python ≥ 3.11 | `scripts/` (nur Standardbibliothek) | Pflicht | `python3 --version` |
| Node ≥ 20.19, `openspec` ≥ 1.14 | Specs und Changes | Pflicht | `openspec --version` |
| `pandoc` ≥ 3.1 | Build der Seite (nur dieses Repo) | Pflicht (Teil B) | `pandoc --version` |
| KI-Agent + Skills | führt die Phasen aus | optional (alles geht von Hand) | `/plugin` |
| `scripts/setup.py` | Klon einrichten: Prüfung, Hooks, Adapter, Labels | Pflicht (einmal je Klon) | `python3 scripts/setup.py --check` |
| `scripts/flow.py` | Prozessdaten prüfen, Ticket starten, in Review geben | Pflicht für Prozessdaten, `start`/`review` optional | `flow validate` |
| `scripts/gate.py` | Commit-Lint, Secret-Scan | Pflicht (läuft in Hook und CI) | `gate commits`, `gate secrets` |
| `workflow/skills.tsv`, `roles.tsv` | welcher Skill welche Phase trägt, welche Rolle was darf; Abdeckung und Skill-Prüfung | Pflicht (Prozessdaten) | `flow validate`, `setup --check` |
| `agents.tsv` `skill_paths` | Orte der Skills je Agent, nie geraten | Pflicht für die Skill-Prüfung | `scripts/setup.d/agents.tsv` |
| Evals `evals/run.py` | prüft, ob der Agent den Prozess einhält | optional (kostet echtes Geld) | `python3 evals/run.py` |
| Adapter `evals/adapters/` | startet den Agenten für die Evals (JSON-Vertrag, jede Sprache) | optional (nur für Evals) | `--adapter <programm>` |
| Abgeleitete Aufgaben `evals/derive.py` | je Guard eine Aufgabe "Übergang muss abbrechen" | optional (Teil der Evals) | automatisch bei `run.py` |
| kvasir | Sicht auf Status, Graph, TUI | **optional, empfohlen** | `kvasir status '#N'` |
| Git-Hooks `.githooks/` | frühe Rückmeldung beim Commit | empfohlen (CI ist verbindlich) | `core.hooksPath` |
| CI (`test.yml`) | verbindliche Prüfung je PR | Pflicht | GitHub Actions |
| Branch-Schutz | PR nur mit grünen Checks | Pflicht (Einstellung des Repo-Eigners) | GitHub-Einstellungen |

## Zwei Dimensionen am Issue

Jedes Ticket trägt **eine Triage-Rolle** (wer ist am Zug) und ab der Bearbeitung **einen Status** (wo steht die Arbeit). Quelle: `workflow/states.tsv` und `transitions.tsv`.

```mermaid
stateDiagram-v2
    direction LR
    state "Triage (Rolle)" as T {
        [*] --> needs_triage: Issue angelegt
        needs_triage --> needs_info: Rückfrage
        needs_info --> needs_triage: Antwort
        needs_triage --> ready_for_agent: Spezifikation reicht
        needs_triage --> ready_for_human: nur Mensch
        needs_triage --> wontfix: abgelehnt
    }
    state "Status (Fluss)" as S {
        [*] --> ready_for_refinement: akzeptiert
        ready_for_refinement --> in_refinement: Grilling läuft
        in_refinement --> in_progress: Tickets geschnitten
        [*] --> in_progress: flow start (Ticket)
        in_progress --> in_review: flow review (Checks grün)
        in_review --> in_progress: Änderungen nötig
        in_review --> closed: PR gemergt
    }
```

- **Feature-Issue** (Elternteil): durchläuft `ready-for-refinement` → `in-refinement`, danach hängen die Tickets als Sub-Issues darunter.
- **Ticket** (Blatt): bekommt `ready-for-agent`, dann `flow start` → `in-progress` → `flow review` → `in-review` → gemergt, Issue schließt, **Status-Label entfernen** (kein Label bei `closed`).

## Phasen

```mermaid
flowchart LR
    S["S Setup<br/>einmal je Klon"] --> P0["0 Eingang<br/>/triage"]
    P0 --> P1["1 Idee schärfen<br/>/grilling"]
    P1 --> P2["2 Anforderungen<br/>/openspec-propose"]
    P2 --> P3["3 Arbeit schneiden<br/>/to-tickets"]
    P3 --> P4["4 Bauen und prüfen<br/>/implement"]
    P4 --> P4b["4b Abnahme<br/>optional"]
    P4b --> P5["5 Abschließen<br/>/openspec-archive-change"]
    P4 --> P5
    P5 --> P6["6 Wissen sichern<br/>ADR · Log"]
    P4 -. "je Ticket: Branch → PR → CI → Merge" .-> P4
```

Die Phasen stehen als Daten in `workflow/phases.tsv` (Spalten `id`, `name`, `tool`, `done_when`, `level`). `done_when` benennt die **Beobachtung**, an der man die Phase als erledigt erkennt (z. B. `subissues_exist`). Daran liest kvasir den Stepper ab.

## Wer darf was entscheiden (menschliche Gates)

| Entscheidung | Wer | Wo sichtbar |
| --- | --- | --- |
| Ticket akzeptiert und geschärft | Mensch | Antworten im Grilling, Label `ready-for-agent` |
| Change (Proposal, Specs, Design, Tasks) freigeben | Mensch | Freigabe vor `/to-tickets` |
| Tickets freigeben | Mensch | Ticketliste vor der Anlage |
| Merge eines PR | Mensch, oder Agent **nur im ausdrücklich erteilten Umfang** bei grüner CI | PR-Historie |
| Branch-Schutz ändern | nur Repo-Eigner | GitHub-Einstellungen |

Grundlage: der Abgleich mit dem Playbook in [../playbook-abgleich.md](../playbook-abgleich.md).
