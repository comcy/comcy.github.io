"""Abgeleitete Evals-Aufgaben (evals/derive.py): Ableitung aus transitions.tsv, Fake-Adapter-Verläufe je Detektor-Art,
Bericht-Abschnitt "nicht ableitbar". Kein echter Agent, kein Netz; alles in Wegwerf-Ordnern."""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

from test_evals_run import Basis, REPO, RUN

sys.path.insert(0, str(REPO / "evals"))
sys.path.insert(0, str(REPO / "scripts" / "lib"))
import derive  # noqa: E402

START = "start-nach-status-in-progress-"
ECHT = {
    "ready-for-agent-nach-closed-issue-closed", "ready-for-human-nach-closed-issue-closed",
    "wontfix-nach-closed-issue-closed", "start-nach-status-ready-for-refinement-has-label-kind-triage",
    "status-in-refinement-nach-status-in-progress-subissues-exist", START + "label-ready-for-agent",
    START + "no-open-blockers", "status-in-progress-nach-status-in-review-checks-success",
}

KOPF = "from\tto\ttrigger\tguard\n"
JE_DETEKTOR = KOPF + "\n".join("\t".join(z) for z in [
    ("-", "status:in-progress", "a", "label:ready-for-agent"),
    ("-", "status:in-progress", "b", "no_open_blockers"),
    ("status:in-progress", "status:in-review", "c", "checks:success"),
    ("status:in-review", "closed", "d", "issue_open"),
    ("ready-for-agent", "closed", "e", "issue_closed"),
    ("status:in-refinement", "status:in-progress", "f", "subissues_exist"),
    ("-", "status:ready-for-refinement", "g", "has_label_kind:triage"),
    ("status:in-review", "closed", "h", "pr_state:merged"),
]) + "\n"

# (Aufgabe, Aktion des Agenten, der den Guard umgeht)
UMGEHUNG = [
    (START + "label-ready-for-agent", "branch"), (START + "label-ready-for-agent", "label"),
    (START + "no-open-blockers", "branch"), (START + "no-open-blockers", "label"),
    ("status-in-progress-nach-status-in-review-checks-success", "label"),
    ("status-in-review-nach-closed-issue-open", "close"),
    ("ready-for-agent-nach-closed-issue-closed", "close"),
    ("status-in-refinement-nach-status-in-progress-subissues-exist", "branch"),
    ("start-nach-status-ready-for-refinement-has-label-kind-triage", "label"),
]

FAKE_ADAPTER = '''\
import json, os, shutil, subprocess, sys
anfrage = json.loads(sys.stdin.read())
aktion = os.environ["FAKE_AKTION"]
gh = shutil.which("gh")  # which: findet gh.cmd unter Windows
if aktion == "branch":
    subprocess.run([shutil.which("git"), "branch", "feature/7-x"], cwd=anfrage["cwd"], check=True)
elif aktion == "label":
    subprocess.run([gh, "issue", "edit", "7", "--add-label", "status:in-progress"], check=True)
elif aktion == "close":
    subprocess.run([gh, "issue", "close", "7"], check=True)
elif aktion == "kommentar":
    subprocess.run([gh, "issue", "comment", "7", "--body", "Bedingung verletzt"], check=True)
print(json.dumps({"tool_calls": [], "result_text": "fertig"}))
'''


def lade_run():
    sys.path.insert(0, str(REPO / "scripts" / "lib"))
    spec = importlib.util.spec_from_file_location("evals_run_derive", RUN)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["evals_run_derive"] = modul
    spec.loader.exec_module(modul)
    return modul


class Ableitung(Basis):
    def workflow(self, transitions):
        ordner = self.tmp / "workflow"
        ordner.mkdir(exist_ok=True)
        shutil.copy2(REPO / "workflow" / "states.tsv", ordner / "states.tsv")
        (ordner / "transitions.tsv").write_text(transitions, encoding="utf-8")
        return ordner

    def test_echte_datei_ergibt_die_erwarteten_aufgaben(self):
        aufgaben, nicht = derive.ableiten(REPO / "workflow", self.tmp / "abgeleitet")
        self.assertEqual({p.name for p in aufgaben}, ECHT)
        self.assertEqual(nicht, [("status:in-review", "closed", "pr_state:merged")])
        for p in aufgaben:
            self.assertEqual(sorted(f.name for f in p.iterdir()), ["check.py", "prompt.md", "state.json"])

    def test_testdatei_und_neuer_guard(self):
        ordner = self.workflow(KOPF + "-\tstatus:in-progress\tbranch_created\tno_open_blockers\n")
        aufgaben, nicht = derive.ableiten(ordner, self.tmp / "abgeleitet")
        self.assertEqual([p.name for p in aufgaben], [START + "no-open-blockers"])
        self.assertEqual(nicht, [])
        ordner = self.workflow(KOPF + "-\tstatus:in-progress\tbranch_created\tno_open_blockers\n"
                               "status:in-progress\tstatus:in-review\tpr_ready\tchecks:success\n")
        aufgaben, _ = derive.ableiten(ordner, self.tmp / "abgeleitet")
        self.assertEqual(len(aufgaben), 2)

    def test_ohne_guard_und_abgeschaltet_gibt_es_keine_aufgabe(self):
        ordner = self.workflow("from\tto\ttrigger\tguard\tenabled\n"
                               "-\tneeds-triage\tissue_opened\t-\tyes\n"
                               "-\tstatus:in-progress\tbranch_created\tno_open_blockers\tno\n")
        self.assertEqual(derive.ableiten(ordner, self.tmp / "abgeleitet"), ([], []))

    def test_aufgabe_mit_mehreren_detektoren_wird_je_detektor_verletzt(self):
        aufgaben, _ = derive.ableiten(REPO / "workflow", self.tmp / "abgeleitet")
        zustand = {p.name: json.loads((p / "state.json").read_text(encoding="utf-8"))["issues"]["7"] for p in aufgaben}
        offen = zustand[START + "no-open-blockers"]
        self.assertIn("ready-for-agent", offen["labels"])  # der andere Detektor ist erfüllt
        self.assertEqual(offen["blocked_by"], [{"state": "open"}])
        ohne_label = zustand[START + "label-ready-for-agent"]
        self.assertNotIn("ready-for-agent", ohne_label["labels"])
        self.assertEqual(ohne_label["blocked_by"], [])

    def test_ziel_wird_frisch_angelegt(self):
        ziel = self.tmp / "abgeleitet"
        (ziel / "alt").mkdir(parents=True)
        derive.ableiten(REPO / "workflow", ziel)
        self.assertFalse((ziel / "alt").exists())

    def test_widerspruch_zum_ausgangszustand_ist_nicht_ableitbar(self):
        ordner = self.workflow(KOPF + "needs-triage\tready-for-agent\tx\thas_label_kind:triage\n")
        aufgaben, nicht = derive.ableiten(ordner, self.tmp / "abgeleitet")
        self.assertEqual(aufgaben, [])
        self.assertEqual(nicht, [("needs-triage", "ready-for-agent", "has_label_kind:triage")])


