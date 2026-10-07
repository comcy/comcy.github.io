# 4. Konfigurationsdateien

Alles, was den Prozess steuert, ist **Datei im Repo** (oder eine Git-Einstellung im Klon). Der Grundsatz: Dateien **beschreiben**, Werkzeuge **werten aus**. Keine Datei enthält ausführbaren Code.

## Übersicht

```mermaid
flowchart LR
    subgraph Prozess["Prozessdaten (workflow/)"]
        st[states.tsv]
        tr[transitions.tsv]
        ph[phases.tsv]
        de[detectors.tsv]
    end
    subgraph Setup["Setup (scripts/setup.d/)"]
        to[tools.tsv]
        ag[agents.tsv]
    end
    subgraph Gate["Gates (scripts/gate.d/, .githooks/)"]
        ct[commit-types.tsv]
        se[secrets.tsv]
        al[allow.tsv]
        hk[commit-msg · pre-commit]
    end
    subgraph Agent["Agenten (AGENTS.md, docs/agents/, openspec/config.yaml)"]
        am[AGENTS.md]
        da[docs/agents/*.md]
        oc[openspec/config.yaml]
    end
    subgraph CI[".github/"]
        tw[workflows/test.yml]
        dw[workflows/deploy.yml]
        pa[actions/setup-pandoc]
    end
    st --> |"Labels (setup --labels)"| GH[(GitHub)]
    tr --> |"Guards (flow start/review)"| FL[flow.py]
    de --> |"Vokabular"| tr & ph
    ph --> |"Stepper"| KV[kvasir]
    to --> SU[setup.py]
    ct & se & al --> GA[gate.py]
    hk --> GA
    tw --> |"ruft auf"| GA & FL
```

| Datei | Gelesen von | Wirkung |
| --- | --- | --- |
| `workflow/states.tsv` | `flow validate`, `setup --labels`, `flow` | Zustände = Labels |
| `workflow/transitions.tsv` | `flow validate`, `flow start`, `flow review` | erlaubte Übergänge mit Bedingungen |
| `workflow/phases.tsv` | `flow validate`, kvasir | Phasen und woran man ihr Ende erkennt |
| `workflow/detectors.tsv` | `flow validate`, `flow`, kvasir | das feste Vokabular der Bedingungen |
| `scripts/setup.d/tools.tsv` | `setup.py` | benötigte Programme und Mindestversionen |
| `scripts/setup.d/agents.tsv` | `setup.py` | Agenten mit lokalem Adapter |
| `scripts/gate.d/commit-types.tsv` | `gate commits` | erlaubte Commit-Typen |
| `scripts/gate.d/secrets.tsv` | `gate secrets` | Muster für Secrets |
| `scripts/gate.d/allow.tsv` | `gate secrets` | begründete Ausnahmen |
| `.githooks/commit-msg`, `pre-commit` | Git (`core.hooksPath`) | rufen `gate.py` auf |
| `openspec/config.yaml` | OpenSpec-Skills | Regeln für Artefakte, Hinweise für apply/archive |
| `AGENTS.md`, `docs/agents/*.md` | Agent, Skills | Tracker, Labels, Domänenhinweise |
| `.github/workflows/*.yml` | GitHub Actions | CI und Deployment |
| `.gitattributes` | Git | LF-Zeilenenden für Skripte und Daten |
| `kvasir.toml` (optional) | kvasir | geteilte Überschreibungen |

## `workflow/`: Prozessdaten

Format: tabulatorgetrennt, **Kopfzeile**, Spalten nach **Namen** (Reihenfolge egal, zusätzliche Spalten werden ignoriert), `#` für Kommentare, optionale Spalte `enabled` (`no` schaltet eine Zeile ab, ohne sie zu löschen). CRLF wird akzeptiert.

### `states.tsv`: Zustände

```
id	kind	color	description
needs-triage	triage	fbca04	Maintainer needs to evaluate
ready-for-agent	triage	0e8a16	Fully specified, ready for an AFK agent
status:in-progress	status	fef2c0	Flow: branch and PR open
closed	terminal	-	Issue closed (no label)
```

`kind`: `triage` (Rolle laut `/triage`), `status` (Fluss), `terminal` (kein Label; genau ein Zustand). `id` ist bei triage und status der **Labelname**. `python3 scripts/setup.py --labels` legt fehlende Labels an, vorhandene bleiben unberührt.

### `transitions.tsv`: Übergänge

```
from	to	trigger	guard
-	status:in-progress	branch_created	label:ready-for-agent,no_open_blockers
status:in-progress	status:in-review	pr_ready	checks:success
status:in-review	closed	pr_merged	pr_state:merged
```

