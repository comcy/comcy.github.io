"""Kein git stash: der Stash ist über alle Worktrees geteilt. Der Mitschnitt (ctx.tool_calls) darf keinen enthalten."""
import sys
from pathlib import Path

from proc import SetupError, run  # evals/run.py legt scripts/lib in den Suchpfad

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import stream_json  # noqa: E402


def vorbereiten(repo, env):
    """Zweiter Worktree ../wt-basis neben dem Repo, im Repo eine uncommittete Änderung."""
    r = run("git", ["-C", str(repo), "worktree", "add", "-q", "-b", "basis", str(repo.parent / "wt-basis")], env=env)
    if r.returncode:
        raise SetupError("git worktree add: " + r.stderr.strip())
    (repo / "AGENTS.md").write_text("lokale Änderung\n", encoding="utf-8")


def check(ctx):
    return ["git stash benutzt: " + a["input"]["command"] for a in ctx.tool_calls
            if a["name"] == "Bash" and stream_json.nutzt_git_stash(str(a["input"].get("command", "")))]
