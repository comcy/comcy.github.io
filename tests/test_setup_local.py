"""Prüft `setup.py` für den lokalen Klon von außen: Agenten-Adapter, Ausschlüsse, Hooks-Pfad, aktuelle Skills.

Aufruf als Prozess in einem temporären Git-Repo, Stub-Programme im PATH, echtes git für die Konfiguration.
"""
import os
import shutil
import sys
import unittest

from support import MitRepo, skill_datei

CLAUDE_DATEIEN = {**skill_datei("1.14.0"), ".claude/skills/openspec-propose/SKILL.md": "x"}


class AgentenWahl(MitRepo):
    def test_argument_ruft_init_auf_und_speichert_die_wahl(self):
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        r = self.run_setup("claude")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        init = self.aufrufe("openspec", "init")
        self.assertEqual(len(init), 1, self.stubs.calls())
        self.assertIn("agents,claude", init[0]["args"])
        self.assertEqual(self.git_config("setup.agents"), "claude")

    def test_gespeicherte_wahl_wird_ohne_argument_genutzt(self):
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        self.run_setup("claude")
        shutil.rmtree(self.repo / ".claude")  # Adapter fehlt wieder, die Wahl bleibt gespeichert
        self.stubs.log.unlink()
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        init = self.aufrufe("openspec", "init")
        self.assertEqual(len(init), 1, self.stubs.calls())
        self.assertIn("agents,claude", init[0]["args"])

    def test_ohne_wahl_nur_agents_mit_hinweis(self):
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        init = self.aufrufe("openspec", "init")
        self.assertEqual(len(init), 1)
        self.assertIn("agents", init[0]["args"])
        self.assertNotIn("claude", " ".join(init[0]["args"]))
        self.assertIsNone(self.git_config("setup.agents"))
        self.assertIn("setup claude", r.stdout)
        self.assertNotIn(".claude/", self.exclude())

    def test_unbekannter_agent_aendert_nichts(self):
        vorher = self.zustand()
        r = self.run_setup("unbekannt")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("scripts/setup.d/agents.tsv", r.stdout + r.stderr)
        self.assertEqual(self.aufrufe("openspec", "init"), [])
        self.assertEqual(self.zustand(), vorher)

    def test_agents_als_argument_wird_ignoriert_nicht_doppelt(self):
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        self.run_setup("agents", "claude", "claude")
        init = self.aufrufe("openspec", "init")
        self.assertEqual(init[0]["args"][init[0]["args"].index("--tools") + 1], "agents,claude")


class AdapterErkennung(MitRepo):
    def test_ein_fremder_agentenordner_ohne_skills_gilt_nicht_als_adapter(self):
        # Claude Code legt .claude/ selbst an (Einstellungen), das ist noch kein Adapter von openspec
        self.adapter_da()  # die Basis ist da, nur .claude/ ist zweideutig
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "settings.local.json").write_text("{}", encoding="utf-8")
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        r = self.run_setup("claude")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self.aufrufe("openspec", "init")), 1, self.stubs.calls())

    def test_agents_als_einziges_argument_behaelt_die_gespeicherte_wahl(self):
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        self.run_setup("claude")
        self.run_setup("agents")
        self.assertEqual(self.git_config("setup.agents"), "claude")

    def test_aufruf_aus_einem_anderen_ordner_arbeitet_im_repo(self):
        import tempfile
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        with tempfile.TemporaryDirectory() as fremd:
            r = self.run_setup("claude", cwd=fremd)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(os.listdir(fremd), [])
        self.assertTrue((self.repo / ".claude" / "skills" / "openspec-propose" / "SKILL.md").is_file())
        self.assertEqual(self.git_config("setup.agents"), "claude")

    @unittest.skipIf(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "Schreibschutz per chmod greift nicht unter Windows oder als root")
    def test_fehlgeschlagenes_git_config_ist_ein_fehler_und_wird_nicht_als_erledigt_gemeldet(self):
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        git_ordner = self.repo / ".git"
        git_ordner.chmod(0o555)  # git config kann die Sperrdatei nicht anlegen
        try:
            r = self.run_setup("claude")
        finally:
            git_ordner.chmod(0o755)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("erledigt Agentenwahl", r.stdout)
        self.assertIn("git config", r.stdout)


