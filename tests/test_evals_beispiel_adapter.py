"""Der Beispiel-Adapter aus der Anleitung (docs/anleitung/04) läuft wirklich: Vertrag direkt und im Runner."""
import json
import subprocess
import sys
import unittest

from test_evals_run import Basis, REPO

BEISPIEL = REPO / "evals" / "adapters" / "beispiel.py"


class BeispielAdapter(Basis):
    def test_antwortet_im_vertragsformat(self):
        anfrage = {"prompt": "x", "cwd": ".", "env": {}, "model": None, "budget_usd": 1.0, "allowed_tools": ["Read"], "timeout_s": 5}
        r = subprocess.run([sys.executable, str(BEISPIEL)], input=json.dumps(anfrage), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        antwort = json.loads(r.stdout)
        self.assertEqual(antwort["tool_calls"], [])
        self.assertEqual(set(antwort), {"tool_calls", "result_text", "cost_usd", "duration_ms", "error"})

    def test_ungueltige_anfrage_ist_adapter_fehler(self):
        r = subprocess.run([sys.executable, str(BEISPIEL)], input="kein json", capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 2)

    def test_runner_bedient_aufgabe_damit(self):
        self.plan.write_text("[]", encoding="utf-8")
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", str(BEISPIEL), "--ohne-abgeleitete")
        # Der Beispiel-Adapter tut nichts: der Runner bedient ihn, die Aufgabe besteht aber nicht ("Zustand nicht gelesen")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("| blocker-offen | 0/1 | durchgefallen |", self.bericht())
        self.assertIn("Zustand nicht gelesen", self.bericht())


if __name__ == "__main__":
    unittest.main()
