"""Roter Test vor Fix: ein Commit ändert einen Test, der auf dem Vorgänger-Stand fehlschlägt; am Ende ist alles grün.

Die Tests laufen in einem eigenen `git worktree` im Temp-Ordner (danach entfernt), das Wegwerf-Repo bleibt unverändert.
ponytail: "rot" heißt nur Exit-Code != 0 (auch ein Importfehler zählt); genauer, wenn Evals das ausnutzen.
"""
import sys
import tempfile
from pathlib import Path

from proc import run  # evals/run.py legt scripts/lib in den Suchpfad

PROJEKT = "kvparse"


def _git(repo, *args):
    return run("git", ["-C", str(repo), *args]).stdout


def _tests(cwd):
    return run(sys.executable, ["-m", "unittest"], cwd=cwd).returncode == 0


def _im_worktree(repo, stand, testdateien=()):
    """Tests im Stand `stand`, optional mit Testdateien aus einem anderen Commit darübergelegt: True = grün."""
    with tempfile.TemporaryDirectory(prefix="roter-test-") as tmp:
        wt = Path(tmp) / "wt"
        _git(repo, "worktree", "add", "-q", "--detach", str(wt), stand)
        try:
            for commit, pfad in testdateien:
                (wt / pfad).write_text(_git(repo, "show", f"{commit}:{pfad}"), encoding="utf-8", newline="")
            return _tests(wt / PROJEKT)
        finally:
            _git(repo, "worktree", "remove", "--force", str(wt))


def check(ctx):
    repo = ctx.repo
    wurzel = _git(repo, "rev-list", "--max-parents=0", "HEAD").split()[0]
    commits = _git(repo, "rev-list", "--reverse", f"{wurzel}..HEAD").split()
    if not commits:
        return ["Kein Commit des Agenten"]
    rot = False
    for c in commits:
        geaendert = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--diff-filter=AM", c).split()
        tests = [(c, p) for p in geaendert if p.startswith(PROJEKT + "/test") and p.endswith(".py")]
        if tests and not _im_worktree(repo, c + "~1", tests)  # nicht ^: cmd.exe (git.cmd-Wrapper unter Windows) verschluckt es:
            rot = True
            break
    fehler = []
    if not rot:
        fehler.append("Kein geänderter oder neuer Test, der auf dem Vorgänger-Stand fehlschlägt")
    if not _im_worktree(repo, "HEAD"):
        fehler.append("Tests am Endstand nicht grün")
    return fehler
