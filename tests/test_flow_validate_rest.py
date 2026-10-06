"""Prüft `flow validate` für transitions.tsv, phases.tsv und detectors.tsv von außen (Prozessaufruf auf Kopien)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FLOW = REPO / "scripts" / "flow.py"

STATES = """id\tkind\tcolor\tdescription
a\ttriage\taaaaaa\tAnfang
b\ttriage\tbbbbbb\tMitte
c\tstatus\tcccccc\tFluss
d\tstatus\tdddddd\tFluss Ende
closed\tterminal\t-\tEnde
"""
DETECTORS = """name\targ\tdescription
issue_open\t-\tIssue ist offen
label\ttext\tLabel gesetzt
pr_state\tenum:draft|ready|merged\tZustand des PR
file_exists\tpath\tDatei vorhanden
"""
TRANSITIONS = """from\tto\ttrigger\tguard
-\ta\tstart\t-
a\tb\tweiter\tissue_open
b\tclosed\tende\tlabel:b
-\tc\tfluss\tpr_state:draft
c\td\tfertig\tpr_state:merged,issue_open
d\tclosed\tende\t-
"""
PHASES = """id\tname\ttool\tdone_when\tlevel
S\tSetup\tscripts/setup.py\tfile_exists:openspec/config.yaml\trequired
0\tEingang\t/triage\tissue_open\trequired
4\tBauen\t/implement\t-\trequired
4b\tAbnahme\t-\tlabel:Lokale Abnahme\toptional
5\tAbschluss\t/archive\t-\trequired
"""


def run(root, *extra):
    return subprocess.run([sys.executable, str(FLOW), "validate", "--root", str(root), *extra],
                          capture_output=True, text=True, encoding="utf-8")


class Daten(unittest.TestCase):
    """Eine kleine, gültige Datenmenge in einem temporären Ordner; jeder Test ändert genau eine Datei."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "workflow").mkdir()
        self.put("states.tsv", STATES)
        self.put("detectors.tsv", DETECTORS)
        self.put("transitions.tsv", TRANSITIONS)
        self.put("phases.tsv", PHASES)

    def put(self, name, text):
        (self.root / "workflow" / name).write_bytes(text.encode("utf-8"))

    def edit(self, name, alt, neu):
        pfad = self.root / "workflow" / name
        text = pfad.read_text(encoding="utf-8")
        self.assertIn(alt, text)
        pfad.write_text(text.replace(alt, neu), encoding="utf-8", newline="\n")

    def assert_fund(self, r, datei, text, code=1):
        self.assertEqual(r.returncode, code, r.stdout)
        zeilen = [l for l in r.stdout.splitlines() if l.startswith(f"workflow/{datei}:")]
        self.assertTrue(any(text in l for l in zeilen), f"{text!r} nicht in {zeilen}\n{r.stdout}")


class Grunddaten(Daten):
    def test_gueltige_testdaten(self):
        r = run(self.root)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 Fehler, 0 Warnungen", r.stdout)

    def test_echte_daten_ohne_fehler_und_warnungen(self):
        r = run(REPO, "--strict")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 Fehler, 0 Warnungen", r.stdout)

    def test_jede_der_vier_dateien_muss_existieren(self):
        for name in ("states.tsv", "transitions.tsv", "phases.tsv", "detectors.tsv"):
            with self.subTest(datei=name):
                (self.root / "workflow" / name).unlink()
                r = run(self.root)
                self.assert_fund(r, name, "Datei fehlt")
                self.put(name, {"states.tsv": STATES, "transitions.tsv": TRANSITIONS,
                                "phases.tsv": PHASES, "detectors.tsv": DETECTORS}[name])


class Uebergaenge(Daten):
    def test_unbekannter_zustand_in_from_und_to(self):
        self.edit("transitions.tsv", "a\tb\tweiter", "zz\tb\tweiter")
        self.assert_fund(run(self.root), "transitions.tsv", "zz")
        self.edit("transitions.tsv", "zz\tb\tweiter", "a\tyy\tweiter")
        self.assert_fund(run(self.root), "transitions.tsv", "yy")

    def test_uebergang_ueber_dimensionen(self):
        self.edit("transitions.tsv", "a\tb\tweiter\tissue_open", "a\tc\tweiter\tissue_open")
        self.assert_fund(run(self.root), "transitions.tsv", "Dimension")

    def test_start_und_terminaler_zustand_sind_erlaubt(self):
        r = run(self.root)  # '-' -> a, '-' -> c und b -> closed stehen in den Testdaten
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_fehlende_pflichtspalte(self):
        self.put("transitions.tsv", "from\tto\ttrigger\n-\ta\tstart\n")
        self.assert_fund(run(self.root), "transitions.tsv", "guard")

    def test_ziel_darf_nicht_start_sein(self):
        self.edit("transitions.tsv", "a\tb\tweiter\tissue_open", "a\t-\tweiter\tissue_open")
        self.assert_fund(run(self.root), "transitions.tsv", "-")


