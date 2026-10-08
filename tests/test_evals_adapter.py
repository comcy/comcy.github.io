"""Adapter-Vertrag der Evals: Fake-Adapter (Python-Skript außerhalb von evals/ bzw. Programm im PATH) und der claude-Adapter
mit Fake-`claude`. Kein echter Agent, kein Netz."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from test_evals_run import Basis, REPO

CLAUDE_ADAPTER = REPO / "evals" / "adapters" / "claude.py"

# Fake-Adapter in einer "anderen Sprache": liest den Vertrag von stdin, legt die Anfrage ab, antwortet laut Plan.
FAKE_ADAPTER = '''\
import json, os, subprocess, sys
anfrage = json.loads(sys.stdin.read())
with open(os.environ["FAKE_PLAN"] + ".req", "a", encoding="utf-8") as f:
    f.write(json.dumps(anfrage) + "\\n")
plan = json.loads(open(os.environ["FAKE_PLAN"], encoding="utf-8").read())
if plan.get("exit"):
    sys.stderr.buffer.write("adapter kaputt: äöü\\n".encode("utf-8"))
    sys.exit(plan["exit"])
if plan.get("kaputt"):
    print("das ist kein json")
    sys.exit(0)
if plan.get("branch"):
    subprocess.run(["git", "branch", "feature/5-x"], cwd=anfrage["cwd"], check=True)
antwort = {"result_text": "fertig", "cost_usd": 0.5, "duration_ms": 2000, "error": None}
if "tool_calls" in plan:
    antwort["tool_calls"] = plan["tool_calls"]
print(json.dumps(antwort))
'''

STASH = [{"name": "Bash", "input": {"command": "git stash"}}]


class FakeAdapter(Basis):
    def adapter(self, plan, als_programm=False):
        """Schreibt den Fake-Adapter nach tmp (außerhalb von evals/); gibt das --adapter-Argument zurück."""
        self.plan.write_text(json.dumps(plan), encoding="utf-8")
        skript = self.tmp / "fake_adapter.py"
        skript.write_text(FAKE_ADAPTER, encoding="utf-8")
        if not als_programm:
            return str(skript)
        if os.name == "nt":
            (self.stubs.dir / "fake-adapter.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
        else:
            w = self.stubs.dir / "fake-adapter"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
            w.chmod(0o755)
        return "fake-adapter"

    def anfragen(self):
        return [json.loads(z) for z in Path(str(self.plan) + ".req").read_text(encoding="utf-8").splitlines()]

    def test_python_skript_als_adapter_bedient_dieselben_aufgaben(self):
        a = self.adapter({"tool_calls": []})
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", a, "--model", "m-test", "--budget", "0.5")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("| blocker-offen | 1/1 | bestanden | $0.5000 |", self.bericht())
        q = self.anfragen()[0]
        self.assertEqual(sorted(q), ["allowed_tools", "budget_usd", "cwd", "env", "model", "prompt", "timeout_s"])
        self.assertIn("Starte Ticket 5", q["prompt"])
        self.assertEqual((q["model"], q["budget_usd"]), ("m-test", 0.5))
        self.assertIn("Bash", q["allowed_tools"])
        self.assertIsInstance(q["timeout_s"], int)
        self.assertIn("STUB_ROOT", q["env"])
        self.assertNotEqual(Path(q["cwd"]).resolve(), REPO)

    def test_programm_im_path_als_adapter_ohne_claude(self):
        a = self.adapter({"branch": True, "tool_calls": []}, als_programm=True)
        env = self.stubs.env()  # PATH nur mit git und dem Adapter, ohne claude
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", a, env=env)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)  # Branch angelegt: Aufgabe fällt durch, unabhängig vom Adapter
        self.assertIn("feature/5-x", self.bericht())

    def test_mitschnitt_wird_an_die_aufgabe_gereicht(self):
        for tool_calls, rc, erwartet, zahl in (([], 0, "bestanden", 1), (STASH, 1, "durchgefallen", 0)):
            with self.subTest(erwartet=erwartet):
                self.out = self.tmp / ("out-" + erwartet)
                a = self.adapter({"tool_calls": tool_calls})
                r = self.run_evals("kein-git-stash", "--runs", "1", "--adapter", a)
                self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
                self.assertIn("| kein-git-stash | %d/1 | %s |" % (zahl, erwartet), self.bericht())

    def test_ohne_tool_calls_ist_die_aufgabe_nicht_pruefbar_andere_bleiben_auswertbar(self):
        a = self.adapter({})
        r = self.run_evals("blocker-offen", "kein-git-stash", "--runs", "2", "--adapter", a)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)  # nicht prüfbar ist kein Durchfall
        text = self.bericht()
        self.assertIn("| blocker-offen | 2/2 | bestanden |", text)
        self.assertIn("| kein-git-stash | - | nicht prüfbar |", text)
        self.assertNotIn("durchgefallen", text)
        self.assertIn("- Nicht prüfbar: 1 von 2 Aufgaben (kein-git-stash)", text)

    def test_adapter_exit_code_ist_lauffehler(self):
        a = self.adapter({"exit": 3})
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", a)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        meldung = r.stdout + r.stderr
        self.assertIn("Exit-Code 3", meldung)
        self.assertIn("adapter kaputt: äöü", meldung)
        self.assertNotIn("Traceback", meldung)
        self.assertFalse((self.out / "reports").exists())

    def test_kaputtes_json_ist_lauffehler(self):
        a = self.adapter({"kaputt": True})
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", a)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("kein gültiges JSON", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_unbekannter_adapter_ist_lauffehler(self):
        self.plan.write_text("{}", encoding="utf-8")
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", "gibt-es-nicht-xyz")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("gibt-es-nicht-xyz", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


STREAM_CLAUDE = '''\
import json, os, sys
with open(os.environ["FAKE_OUT"], "w", encoding="utf-8") as f:
    json.dump({"args": sys.argv[1:], "cwd": os.getcwd(), "mem": os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"),
               "marker": os.environ.get("MARKER")}, f)
if os.environ.get("FAKE_FAIL"):
    sys.stderr.write("kaputt\\n")
    sys.exit(1)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "git status"}}]}}))
print(json.dumps({"type": "result", "result": "Fertig äöü", "total_cost_usd": 0.25, "duration_ms": 1234}))
'''


class ClaudeAdapter(Basis):
    def adapter(self, anfrage, **extra_env):
        skript = self.stubs.dir / "fake_claude.py"
        skript.write_text(STREAM_CLAUDE, encoding="utf-8")
        if os.name == "nt":
            (self.stubs.dir / "claude.cmd").write_text(f'@"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8")
        else:
            w = self.stubs.dir / "claude"
            w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8")
            w.chmod(0o755)
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        anfrage["env"] = dict(anfrage["env"], PATH=env["PATH"], FAKE_OUT=str(self.tmp / "claude.json"), **extra_env)
        return subprocess.run([sys.executable, str(CLAUDE_ADAPTER)], input=json.dumps(anfrage), capture_output=True,
                              text=True, encoding="utf-8", env=env)

    def anfrage(self, **kw):
        return dict({"prompt": "Mach es", "cwd": str(self.tmp), "env": dict(os.environ, MARKER="m1"), "model": "m-test",
                     "budget_usd": 0.5, "allowed_tools": ["Bash", "Read"], "timeout_s": 60}, **kw)

    def test_uebersetzt_den_mitschnitt_in_normalisiertes_json(self):
        r = self.adapter(self.anfrage())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {
            "tool_calls": [{"name": "Bash", "input": {"command": "git status"}}],
            "result_text": "Fertig äöü", "cost_usd": 0.25, "duration_ms": 1234, "error": None})

    def test_isolations_flags_budget_tools_und_umgebung(self):
        self.adapter(self.anfrage())
        aufruf = json.loads((self.tmp / "claude.json").read_text(encoding="utf-8"))
        a = aufruf["args"]
        self.assertEqual(a[a.index("-p") + 1], "Mach es")
        self.assertEqual(a[a.index("--setting-sources") + 1], "project,local")
        self.assertIn("--strict-mcp-config", a)
        self.assertEqual(a[a.index("--max-budget-usd") + 1], "0.5")
        self.assertEqual(a[a.index("--allowedTools") + 1], "Bash Read")
        self.assertEqual(a[a.index("--output-format") + 1], "stream-json")
        self.assertIn("--verbose", a)
        self.assertEqual(a[a.index("--model") + 1], "m-test")
        self.assertEqual(aufruf["mem"], "1")
        self.assertEqual(aufruf["marker"], "m1")  # env aus der Anfrage
        self.assertEqual(Path(aufruf["cwd"]).resolve(), self.tmp.resolve())

    def test_claude_fehler_steht_im_feld_error_exit_code_null(self):
        r = self.adapter(self.anfrage(), FAKE_FAIL="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        antwort = json.loads(r.stdout)
        self.assertIn("kaputt", antwort["error"])
        self.assertEqual(antwort["tool_calls"], [])

    def test_nicht_angemeldet_ist_adapter_fehler(self):
        skript = self.stubs.dir / "fake_claude.py"
        self.adapter(self.anfrage(), FAKE_FAIL="1")  # legt die Fakes an
        skript.write_text("import sys\nsys.stderr.write('Invalid API key - Please run /login\\n')\nsys.exit(1)\n", encoding="utf-8")
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        r = subprocess.run([sys.executable, str(CLAUDE_ADAPTER)], input=json.dumps(self.anfrage(env=env)), capture_output=True,
                           text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("angemeldet", r.stderr)


if __name__ == "__main__":
    unittest.main()
