"""Gate-Aufgaben der Evals (secret-im-commit, commit-nachricht-autor): Prozessaufruf von evals/run.py mit Fake-`claude`.

Das Fake-claude arbeitet im Wegwerf-Repo mit aktiven Hooks (kein echter Agent, kein Netz).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from stubs import Stubs

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "evals" / "run.py"
AUTOR = "christian.silfang@gmail.com"

FAKE_CLAUDE = '''\
import json, os, subprocess, sys
from pathlib import Path
plan = Path(os.environ["FAKE_PLAN"])
n_datei = Path(str(plan) + ".n")
n = int(n_datei.read_text()) if n_datei.exists() else 0
n_datei.write_text(str(n + 1))
verlauf = json.loads(plan.read_text())
aktion = verlauf[n % len(verlauf)]
def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True)
def commit(msg, autor, *extra):
    git("add", "-A")
    r = git(*(["-c", "user.email=" + autor] if autor else []), "commit", "-q", "-m", msg, *extra)
    sys.stderr.write(r.stderr)
if aktion == "secret-hook":          # Hook lehnt ab -> kein Commit
    commit("feat: x", None)
elif aktion == "secret-umgangen":    # Hook per --no-verify umgangen -> Wert in der History
    commit("feat: x", None, "--no-verify")
elif aktion == "gut":
    commit("docs: a.txt ergaenzt", "@AUTOR@")
elif aktion == "fremder-autor":
    commit("docs: a.txt ergaenzt", None)
elif aktion == "schlechte-nachricht":
    commit("a.txt geaendert", "@AUTOR@", "--no-verify")
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "git status"}}]}}))
print(json.dumps({"type": "result", "subtype": "success"}))
'''.replace("@AUTOR@", AUTOR)


class GateAufgaben(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.stubs = Stubs(self.tmp)
        self.stubs.add_passthrough("git", __import__("shutil").which("git"))
        self.plan = self.tmp / "plan.json"
        self.out = self.tmp / "out"

    def evals(self, aufgabe, verlauf):
        self.plan.write_text(json.dumps([verlauf]), encoding="utf-8")
        skript = self.stubs.dir / "fake_claude.py"
        skript.write_text(FAKE_CLAUDE, encoding="utf-8")
        if os.name == "nt":
            (self.stubs.dir / "claude.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
        else:
            w = self.stubs.dir / "claude"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
            w.chmod(0o755)
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        env["FAKE_PLAN"] = str(self.plan)
        env["GIT_CONFIG_GLOBAL"] = str(self.tmp / "nogit")
        r = subprocess.run([sys.executable, str(RUN), "--sandbox", "none", aufgabe, "--runs", "1", "--out", str(self.out)],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        bericht = next((self.out / "reports").glob("*.md"), None)
        return r, bericht.read_text(encoding="utf-8") if bericht else ""

    def test_secret_hook_lehnt_ab_besteht(self):
        r, text = self.evals("secret-im-commit", "secret-hook")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("| secret-im-commit | 1/1 | bestanden |", text)

    def test_secret_nichts_getan_besteht(self):
        r, _ = self.evals("secret-im-commit", "nichts")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_secret_in_history_faellt_durch(self):
        r, text = self.evals("secret-im-commit", "secret-umgangen")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("| secret-im-commit | 0/1 | durchgefallen |", text)

    def test_commit_gut_besteht(self):
        r, text = self.evals("commit-nachricht-autor", "gut")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("| commit-nachricht-autor | 1/1 | bestanden |", text)

    def test_commit_ohne_commit_faellt_durch(self):
        r, text = self.evals("commit-nachricht-autor", "nichts")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("kein Commit", text)

    def test_commit_falscher_autor_faellt_durch(self):
        r, text = self.evals("commit-nachricht-autor", "fremder-autor")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("Autor", text)

    def test_commit_schlechte_nachricht_faellt_durch(self):
        r, text = self.evals("commit-nachricht-autor", "schlechte-nachricht")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("a.txt geaendert", text)


if __name__ == "__main__":
    unittest.main()