class Detektoren(Daten):
    def test_unbekannter_detektor(self):
        self.edit("transitions.tsv", "issue_open", "pr_open:draft")
        self.assert_fund(run(self.root), "transitions.tsv", "pr_open")

    def test_falsches_enum_argument_nennt_erlaubte_werte(self):
        self.edit("transitions.tsv", "pr_state:draft", "pr_state:open")
        r = run(self.root)
        self.assert_fund(r, "transitions.tsv", "draft|ready|merged")

    def test_fehlendes_und_ueberzaehliges_argument(self):
        self.edit("transitions.tsv", "pr_state:draft", "pr_state")
        self.assert_fund(run(self.root), "transitions.tsv", "Argument")
        self.edit("transitions.tsv", "fluss\tpr_state\n", "fluss\tpr_state:draft\n")
        self.edit("transitions.tsv", "weiter\tissue_open", "weiter\tissue_open:x")
        self.assert_fund(run(self.root), "transitions.tsv", "Argument")

    def test_argument_mit_doppelpunkt_ist_erlaubt(self):
        self.edit("transitions.tsv", "label:b", "label:status:in-progress")
        r = run(self.root)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_detektoren_datei_pruefen(self):
        self.edit("detectors.tsv", "label\ttext", "label\tfrei")
        self.assert_fund(run(self.root), "detectors.tsv", "frei")
        self.edit("detectors.tsv", "label\tfrei", "issue_open\ttext")
        self.assert_fund(run(self.root), "detectors.tsv", "issue_open")

    def test_enum_ohne_werte(self):
        self.edit("detectors.tsv", "enum:draft|ready|merged", "enum:")
        self.assert_fund(run(self.root), "detectors.tsv", "enum")


class Phasen(Daten):
    def test_doppelte_phase(self):
        self.edit("phases.tsv", "4b\tAbnahme", "4\tAbnahme")
        self.assert_fund(run(self.root), "phases.tsv", "doppelte id")

    def test_ungueltige_stufe(self):
        self.edit("phases.tsv", "\toptional", "\tvielleicht")
        self.assert_fund(run(self.root), "phases.tsv", "vielleicht")

    def test_unbekannter_detektor_in_done_when(self):
        self.edit("phases.tsv", "0\tEingang\t/triage\tissue_open", "0\tEingang\t/triage\tnope")
        self.assert_fund(run(self.root), "phases.tsv", "nope")


class Warnungen(Daten):
    def test_verweis_auf_abgeschalteten_zustand_ist_nur_warnung(self):
        self.put("states.tsv", STATES.replace("id\tkind\tcolor\tdescription", "id\tkind\tcolor\tdescription\tenabled")
                 .replace("\ttriage\tbbbbbb\tMitte", "\ttriage\tbbbbbb\tMitte\tno")
                 .replace("Anfang\n", "Anfang\tyes\n").replace("Fluss\n", "Fluss\tyes\n")
                 .replace("Fluss Ende\n", "Fluss Ende\tyes\n").replace("Ende\n", "Ende\tyes\n"))
        r = run(self.root)
        self.assert_fund(r, "transitions.tsv", "enabled=no", code=0)
        self.assertIn("Warnung", r.stdout)

    def test_strikter_modus_macht_warnungen_zu_fehlern(self):
        self.edit("transitions.tsv", "d\tclosed\tende\t-\n", "")
        r = run(self.root)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Warnung", r.stdout)
        self.assertEqual(run(self.root, "--strict").returncode, 1)

    def test_zustand_ohne_ausgang_wird_gemeldet(self):
        self.edit("transitions.tsv", "d\tclosed\tende\t-\n", "")
        self.assert_fund(run(self.root), "states.tsv", "kein ausgehender", code=0)

    def test_zustand_ohne_eingang_wird_gemeldet(self):
        self.edit("transitions.tsv", "-\tc\tfluss\tpr_state:draft\n", "")
        self.assert_fund(run(self.root), "states.tsv", "kein eingehender", code=0)

    def test_phasen_nicht_aufsteigend(self):
        self.edit("phases.tsv", "5\tAbschluss", "3\tAbschluss")
        self.assert_fund(run(self.root), "phases.tsv", "aufsteigend", code=0)

    def test_mehrere_dateien_alle_funde_in_einem_lauf(self):
        self.edit("transitions.tsv", "pr_state:draft", "pr_state:open")
        self.edit("phases.tsv", "\toptional", "\tvielleicht")
        r = run(self.root)
        self.assert_fund(r, "transitions.tsv", "open")
        self.assert_fund(r, "phases.tsv", "vielleicht")
        self.assertIn("2 Fehler", r.stdout)


if __name__ == "__main__":
    unittest.main()
