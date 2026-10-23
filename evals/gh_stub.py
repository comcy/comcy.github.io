"""Stub-gh für die Evals: Zustand aus state.json (EVAL_STATE), Schreibaufrufe landen im Protokoll gh-writes.jsonl.

Schreibt nur in den Ordner von EVAL_STATE und nur, wenn der unterhalb von STUB_ROOT liegt. Nur Standardbibliothek.
"""
import json
import os
import sys
from pathlib import Path

def api_schreibt(args):
    """gh api schreibt bei -X/--method, -f/-F/--field/--raw-field oder --input (auch als --opt=wert, -XPUT)."""
    return any(a in ("-f", "-F") or a.startswith(("-X", "--method", "--field", "--raw-field", "--input")) for a in args)


def main(args):
    state_pfad = Path(os.environ["EVAL_STATE"]).resolve()
    state = json.loads(state_pfad.read_text(encoding="utf-8"))
    issues = state.get("issues", {})
    if args[:1] == ["--version"]:
        print("gh version 2.50.0 (eval-stub)")
    elif args[:2] == ["auth", "status"]:
        pass
    elif args[:2] == ["issue", "view"]:
        i = issues.get(args[2])
        if i is None:
            sys.exit("Stub: unbekanntes Issue " + args[2])
        voll = {"title": i["title"], "state": i["state"], "labels": [{"name": n} for n in i["labels"]]}
        felder = args[args.index("--json") + 1].split(",") if "--json" in args else list(voll)
        print(json.dumps({k: voll[k] for k in felder if k in voll}))
    elif args[:2] == ["pr", "checks"]:
        if "checks" not in state:
            sys.exit("no pull requests found")
        print(json.dumps([{"bucket": b} for b in state["checks"]]))
    elif args[:1] == ["api"] and not api_schreibt(args):
        teile = args[1].split("/")  # repos/{owner}/{repo}/issues/<n>/<dependencies/blocked_by|sub_issues>
        i = issues.get(teile[4], {}) if len(teile) > 5 else {}
        print(json.dumps(i.get("sub_issues" if teile[-1] == "sub_issues" else "blocked_by", [])))
    else:
        schreiben(args, state, state_pfad)


def schreiben(args, state, state_pfad):
    root = os.environ.get("STUB_ROOT")
    if not root or Path(root).resolve() not in state_pfad.parents:
        sys.exit("Stub darf nur unter STUB_ROOT schreiben, Zustand: %s" % state_pfad)
    with open(state_pfad.parent / "gh-writes.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"args": args}) + "\n")
    if args[:2] == ["issue", "edit"] and args[2] in state.get("issues", {}):
        labels = state["issues"][args[2]]["labels"]
        for flag, wert in zip(args, args[1:]):
            if flag == "--add-label" and wert not in labels:
                labels.append(wert)
            elif flag == "--remove-label" and wert in labels:
                labels.remove(wert)
        state_pfad.write_text(json.dumps(state, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
