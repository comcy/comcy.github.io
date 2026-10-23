"""Prüft `flow review [<issue>]` von außen: Label-Wechsel nach status:in-review, Issue aus dem Branchnamen."""
import json
import subprocess
import unittest

from support import MitRepo


class FlowReview(MitRepo):
    def setUp(self):
        super().setUp()
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "commit", "--allow-empty", "-q", "-m", "init"], check=True)

    def issue(self, labels=()):
        antwort = {"title": "T", "state": "OPEN", "labels": [{"name": n} for n in labels]}
        self.stubs.add("gh", "gh version 2.50.0", responses=[
            {"args": ["issue", "view"], "stdout": json.dumps(antwort)}, {"args": ["issue", "edit"]},
            {"args": ["pr", "checks"], "stdout": '[{"bucket": "pass"}]'}])  # guard checks:success erfüllt

    def edits(self):
        return [a["args"] for a in self.aufrufe("gh", "issue") if a["args"][1:2] == ["edit"]]

    def branch(self, name):
        subprocess.run(["git", "-C", str(self.repo), "checkout", "-q", "-b", name], check=True)

    def test_review_aus_branchname(self):
        self.branch("feature/42-x")
        self.issue(labels=["status:in-progress", "enhancement"])
        r = self.run_flow("review")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.edits(), [["issue", "edit", "42", "--add-label", "status:in-review",
                                         "--remove-label", "status:in-progress"]])

    def test_review_mit_angabe(self):
        self.issue(labels=["status:in-progress"])
        r = self.run_flow("review", "7")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.edits()[0][2], "7")

    def test_ohne_in_progress_nichts_geaendert(self):
        for alt in ("status:in-review", "status:in-refinement"):
            with self.subTest(alt=alt):
                self.issue(labels=[alt])
                r = self.run_flow("review", "42")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn(f"{alt} -> status:in-review", r.stdout + r.stderr)
                self.assertEqual(self.edits(), [])

    def test_kein_label_nichts_geaendert(self):
        self.issue(labels=["enhancement"])
        r = self.run_flow("review", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.edits(), [])

    def test_branch_ohne_nummer_und_keine_angabe(self):
        self.branch("master-neu")
        self.issue(labels=["status:in-progress"])
        r = self.run_flow("review")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Issue-Nummer", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertEqual(self.aufrufe("gh", "issue"), [])

    def test_dry_run_aendert_nichts(self):
        self.issue(labels=["status:in-progress"])
        r = self.run_flow("review", "42", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("status:in-review", r.stdout)
        self.assertEqual(self.edits(), [])


if __name__ == "__main__":
    unittest.main()
