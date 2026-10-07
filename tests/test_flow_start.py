"""Prüft `flow start <issue>` von außen: Branch und Label gemäß transitions.tsv.

Prozessaufruf in einem temporären Git-Repo, `gh` als Stub (issue view, issue edit), echtes git über Wrapper.
"""
import json
import subprocess
import unittest

from support import MitRepo


class FlowStart(MitRepo):
    def setUp(self):
        super().setUp()
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "commit", "--allow-empty", "-q", "-m", "init"], check=True)

    def issue(self, titel="Mein Ticket", labels=(), state="OPEN", view_code=0, view_stderr=""):
        antwort = {"title": titel, "state": state, "labels": [{"name": n} for n in labels]}
        self.stubs.add("gh", "gh version 2.50.0", responses=[
            {"args": ["issue", "view"], "stdout": json.dumps(antwort), "code": view_code, "stderr": view_stderr},
            {"args": ["issue", "edit"]}])

    def branches(self):
        r = subprocess.run(["git", "-C", str(self.repo), "branch", "--list", "feature/*", "--format=%(refname:short)"],
                           capture_output=True, text=True)
        return r.stdout.split()

    def edits(self):
        return [a["args"] for a in self.aufrufe("gh", "issue") if a["args"][1:2] == ["edit"]]

    def test_start_legt_branch_an_und_setzt_label(self):
        self.issue("Mein Ticket", labels=["enhancement"])
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.branches(), ["feature/42-mein-ticket"])
        self.assertEqual(self.edits(), [["issue", "edit", "42", "--add-label", "status:in-progress"]])

    def test_altes_status_label_wird_entfernt(self):
        self.issue(labels=["status:in-refinement", "enhancement"])
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.edits(), [["issue", "edit", "42", "--add-label", "status:in-progress",
                                         "--remove-label", "status:in-refinement"]])

    def test_nicht_erlaubter_uebergang_aendert_nichts(self):
        for alt in ("status:in-progress", "status:ready-for-refinement"):
            with self.subTest(alt=alt):
                self.issue(labels=[alt])
                r = self.run_flow("start", "42")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn(f"{alt} -> status:in-progress", r.stdout + r.stderr)
                self.assertEqual(self.branches(), [])
                self.assertEqual(self.edits(), [])

    def test_geschlossenes_issue_ist_ein_fehler(self):
        self.issue(state="CLOSED")
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.branches(), [])
        self.assertEqual(self.edits(), [])

    def test_vorhandener_branch_bricht_ab_ohne_label(self):
        self.issue("Mein Ticket")
        subprocess.run(["git", "-C", str(self.repo), "branch", "feature/42-mein-ticket"], check=True)
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("feature/42-mein-ticket", r.stdout + r.stderr)
        self.assertEqual(self.edits(), [])

    def test_dry_run_zeigt_schritte_und_aendert_nichts(self):
        self.issue("Mein Ticket")
        r = self.run_flow("start", "42", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("feature/42-mein-ticket", r.stdout)
        self.assertIn("status:in-progress", r.stdout)
        self.assertEqual(self.branches(), [])
        self.assertEqual(self.edits(), [])

    def test_ohne_gh_klare_meldung_ohne_traceback(self):
        self.issue()
        r = self.run_flow("start", "42", entfernen=["gh"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("gh", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertEqual(self.branches(), [])

    def test_ohne_remote_klare_meldung_ohne_traceback(self):
        self.issue(view_code=1, view_stderr="none of the git remotes point to a known GitHub host")
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("known GitHub host", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertEqual(self.branches(), [])

    def test_slug(self):
        faelle = [
            ("Größe ändern: Übergänge & Maße", "groesse-aendern-uebergaenge-masse"),
            ("  --Hallo,   Welt!!  ", "hallo-welt"),
            ("Café déjà vu", "cafe-deja-vu"),
            ("flow start <issue>: Branch/Label", "flow-start-issue-branch-label"),
            ("a" * 30 + " " + "b" * 30, "a" * 30),  # auf 40 Zeichen an Wortgrenze gekürzt
            ("日本語", "issue"),  # nichts Verwertbares: Ersatz
        ]
        for nummer, (titel, slug) in enumerate(faelle, start=1):
            with self.subTest(titel=titel):
                self.issue(titel)
                r = self.run_flow("start", str(nummer))
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn(f"feature/{nummer}-{slug}", self.branches())


if __name__ == "__main__":
    unittest.main()
