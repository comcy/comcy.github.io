"""Prüft `flow validate` für metrics.tsv und metric-sources.tsv von außen (Prozessaufruf auf Kopien, je Test ein Defekt)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FLOW = REPO / "scripts" / "flow.py"

FILES = {
    "states.tsv": "id\tkind\tcolor\tdescription\na\ttriage\taaaaaa\tAnfang\nclosed\tterminal\t-\tEnde\n",
    "detectors.tsv": "name\targ\tdescription\nissue_open\t-\tIssue ist offen\n",
    "transitions.tsv": "from\tto\ttrigger\tguard\n-\ta\tstart\t-\na\tclosed\tende\tissue_open\n",
    "phases.tsv": "id\tname\ttool\tdone_when\tlevel\n6\tWissen\t-\t-\trequired\n",
    "skills.tsv": "skill\tphase\tlevel\tsource\thint\tmanual\n-\t6\t\t\t\tyes\n",
    "roles.tsv": "role\tphases\tallowed_tools\thuman_gate\tdescription\nhuman\t6\t-\tyes\tGibt frei\n",
    "metric-sources.tsv": "name\targ\tdescription\nticket_cycle_time\t-\tZeit\npr_duration\t-\tPR\n",
    "metrics.tsv": "id\tart\tname\tunit\tsource\ttarget\tenabled\n"
                   "cycle\tlagging\tDurchlaufzeit\th\tticket_cycle_time\t48\tyes\n"
                   "pr\tleading\tPR-Dauer\th\tpr_duration\t\tyes\n",
}


def run(root, *extra):
    return subprocess.run([sys.executable, str(FLOW), "validate", "--root", str(root), *extra],
                          capture_output=True, text=True, encoding="utf-8")


class Metriken(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "workflow").mkdir()
        for name, text in FILES.items():
            self.put(name, text)

    def put(self, name, text):
        (self.root / "workflow" / name).write_bytes(text.encode("utf-8"))

    def edit(self, name, alt, neu):
        self.assertIn(alt, FILES[name])
        self.put(name, FILES[name].replace(alt, neu))

    def assert_fund(self, r, datei, zeile, text, stufe, code):
        self.assertEqual(r.returncode, code, r.stdout)
        erwartet = f"workflow/{datei}:{zeile}: {stufe}:"
        self.assertTrue(any(l.startswith(erwartet) and text in l for l in r.stdout.splitlines()),
                        f"{erwartet} {text!r} nicht in\n{r.stdout}")

    def test_gueltige_daten(self):
        r = run(self.root, "--strict")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 Fehler, 0 Warnungen", r.stdout)

    def test_echte_dateien_bestehen_strict(self):
        r = run(REPO, "--strict")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 Fehler, 0 Warnungen", r.stdout)

    def test_echte_dateien_enthalten_fuenf_metriken(self):
        text = (REPO / "workflow" / "metrics.tsv").read_text(encoding="utf-8")
        for quelle in ("ticket_cycle_time", "pr_duration", "ci_red_before_merge",
                       "rework_fixes_per_change", "eval_pass_rate"):
            self.assertIn(f"\t{quelle}\t", text)

    def test_dateien_muessen_existieren(self):
        for name in ("metrics.tsv", "metric-sources.tsv"):
            with self.subTest(datei=name):
                (self.root / "workflow" / name).unlink()
                self.assert_fund(run(self.root), name, 1, "Datei fehlt", "Fehler", 1)
                self.put(name, FILES[name])

    def test_doppelte_id(self):
        self.edit("metrics.tsv", "pr\tleading", "cycle\tleading")
        self.assert_fund(run(self.root), "metrics.tsv", 3, "doppelte id 'cycle'", "Fehler", 1)

    def test_art_ungueltig(self):
        self.edit("metrics.tsv", "\tleading\t", "\tbanane\t")
        self.assert_fund(run(self.root), "metrics.tsv", 3, "'banane'", "Fehler", 1)

    def test_unit_ungueltig(self):
        self.edit("metrics.tsv", "PR-Dauer\th", "PR-Dauer\tkg")
        self.assert_fund(run(self.root), "metrics.tsv", 3, "'kg'", "Fehler", 1)

    def test_target_keine_zahl(self):
        self.edit("metrics.tsv", "\t48\t", "\tschnell\t")
        self.assert_fund(run(self.root), "metrics.tsv", 2, "target", "Fehler", 1)

    def test_target_dezimal_und_leer_sind_gueltig(self):
        self.edit("metrics.tsv", "\t48\t", "\t0.5\t")
        self.assertEqual(run(self.root, "--strict").returncode, 0)

    def test_unbekannte_quelle(self):
        self.edit("metrics.tsv", "\tpr_duration\t", "\tnirgends\t")
        self.assert_fund(run(self.root), "metrics.tsv", 3, "'nirgends'", "Fehler", 1)

    def test_quelle_abgeschaltet_ist_warnung(self):
        self.put("metric-sources.tsv", FILES["metric-sources.tsv"].replace("description", "description\tenabled")
                 .replace("Zeit", "Zeit\tno").replace("PR\n", "PR\tyes\n"))
        r = run(self.root)
        self.assert_fund(r, "metrics.tsv", 2, "abgeschaltet", "Warnung", 0)
        self.assertEqual(run(self.root, "--strict").returncode, 1)

    def test_fehlende_pflichtspalte(self):
        self.put("metrics.tsv", "id\tart\tname\tunit\ttarget\tenabled\n")
        self.assert_fund(run(self.root), "metrics.tsv", 1, "'source'", "Fehler", 1)
        self.put("metrics.tsv", FILES["metrics.tsv"])
        self.put("metric-sources.tsv", "name\tdescription\n")
        self.assert_fund(run(self.root), "metric-sources.tsv", 1, "'arg'", "Fehler", 1)


if __name__ == "__main__":
    unittest.main()
