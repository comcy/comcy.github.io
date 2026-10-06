"""Stub-Programme für die Tests von setup.py: kleine Python-Skripte hinter einem Wrapper, der unter Linux und macOS
ein Shell-Skript und unter Windows eine .cmd-Datei ist. Jeder Aufruf wird in einer Logdatei festgehalten.

Aufbau: <tmp>/bin/stub.py (gemeinsames Skript), <tmp>/bin/<name>(.cmd) (Wrapper), <tmp>/bin/<name>.json (Antworten).
"""
import json
import os
import sys
from pathlib import Path

STUB_SCRIPT = '''\
import json, os, sys
from pathlib import Path
name = sys.argv[1]
args = sys.argv[2:]
here = Path(__file__).resolve().parent
config = json.loads((here / (name + ".json")).read_text(encoding="utf-8"))
log = os.environ.get("STUB_LOG")
if log:
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps({"name": name, "args": args}) + "\\n")
antwort = config.get("default", {})
for kandidat in config.get("responses", []):
    if args[:len(kandidat["args"])] == kandidat["args"]:
        antwort = kandidat
        break
for pfad, inhalt in antwort.get("write", {}).items():  # simuliert erzeugte Dateien relativ zum Arbeitsordner
    erlaubt = os.environ.get("STUB_ROOT")
    if not erlaubt or Path(erlaubt).resolve() not in [Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        sys.exit("Stub darf nur im Testordner schreiben (STUB_ROOT), Arbeitsordner: %s" % Path.cwd())
    ziel = Path.cwd() / pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(inhalt, encoding="utf-8")
sys.stdout.write(antwort.get("stdout", ""))
sys.stderr.write(antwort.get("stderr", ""))
sys.exit(antwort.get("code", 0))
'''


class Stubs:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.dir = tmp / "bin"
        self.dir.mkdir()
        self.log = tmp / "stub.log"
        (self.dir / "stub.py").write_text(STUB_SCRIPT, encoding="utf-8")

    def add(self, name, version="", responses=None, default=None):
        """Legt ein Programm an. version: Ausgabe von `<name> --version`; responses: Liste mit args, stdout, code."""
        antworten = [{"args": ["--version"], "stdout": version}] if version else []
        antworten += responses or []
        (self.dir / f"{name}.json").write_text(
            json.dumps({"responses": antworten, "default": default or {}}), encoding="utf-8")
        stub = self.dir / "stub.py"
        if os.name == "nt":
            (self.dir / f"{name}.cmd").write_text(f'@"{sys.executable}" "{stub}" {name} %*\r\n', encoding="utf-8")
        else:
            wrapper = self.dir / name
            wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{stub}" {name} "$@"\n', encoding="utf-8")
            wrapper.chmod(0o755)

    def add_passthrough(self, name, ziel):
        """Wrapper, der unverändert ein echtes Programm (absoluter Pfad) aufruft, ohne dessen Ordner in den PATH zu legen."""
        if os.name == "nt":
            (self.dir / f"{name}.cmd").write_text(f'@"{ziel}" %*\r\n', encoding="utf-8")
        else:
            wrapper = self.dir / name
            wrapper.write_text(f'#!/bin/sh\nexec "{ziel}" "$@"\n', encoding="utf-8")
            wrapper.chmod(0o755)

    def env(self, extra_path=()):
        """Umgebung mit PATH nur aus dem Stub-Ordner (plus extra_path), damit echte Programme nicht stören."""
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join([str(self.dir), *map(str, extra_path)])
        env["STUB_LOG"] = str(self.log)
        env["STUB_ROOT"] = str(self.tmp)
        return env

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(z) for z in self.log.read_text(encoding="utf-8").splitlines() if z.strip()]
