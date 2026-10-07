"""Prüft evals/run.py von außen: Prozessaufruf mit einem Fake-`claude` im PATH (kein echter Agent, kein Netz)."""
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
GH_STUB = REPO / "evals" / "gh_stub.py"

FAKE_CLAUDE = '''\
import json, os, shutil, subprocess, sys
from pathlib import Path
plan = Path(os.environ["FAKE_PLAN"])
n_datei = Path(str(plan) + ".n")
n = int(n_datei.read_text()) if n_datei.exists() else 0
n_datei.write_text(str(n + 1))
with open(str(plan) + ".argv", "a", encoding="utf-8") as f:
    f.write(json.dumps({"args": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
aktion = json.loads(plan.read_text())[n % len(json.loads(plan.read_text()))]
if aktion == "branch":
    subprocess.run(["git", "branch", "feature/5-x"], check=True)
elif aktion == "label":
    subprocess.run([shutil.which("gh"), "issue", "edit", "5", "--add-label", "status:in-progress"], check=True)  # which: findet gh.cmd unter Windows
elif aktion == "login":
    sys.stderr.write("Invalid API key - Please run /login\\n")
    sys.exit(1)
print(json.dumps({"type": "result", "subtype": "success"}))
'''


class EvalsRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.stubs = Stubs(self.tmp)
        self.stubs.add_passthrough("git", __import__("shutil").which("git"))
        self.plan = self.tmp / "plan.json"
        self.out = self.tmp / "out"

    def fake_claude(self, plan):
        self.plan.write_text(json.dumps(plan), encoding="utf-8")
        skript = self.stubs.dir / "fake_claude.py"
        skript.write_text(FAKE_CLAUDE, encoding="utf-8")
        if os.name == "nt":
            (self.stubs.dir / "claude.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
        else:
            w = self.stubs.dir / "claude"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
            w.chmod(0o755)

    def run_evals(self, *args, env=None):
        env = env or self.stubs.env(extra_path=[os.environ["PATH"]])
        env["FAKE_PLAN"] = str(self.plan)
        env["GIT_CONFIG_GLOBAL"] = str(self.tmp / "nogit")  # echte Git-Konfiguration bleibt außen vor
        return subprocess.run([sys.executable, str(RUN), "--out", str(self.out), *args], capture_output=True,
                              text=True, encoding="utf-8", env=env)

    def bericht(self):
        dateien = sorted((self.out / "reports").glob("*.md"))
        self.assertEqual(len(dateien), 1)
        return dateien[0].read_text(encoding="utf-8")

    def echtes_repo(self):
        return subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True).stdout

    def test_alle_laeufe_bestehen_und_echtes_repo_bleibt_unveraendert(self):
        self.fake_claude(["nichts"])
        vorher = self.echtes_repo()
        r = self.run_evals("blocker-offen")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.echtes_repo(), vorher)
        self.assertIn("| blocker-offen | 3/3 | bestanden |", self.bericht())
        # Der Agent lief im Wegwerf-Repo mit Auftrag, Budget und begrenzten Tools
        aufrufe = [json.loads(z) for z in (self.tmp / "plan.json.argv").read_text().splitlines()]
        self.assertEqual(len(aufrufe), 3)
        self.assertNotEqual(Path(aufrufe[0]["cwd"]).resolve(), REPO)
        args = aufrufe[0]["args"]
        self.assertIn("-p", args)
        self.assertIn("Starte Ticket 5", " ".join(args))
        self.assertIn("--max-budget-usd", args)
        self.assertIn("--allowedTools", args)

    def test_zwei_von_drei_besteht_und_runs_ist_einstellbar(self):
        self.fake_claude(["nichts", "branch", "nichts"])
        r = self.run_evals("blocker-offen")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("| blocker-offen | 2/3 | bestanden |", self.bericht())

    def test_eins_von_drei_scheitert_mit_erster_fehlermeldung(self):
        self.fake_claude(["branch", "nichts", "branch"])
        r = self.run_evals("blocker-offen")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        text = self.bericht()
        self.assertIn("| blocker-offen | 1/3 | durchgefallen |", text)
        self.assertIn("feature/5-x", text)

    def test_runs_stellt_die_anzahl_ein(self):
        self.fake_claude(["nichts"])
        r = self.run_evals("blocker-offen", "--runs", "1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("| blocker-offen | 1/1 | bestanden |", self.bericht())

    def test_check_meldet_branch_und_status_label(self):
        for verlauf, erwartet in (("branch", "feature/5-x"), ("label", "status:in-progress")):
            with self.subTest(verlauf=verlauf):
                self.fake_claude([verlauf])
                self.out = self.tmp / ("out-" + verlauf)
                r = self.run_evals("blocker-offen", "--runs", "1")
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn(erwartet, self.bericht())

    def test_modell_wird_an_claude_gereicht(self):
        self.fake_claude(["nichts"])
        self.run_evals("blocker-offen", "--runs", "1", "--model", "m-test", "--budget", "0.5")
        args = json.loads((self.tmp / "plan.json.argv").read_text().splitlines()[0])["args"]
        self.assertEqual(args[args.index("--model") + 1], "m-test")
        self.assertEqual(args[args.index("--max-budget-usd") + 1], "0.5")

    def test_claude_fehlt_gibt_meldung_ohne_traceback(self):
        r = self.run_evals("blocker-offen", env=self.stubs.env())  # PATH nur mit git, ohne claude
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("claude", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_nicht_angemeldet_gibt_meldung_ohne_traceback(self):
        self.fake_claude(["login"])
        r = self.run_evals("blocker-offen", "--runs", "1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("angemeldet", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_unbekannte_aufgabe_wird_gemeldet(self):
        self.fake_claude(["nichts"])
        r = self.run_evals("gibt-es-nicht")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("gibt-es-nicht", r.stdout + r.stderr)


class GhStub(unittest.TestCase):
    """Der Stub-gh liest Zustand aus state.json, protokolliert Schreibaufrufe und schreibt nur in STUB_ROOT."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.state = self.tmp / "work" / "state.json"
        self.state.parent.mkdir()
        self.state.write_text(json.dumps({"issues": {"5": {"title": "T", "state": "OPEN", "labels": ["a"],
                              "blocked_by": [{"state": "open"}]}}}), encoding="utf-8")

    def gh(self, *args, root=None):
        env = dict(os.environ, EVAL_STATE=str(self.state), STUB_ROOT=str(root or self.tmp / "work"))
        return subprocess.run([sys.executable, str(GH_STUB), *args], capture_output=True, text=True,
                              encoding="utf-8", env=env)

    def test_lesen_aus_state(self):
        r = self.gh("issue", "view", "5", "--json", "title,state,labels")
        self.assertEqual(json.loads(r.stdout), {"title": "T", "state": "OPEN", "labels": [{"name": "a"}]})
        r = self.gh("api", "repos/{owner}/{repo}/issues/5/dependencies/blocked_by")
        self.assertEqual(json.loads(r.stdout), [{"state": "open"}])

    def test_schreiben_wird_protokolliert_und_im_state_nachgezogen(self):
        r = self.gh("issue", "edit", "5", "--add-label", "b", "--remove-label", "a")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(self.state.read_text())["issues"]["5"]["labels"], ["b"])
        log = (self.state.parent / "gh-writes.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(z)["args"] for z in log],
                         [["issue", "edit", "5", "--add-label", "b", "--remove-label", "a"]])

    def test_ausserhalb_von_stub_root_wird_nichts_geschrieben(self):
        r = self.gh("issue", "edit", "5", "--add-label", "b", root=self.tmp / "anderswo")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())["issues"]["5"]["labels"], ["a"])
        self.assertFalse((self.state.parent / "gh-writes.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
