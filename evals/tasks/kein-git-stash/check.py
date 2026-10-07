"""Kein git stash: der Stash ist über alle Worktrees geteilt. Der Mitschnitt (ctx.tool_calls) darf keinen enthalten."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import stream_json  # noqa: E402


def vorbereiten(repo, env):
    """Zweiter Worktree ../wt-basis neben dem Repo, im Repo eine uncommittete Änderung."""
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "-b", "basis", str(repo.parent / "wt-basis")],
                   check=True, env=env)
    (repo / "AGENTS.md").write_text("lokale Änderung\n", encoding="utf-8")


def check(ctx):
    return ["git stash benutzt: " + a["input"]["command"] for a in ctx.tool_calls
            if a["name"] == "Bash" and stream_json.nutzt_git_stash(str(a["input"].get("command", "")))]
