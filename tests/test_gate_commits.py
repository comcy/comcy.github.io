"""Prüft `gate.py commits` und den Hook `commit-msg` von außen: Prozessaufruf in einem Wegwerf-Git-Repo.

Das echte Repo wird nie berührt: Skript und Hooks werden in ein temporäres Repo kopiert, Git-Konfiguration isoliert.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class MitGitRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        self.git("init", "-q", "-b", "main")
        for k, v in (("user.name", "Test"), ("user.email", "test@example.org"), ("commit.gpgsign", "false")):
            self.git("config", k, v)
        shutil.copytree(REPO / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(REPO / ".githooks", self.repo / ".githooks")

    def git(self, *args, check=True):
        r = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, encoding="utf-8",
                           env=self.env)
        if check and r.returncode:
            self.fail(f"git {' '.join(args)}: {r.stdout}{r.stderr}")
        return r

    def commit(self, betreff, *extra, check=True):
        return self.git("commit", "-q", "--allow-empty", *extra, "-m", betreff, check=check)

    def gate(self, *args):
        return subprocess.run([sys.executable, str(self.repo / "scripts" / "gate.py"), *args], cwd=self.repo,
                              capture_output=True, text=True, encoding="utf-8", env=self.env)


class CommitsBereich(MitGitRepo):
    def pruefe(self, betreff):
        self.commit("chore: Start")
        self.commit(betreff)
        return self.gate("commits", "HEAD~1..HEAD")

    def test_gueltiger_betreff(self):
        r = self.pruefe("feat(setup): Labels anlegen")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_ungueltiger_betreff_nennt_commit_und_regel(self):
        r = self.pruefe("Labels angelegt")
        self.assertNotEqual(r.returncode, 0)
        sha = self.git("rev-parse", "--short", "HEAD").stdout.strip()
        self.assertIn(sha, r.stdout)
        self.assertIn("Labels angelegt", r.stdout)
        self.assertIn("type(scope)!: Betreff", r.stdout)

    def test_ohne_scope(self):
        self.assertEqual(self.pruefe("fix: Tippfehler").returncode, 0)

    def test_breaking_mit_ausrufezeichen(self):
        self.assertEqual(self.pruefe("feat(api)!: Format ändern").returncode, 0)
        self.assertEqual(self.pruefe("refactor!: Aufbau ändern").returncode, 0)

    def test_unbekannter_typ(self):
        self.assertNotEqual(self.pruefe("wip: halb fertig").returncode, 0)

    def test_leerer_betreff_und_leerer_scope(self):
        self.assertNotEqual(self.pruefe("feat:").returncode, 0)
        self.assertNotEqual(self.pruefe("feat(): Betreff").returncode, 0)

    def test_revert_ist_erlaubt(self):
        self.assertEqual(self.pruefe('Revert "feat(setup): Labels anlegen"').returncode, 0)

    def test_merge_commit_ist_erlaubt(self):
        self.commit("chore: Start")
        self.git("checkout", "-q", "-b", "zweig")
        self.commit("feat: Zweig")
        self.git("checkout", "-q", "main")
        self.commit("fix: Main")
        self.git("merge", "-q", "--no-ff", "-m", "Merge branch 'zweig'", "zweig")
        r = self.gate("commits", "HEAD~1..HEAD")  # nur der Merge-Commit
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_mehrere_commits_alle_ungueltigen_werden_genannt(self):
        self.commit("chore: Start")
        self.commit("schlecht eins")
        self.commit("feat: gut")
        self.commit("schlecht zwei")
        r = self.gate("commits", "HEAD~3..HEAD")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("schlecht eins", r.stdout)
        self.assertIn("schlecht zwei", r.stdout)
        self.assertNotIn("feat: gut", r.stdout)


class HookCommitMsg(MitGitRepo):
    def setUp(self):
        super().setUp()
        self.git("config", "core.hooksPath", ".githooks")

    def test_hook_ist_duenne_sh_huelle(self):
        text = (REPO / ".githooks" / "commit-msg").read_bytes()
        self.assertTrue(text.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r", text)
        if sys.platform != "win32":
            self.assertTrue(os.access(REPO / ".githooks" / "commit-msg", os.X_OK))

    def test_ungueltiger_commit_wird_abgelehnt(self):
        r = self.commit("Labels angelegt", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("type(scope)!: Betreff", r.stdout + r.stderr)
        self.assertEqual(self.git("rev-list", "--all", "--count").stdout.strip(), "0")

    def test_gueltiger_commit_geht_durch(self):
        self.commit("feat(setup): Labels anlegen")
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), "feat(setup): Labels anlegen")

    def test_merge_nachricht_geht_durch(self):
        self.commit("chore: Start")
        self.git("checkout", "-q", "-b", "zweig")
        self.commit("feat: Zweig")
        self.git("checkout", "-q", "main")
        self.commit("fix: Main")
        self.git("merge", "-q", "--no-ff", "zweig")  # Standardnachricht "Merge branch 'zweig'"
        self.assertTrue(self.git("log", "-1", "--format=%s").stdout.startswith("Merge branch"))


if __name__ == "__main__":
    unittest.main()
