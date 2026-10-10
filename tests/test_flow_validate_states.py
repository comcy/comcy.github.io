"""Prüft `flow validate` für workflow/states.tsv von außen: Aufruf als Prozess auf Kopien mit je einem Defekt.

Teststellen: der Aufruf `python scripts/flow.py validate --root <Ordner>` (Ausgabe und Exit-Code) und die Daten
darunter. Nichts im Skript wird direkt importiert, außer der Versionsprüfung.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FLOW = REPO / "scripts" / "flow.py"

HEADER = "id\tkind\tcolor\tdescription"
GOOD = [
    "needs-triage\ttriage\tfbca04\tMaintainer needs to evaluate",
    "ready-for-agent\ttriage\t0e8a16\tFully specified, ready for an AFK agent",
    "status:in-progress\tstatus\tfef2c0\tFlow: branch and PR open",
    "closed\tterminal\t-\tIssue closed (no label)",
]


def run_validate(root, *extra):
    return subprocess.run(
        [sys.executable, str(FLOW), "validate", "--root", str(root), *extra],
        capture_output=True, text=True, encoding="utf-8",
    )


# Die übrigen fünf Dateien müssen existieren (jede Datei ist Pflicht) und zu den Zuständen in GOOD passen,
# damit die Tests hier nur die Zustände prüfen.
SUPPORT = {
    "detectors.tsv": "name\targ\tdescription\nissue_open\t-\tIssue ist offen\n",
    "phases.tsv": "id\tname\ttool\tdone_when\tlevel\n0\tEingang\t/triage\tissue_open\trequired\n",
    "skills.tsv": "skill\tphase\tlevel\tsource\thint\tmanual\ntriage\t0\trequired\t\t\tno\n",
    "roles.tsv": "role\tphases\tallowed_tools\thuman_gate\tdescription\nplanner\t0\t-\tno\tPlant\n",
    "transitions.tsv": "from\tto\ttrigger\tguard\n"
                       "-\tneeds-triage\tstart\t-\n"
                       "needs-triage\tready-for-agent\tready\tissue_open\n"
                       "ready-for-agent\tclosed\tfertig\t-\n"
                       "-\tstatus:in-progress\tfluss\t-\n"
                       "status:in-progress\tclosed\tende\t-\n",
}


class WithStates(unittest.TestCase):
    """Legt je Test einen temporären Ordner mit workflow/states.tsv und den Begleitdateien an."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "workflow").mkdir()
        for name, text in SUPPORT.items():
            (self.root / "workflow" / name).write_bytes(text.encode("utf-8"))

    def write_states(self, lines, newline="\n", header=HEADER):
        text = newline.join([header, *lines]) + newline
        (self.root / "workflow" / "states.tsv").write_bytes(text.encode("utf-8"))
        return run_validate(self.root)


class RealData(unittest.TestCase):
    def test_echte_zustaende_sind_gueltig(self):
        r = run_validate(REPO)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 Fehler", r.stdout)

    def test_echte_zustaende_enthalten_alle_labels(self):
        ids = [line.split("\t")[0] for line in (REPO / "workflow" / "states.tsv").read_text(encoding="utf-8").splitlines()
               if line and not line.startswith("#")][1:]
        for erwartet in ["prio:1", "prio:2", "prio:3", "prio:4", "needs-triage", "needs-info", "ready-for-agent", "ready-for-human", "wontfix",
                         "status:ready-for-refinement", "status:in-refinement", "status:in-progress",
                         "status:in-review", "closed"]:
            self.assertIn(erwartet, ids)


