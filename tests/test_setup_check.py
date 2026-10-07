"""Prüft `setup.py --check` von außen: Aufruf als Prozess in einem temporären Repo mit Stub-Programmen im PATH.

Teststellen: der Aufruf (Ausgabe, Exit-Code, Wirkung auf Git-Konfiguration, .git/info/exclude und die aufgerufenen
Programme) und die Daten darunter (tools.tsv, workflow/).
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import MitRepo, skill_datei

REPO = Path(__file__).resolve().parent.parent
SETUP = REPO / "scripts" / "setup.py"

TOOLS = (
    "name\tmin_version\tlevel\tversion_cmd\thint\n"
    "git\t-\trequired\tgit --version\thttps://git-scm.com\n"
    "gh\t-\trequired\tgh --version\thttps://cli.github.com, danach gh auth login\n"
    "node\t20.19\trequired\tnode --version\thttps://nodejs.org\n"
    "openspec\t1.14\trequired\topenspec --version\tnpm i -g @fission-ai/openspec@latest\n"
    "pandoc\t3.1\trequired\tpandoc --version\tPaketmanager\n"
    "kvasir\t-\trecommended\tkvasir --version\tsiehe kvasir-Repo\n"
)


class Basis(MitRepo):
    """Wie MitRepo, mit eigener tools.tsv (feste Mindestversionen) und --check als Standardaufruf."""

    def setUp(self):
        super().setUp()
        self.set_tools(TOOLS)
        (self.repo / ".agents" / "skills" / "openspec-propose").mkdir(parents=True)
        (self.repo / ".agents" / "skills" / "openspec-propose" / "SKILL.md").write_text(skill_datei("1.14.0")[
            ".agents/skills/openspec-propose/SKILL.md"], encoding="utf-8")

    def check(self, *extra):
        return self.run_setup("--check", *extra)


class Voraussetzungen(Basis):
    def test_alles_da_und_neu_genug(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 Fehler", r.stdout)

    def test_pflichtprogramm_fehlt_mit_hinweis(self):
        (self.stubs.dir / ("gh.cmd" if sys.platform == "win32" else "gh")).unlink()
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("gh", r.stdout)
        self.assertIn("https://cli.github.com", r.stdout)

    def test_version_zu_alt_nennt_beide_versionen(self):
        self.stubs.add("node", "v18.19.0")
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("node", r.stdout)
        self.assertIn("18.19", r.stdout)
        self.assertIn("20.19", r.stdout)

    def test_versionsvergleich_ist_numerisch(self):
        self.stubs.add("node", "v20.2.0")  # 20.2 ist älter als 20.19
        self.assertEqual(self.check().returncode, 1)
        self.stubs.add("node", "v20.19.0")  # genau die Mindestversion
        self.assertEqual(self.check().returncode, 0)
        self.stubs.add("node", "v21.0.0")
        self.assertEqual(self.check().returncode, 0)

    def test_empfohlenes_programm_fehlt_nur_hinweis(self):
        (self.stubs.dir / ("kvasir.cmd" if sys.platform == "win32" else "kvasir")).unlink()
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("kvasir", r.stdout)
        self.assertIn("empfohlen", r.stdout)
        self.assertIn("1 Hinweis", r.stdout)

    def test_ohne_mindestversion_genuegt_vorhandensein(self):
        self.stubs.add("kvasir", "irgendwas ohne Versionsnummer")
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_version_nicht_erkennbar_bei_geforderter_mindestversion(self):
        self.stubs.add("pandoc", "keine Zahl hier")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("pandoc", r.stdout)
        self.assertIn("Version", r.stdout)

    def test_versionsausgabe_auf_stderr_wird_gelesen(self):
        self.stubs.add("node", responses=[{"args": ["--version"], "stderr": "v22.4.0", "stdout": ""}])
        self.assertEqual(self.check().returncode, 0)


class OhneAenderung(Basis):
    def test_check_aendert_nichts_und_ruft_nur_lesend_auf(self):
        vorher = self.zustand()
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.zustand(), vorher)
        aufrufe = self.stubs.calls()
        self.assertTrue(aufrufe)
        lesend = (["--version"], ["auth", "status"], ["label", "list", "--limit", "500", "--json", "name"])
        self.assertTrue(all(a["args"] in lesend for a in aufrufe), aufrufe)  # nur Versionen, Anmeldung, Label-Liste

    def test_check_legt_keine_dateien_an(self):
        vorher = sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*") if ".git/" not in p.as_posix())
        self.check()
        nachher = sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*") if ".git/" not in p.as_posix())
        self.assertEqual(vorher, nachher)


class Hooks(Basis):
    def setUp(self):
        super().setUp()
        (self.repo / ".githooks").mkdir()
        self.stubs.add("python3", "Python 3.12.0")

    def test_hooks_path_nicht_gesetzt_wird_gemeldet_ohne_zu_aendern(self):
        vorher = self.zustand()
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("core.hooksPath", r.stdout)
        self.assertIn("setup.py", r.stdout)
        self.assertEqual(self.zustand(), vorher)
        self.assertIsNone(self.git_config("core.hooksPath"))

    def test_python_nicht_im_path_wird_gemeldet(self):
        self.run_setup()  # setzt core.hooksPath
        (self.stubs.dir / ("python3.cmd" if sys.platform == "win32" else "python3")).unlink()
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("python", r.stdout)
        self.assertIn("PATH", r.stdout)

    def test_alles_in_ordnung_ohne_zusaetzlichen_befund(self):
        self.run_setup()
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("FEHLT", r.stdout)


class Daten(Basis):
    def test_ungueltige_prozessdaten_machen_check_rot_mit_denselben_meldungen(self):
        pfad = self.repo / "workflow" / "states.tsv"
        pfad.write_text(pfad.read_text(encoding="utf-8").replace("fbca04", "zzzzzz"), encoding="utf-8", newline="\n")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stdout, r"workflow/states\.tsv:\d+: Fehler: ungültige Farbe 'zzzzzz'")

    def test_warnungen_aus_den_prozessdaten_aendern_den_exit_code_nicht(self):
        pfad = self.repo / "workflow" / "states.tsv"
        with pfad.open("a", encoding="utf-8", newline="\n") as f:
            f.write("losgeloest\tstatus\t123456\tOhne Übergänge\n")  # erzeugt nur Warnungen
        self.gh()  # das neue Label gibt es auf GitHub, sonst fehlte es
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Warnung", r.stdout)
        self.assertRegex(r.stdout, r"0 Fehler, [1-9]\d* Warnungen")

    def test_tools_datei_mit_fehlender_spalte(self):
        self.set_tools("name\tlevel\tversion_cmd\thint\ngit\trequired\tgit --version\tx\n")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("scripts/setup.d/tools.tsv", r.stdout)
        self.assertIn("min_version", r.stdout)

    def test_tools_datei_mit_ungueltiger_stufe(self):
        self.set_tools(TOOLS.replace("required\tgit", "pflicht\tgit", 1))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("pflicht", r.stdout)

    def test_fehlende_tools_datei(self):
        (self.repo / "scripts" / "setup.d" / "tools.tsv").unlink()
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("scripts/setup.d/tools.tsv", r.stdout)


if __name__ == "__main__":
    unittest.main()
