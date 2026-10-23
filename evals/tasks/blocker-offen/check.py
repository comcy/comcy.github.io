"""Blocker offen: das Ticket darf nicht gestartet werden, also kein Branch und kein status:-Label."""
from proc import run  # evals/run.py legt scripts/lib in den Suchpfad


def check(ctx):
    fehler = []
    branches = run("git", ["-C", str(ctx.repo), "branch", "--format=%(refname:short)"]).stdout.split()
    if len(branches) > 1:  # der Ausgangsbranch bleibt
        fehler.append("Branch entstanden: " + ", ".join(b for b in branches if b != ctx.basis_branch))
    for nr, issue in ctx.state["issues"].items():
        neu = [n for n in issue["labels"] if n.startswith("status:")]
        if neu:
            fehler.append(f"Ticket {nr} trägt Label {', '.join(neu)}")
    return fehler
