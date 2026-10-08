"""--sandbox der Evals: gebauter bwrap-Befehl (portabel), Schreibversuch unter echtem bwrap (übersprungen ohne bwrap), Abbruch ohne bwrap."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_evals_adapter
from test_evals_run import Basis
from test_evals_run import RUN


def lade_run():
    sys.path.insert(0, str(RUN.parent.parent / "scripts" / "lib"))
    spec = importlib.util.spec_from_file_location("evals_run_sandbox", RUN)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["evals_run_sandbox"] = modul
    spec.loader.exec_module(modul)
    return modul


def bwrap_geht():
    if not sys.platform.startswith("linux") or shutil.which("bwrap") is None:
        return False
    try:
        return subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# Schreibt einmal außerhalb und einmal innerhalb des Arbeitsverzeichnisses (Elternordner des Wegwerf-Repos), meldet beides in result_text.
SCHREIBER = '''\
import json, os, sys
from pathlib import Path
anfrage = json.loads(sys.stdin.read())
def versuch(pfad):
    try:
        Path(pfad).write_text("x")
        return "ok"
    except OSError:
        return "fehler"
aussen = versuch(os.environ["AUSSEN"])
innen = versuch(Path(anfrage["cwd"]).parent / "innen.txt")
print(json.dumps({"tool_calls": [], "result_text": "aussen=%s innen=%s" % (aussen, innen)}))
'''


class SandboxBefehl(unittest.TestCase):
    def test_befehl_reihenfolge_und_nur_vorhandene_binds(self):
        run = lade_run()
        with tempfile.TemporaryDirectory() as t:
            home = Path(t)
            (home / ".claude").mkdir()  # .claude.json fehlt -> kein Bind
            cmd = run.sandbox_befehl("/w", home)
        self.assertEqual(cmd, ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--bind", "/w", "/w",
                               "--bind", str(home / ".claude"), str(home / ".claude"), "--unshare-pid", "--die-with-parent", "--"])

    def test_beide_konfig_pfade_gebunden_wenn_vorhanden(self):
        run = lade_run()
        with tempfile.TemporaryDirectory() as t:
            home = Path(t)
            (home / ".claude").mkdir()
            (home / ".claude.json").write_text("{}")
            cmd = run.sandbox_befehl("/w", home)
        self.assertEqual(cmd.count("--bind"), 3)
        self.assertIn(str(home / ".claude.json"), cmd)

    def test_bericht_nennt_den_modus(self):
        run = lade_run()
        from datetime import datetime
        text = run.bericht({"a": [([], None, None)]}, 1, "abc", None, datetime(2026, 1, 1), sandbox="bwrap")
        self.assertIn("- Sandbox: bwrap\n", text)


class SandboxLauf(Basis):
    adapter = test_evals_adapter.FakeAdapter.adapter  # nur der Helfer, nicht dessen Tests

    def test_ohne_bwrap_und_ohne_none_abbruch_exit_2(self):
        adapter = self.adapter({})
        env = self.stubs.env()  # PATH nur mit Stubs: kein bwrap
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", adapter, "--sandbox", "auto", env=env)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("bwrap", r.stderr)
        self.assertIn("--sandbox none", r.stderr)
        self.assertFalse((self.out / "reports").exists())

    def test_bwrap_explizit_ohne_bwrap_abbruch(self):
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", self.adapter({}), "--sandbox", "bwrap", env=self.stubs.env())
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_none_laeuft_und_bericht_sagt_keine(self):
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", self.adapter({"tool_calls": []}), "--sandbox", "none")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- Sandbox: keine\n", self.bericht())

    @unittest.skipUnless(bwrap_geht(), "bwrap fehlt oder User-Namespaces nicht verfügbar")
    def test_schreiben_ausserhalb_scheitert_innerhalb_geht(self):
        skript = self.tmp / "schreiber.py"
        skript.write_text(SCHREIBER, encoding="utf-8")
        aussen = self.tmp / "aussen.txt"
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        env["AUSSEN"] = str(aussen)
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", str(skript), "--sandbox", "bwrap", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(aussen.exists())
        roh = next((self.out / "runs").glob("*/blocker-offen-1/agent.out"))
        self.assertIn("aussen=fehler innen=ok", json.loads(roh.read_text(encoding="utf-8"))["result_text"])
        self.assertIn("- Sandbox: bwrap\n", self.bericht())


if __name__ == "__main__":
    unittest.main()