- `from`: Zustand oder `-` (Start). `to`: Zustand (auch `closed`). Übergänge gibt es **nur innerhalb einer Dimension** (triage oder status), außer vom Start oder nach `closed`.
- `trigger`: Name des Ereignisses (Anzeige, und `flow` wählt daran den Übergang: `branch_created`, `work_started`, `pr_ready`).
- `guard`: Detektoren aus `detectors.tsv`, Komma = UND, `-` = keine Bedingung. `flow start` und `flow review` **werten die Guards aus** und brechen ab, wenn einer nicht erfüllt ist.

### `phases.tsv`: Phasen

```
id	name	tool	done_when	level
2	Anforderungen festhalten	/openspec-propose	openspec_artifacts_complete	required
4b	Abnahme	-	pr_checklist:Lokale Abnahme	optional
6	Wissen sichern	-	-	required
```

`tool` ist nur Anzeige. `done_when` sind Detektoren (Komma = UND) oder `-` (nicht beobachtbar, erscheint nicht im Stepper). `level`: `required` oder `optional`. Eine Phase abschalten: Spalte `enabled` mit `no` ergänzen.

### `detectors.tsv`: das Vokabular

```
name	arg	description
label	text	Das Label mit diesem Namen ist gesetzt
checks	enum:success|failure	Ergebnis der Checks des Pull Requests
file_exists	path	Die Datei existiert im Repo
```

`arg`: `-` (kein Argument), `text`, `path` oder `enum:a|b|c`. Aufruf in `guard`/`done_when` als `name` oder `name:argument`. **Neuer Detektor**: erst hier eintragen, dann im Werkzeug auswerten (`scripts/lib/transition.py` für `flow`, kvasir für den Stepper). Ein Name, den ein Werkzeug nicht kennt, ist dort "unbekannt" (Warnung bei `flow`, `doctor`-Meldung bei kvasir), nie ein stilles Durchwinken.

### Prüfen

```sh
python3 scripts/flow.py validate            # Fehler und Warnungen
python3 scripts/flow.py validate --strict   # Warnungen werden zu Fehlern (so läuft es in der CI)
```

**echt:** `0 Fehler, 0 Warnungen`. Geprüft werden Spalten, doppelte IDs, Farben, Verweise zwischen den Dateien, Dimensionen, das Vokabular, Sackgassen und die Reihenfolge der Phasen.

## `scripts/setup.d/`

`tools.tsv` (`name`, `min_version`, `level`, `version_cmd`, `hint`): Was `setup.py --check` verlangt. `level=required` bricht ab, `recommended` warnt. **Neues Werkzeug**: Zeile ergänzen, `python3 scripts/setup.py --check`.

```
name	min_version	level
openspec	1.14	required
kvasir	-	recommended
```

`agents.tsv` (`agent`, `folder`): Für welche Agenten `setup <agent>` einen lokalen Adapter erzeugt. Der Ordner kommt in `.git/info/exclude` (lokal, nicht eingecheckt); `.agents/` mit den OpenSpec-Skills bleibt eingecheckt (agentenneutrale Basis).

## `scripts/gate.d/` und `.githooks/`

```
commit-types.tsv      type  description        feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
secrets.tsv           id  kind  pattern  description   (kind: line | file; Muster = Python-Regex)
allow.tsv             path  pattern  reason            (reason ist Pflicht, sonst Fehler)
```

- `secrets.tsv` erkennt privaten Schlüssel, GitHub-, AWS-, Slack-, Anthropic-Token, `KEY=`/`PASSWORD=` mit Wert und `.env`-Dateien (außer `.env.example`).
- **Ausnahme eintragen** (nie den Hook umgehen): eine Zeile in `allow.tsv`, z. B. `docs/**/*.md<TAB>ghp_example<TAB>Beispielwert in der Doku`.
- Die Hooks sind **dünne `sh`-Hüllen**: suchen `python3`, `python` oder `py -3` und rufen `scripts/gate.py commit-msg <datei>` bzw. `secrets` auf. Logik liegt nur in `gate.py`, damit Hook und CI dasselbe prüfen.

## `openspec/config.yaml`

```yaml
schema: spec-driven
context: |
  Language: de
  All artifacts must be written in de.
  Keep OpenSpec structural headings and SHALL/MUST keywords in English.
rules:
  tasks:
    - Tasks nach vertikalen Scheiben schneiden ...
operations:
  apply:
    guidance:
      - Umsetzung je GitHub-Ticket mit /implement (tdd, dann code-review), build.sh-Ausgabe zählt als Test
  archive:
    guidance:
      - Vor dem Archivieren code-review gegen die Delta-Specs laufen lassen
```

`context` gilt für alle Artefakte, `rules.<artefakt>` für ein bestimmtes, `operations.*.guidance` für apply/archive. Das ist die **Skill-Konfiguration**: Sie wird beim Lauf der Skills gelesen (weich), ist also keine harte Durchsetzung.