class Ausschluesse(MitRepo):
    def setUp(self):
        super().setUp()
        self.openspec(init_schreibt=CLAUDE_DATEIEN)

    def test_eintrag_genau_einmal_vorhandenes_bleibt(self):
        pfad = self.repo / ".git" / "info" / "exclude"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text("# eigene Zeile\n*.log", encoding="utf-8")  # ohne Zeilenende am Schluss
        self.run_setup("claude")
        text = self.exclude()
        self.assertEqual(text.splitlines().count(".claude/"), 1, text)
        self.assertIn("# eigene Zeile", text)
        self.assertIn("*.log", text.splitlines())

    def test_vorhandener_eintrag_wird_nicht_verdoppelt(self):
        pfad = self.repo / ".git" / "info" / "exclude"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(".claude/\n", encoding="utf-8")
        self.run_setup("claude")
        self.assertEqual(self.exclude().splitlines().count(".claude/"), 1)

    def test_agents_ordner_wird_nie_ausgeschlossen(self):
        self.run_setup("claude")
        self.assertNotIn(".agents", self.exclude())


class Idempotenz(MitRepo):
    def test_zweiter_lauf_aendert_nichts(self):
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        self.run_setup("claude")
        vorher = self.zustand()
        self.stubs.log.unlink()
        r = self.run_setup("claude")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nichts zu tun", r.stdout)
        self.assertEqual(self.aufrufe("openspec", "init"), [])
        self.assertEqual(self.aufrufe("openspec", "update"), [])
        self.assertEqual(self.zustand(), vorher)

    def test_check_nach_dem_setup_ist_gruen(self):
        self.openspec(init_schreibt=CLAUDE_DATEIEN)
        self.run_setup("claude")
        r = self.run_setup("--check", "claude")
        self.assertEqual(r.returncode, 0, r.stdout)


class HooksPfad(MitRepo):
    def test_gesetzt_wenn_der_ordner_existiert(self):
        (self.repo / ".githooks").mkdir()
        self.run_setup()
        self.assertEqual(self.git_config("core.hooksPath"), ".githooks")

    def test_unveraendert_ohne_ordner(self):
        self.run_setup()
        self.assertIsNone(self.git_config("core.hooksPath"))


class AktuelleSkills(MitRepo):
    def setUp(self):
        super().setUp()
        for pfad, text in skill_datei("1.13.0").items():
            (self.repo / pfad).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / pfad).write_text(text, encoding="utf-8")

    def test_normaler_lauf_ruft_update_auf(self):
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self.aufrufe("openspec", "update")), 1)
        self.assertEqual(self.aufrufe("openspec", "init"), [])

    def test_check_meldet_veraltet_ohne_aufruf(self):
        r = self.run_setup("--check")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Adapter veraltet", r.stdout)
        self.assertEqual(self.aufrufe("openspec", "update"), [])
        self.assertEqual(self.aufrufe("openspec", "init"), [])

    def test_aelteres_openspec_als_die_skills_loest_kein_update_aus(self):
        for pfad, text in skill_datei("1.15.0").items():  # Skills von einem neueren openspec (1.14.0 ist installiert)
            (self.repo / pfad).write_text(text, encoding="utf-8")
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.aufrufe("openspec", "update"), [])

    def test_gleiche_version_braucht_kein_update(self):
        for pfad, text in skill_datei("1.14.0").items():
            (self.repo / pfad).write_text(text, encoding="utf-8")
        self.run_setup()
        self.assertEqual(self.aufrufe("openspec", "update"), [])


class Pruefmodus(MitRepo):
    def test_check_meldet_fehlendes_und_aendert_nichts(self):
        vorher = self.zustand()
        r = self.run_setup("--check", "claude")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(".claude/", r.stdout)
        self.assertEqual(self.zustand(), vorher)
        self.assertEqual(self.aufrufe("openspec", "init"), [])

    def test_normaler_lauf_bricht_bei_fehlendem_pflichtprogramm_ab(self):
        vorher = self.zustand()
        r = self.run_setup("claude", entfernen=("gh",))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("gh", r.stdout)
        self.assertEqual(self.aufrufe("openspec", "init"), [])
        self.assertEqual(self.zustand(), vorher)

    def test_agents_datei_wird_geprueft(self):
        (self.repo / "scripts" / "setup.d" / "agents.tsv").write_text("agent\tfolder\nclaude\tclaude\n", encoding="utf-8")
        r = self.run_setup("--check", "claude")
        self.assertEqual(r.returncode, 1)
        self.assertIn("agents.tsv", r.stdout)


if __name__ == "__main__":
    unittest.main()
