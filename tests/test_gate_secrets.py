"""Prüft `gate.py secrets` und den Hook `pre-commit` von außen: Prozessaufruf in einem Wegwerf-Git-Repo.

Testwerte werden zusammengesetzt, damit weder echte Zugangsdaten noch Treffer des Scans in dieser Datei stehen.
"""
import unittest

from test_gate_commits import MitGitRepo

TOKEN = "gh" + "p_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"  # 36 Zeichen nach dem Präfix
AWS = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
PEM = "-----BEGIN " + "RSA PRIVATE KEY-----"
ZUWEISUNG = "DB_PASS" + "WORD=" + "hunter2hunter2"


class Secrets(MitGitRepo):
    def schreibe(self, pfad, text, stage=True):
        datei = self.repo / pfad
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(text, encoding="utf-8")
        if stage:
            self.git("add", pfad)

    def keine_werte(self, r, *werte):
        for wert in werte:
            self.assertNotIn(wert, r.stdout + r.stderr)

    def test_sauberer_index(self):
        self.schreibe("a.txt", "nichts Besonderes\npassword = None\nkey=lambda x: x\n")
        r = self.gate("secrets")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_treffer_nennt_datei_und_regel_nicht_den_wert(self):
        for text, wert in ((f"t = '{TOKEN}'\n", TOKEN), (f"x\n{AWS}\n", AWS), (f"{PEM}\n", PEM),
                           (f"{ZUWEISUNG}\n", "hunter2hunter2")):
            with self.subTest(wert=wert[:6]):
                self.schreibe("conf/a.txt", text)
                r = self.gate("secrets")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("conf/a.txt", r.stdout)
                self.assertIn("Regel", r.stdout)
                self.keine_werte(r, wert)

    def test_nur_hinzugefuegte_zeilen(self):
        self.schreibe("a.txt", f"{TOKEN}\n")
        self.git("commit", "-q", "--no-verify", "-m", "chore: Start")
        self.schreibe("a.txt", "sauber\n")  # entfernte Zeile zählt nicht
        r = self.gate("secrets")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_env_als_neue_datei(self):
        self.schreibe(".env", "")
        r = self.gate("secrets")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(".env", r.stdout)

    def test_bereich(self):
        self.git("commit", "-q", "--allow-empty", "-m", "chore: Start")
        self.schreibe("a.txt", f"{TOKEN}\n")
        self.git("commit", "-q", "--no-verify", "-m", "feat: a")
        self.assertEqual(self.gate("secrets").returncode, 0)  # Index ist leer
        r = self.gate("secrets", "--range", "HEAD~1..HEAD")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("a.txt", r.stdout)
        self.keine_werte(r, TOKEN)

    def test_bereich_findet_wieder_entferntes_secret(self):
        self.git("commit", "-q", "--allow-empty", "-m", "chore: Start")
        self.schreibe("a.txt", f"{TOKEN}\n")
        self.git("commit", "-q", "--no-verify", "-m", "feat: a")
        self.schreibe("a.txt", "sauber\n")
        self.git("commit", "-q", "--no-verify", "-m", "fix: a bereinigt")
        r = self.gate("secrets", "--range", "HEAD~2..HEAD")  # Netto-Diff ist sauber, die History nicht
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("a.txt", r.stdout)
        self.keine_werte(r, TOKEN)

    def allow(self, zeile):
        (self.repo / "scripts/gate.d/allow.tsv").write_text(f"path\tpattern\treason\n{zeile}\n", encoding="utf-8")

    def test_allowlist_mit_grund(self):
        self.schreibe("doc/a.md", f"{TOKEN}\n")
        self.allow("doc/*.md\tgh" + "p_\tBeispielwert für die Doku")
        r = self.gate("secrets")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_allowlist_trifft_nur_ihr_muster_und_ihren_pfad(self):
        self.schreibe("doc/a.md", f"{TOKEN}\n")
        self.allow("doc/*.md\tANDERES\tGrund")
        self.assertNotEqual(self.gate("secrets").returncode, 0)
        self.allow("andere/*\tgh" + "p_\tGrund")
        self.assertNotEqual(self.gate("secrets").returncode, 0)

    def test_allowlist_ohne_grund_ist_fehler(self):
        self.schreibe("doc/a.md", "harmlos\n")
        self.allow("doc/*.md\tgh" + "p_\t")
        r = self.gate("secrets")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("allow.tsv", r.stdout)

    def test_hook_lehnt_commit_ab(self):
        self.git("config", "core.hooksPath", ".githooks")
        self.schreibe("a.txt", f"{TOKEN}\n")
        r = self.git("commit", "-q", "-m", "feat: a", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("a.txt", r.stdout + r.stderr)
        self.keine_werte(r, TOKEN)
        self.schreibe("a.txt", "sauber\n")
        self.git("commit", "-q", "-m", "feat: a")


if __name__ == "__main__":
    unittest.main()
