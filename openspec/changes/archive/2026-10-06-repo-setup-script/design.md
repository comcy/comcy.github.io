# Design

## Context

- Der Prozess steht als Prosa (`docs/workflow.md`, `docs/agents/*.md`), Labels auf GitHub sind von Hand angelegt, Adapter von Hand eingerichtet. Entscheidungen aus dem Grilling zu #14, #28 und #11 sind im Kommentar bei #14 zusammengefasst; Motivation siehe `proposal.md`, Anforderungen siehe die Specs `workflow-definition` und `repo-setup`.
- kvasir (Python, optional) liest später dieselben Dateien; der Blog bleibt Shell und pandoc auf Linux.

## Goals / Non-Goals

**Goals:**
- Daten statt Code: Zustände, Übergänge, Phasen, Vokabular und Programme als Dateien, prüfbar, mit einem Leser als einzige Zugriffsstelle.
- Dasselbe Verhalten unter Linux, macOS und Windows, geprüft in der CI.
- Hohe Testautomatisierung (Teststellen von außen, wenige Zeilen Produktionscode je Test).

**Non-Goals:**
- Kein Ausführen von Übergängen, keine Auswertung der Detektoren gegen den Tracker, keine Git-Hooks (siehe Out of Scope im Proposal).
- Keine JSON- oder YAML-Quelle, kein Paket zur Installation.

## Decisions

**1. Python ab 3.11, nur Standardbibliothek.**
Gründe: kvasir ist Python (später gemeinsame Auswertung der Detektoren möglich), der KI-Werkzeugkasten (Evals, Orchestrierung) ist überwiegend Python, es ist vorhanden. `csv`, `argparse`, `subprocess`, `shutil.which` und `unittest` reichen. *Alternative Node mit TypeScript:* Node ist ohnehin Voraussetzung (OpenSpec), aber ein zweiter Auswerter neben kvasir wäre nötig und TypeScript bräuchte eine höhere Node-Mindestversion oder `tsc`.

**2. Aufbau.**
`scripts/lib/workflow.py` (Leser und Prüfungen), `scripts/flow.py` (Befehlszeile: `validate`), `scripts/setup.py` (Befehlszeile), `scripts/setup.d/tools.tsv`, `scripts/setup.d/agents.tsv`. Aufruf: `python3 scripts/setup.py` (Windows `py -3 scripts\setup.py`). Ein dünner Einstieg am Anfang jeder Datei prüft `sys.version_info` vor dem Import, damit zu altes Python eine klare Meldung statt eines Syntaxfehlers gibt.

**3. Der Leser ist die Grenze.**
`scripts/lib/workflow.py` liest TSV (Kommentare, Kopfzeile, Zuordnung nach Namen, CRLF) und liefert Datensätze. Alle Prüfungen und Verbraucher nutzen nur diese Datensätze. Ein späterer Wechsel auf JSON oder YAML ändert nur den Leser. Kriterien für den Wechsel: ODER-Bedingungen oder Alternativen werden gebraucht, ein Schritt braucht mehr als etwa acht Eigenschaften, Tab-Fehler häufen sich.

**3a. Prüfungen als Liste kleiner Funktionen.**
Jede Prüfung (Spalten, Eindeutigkeit, Farben, Verweise, Detektoren, Warnungen) ist eine Funktion, die Funde als `(datei, zeile, stufe, meldung)` liefert. `flow validate` sammelt alle, sortiert nach Datei und Zeile und gibt sie aus. So lassen sich Prüfungen einzeln ergänzen und testen.

**4. Programme nur über `subprocess` mit Argumentlisten, aufgelöst mit `shutil.which`.**
Kein `shell=True`, keine Zeichenketten. `shutil.which` berücksichtigt unter Windows `PATHEXT`, dadurch werden `.cmd`-Programme gefunden. Versionen kommen aus dem Aufruf in `tools.tsv` (z. B. `node --version`), die Zahl wird per regulärem Ausdruck gelesen und als Tupel verglichen.

**5. Wirkungen von `setup` und Reihenfolge.**
Lokal: `git config --local` lesen und schreiben, `.git/info/exclude` zeilenweise ergänzen (nur fehlende Zeilen, nie überschreiben), `openspec init --tools …` und `openspec update`. Außen: `gh label list` (lesen) und `gh label create` nur mit `--labels`. Jede Wirkung gibt eine Zeile aus ("angelegt", "unverändert", "fehlt"), `--check` nutzt dieselben Schritte als reines Lesen. Dadurch entsteht keine zweite Logik für die Prüfung.

**6. Tests von außen, Programme als Stubs.**
`unittest` in `tests/`. Zwei Gruppen: (a) `setup.py` und `flow.py` als Prozess in einem **temporären Git-Repo** mit **Stubs** für `gh`, `openspec`, `node`, `pandoc` am Anfang von `PATH`; die Stubs schreiben ihre Aufrufe in eine Logdatei und geben Fixture-Antworten aus. (b) `flow validate` auf **Kopien der Daten** mit je einem Defekt. Stubs sind kleine Python-Skripte; unter Windows liegt je Stub ein `.cmd`-Wrapper, der sie mit `python` startet.

