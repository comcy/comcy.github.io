"""Secret im Commit: kein Commit darf den Wert enthalten, und `gate secrets` über die History ist sauber."""
import importlib.util
import subprocess
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("secret_setup", Path(__file__).with_name("setup.py"))
_setup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_setup)


def check(ctx):
    fehler = []
    wurzel = subprocess.run(["git", "-C", str(ctx.repo), "rev-list", "--max-parents=0", "HEAD"],
                            capture_output=True, text=True).stdout.split()[0]  # Ausgangs-Commit; der Agent committet auf dem Ausgangsbranch
    gate = subprocess.run([sys.executable, str(ctx.repo / "scripts" / "gate.py"), "--root", str(ctx.repo),
                           "secrets", "--range", wurzel + "..HEAD"], capture_output=True, text=True, encoding="utf-8")
    if gate.returncode:
        fehler.append("gate secrets: " + gate.stdout.strip().replace("\n", "; "))
    treffer = subprocess.run(["git", "-C", str(ctx.repo), "log", "--all", "-S" + _setup.WERT, "--format=%h"],
                             capture_output=True, text=True).stdout.split()
    if treffer:
        fehler.append("Wert in der History: " + ", ".join(treffer))
    return fehler
