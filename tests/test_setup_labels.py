"""Prüft `setup.py --labels` von außen: Labels aus workflow/states.tsv anlegen, nur fehlende, nur mit Schalter.

Prozessaufruf in einem temporären Git-Repo, `gh` als Stub (Anmeldung, `label list`, `label create`).
"""
import json
import unittest

from support import MitRepo


class LabelsAnlegen(MitRepo):
    def erstellt(self):
        return self.aufrufe("gh", "label")

    def create_aufrufe(self):
        return [a["args"] for a in self.stubs.calls() if a["name"] == "gh" and a["args"][:2] == ["label", "create"]]

    def test_zwei_fehlende_labels_werden_mit_farbe_und_beschreibung_angelegt(self):
        alle = self.zustands_labels()
        self.gh(vorhanden=[n for n, _, _ in alle if n not in ("needs-info", "status:in-review")])
        r = self.run_setup("--labels")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        angelegt = {a[2]: a for a in self.create_aufrufe()}
        self.assertEqual(sorted(angelegt), ["needs-info", "status:in-review"])
        farben = {n: (c, d) for n, c, d in alle}
        for name, args in angelegt.items():
            self.assertEqual(args[args.index("--color") + 1], farben[name][0])
            self.assertEqual(args[args.index("--description") + 1], farben[name][1])

    def test_alle_vorhanden_nichts_wird_angelegt(self):
        r = self.run_setup("--labels")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.create_aufrufe(), [])

    def test_vorhandene_labels_bleiben_unveraendert(self):
        self.gh(vorhanden=["needs-triage"])
        self.run_setup("--labels")
        unterbefehle = {tuple(a["args"][:2]) for a in self.stubs.calls() if a["name"] == "gh"}
        self.assertTrue(unterbefehle <= {("--version",), ("auth", "status"), ("label", "list"), ("label", "create")},
                        unterbefehle)
        self.assertNotIn("needs-triage", [a[2] for a in self.create_aufrufe()])

    def test_ohne_schalter_wird_nichts_angelegt_aber_die_zahl_genannt(self):
        alle = self.zustands_labels()
        self.gh(vorhanden=[n for n, _, _ in alle][2:])
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.create_aufrufe(), [])
        self.assertIn("2 Labels fehlen", r.stdout)
        self.assertIn("--labels", r.stdout)

    def test_ohne_anmeldung_mit_schalter_ist_ein_fehler_ohne_aenderung(self):
        self.gh(angemeldet=False)
        vorher = self.zustand()
        r = self.run_setup("--labels", "claude")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("gh auth login", r.stdout)
        self.assertEqual(self.create_aufrufe(), [])
        self.assertEqual(self.aufrufe("openspec", "init"), [])
        self.assertEqual(self.zustand(), vorher)

    def test_ohne_anmeldung_ohne_schalter_nur_hinweis(self):
        self.gh(angemeldet=False)
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nicht angemeldet", r.stdout)

    def test_abgeschaltete_zustaende_und_der_terminale_werden_nicht_angelegt(self):
        pfad = self.repo / "workflow" / "states.tsv"
        text = pfad.read_text(encoding="utf-8").splitlines()
        kopf = next(i for i, z in enumerate(text) if z and not z.startswith("#"))
        text[kopf] += "\tenabled"
        text = [z + ("\tyes" if i > kopf and z and not z.startswith("#") else "") for i, z in enumerate(text)]
        text = [z.replace("wontfix\ttriage\tffffff\tThis will not be worked on\tyes",
                          "wontfix\ttriage\tffffff\tThis will not be worked on\tno") for z in text]
        pfad.write_text("\n".join(text) + "\n", encoding="utf-8", newline="\n")
        self.gh(vorhanden=[])
        r = self.run_setup("--labels")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        namen = [a[2] for a in self.create_aufrufe()]
        self.assertNotIn("wontfix", namen)
        self.assertNotIn("closed", namen)
        self.assertIn("needs-triage", namen)

    def test_reihenfolge_wie_in_states_tsv(self):
        self.gh(vorhanden=[])
        self.run_setup("--labels")
        erwartet = [n for n, _, _ in self.zustands_labels()]
        self.assertEqual([a[2] for a in self.create_aufrufe()], erwartet)

    def test_unlesbare_label_liste_ist_ein_fehler(self):
        self.gh(liste_stdout="das ist kein json")
        r = self.run_setup("--labels")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("label list", r.stdout)
        self.assertEqual(self.create_aufrufe(), [])

    def test_label_liste_nicht_abrufbar_ist_ohne_schalter_nur_ein_hinweis(self):
        # zum Beispiel ein Klon ohne GitHub-Remote: gh label list scheitert, ohne --labels ist das kein Fehler
        self.stubs.add("gh", "gh version 2.50.0", responses=[
            {"args": ["auth", "status"], "code": 0},
            {"args": ["label", "list"], "code": 1, "stderr": "none of the git remotes point to a known GitHub host"}])
        self.adapter_da()
        for argumente in ([], ["--check"]):
            with self.subTest(argumente=argumente):
                r = self.run_setup(*argumente)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("Labels nicht geprüft", r.stdout)
                self.assertIn("known GitHub host", r.stdout)
        r = self.run_setup("--labels")
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_zweiter_lauf_legt_nichts_mehr_an(self):
        self.gh(vorhanden=[])
        self.run_setup("--labels")
        self.gh()  # jetzt sind alle da
        self.stubs.log.unlink()
        r = self.run_setup("--labels")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.create_aufrufe(), [])


class PruefmodusLabels(MitRepo):
    def setUp(self):
        super().setUp()
        self.adapter_da()

    def test_check_meldet_fehlende_labels_ohne_sie_anzulegen(self):
        alle = self.zustands_labels()
        self.gh(vorhanden=[n for n, _, _ in alle if n != "wontfix"])
        r = self.run_setup("--check")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("wontfix", r.stdout)
        self.assertEqual([a for a in self.stubs.calls() if a["args"][:2] == ["label", "create"]], [])

    def test_check_alle_vorhanden_ist_gruen(self):
        r = self.run_setup("--check")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_check_ohne_anmeldung_nur_hinweis(self):
        self.gh(angemeldet=False)
        r = self.run_setup("--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("nicht angemeldet", r.stdout)


if __name__ == "__main__":
    unittest.main()
