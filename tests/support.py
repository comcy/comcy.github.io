"""Gemeinsame Hilfen für die Tests von setup.py: temporäres Git-Repo mit Daten und Stub-Programmen."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from stubs import Stubs

REPO = Path(__file__).resolve().parent.parent
SETUP = REPO / "scripts" / "setup.py"

ALLE = {"git": "git version 2.45.1", "gh": "gh version 2.50.0 (2026-01-01)", "node": "v22.4.0",
        "openspec": "1.14.0", "pandoc": "pandoc 3.1.3", "kvasir": "kvasir 0.3.0"}
SKILL = '---\nname: openspec-propose\nmetadata:\n  generatedBy: "%s"\n---\n'


def skill_datei(version):
    return {".agents/skills/openspec-propose/SKILL.md": SKILL % version}


class MitRepo(unittest.TestCase):
    """Temporäres Git-Repo mit den echten Daten (workflow/, scripts/setup.d/) und Stub-Programmen.

    Das echte git bleibt im PATH (setup ruft es für die Konfiguration auf), alle anderen Programme sind Stubs.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.repo = tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        shutil.copytree(REPO / "workflow", self.repo / "workflow")
        shutil.copytree(REPO / "scripts" / "setup.d", self.repo / "scripts" / "setup.d")
        self.stubs = Stubs(tmp)
        for name, version in ALLE.items():
            if name != "git":
                self.stubs.add(name, version)
        # git bleibt echt (setup liest und schreibt die Git-Konfiguration), aber nur über einen Wrapper im Stub-Ordner
        self.stubs.add_passthrough("git", shutil.which("git"))
        self.openspec(init_schreibt=skill_datei("1.14.0"))
        self.gh()  # angemeldet, alle Labels vorhanden

    def openspec(self, version="1.14.0", init_schreibt=None):
        """Stub für openspec: --version, init und update; init schreibt die angegebenen Dateien."""
        antworten = [{"args": ["init"], "write": init_schreibt or {}}, {"args": ["update"]}]
        self.stubs.add("openspec", version, responses=antworten)

    def zustands_labels(self):
        """(id, farbe, beschreibung) aller aktivierten Zustände der Art triage und status aus der echten states.tsv."""
        zeilen = [z.split("\t") for z in (self.repo / "workflow" / "states.tsv").read_text(encoding="utf-8").splitlines()
                  if z and not z.startswith("#")]
        kopf, daten = zeilen[0], zeilen[1:]
        return [(r[kopf.index("id")], r[kopf.index("color")], r[kopf.index("description")]) for r in daten
                if r[kopf.index("kind")] in ("triage", "status")]

    def gh(self, vorhanden=None, angemeldet=True, liste_stdout=None):
        """Stub für gh: Version, Anmeldung und `label list` (Standard: alle Labels aus states.tsv sind vorhanden)."""
        namen = [n for n, _, _ in self.zustands_labels()] if vorhanden is None else vorhanden
        antworten = [{"args": ["auth", "status"], "code": 0 if angemeldet else 1,
                      "stderr": "" if angemeldet else "You are not logged into any GitHub hosts."},
                     {"args": ["label", "list"],
                      "stdout": liste_stdout if liste_stdout is not None else json.dumps([{"name": n} for n in namen])},
                     {"args": ["label", "create"]}]
        self.stubs.add("gh", ALLE["gh"], responses=antworten)

    def adapter_da(self, version="1.14.0"):
        """Die agentenneutrale Basis ist schon eingerichtet (für --check-Tests, die sonst den Adapter melden würden)."""
        for pfad, text in skill_datei(version).items():
            (self.repo / pfad).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / pfad).write_text(text, encoding="utf-8")

    def set_tools(self, text):
        (self.repo / "scripts" / "setup.d" / "tools.tsv").write_bytes(text.encode("utf-8"))

    def run_setup(self, *args, entfernen=(), cwd=None):
        """Ruft setup.py als Prozess auf; entfernen: Stub-Programme, die fehlen sollen; cwd: Arbeitsordner des Aufrufs."""
        for name in entfernen:
            (self.stubs.dir / (f"{name}.cmd" if sys.platform == "win32" else name)).unlink()
        return subprocess.run([sys.executable, str(SETUP), "--root", str(self.repo), *args], capture_output=True,
                              text=True, encoding="utf-8", env=self.stubs.env(), cwd=cwd)

    def git_config(self, schluessel):
        r = subprocess.run(["git", "-C", str(self.repo), "config", "--local", "--get", schluessel],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    def exclude(self):
        pfad = self.repo / ".git" / "info" / "exclude"
        return pfad.read_text(encoding="utf-8") if pfad.exists() else ""

    def aufrufe(self, programm, erstes_argument=None):
        return [a for a in self.stubs.calls() if a["name"] == programm
                and (erstes_argument is None or a["args"][:1] == [erstes_argument])]

    def zustand(self):
        config = subprocess.run(["git", "-C", str(self.repo), "config", "--local", "--list"],
                                capture_output=True, text=True).stdout
        return config, self.exclude()
