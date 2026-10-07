"""Prüft die guard-Bedingungen aus transitions.tsv bei `flow start` und `flow review` von außen (gh als Stub)."""
import json
import subprocess
import unittest

from support import MitRepo

BLOCKED = "repos/{owner}/{repo}/issues/42/dependencies/blocked_by"
SUB = "repos/{owner}/{repo}/issues/42/sub_issues"


class FlowGuards(MitRepo):
    def setUp(self):
        super().setUp()
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "commit", "--allow-empty", "-q", "-m", "init"], check=True)

    def gh_stub(self, labels, blockers=(), subs=(), checks=None, checks_code=0, checks_stderr=""):
        view = {"title": "T", "state": "OPEN", "labels": [{"name": n} for n in labels]}
        antworten = [
            {"args": ["issue", "view"], "stdout": json.dumps(view)}, {"args": ["issue", "edit"]},
            {"args": ["api", BLOCKED], "stdout": json.dumps([{"state": s} for s in blockers])},
            {"args": ["api", SUB], "stdout": json.dumps([{"state": s} for s in subs])}]
        if checks is not None or checks_code:
            antworten.append({"args": ["pr", "checks"], "stdout": json.dumps([{"bucket": b} for b in checks or []]),
                              "code": checks_code, "stderr": checks_stderr})
        self.stubs.add("gh", "gh version 2.50.0", responses=antworten)

    def edits(self):
        return [a for a in self.aufrufe("gh", "issue") if a["args"][1:2] == ["edit"]]

    def branches(self):
        r = subprocess.run(["git", "-C", str(self.repo), "branch", "--list", "feature/*"], capture_output=True, text=True)
        return r.stdout.split()

    def text(self, r):
        return r.stdout + r.stderr

    def test_start_ohne_label_ready_for_agent_bricht_ab(self):
        self.gh_stub(["enhancement"])
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("label:ready-for-agent", self.text(r))
        self.assertEqual((self.branches(), self.edits()), ([], []))

    def test_start_mit_offenem_blocker_bricht_ab(self):
        self.gh_stub(["ready-for-agent"], blockers=["open", "closed"])
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("no_open_blockers", self.text(r))
        self.assertEqual((self.branches(), self.edits()), ([], []))

    def test_start_mit_geschlossenen_blockern_geht(self):
        self.gh_stub(["ready-for-agent"], blockers=["closed"])
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 0, self.text(r))
        self.assertEqual(len(self.edits()), 1)

    def test_start_aus_refinement_braucht_sub_issues(self):
        self.gh_stub(["status:in-refinement"])
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("subissues_exist", self.text(r))
        self.assertEqual(self.edits(), [])
        self.gh_stub(["status:in-refinement"], subs=["open"])
        self.assertEqual(self.run_flow("start", "42").returncode, 0)

    def test_nicht_auswertbarer_detektor_ist_warnung_ohne_blockade(self):
        self.gh_stub(["ready-for-agent"])
        # kaputte Antwort der API: nicht auswertbar
        self.stubs.add("gh", "gh version 2.50.0", responses=[
            {"args": ["issue", "view"], "stdout": json.dumps(
                {"title": "T", "state": "OPEN", "labels": [{"name": "ready-for-agent"}]})},
            {"args": ["issue", "edit"]}, {"args": ["api"], "stdout": "kein json", "code": 1, "stderr": "HTTP 404"}])
        r = self.run_flow("start", "42")
        self.assertEqual(r.returncode, 0, self.text(r))
        self.assertIn("Warnung", self.text(r))
        self.assertIn("no_open_blockers", self.text(r))
        self.assertEqual(len(self.edits()), 1)

    def test_dry_run_wertet_guards_aus(self):
        self.gh_stub(["enhancement"])
        r = self.run_flow("start", "42", "--dry-run")
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_review_mit_gruenen_checks_geht(self):
        self.gh_stub(["status:in-progress"], checks=["pass", "skipping"])
        r = self.run_flow("review", "42")
        self.assertEqual(r.returncode, 0, self.text(r))
        self.assertEqual(len(self.edits()), 1)

    def test_review_mit_roten_oder_laufenden_checks_bricht_ab(self):
        for buckets in (["pass", "fail"], ["pending"], []):
            with self.subTest(buckets=buckets):
                self.gh_stub(["status:in-progress"], checks=buckets, checks_code=1 if buckets else 0)
                r = self.run_flow("review", "42")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("checks:success", self.text(r))
                self.assertEqual(self.edits(), [])

    def test_review_ohne_pr_bricht_ab(self):
        self.gh_stub(["status:in-progress"], checks_code=1, checks_stderr="no pull requests found for branch")
        r = self.run_flow("review", "42")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("checks:success", self.text(r))
        self.assertEqual(self.edits(), [])


if __name__ == "__main__":
    unittest.main()