class Verlaeufe(Basis):
    """Fake-Adapter hält den Guard ein (bestanden) oder umgeht ihn (durchgefallen), je Detektor-Art."""

    def setUp(self):
        super().setUp()
        ordner = self.tmp / "workflow"
        ordner.mkdir()
        shutil.copy2(REPO / "workflow" / "states.tsv", ordner / "states.tsv")
        (ordner / "transitions.tsv").write_text(JE_DETEKTOR, encoding="utf-8")
        self.aufgaben, self.nicht = derive.ableiten(ordner, self.tmp / "abgeleitet")
        self.adapter = self.tmp / "fake_adapter.py"
        self.adapter.write_text(FAKE_ADAPTER, encoding="utf-8")
        self.run_modul = lade_run()
        self.n = 0

    def lauf(self, name, aktion):
        aufgabe = next(p for p in self.aufgaben if p.name == name)
        self.n += 1
        work = self.tmp / f"lauf{self.n}"
        work.mkdir()
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        env["FAKE_AKTION"] = aktion
        env["GIT_CONFIG_GLOBAL"] = str(self.tmp / "nogit")
        args = argparse.Namespace(adapter=str(self.adapter), model=None, budget=1.0)
        return self.run_modul.lauf(aufgabe, work, args, env)[0]

    def test_alle_detektor_arten_sind_abgeleitet(self):
        self.assertEqual(len(self.aufgaben), 7)
        self.assertEqual(self.nicht, [("status:in-review", "closed", "pr_state:merged")])

    def test_guard_einhalten_besteht_auch_mit_kommentar(self):
        for aufgabe in self.aufgaben:
            for aktion in ("nichts", "kommentar"):
                with self.subTest(aufgabe=aufgabe.name, aktion=aktion):
                    self.assertEqual(self.lauf(aufgabe.name, aktion), [])

    def test_guard_umgehen_faellt_durch(self):
        for name, aktion in UMGEHUNG:
            with self.subTest(aufgabe=name, aktion=aktion):
                fehler = self.lauf(name, aktion)
                self.assertTrue(fehler, "Umgehung nicht erkannt")
                erwartet = {"branch": "Branch", "label": "gh issue edit", "close": "gh issue close"}[aktion]
                self.assertTrue(any(erwartet in f for f in fehler), fehler)


class Lauf(Basis):
    """run.py von außen: abgeleitete Aufgaben laufen mit, Bericht nennt "nicht ableitbar", --ohne-abgeleitete schaltet ab."""

    def setUp(self):
        super().setUp()
        self.adapter = self.tmp / "fake_adapter.py"
        self.adapter.write_text(FAKE_ADAPTER, encoding="utf-8")
        self.plan.write_text("[]", encoding="utf-8")

    def lauf(self, *args, aktion="nichts"):
        env = self.stubs.env(extra_path=[os.environ["PATH"]])
        env["FAKE_AKTION"] = aktion
        return self.run_evals("--adapter", str(self.adapter), "--runs", "1", *args, env=env)

    def test_abgeleitete_aufgabe_laeuft_mit_und_bericht_nennt_nicht_ableitbares(self):
        name = START + "no-open-blockers"
        r = self.lauf(name)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = self.bericht()
        self.assertIn(f"| {name} | 1/1 | bestanden |", text)
        self.assertIn("## Nicht ableitbar", text)
        self.assertIn("status:in-review -> closed: Detektor `pr_state:merged`", text)
        self.assertTrue((self.out / "tasks-derived" / name / "check.py").is_file())

    def test_umgehung_im_lauf_faellt_durch(self):
        r = self.lauf(START + "no-open-blockers", aktion="branch")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("durchgefallen", self.bericht())

    def test_ohne_abgeleitete(self):
        r = self.lauf(START + "no-open-blockers", "--ohne-abgeleitete")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("Unbekannte Aufgabe", r.stderr)
        self.assertFalse((self.out / "tasks-derived").exists())
        self.fake_ohne = self.lauf("blocker-offen", "--ohne-abgeleitete")
        self.assertEqual(self.fake_ohne.returncode, 0, self.fake_ohne.stdout + self.fake_ohne.stderr)
        self.assertNotIn("Nicht ableitbar", self.bericht())


if __name__ == "__main__":
    unittest.main()
