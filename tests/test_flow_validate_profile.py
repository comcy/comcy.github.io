"""Prüft `flow validate` für skills.tsv und roles.tsv von außen (Prozessaufruf auf Kopien, je Test ein Defekt)."""
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
    "phases.tsv": "id\tname\ttool\tdone_when\tlevel\tenabled\n"
                  "0\tEingang\t/triage\t-\trequired\tyes\n"
                  "3\tSchneiden\t/to-tickets\t-\trequired\tyes\n"
                  "6\tWissen\t-\t-\trequired\tyes\n"
                  "7\tOptional\t-\t-\toptional\tno\n",
    "skills.tsv": "skill\tphase\tlevel\tsource\thint\tmanual\n"
                  "triage\t0\trequired\tplugin x\tinstall x\tno\n"
                  "to-tickets\t3\t\tplugin x\tinstall x\tno\n"
                  "-\t6\t\t\t\tyes\n",
    "roles.tsv": "role\tphases\tallowed_tools\thuman_gate\tdescription\n"
                 "planner\t0,3\tRead Glob\tno\tPlant\n"
                 "human\t6\t-\tyes\tGibt frei\n",
}


def run(root, *extra):
    return subprocess.run([sys.executable, str(FLOW), "validate", "--root", str(root), *extra],
                          capture_output=True, text=True, encoding="utf-8")


class Profil(unittest.TestCase):
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
        self.put(name, FILES[name].replace(alt, neu))
        self.assertNotEqual(FILES[name], FILES[name].replace(alt, neu))

    def assert_fund(self, r, datei, text, stufe, code):
        self.assertEqual(r.returncode, code, r.stdout)
        zeilen = [l for l in r.stdout.splitlines() if l.startswith(f"workflow/{datei}:") and stufe in l]
        self.assertTrue(any(text in l for l in zeilen), f"{text!r} nicht in {zeilen}\n{r.stdout}")

    def test_gueltige_daten(self):
        r = run(self.root, "--strict")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 Fehler, 0 Warnungen", r.stdout)

    def test_echte_dateien_bestehen_strict(self):
        r = run(REPO, "--strict")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 Fehler, 0 Warnungen", r.stdout)

    def test_dateien_muessen_existieren(self):
        for name in ("skills.tsv", "roles.tsv"):
            with self.subTest(datei=name):
                (self.root / "workflow" / name).unlink()
                self.assert_fund(run(self.root), name, "Datei fehlt", "Fehler", 1)
                self.put(name, FILES[name])

    def test_unbekannte_phase(self):
        self.edit("skills.tsv", "to-tickets\t3", "to-tickets\t9")
        self.assert_fund(run(self.root), "skills.tsv", "'9'", "Fehler", 1)

    def test_roles_enabled_muss_yes_oder_no_sein(self):
        self.put("roles.tsv", FILES["roles.tsv"].replace("human_gate\tdescription", "human_gate\tdescription\tenabled")
                 .replace("Plant", "Plant\tyes").replace("Gibt frei", "Gibt frei\tbanane"))
        self.assert_fund(run(self.root), "roles.tsv", "enabled muss yes oder no sein, nicht 'banane'", "Fehler", 1)

    def test_unbekannte_phase_in_rolle(self):
        self.edit("roles.tsv", "planner\t0,3", "planner\t0,3,9")
        self.assert_fund(run(self.root), "roles.tsv", "'9'", "Fehler", 1)

    def test_fehlende_pflichtspalte(self):
        self.put("skills.tsv", "skill\tphase\tlevel\tsource\thint\n")
        self.assert_fund(run(self.root), "skills.tsv", "'manual'", "Fehler", 1)
        self.put("roles.tsv", "role\tphases\tallowed_tools\tdescription\n")
        self.assert_fund(run(self.root), "roles.tsv", "'human_gate'", "Fehler", 1)

    def test_unbedeckte_pflichtphase(self):
        self.edit("skills.tsv", "to-tickets\t3\t\tplugin x\tinstall x\tno\n", "")
        self.assert_fund(run(self.root), "phases.tsv", "Phase 3", "Fehler", 1)

    def test_manual_deckt_pflichtphase(self):
        self.edit("skills.tsv", "to-tickets\t3\t\tplugin x\tinstall x\tno", "-\t3\t\t\t\tyes")
        self.assertEqual(run(self.root, "--strict").returncode, 0)

    def test_phase_ohne_rolle(self):
        self.edit("roles.tsv", "planner\t0,3", "planner\t0")
        self.assert_fund(run(self.root), "phases.tsv", "Phase 3", "Fehler", 1)

    def test_rolle_ohne_phase_ist_warnung(self):
        self.put("roles.tsv", FILES["roles.tsv"] + "idle\t\t-\tno\tNichts\n")
        r = run(self.root)
        self.assert_fund(r, "roles.tsv", "idle", "Warnung", 0)
        self.assertEqual(run(self.root, "--strict").returncode, 1)

    def test_skill_einer_abgeschalteten_phase_ist_warnung(self):
        self.put("skills.tsv", FILES["skills.tsv"] + "x\t7\toptional\t\t\tno\n")
        r = run(self.root)
        self.assert_fund(r, "skills.tsv", "Phase '7'", "Warnung", 0)
        self.assertEqual(run(self.root, "--strict").returncode, 1)


if __name__ == "__main__":
    unittest.main()
