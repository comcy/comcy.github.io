"""Aufgabe roter-test: Prozessaufruf von evals/run.py mit einem Fake-`claude`, der echte Git-Verläufe im Wegwerf-Repo erzeugt."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from stubs import Stubs

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "evals" / "run.py"
AUFGABE = REPO / "evals" / "tasks" / "roter-test"

FAKE_CLAUDE = '''\
import os, subprocess
from pathlib import Path
aktion = Path(os.environ["FAKE_PLAN"]).read_text().strip()
TEST = """

class Regression(unittest.TestCase):
    def test_gleichheitszeichen_im_wert(self):
        self.assertEqual(kv.parse("url=a=b"), {"url": "a=b"})
"""
def git(*a):
    subprocess.run(["git", *a], check=True, capture_output=True)
def fix():
    p = Path("kvparse/kv.py")
    p.write_text(p.read_text().replace('.split("=")[:2]', '.split("=", 1)'))
def test():
    p = Path("kvparse/test_kv.py")
    p.write_text(p.read_text() + TEST)
def commit(msg):
    git("add", "-A")
    git("commit", "-q", "-m", msg)
if aktion == "test-zuerst":
    test(); commit("test: roter Test"); fix(); commit("fix: parse")
elif aktion == "nur-fix":
    fix(); commit("fix: parse")
elif aktion == "ein-commit":
    test(); fix(); commit("fix: parse mit Test")
elif aktion == "test-danach":
    fix(); commit("fix: parse"); test(); commit("test: nachgereicht")
elif aktion == "nur-test":
    test(); commit("test: roter Test")
'''


def lade_check():
    spec = importlib.util.spec_from_file_location("check_roter_test", AUFGABE / "check.py")
    modul = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "scripts" / "lib"))
    spec.loader.exec_module(modul)
    return modul.check


class RoterTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.stubs = Stubs(self.tmp)
        self.stubs.add_passthrough("git", __import__("shutil").which("git"))
        skript = self.stubs.dir / "fake_claude.py"
        skript.write_text(FAKE_CLAUDE, encoding="utf-8")
        if os.name == "nt":
            (self.stubs.dir / "claude.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
        else:
            w = self.stubs.dir / "claude"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
            w.chmod(0o755)

    def lauf(self, aktion):
        (self.tmp / "plan").write_text(aktion, encoding="utf-8")
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        env["FAKE_PLAN"] = str(self.tmp / "plan")
        env["GIT_CONFIG_GLOBAL"] = str(self.tmp / "nogit")
        out = self.tmp / ("out-" + aktion)
        r = subprocess.run([sys.executable, str(RUN), "roter-test", "--runs", "1", "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        return r, (r.stdout + r.stderr)

    def test_test_zuerst_besteht(self):
        r, text = self.lauf("test-zuerst")
        self.assertEqual(r.returncode, 0, text)
        self.assertIn("| roter-test | 1/1 | bestanden |", text)

    def test_fix_und_test_im_selben_commit_besteht(self):
        r, text = self.lauf("ein-commit")
        self.assertEqual(r.returncode, 0, text)

    def test_fix_ohne_neuen_test_scheitert(self):
        r, text = self.lauf("nur-fix")
        self.assertEqual(r.returncode, 1, text)
        self.assertIn("fehlschlägt", text)

    def test_test_erst_nach_dem_fix_scheitert(self):
        r, text = self.lauf("test-danach")
        self.assertEqual(r.returncode, 1, text)
        self.assertIn("fehlschlägt", text)

    def test_roter_test_ohne_fix_scheitert(self):
        r, text = self.lauf("nur-test")
        self.assertEqual(r.returncode, 1, text)
        self.assertIn("Endstand", text)

    def test_kein_commit_scheitert(self):
        r, text = self.lauf("nichts")
        self.assertEqual(r.returncode, 1, text)
        self.assertIn("Commit", text)

    def test_pruefung_veraendert_das_repo_nicht(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        git = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@x", *a],
                                        check=True, capture_output=True, text=True).stdout
        git("init", "-q", "-b", "master")
        for datei in (AUFGABE / "files").rglob("*"):
            if datei.is_file():
                ziel = repo / datei.relative_to(AUFGABE / "files")
                ziel.parent.mkdir(parents=True, exist_ok=True)
                ziel.write_bytes(datei.read_bytes())
        git("add", "-A"); git("commit", "-q", "-m", "chore: Start")
        (repo / "kvparse" / "kv.py").write_text(
            (repo / "kvparse" / "kv.py").read_text().replace('.split("=")[:2]', '.split("=", 1)'))
        git("commit", "-qam", "fix: parse")  # Fix ohne Test: die Prüfung muss einen Fehler melden
        ansicht = lambda: [git("status", "--porcelain"), git("worktree", "list"), git("branch"), git("rev-parse", "HEAD")]
        vorher = ansicht()
        fehler = lade_check()(SimpleNamespace(repo=repo, basis_branch="master"))
        self.assertTrue(fehler)
        self.assertEqual(ansicht(), vorher)
        self.assertEqual(len(vorher[1].splitlines()), 1)  # nur das Hauptverzeichnis, Prüf-Worktree entfernt


if __name__ == "__main__":
    unittest.main()