class Leser(WithStates):
    def test_spalten_in_anderer_reihenfolge(self):
        zeilen = [f"{d}\t{c}\t{k}\t{i}" for (i, k, c, d) in (l.split("\t") for l in GOOD)]
        r = self.write_states(zeilen, header="description\tcolor\tkind\tid")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_zusaetzliche_spalte_wird_ignoriert(self):
        r = self.write_states([l + "\tegal" for l in GOOD], header=HEADER + "\tnotiz")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_fehlende_pflichtspalte(self):
        r = self.write_states([l.rsplit("\t", 1)[0] for l in GOOD], header="id\tkind\tcolor")
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv", r.stdout)
        self.assertIn("description", r.stdout)

    def test_windows_zeilenenden(self):
        r = self.write_states(GOOD, newline="\r\n")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_sonderzeichen_in_der_beschreibung_trennen_keine_zeilen(self):
        # \x0b und \x0c gelten bei str.splitlines als Zeilenende, in einer Datei sind sie nur Zeichen
        r = self.write_states([GOOD[0].replace("evaluate", "eval\x0cuate"), *GOOD[1:]])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_kommentare_und_leerzeilen_werden_ignoriert(self):
        r = self.write_states(["# Kommentar", "", *GOOD, "   ", "# noch einer"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_falsche_spaltenzahl_mit_zeilennummer(self):
        r = self.write_states([GOOD[0], "kaputt\ttriage\tfbca04", *GOOD[1:]])
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv:3:", r.stdout)

    def test_fehlende_datei(self):
        (self.root / "workflow" / "states.tsv").unlink(missing_ok=True)
        r = run_validate(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv", r.stdout)


class Zustaende(WithStates):
    def test_doppelte_kennung_mit_zeile(self):
        r = self.write_states([GOOD[0], GOOD[0], *GOOD[1:]])
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv:3:", r.stdout)
        self.assertIn("needs-triage", r.stdout)

    def test_ungueltige_farbe(self):
        for farbe in ["fbca0", "gggggg", "fbca044", "#fbca04", ""]:
            with self.subTest(farbe=farbe):
                r = self.write_states(["needs-triage\ttriage\t%s\tBeschreibung" % farbe, GOOD[3]])
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("workflow/states.tsv:2:", r.stdout)

    def test_strich_als_farbe_nur_bei_terminal(self):
        r = self.write_states(["needs-triage\ttriage\t-\tBeschreibung", GOOD[3]])
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv:2:", r.stdout)

    def test_leere_beschreibung(self):
        r = self.write_states(["needs-triage\ttriage\tfbca04\t", GOOD[3]])
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv:2:", r.stdout)

    def test_ungueltige_art(self):
        r = self.write_states(["needs-triage\tflow\tfbca04\tBeschreibung", GOOD[3]])
        self.assertEqual(r.returncode, 1)
        self.assertIn("flow", r.stdout)

    def test_kein_terminaler_zustand(self):
        r = self.write_states(GOOD[:3])
        self.assertEqual(r.returncode, 1)
        self.assertIn("terminal", r.stdout)

    def test_zwei_terminale_zustaende(self):
        r = self.write_states([*GOOD, "done\tterminal\t-\tAndere Ende"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("terminal", r.stdout)

    def test_enabled_nur_yes_oder_no(self):
        r = self.write_states([l + "\tyes" for l in GOOD[:3]] + [GOOD[3] + "\tvielleicht"], header=HEADER + "\tenabled")
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv:5:", r.stdout)

    def test_alle_funde_werden_ausgegeben_mit_zusammenfassung(self):
        r = self.write_states(["a\ttriage\tzzzzzz\tx", "b\ttriage\tfbca04\t", GOOD[3]])
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow/states.tsv:2:", r.stdout)
        self.assertIn("workflow/states.tsv:3:", r.stdout)
        zustandsfunde = [l for l in r.stdout.splitlines() if l.startswith("workflow/states.tsv:")]
        self.assertEqual(len(zustandsfunde), 2, r.stdout)
        self.assertRegex(r.stdout, r"\d+ Fehler, \d+ Warnungen")

    def test_ausgabeformat_datei_zeile_meldung(self):
        r = self.write_states([GOOD[0], GOOD[0], *GOOD[1:]])
        erste = next(l for l in r.stdout.splitlines() if l.startswith("workflow/"))
        teile = erste.split(":", 2)
        self.assertEqual(teile[0], "workflow/states.tsv")
        self.assertTrue(teile[1].isdigit())
        self.assertTrue(teile[2].strip())


class Versionspruefung(unittest.TestCase):
    # ponytail: Ausnahme von "Tests von außen": ein Test-Interpreter kann nicht als Python 3.9 starten, deshalb wird die
    # Funktion direkt aufgerufen. Der Start unter echtem altem Python ist nicht geprüft.
    def test_zu_altes_python_meldet_die_geforderte_version(self):
        sys.path.insert(0, str(REPO / "scripts"))
        try:
            import pycheck
        finally:
            sys.path.pop(0)
        with self.assertRaises(SystemExit) as ctx:
            pycheck.require_python((3, 9, 1))
        self.assertIn("3.11", str(ctx.exception.code))
        self.assertIn("3.9", str(ctx.exception.code))
        pycheck.require_python((3, 11, 0))  # keine Ausnahme


if __name__ == "__main__":
    unittest.main()
