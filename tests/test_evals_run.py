"""Prüft evals/run.py von außen: Prozessaufruf mit einem Fake-`claude` im PATH (kein echter Agent, kein Netz)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
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
    f.write(json.dumps({"args": sys.argv[1:], "cwd": os.getcwd(), "mem": os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY")}) + "\\n")
aktion = json.loads(plan.read_text())[n % len(json.loads(plan.read_text()))]
if aktion == "branch":
    subprocess.run(["git", "branch", "feature/5-x"], check=True)
elif aktion == "label":
    subprocess.run([shutil.which("gh"), "issue", "edit", "5", "--add-label", "status:in-progress"], check=True)  # which: findet gh.cmd unter Windows
elif aktion == "login":
    sys.stderr.write("Invalid API key - Please run /login\\n")
    sys.exit(1)
elif aktion == "auth-fehler":
    sys.stderr.write("git: authentication failed for remote\\n")
    sys.exit(1)
print(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0.01, "duration_ms": 1500}))
'''


class Basis(unittest.TestCase):
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
        return subprocess.run([sys.executable, str(RUN), "--sandbox", "none", "--out", str(self.out), *args], capture_output=True,
                              text=True, encoding="utf-8", env=env)

    def bericht(self):
        dateien = sorted((self.out / "reports").glob("*.md"))
        self.assertEqual(len(dateien), 1)
        return dateien[0].read_text(encoding="utf-8")

    def echtes_repo(self):
        return subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True).stdout

class EvalsRun(Basis):
    def test_agent_laeuft_ohne_nutzer_einstellungen(self):
        # Gemessen im echten Lauf: ohne diese Flags liefen Hooks, Plugins, MCP und Auto-Memory aus dem echten HOME mit.
        self.fake_claude(["nichts"])
        self.run_evals("blocker-offen", "--runs", "1")
        aufruf = json.loads((self.tmp / "plan.json.argv").read_text().splitlines()[0])
        args = aufruf["args"]
        self.assertEqual(args[args.index("--setting-sources") + 1], "project,local")
        self.assertIn("--strict-mcp-config", args)
        self.assertEqual(aufruf["mem"], "1")

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

    def test_runs_unter_eins_wird_abgelehnt(self):
        self.fake_claude(["nichts"])
        for wert in ("0", "-1"):
            with self.subTest(runs=wert):
                r = self.run_evals("blocker-offen", "--runs", wert)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("--runs", r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stdout + r.stderr)

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

    def test_allgemeines_authentication_ist_kein_login_hinweis(self):
        self.fake_claude(["auth-fehler"])
        r = self.run_evals("blocker-offen", "--runs", "1")
        self.assertNotIn("angemeldet", r.stdout + r.stderr)
        self.assertIn("| blocker-offen | 0/1 | durchgefallen |", self.bericht())  # error des Adapters = Lauf fehlgeschlagen
        self.assertIn("Adapter-Fehler: claude Exit-Code 1", self.bericht())

    def test_unbekannte_aufgabe_wird_gemeldet(self):
        self.fake_claude(["nichts"])
        r = self.run_evals("gibt-es-nicht")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("gibt-es-nicht", r.stdout + r.stderr)


SECRET = "gh" + "p_" + "a" * 36  # zusammengesetzt: der Secret-Scan des echten Repos soll nicht anschlagen


class Bericht(Basis):
    """Vollständiger Bericht: Kopf, Tabelle, Diagramm, Vergleich, Auffälligkeiten, Secret-Scan."""

    ERGEBNISSE = {"blocker-offen": [([], 0.01, 1000)] * 3,
                  "kein-git-stash": [(["git stash benutzt"], 0.02, 2000), ([], 0.02, 2000), (["x"], None, None)]}

    def test_bericht_entspricht_der_referenzdatei(self):
        import importlib.util
        sys.path.insert(0, str(REPO / "scripts" / "lib"))
        spec = importlib.util.spec_from_file_location("evals_run", RUN)
        modul = importlib.util.module_from_spec(spec)
        sys.modules["evals_run"] = modul  # dataclass braucht den Eintrag
        spec.loader.exec_module(modul)
        vorher = ("2026-03-03-0000.md", "| blocker-offen | 1/3 | durchgefallen | - |\n| kein-git-stash | 3/3 | bestanden | - |\n")
        text = modul.bericht(self.ERGEBNISSE, 3, "abc1234", "m-test", datetime(2026, 3, 4, 5, 6), vorher)
        self.assertEqual(text, (REPO / "tests" / "referenz" / "eval-bericht.md").read_text(encoding="utf-8"))

    def test_commit_angabe_weist_lokale_aenderungen_aus(self):
        import importlib.util
        sys.path.insert(0, str(REPO / "scripts" / "lib"))
        spec = importlib.util.spec_from_file_location("evals_run2", RUN)
        modul = importlib.util.module_from_spec(spec)
        sys.modules["evals_run2"] = modul
        spec.loader.exec_module(modul)
        repo = self.tmp / "r"
        repo.mkdir()
        env = dict(os.environ, GIT_CONFIG_GLOBAL=str(self.tmp / "nogit"), GIT_CONFIG_NOSYSTEM="1")
        git = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *a],  # noqa: E731
                                        check=True, capture_output=True, text=True, env=env)
        git("init", "-q")
        (repo / "AGENTS.md").write_text("a\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "chore: x")
        sha = git("rev-parse", "--short", "HEAD").stdout.strip()
        self.assertEqual(modul.commit_angabe(repo), sha)
        (repo / "evals").mkdir()
        (repo / "evals" / "x.md").write_text("nicht im Fixture\n", encoding="utf-8")
        self.assertEqual(modul.commit_angabe(repo), sha)
        (repo / "AGENTS.md").write_text("b\n", encoding="utf-8")
        self.assertEqual(modul.commit_angabe(repo), sha + " (+ lokale Änderungen)")

    def test_mermaid_block_hat_gueltige_form(self):
        self.fake_claude(["nichts", "nichts", "branch"])
        self.run_evals("blocker-offen", "--runs", "3", "--zeit", "2026-03-04T05:06")
        m = re.search(r"```mermaid\nxychart-beta\n    title \"[^\"\n]+\"\n    x-axis \[(\"[^\"\n]+\"(, )?)+\]\n"
                      r"    y-axis \"[^\"\n]+\" 0 --> 100\n    bar \[(\d+(, )?)+\]\n```\n", self.bericht())
        self.assertIsNotNone(m)
        self.assertIn("bar [67]", m.group(0))

    def test_ohne_frueheren_bericht_kein_vergleich_mit_kosten_aus_result(self):
        self.fake_claude(["nichts"])
        r = self.run_evals("blocker-offen", "--zeit", "2026-03-04T05:06")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = self.bericht()
        self.assertNotIn("Vergleich", text)
        self.assertIn("- Kosten: $0.0300", text)
        self.assertIn("- Dauer: 4 s", text)
        self.assertTrue((self.out / "reports" / "2026-03-04-050600.md").exists())

    def test_mit_frueherem_bericht_neu_rot_und_neu_gruen(self):
        self.fake_claude(["nichts"])
        self.run_evals("blocker-offen", "--zeit", "2026-03-04T05:06")
        self.fake_claude(["branch"])
        r = self.run_evals("blocker-offen", "--zeit", "2026-03-04T06:00")
        self.assertEqual(r.returncode, 1)
        neu = (self.out / "reports" / "2026-03-04-060000.md").read_text(encoding="utf-8")
        self.assertIn("## Vergleich zum letzten Bericht (2026-03-04-050600.md)", neu)
        self.assertIn("- Neu rot: blocker-offen", neu)
        self.fake_claude(["nichts"])
        self.run_evals("blocker-offen", "--zeit", "2026-03-04T07:00")
        gruen = (self.out / "reports" / "2026-03-04-070000.md").read_text(encoding="utf-8")
        self.assertIn("- Neu grün: blocker-offen", gruen)

    def test_zwei_laeufe_in_einer_minute_ueberschreiben_sich_nicht(self):
        self.fake_claude(["nichts"])
        self.run_evals("blocker-offen", "--runs", "1", "--zeit", "2026-03-04T05:06:10")
        self.fake_claude(["branch"])
        self.run_evals("blocker-offen", "--runs", "1", "--zeit", "2026-03-04T05:06:40")
        self.assertEqual(sorted(p.name for p in (self.out / "reports").glob("*.md")),
                         ["2026-03-04-050610.md", "2026-03-04-050640.md"])
        neu = (self.out / "reports" / "2026-03-04-050640.md").read_text(encoding="utf-8")
        self.assertIn("## Vergleich zum letzten Bericht (2026-03-04-050610.md)", neu)
        self.assertIn("- Neu rot: blocker-offen", neu)

    def test_alter_bericht_mit_minutenname_bleibt_vergleichbar(self):
        alt = self.out / "reports"
        alt.mkdir(parents=True)
        (alt / "2026-03-04-0506.md").write_text("| blocker-offen | 1/1 | bestanden | $0.01 | - |\n", encoding="utf-8")
        self.fake_claude(["branch"])
        self.run_evals("blocker-offen", "--runs", "1", "--zeit", "2026-03-04T05:06:30")
        neu = (alt / "2026-03-04-050630.md").read_text(encoding="utf-8")
        self.assertIn("(2026-03-04-0506.md)", neu)
        self.assertIn("- Neu rot: blocker-offen", neu)

    def test_secret_im_bericht_wird_nicht_geschrieben(self):
        self.fake_claude(["nichts"])
        r = self.run_evals("blocker-offen", "--runs", "1", "--model", SECRET)  # Modellname landet im Berichtskopf
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(list((self.out / "reports").glob("*.md")) if (self.out / "reports").exists() else [])
        self.assertNotIn(SECRET, r.stdout + r.stderr)
        self.assertIn("github-token", r.stdout + r.stderr)


class Aufgaben(unittest.TestCase):
    def test_checks_rufen_programme_ueber_proc_run(self):
        # Windows: git/gh sind dort .cmd-Wrapper, die subprocess.run nicht findet; proc.run löst sie über shutil.which auf.
        import ast
        for datei in sorted((REPO / "evals" / "tasks").glob("*/check.py")):
            for knoten in ast.walk(ast.parse(datei.read_text(encoding="utf-8"))):
                if (isinstance(knoten, ast.Attribute) and isinstance(knoten.value, ast.Name)
                        and knoten.value.id == "subprocess" and knoten.attr in ("run", "Popen", "call", "check_call", "check_output")):
                    self.fail("%s:%d nutzt subprocess.%s statt proc.run" % (datei.parent.name, knoten.lineno, knoten.attr))


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