## `AGENTS.md` und `docs/agents/`

Kurzer Einstieg für Agenten, Details ausgelagert:

| Datei | Inhalt |
| --- | --- |
| `AGENTS.md` | Verweise: Issue-Tracker, Triage-Labels, Flow-Labels, Domänenhinweise |
| `docs/agents/issue-tracker.md` | GitHub Issues über `gh`; Sub-Issues und `blocked_by` über `gh api` |
| `docs/agents/triage-labels.md` | die fünf Triage-Rollen |
| `docs/agents/flow-labels.md` | `status:*`-Labels, genau eines je Issue, Regeln für den Wechsel |
| `docs/agents/domain.md` | Einzelkontext, wo Begriffe und ADRs liegen |

`/setup-matt-pocock-skills` erzeugt diese Dateien einmalig. `flow-labels.md` ist eine **eigene Datei**, damit ein erneuter Lauf des Setup-Skills sie nicht überschreibt.

## `.github/`

`workflows/test.yml` (bei jedem Pull Request und manuell):

| Job | Inhalt |
| --- | --- |
| `test` | `sh tests/run.sh` (Seite bauen, Shell- und Python-Tests); **Pflicht-Check** |
| `python (…)` je System: Ubuntu, macOS, Windows | `python -m unittest discover` und `flow validate` mit Python 3.11 |
| `gates` | `gate.py commits` und `gate.py secrets --range` über `origin/<Basis>..HEAD` |

`workflows/deploy.yml`: bei Push auf `master` Tests, Bau, Veröffentlichung auf GitHub Pages (`test` → `build` → `deploy`). `actions/setup-pandoc`: gemeinsame Installation der pandoc-Version.

**Branch-Schutz** auf `master` (Einstellung des Repo-Eigners, nicht im Repo): Pflicht-Checks `test`, `gates`, `python (ubuntu-latest)`, `python (macos-latest)`, `python (windows-latest)`; Verwaltende dürfen ihn umgehen (`enforce_admins` aus). Ändern:

```sh
gh api -X PATCH repos/comcy/comcy.github.io/branches/master/protection/required_status_checks \
  -F strict=false -f 'contexts[]=test' -f 'contexts[]=gates' -f 'contexts[]=python (ubuntu-latest)' \
  -f 'contexts[]=python (macos-latest)' -f 'contexts[]=python (windows-latest)'
```

## Git-Einstellungen im Klon

| Schlüssel / Datei | Gesetzt von | Bedeutung |
| --- | --- | --- |
| `core.hooksPath = .githooks` | `setup.py` | Hooks aktiv |
| `setup.agents` | `setup.py <agent>` | gewählte Agenten, beim nächsten Aufruf ohne Argument benutzt |
| `.git/info/exclude` | `setup.py` | lokale Agentenordner (`.claude/`) nicht einchecken |
| `user.email = christian.silfang@gmail.com` | von Hand | Autor der Commits |

`setup --check` meldet, wenn `core.hooksPath` fehlt (**echt**: `FEHLT core.hooksPath auf .githooks setzen (Abhilfe: python3 scripts/setup.py)`).

## kvasir-Konfiguration (optional)

| Datei | Ort | Inhalt |
| --- | --- | --- |
| `repos.toml` | `~/.config/kvasir/` | je Remote-URL: Branch-Vorlagen, Fetch- und Plattform-Intervall (synchronisierbar) |
| `local.toml` | `~/.config/kvasir/` | lokaler Pfad je Repo, `open_command` |
| `kvasir.toml` | Repo-Wurzel | geteilt: `[branches] patterns`, optional `[[phases]]` |

Vorrang: lokal vor Repo vor Standard. Siehe [03-beispiel-mit-kvasir.md](03-beispiel-mit-kvasir.md).

## Rezepte

| Ziel | Schritte |
| --- | --- |
| Neuen Status einführen | `states.tsv` (neue Zeile) → `transitions.tsv` (Übergänge) → `flow validate --strict` → `setup --labels` → `docs/agents/flow-labels.md` ergänzen |
| Phase abschalten | in `phases.tsv` Spalte `enabled` mit `no` |
| Neue Bedingung | `detectors.tsv` → Auswertung in `transition.py` (und kvasir) → Test → Doku |
| Commit-Typ erlauben | Zeile in `commit-types.tsv` |
| Secret-Treffer ist ein Fehlalarm | Zeile in `allow.tsv` mit Grund |
| Neues Pflichtprogramm | Zeile in `tools.tsv`, `setup --check` |
| Zusätzlicher Agent | Zeile in `agents.tsv` (Ordner vorher prüfen) |
