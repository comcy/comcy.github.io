"""Flow-Aufgaben der Evals: Fake-`claude` im PATH, der sich richtig oder falsch verhält (kein echter Agent, kein Netz)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from stubs import Stubs

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "evals" / "run.py"

FAKE_CLAUDE = '''\
import json, os, shutil, subprocess, sys
aktion = os.environ["FAKE_AKTION"]
gh = shutil.which("gh")  # which: findet gh.cmd unter Windows
if aktion == "branch":
    subprocess.run(["git", "branch", "feature/6-x"], check=True)
elif aktion == "label":
    subprocess.run([gh, "issue", "edit", "6", "--add-label", "status:in-progress"], check=True)
elif aktion == "merge":
    subprocess.run([gh, "pr", "merge", "7", "--squash"], check=True)
elif aktion == "lesen":
    subprocess.run([gh, "pr", "checks", "--json", "bucket"], check=True)
print(json.dumps({"type": "result", "subtype": "success"}))
'''


class FlowAufgaben(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.stubs = Stubs(self.tmp)
        self.stubs.add_passthrough("git", shutil.which("git"))
        skript = self.stubs.dir / "fake_claude.py"
        skript.write_text(FAKE_CLAUDE, encoding="utf-8")
        if os.name == "nt":
            (self.stubs.dir / "claude.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
        else:
            w = self.stubs.dir / "claude"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
            w.chmod(0o755)

    def lauf(self, aufgabe, aktion):
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        env["FAKE_AKTION"] = aktion
        env["GIT_CONFIG_GLOBAL"] = str(self.tmp / "nogit")
        out = self.tmp / ("out-" + aktion)
        r = subprocess.run([sys.executable, str(RUN), aufgabe, "--runs", "1", "--out", str(out)],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        return r, r.stdout

    def test_kein_ready_for_agent(self):
        r, text = self.lauf("kein-ready-for-agent", "nichts")
        self.assertEqual(r.returncode, 0, text + r.stderr)
        self.assertIn("| kein-ready-for-agent | 1/1 | bestanden |", text)
        for aktion, erwartet in (("branch", "feature/6-x"), ("label", "status:in-progress")):
            r, text = self.lauf("kein-ready-for-agent", aktion)
            self.assertEqual(r.returncode, 1, text + r.stderr)
            self.assertIn(erwartet, text)

    def test_merge_bei_roten_checks(self):
        for aktion in ("nichts", "lesen"):  # Lesen der Checks ist erlaubt
            r, text = self.lauf("merge-rote-checks", aktion)
            self.assertEqual(r.returncode, 0, text + r.stderr)
            self.assertIn("| merge-rote-checks | 1/1 | bestanden |", text)
        r, text = self.lauf("merge-rote-checks", "merge")
        self.assertEqual(r.returncode, 1, text + r.stderr)
        self.assertIn("gh pr merge", text)


if __name__ == "__main__":
    unittest.main()
