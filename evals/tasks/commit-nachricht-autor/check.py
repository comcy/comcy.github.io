"""Commit-Nachricht und Autor: neue Commits bestehen `gate commits` des Wegwerf-Repos und tragen den festen Autor."""
import sys

from proc import run  # evals/run.py legt scripts/lib in den Suchpfad

AUTOR = "christian.silfang@gmail.com"


def check(ctx):
    # der Agent committet auf dem Ausgangsbranch: Bereich ab dem Ausgangs-Commit (Wurzel)
    wurzel = run("git", ["-C", str(ctx.repo), "rev-list", "--max-parents=0", "HEAD"]).stdout.split()[0]
    bereich = wurzel + "..HEAD"
    log = run("git", ["-C", str(ctx.repo), "log", "--format=%h %ae", bereich]).stdout.splitlines()
    if not log:
        return ["kein Commit entstanden"]
    fehler = ["Autor %s statt %s (%s)" % (e, AUTOR, sha) for sha, e in (z.split() for z in log) if e != AUTOR]
    gate = run(sys.executable, [str(ctx.repo / "scripts" / "gate.py"), "--root", str(ctx.repo), "commits", bereich])
    if gate.returncode:
        fehler.append("gate commits: " + gate.stdout.strip().replace("\n", "; "))
    return fehler
