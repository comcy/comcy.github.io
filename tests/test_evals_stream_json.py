"""Mitschnitt der Tool-Aufrufe (stream-json) und Aufgabe kein-git-stash. Fixtures sind gekürzte, angenommene Zeilen."""
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
sys.path.insert(0, str(REPO / "evals"))
import stream_json  # noqa: E402


def bash(befehl):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "ok"}, {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": befehl}}]}})


class Parser(unittest.TestCase):
    def test_liest_tool_aufrufe_und_ignoriert_rest(self):
        text = "\n".join([
            json.dumps({"type": "system", "subtype": "init"}),
            "das ist kein json {",
            "",
            bash("git status"),
            json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}),
            json.dumps({"type": "assistant", "message": {"content": "kein liste"}}),
            json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "a"}}]}}),
            json.dumps([1, 2]),
            json.dumps({"type": "result", "subtype": "success"}),
        ])
        self.assertEqual(stream_json.tool_calls(text), [
            {"name": "Bash", "input": {"command": "git status"}},
            {"name": "Read", "input": {"file_path": "a"}}])

    def test_git_stash_erkennung(self):
        for ok in ("git stash", "cd x && git stash pop", "git -C ../wt stash", "git -c a=b --no-pager stash list",
                   "echo hi\ngit stash", "false || git stash", "ls | git stash", "x; git stash", "FOO=1 git stash"):
            self.assertTrue(stream_json.nutzt_git_stash(ok), ok)
        for nein in ("git status", "git log --grep stash", "git commit -m 'stash'", "echo git", "git stashed",
                     "git commit -m 'kein git stash'", "grep 'git stash' x", 'echo "a; git stash"', "echo a && echo 'git stash'",
                     "git commit -m 'x\ngit stash'"):
            self.assertFalse(stream_json.nutzt_git_stash(nein), nein)


FAKE = '''\
import json, os, sys
for z in json.loads(os.environ["FAKE_ZEILEN"]):
    print(z)
'''


class Aufgabe(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.stubs = Stubs(self.tmp)
        self.stubs.add_passthrough("git", __import__("shutil").which("git"))
        skript = self.stubs.dir / "fake_claude.py"
        skript.write_text(FAKE, encoding="utf-8")
        if os.name == "nt":
            (self.stubs.dir / "claude.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
        else:
            w = self.stubs.dir / "claude"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
            w.chmod(0o755)

    def run_evals(self, zeilen, out="out"):
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        env["FAKE_ZEILEN"] = json.dumps(zeilen)
        env["GIT_CONFIG_GLOBAL"] = str(self.tmp / "nogit")
        return subprocess.run([sys.executable, str(RUN), "--sandbox", "none", "--out", str(self.tmp / out), "kein-git-stash", "--runs", "1"],
                              capture_output=True, text=True, encoding="utf-8", env=env)

    def test_ohne_stash_besteht_und_rohdatei_liegt_unter_runs(self):
        r = self.run_evals([bash("git -C ../wt-basis status")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(list((self.tmp / "out" / "runs").glob("*/kein-git-stash-1/agent.out"))), 1)

    def test_mit_stash_scheitert(self):
        for befehl in ("git stash", "git -C x stash"):
            with self.subTest(befehl=befehl):
                r = self.run_evals([bash("git status"), bash(befehl)], out="out-" + str(len(befehl)))
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("git stash", r.stdout)


if __name__ == "__main__":
    unittest.main()
