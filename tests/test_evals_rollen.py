"""Rollen steuern die Tools der Evals: task.json (`role`, Standard builder) -> allowed_tools aus workflow/roles.tsv beim Adapter."""
import importlib.util
import json
import shutil
import sys
import unittest

import test_evals_adapter
from test_evals_adapter import LIEST
from test_evals_run import Basis, REPO


class Rollen(Basis):
    adapter = test_evals_adapter.FakeAdapter.adapter
    anfragen = test_evals_adapter.FakeAdapter.anfragen

    def aufgaben(self, **rollen):
        """Wegwerf-Aufgabenordner: blocker-offen je Name, mit task.json (Wert None = keine Datei, sonst Rolle; "" = Datei ohne role)."""
        ordner = self.tmp / "tasks"
        for name, rolle in rollen.items():
            shutil.copytree(REPO / "evals" / "tasks" / "blocker-offen", ordner / name)
            if rolle is not None:
                (ordner / name / "task.json").write_text(json.dumps({"role": rolle} if rolle else {}), encoding="utf-8")
        return ["--tasks", str(ordner)]

    def tools(self):
        return [q["allowed_tools"] for q in self.anfragen()]

    def test_tools_entsprechen_der_rolle(self):
        a = self.adapter({"tool_calls": LIEST})
        r = self.run_evals("--runs", "1", "--adapter", a, "--ohne-abgeleitete", *self.aufgaben(pruefer="reviewer", planer="planner", mensch="human"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(self.tools(), key=len),
                         [[], ["Read", "Glob", "Grep", "Bash"], ["Read", "Glob", "Grep", "Bash"]])

    def test_ohne_role_oder_datei_gilt_builder(self):
        a = self.adapter({"tool_calls": LIEST})
        r = self.run_evals("--runs", "1", "--adapter", a, "--ohne-abgeleitete", *self.aufgaben(ohne_datei=None, ohne_feld=""))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.tools(), [["Bash", "Read", "Edit", "Write", "Glob", "Grep"]] * 2)

    def test_bestehende_aufgaben_laufen_als_builder(self):
        a = self.adapter({"tool_calls": LIEST})
        r = self.run_evals("blocker-offen", "--runs", "1", "--adapter", a)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.tools(), [["Bash", "Read", "Edit", "Write", "Glob", "Grep"]])

    def test_unbekannte_rolle_nennt_datei_und_rolle(self):
        a = self.adapter({"tool_calls": LIEST})
        r = self.run_evals("--runs", "1", "--adapter", a, *self.aufgaben(x="gibt-es-nicht"))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("roles.tsv", r.stderr)
        self.assertIn("gibt-es-nicht", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse(Path_exists(self.plan, ".req"))  # Agent nie gestartet

    def test_abgeschaltete_rolle_ist_wie_unbekannt(self):
        # run.py liest REPO/workflow/roles.tsv: Modul laden und REPO auf einen Wegwerf-Ordner umbiegen
        spec = importlib.util.spec_from_file_location("run_rollen", REPO / "evals" / "run.py")
        sys.path.insert(0, str(REPO / "scripts" / "lib"))
        modul = importlib.util.module_from_spec(spec)
        sys.modules["run_rollen"] = modul
        spec.loader.exec_module(modul)
        modul.REPO = self.tmp
        (self.tmp / "workflow").mkdir()
        (self.tmp / "workflow" / "roles.tsv").write_text(
            "role\tphases\tallowed_tools\thuman_gate\tdescription\tenabled\n"
            "builder\t4\tBash\tno\tBaut\tyes\nreviewer\t5\tRead\tno\tPrueft\tno\n", encoding="utf-8")
        aufgabe = self.tmp / "aufgabe"
        aufgabe.mkdir()
        self.assertEqual(modul.rollen_tools(aufgabe), ["Bash"])
        (aufgabe / "task.json").write_text(json.dumps({"role": "reviewer"}), encoding="utf-8")
        with self.assertRaises(modul.SetupError) as e:
            modul.rollen_tools(aufgabe)
        self.assertIn("reviewer", str(e.exception))


def Path_exists(plan, suffix):
    return (plan.parent / (plan.name + suffix)).exists()


if __name__ == "__main__":
    unittest.main()
