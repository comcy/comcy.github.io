"""Commit-Nachricht und Autor: neue Commits bestehen `gate commits` des Wegwerf-Repos und tragen den festen Autor."""
import subprocess
import sys

AUTOR = "christian.silfang@gmail.com"


def check(ctx):
    # der Agent committet auf dem Ausgangsbranch: Bereich ab dem Ausgangs-Commit (Wurzel)
    wurzel = subprocess.run(["git", "-C", str(ctx.repo), "rev-list", "--max-parents=0", "HEAD"],
                            capture_output=True, text=True).stdout.split()[0]
    bereich = wurzel + "..HEAD"
    log = subprocess.run(["git", "-C", str(ctx.repo), "log", "--format=%h %ae", bereich],
                         capture_output=True, text=True).stdout.splitlines()
    if not log:
        return ["kein Commit entstanden"]
    fehler = ["Autor %s statt %s (%s)" % (e, AUTOR, sha) for sha, e in (z.split() for z in log) if e != AUTOR]
    gate = subprocess.run([sys.executable, str(ctx.repo / "scripts" / "gate.py"), "--root", str(ctx.repo),
                           "commits", bereich], capture_output=True, text=True, encoding="utf-8")
    if gate.returncode:
        fehler.append("gate commits: " + gate.stdout.strip().replace("\n", "; "))
    return fehler