**7. CI.**
Neuer Job mit Matrix `ubuntu-latest`, `macos-latest`, `windows-latest`, der nur die Python-Tests und `flow validate` ausführt (ohne pandoc). Der Check heißt weiterhin `test` für die Shell-Tests auf Ubuntu; der neue Job bekommt einen eigenen Namen und wird erst nach der ersten grünen Reihe in den Branch-Schutz aufgenommen. `.gitattributes` setzt `eol=lf` für `workflow/*.tsv`, `scripts/**` und `tests/**`, damit Windows keine CRLF in die Daten schreibt (der Leser akzeptiert beides).

**8. Schritte statt Verzweigungen (Umsetzung).**
`scripts/lib/local.py` plant die Schritte (`Step` mit Beschriftung und Ausführung), `plan` liefert nur die fehlenden. Der normale Lauf führt sie aus, `--check` meldet dieselbe Liste als `FEHLT`. Dadurch gibt es keine zweite Prüflogik. Programme laufen mit dem Repo als Arbeitsordner (`cwd=<Repo>`), weil `openspec init` im Arbeitsordner arbeitet. `openspec init` läuft mit `--no-animation`.

**9. Fehler und Hinweise (Umsetzung).**
Fehlendes Pflichtprogramm und unbekannter Agent sind Fehler und verhindern jede Änderung. Dinge, die ohne GitHub nicht prüfbar sind (keine Anmeldung, kein GitHub-Remote), sind ohne `--labels` nur ein Hinweis, mit `--labels` ein Fehler. Diese Regel kam aus einem manuellen Probelauf in einem Klon ohne GitHub-Remote.

**10. Gemeinsamer Programmaufruf und Folgen des Reviews.**
Alle Programmaufrufe laufen über `scripts/lib/proc.py` (Argumentliste, ohne Shell, Zeitlimit 60 Sekunden, einheitliche Kodierung, `SetupError` bei fehlendem Programm oder Zeitüberschreitung). Das Review vor dem Archivieren fand außerdem: fehlgeschlagenes `git config` wurde als erledigt gemeldet, ein bloßer `.claude/`-Ordner galt als Adapter, `setup agents` löschte die gespeicherte Wahl, ein älteres `openspec` löste ein Update aus, Labelnamen wurden groß- und kleinschreibungsabhängig verglichen, und `splitlines` trennte Dateien an Sonderzeichen. Alles ist behoben und per Test belegt.

**Über die Spec hinaus geprüft** (bewusst, mit Tests): `enabled` nur `yes` oder `no`, leerer `trigger`, kein Übergang aus `terminal`, Mindestversion, Stufe und Aufruf in `tools.tsv`, Ordnerform in `agents.tsv`.

## Risks / Trade-offs

- [Stubs bilden `gh` und `openspec` nur nach, wie sie dokumentiert sind] → Manueller Probelauf im PR mit den echten Programmen, Ausgabe als Beleg; Abweichungen werden zu neuen Testfällen.
- [`.cmd`-Stubs unter Windows verhalten sich anders als Skripte] → Die Windows-Reihe in der CI deckt das auf; als Rückfall eine Umgebungsvariable für das Verzeichnis der Stubs vor dem Aufruf.
- [`python3` und `py -3` unterscheiden sich] → Die README nennt beide Formen, die CI nutzt den jeweiligen Befehl; Python vor 3.11 bekommt eine eigene Meldung.
- [Detektoren hier nur als Namen] → Es entsteht keine zweite Auswertung neben kvasir; die Auswertung kommt erst mit `flow start` bzw. kvasir, dann gegen dasselbe Vokabular.
- [Daten ohne Verbraucher verrotten] → `flow validate` läuft in jedem PR; `states.tsv` ist ab dem ersten Ticket Quelle der Labels, die Doku verweist darauf.
- [TSV ist für Menschen fehleranfällig (Tabs)] → `.editorconfig`-Hinweis in der README, `flow validate` meldet Spaltenzahl und Zeile.

## Migration Plan

Neue Dateien, keine Umleitung bestehender URLs. Die bestehende Checkliste in `docs/workflow.md` bleibt bis zum letzten Ticket und wird dort durch den Aufruf ersetzt. Rollback: Ordner und Skripte entfernen, die Labels auf GitHub bleiben unverändert.

## Open Questions

- Soll `setup` später auch `kvasir init` aufrufen? Das gehört in das kvasir-Ticket zu `kvasir.toml` (#53), nicht hierher. `setup` meldet nur einen Hinweis, wenn kvasir fehlt.
- Echte Prüfung von `gh label create` gegen ein Repo mit fehlenden Labels steht aus (nur Stubs und ein Probelauf ohne fehlende Labels).
