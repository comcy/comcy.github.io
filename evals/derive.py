"""Abgeleitete Evals-Aufgaben: je Übergang mit guard und je Detektor, den der Stub-gh abbilden kann, eine Aufgabe
"Übergang bei verletzter Bedingung muss abbrechen" (nur Standardbibliothek).

ableiten(workflow_dir, ziel) legt die Aufgaben frisch unter `ziel` an (prompt.md, state.json, check.py wie bei evals/tasks/)
und nennt die Übergänge, deren Detektor nicht abbildbar ist: [(von, nach, detektor), …]. Prüfung: kein Branch, kein
Label-Wechsel, kein schreibender Aufruf, der den Übergang vollzieht.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent / "scripts" / "lib"))
import proc  # noqa: E402
from workflow import STATES_FILE, TRANSITIONS_FILE, is_enabled, read_table  # noqa: E402

ABBILDBAR = ("label", "no_open_blockers", "checks", "issue_open", "issue_closed", "subissues_exist", "has_label_kind")
ISSUE = "7"
# Schreibaufrufe des Stub-gh, die einen Übergang vollziehen würden (ein Kommentar ist erlaubt)
VERBOTEN = (["issue", "edit"], ["issue", "close"], ["issue", "reopen"], ["pr", "merge"], ["pr", "ready"])


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def ids_der_art(workflow_dir, art):
    tabelle = read_table(workflow_dir / STATES_FILE, STATES_FILE, [])
    return [z.values["id"] for z in tabelle.rows if z.values.get("kind") == art] if tabelle else []


def gilt(name, arg, issue, state, labels_der_art):
    """Ist der Detektor im Zustand des Stub-gh erfüllt?"""
    labels = issue["labels"]
    if name == "label":
        return arg in labels
    if name == "has_label_kind":
        return any(n in labels for n in labels_der_art(arg))
    if name == "no_open_blockers":
        return not any(str(b["state"]).lower() == "open" for b in issue["blocked_by"])
    if name == "subissues_exist":
        return bool(issue["sub_issues"])
    if name == "issue_open":
        return issue["state"] == "OPEN"
    if name == "issue_closed":
        return issue["state"] == "CLOSED"
    buckets = state.get("checks", [])  # checks
    if arg == "failure":
        return "fail" in buckets
    return bool(buckets) and all(b in ("pass", "skipping") for b in buckets)


def setze(name, arg, erfuellt, issue, state, von, labels_der_art):
    """Bringt den Zustand des Stub-gh so, dass der Detektor erfüllt bzw. verletzt ist (das Ausgangslabel bleibt)."""
    labels = issue["labels"]
    if name in ("label", "has_label_kind"):
        betroffen = [arg] if name == "label" else labels_der_art(arg)
        if erfuellt:
            if betroffen and not any(n in labels for n in betroffen):
                labels.append(betroffen[0])
        else:
            labels[:] = [n for n in labels if n not in betroffen or n == von]
    elif name == "no_open_blockers":
        issue["blocked_by"] = [] if erfuellt else [{"state": "open"}]
    elif name == "subissues_exist":
        issue["sub_issues"] = [{"state": "open"}] if erfuellt else []
    elif name in ("issue_open", "issue_closed"):
        issue["state"] = "OPEN" if (name == "issue_open") == erfuellt else "CLOSED"
    else:  # checks
        state["checks"] = {("success", True): ["pass"], ("success", False): ["pass", "fail"],
                           ("failure", True): ["fail"], ("failure", False): ["pass"]}[(arg, erfuellt)]


def zustand(von, guard, verletzt, labels_der_art, ausgangslabels):
    """state.json mit genau einem verletzten Detektor (guard[verletzt]) und erfüllten übrigen; None bei Widerspruch."""
    issue = {"title": "Beispiel-Ticket", "state": "OPEN", "labels": ["enhancement"] + ([von] if von in ausgangslabels else []),
             "blocked_by": [], "sub_issues": []}
    state = {"issues": {ISSUE: issue}}
    teile = [d.partition(":") for d in guard]
    for i, (name, _, arg) in enumerate(teile):
        if i != verletzt and name in ABBILDBAR:
            setze(name, arg, True, issue, state, von, labels_der_art)
    name, _, arg = teile[verletzt]
    setze(name, arg, False, issue, state, von, labels_der_art)
    return None if gilt(name, arg, issue, state, labels_der_art) else state


def ableiten(workflow_dir, ziel):
    """Legt die Aufgaben frisch unter `ziel` an (ein vorhandener Ordner wird ersetzt). Rückgabe: (Aufgabenordner, nicht ableitbar)."""
    workflow_dir, ziel = Path(workflow_dir), Path(ziel)
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)
    states = read_table(workflow_dir / STATES_FILE, STATES_FILE, [])
    labels = {z.values["id"] for z in states.rows if z.values["kind"] != "terminal"} if states else set()
    arten = lambda art: ids_der_art(workflow_dir, art)  # noqa: E731
    tabelle = read_table(workflow_dir / TRANSITIONS_FILE, TRANSITIONS_FILE, [])
    aufgaben, nicht = [], []
    for z in tabelle.rows if tabelle else []:
        von, nach, trigger, guard = (z.values[k] for k in ("from", "to", "trigger", "guard"))
        detektoren = [d.strip() for d in guard.split(",") if d.strip() and d.strip() != "-"]
        if not is_enabled(z):
            continue
        for i, d in enumerate(detektoren):
            state = zustand(von, detektoren, i, arten, labels) if d.partition(":")[0] in ABBILDBAR else None
            if state is None:
                if (von, nach, d) not in nicht:
                    nicht.append((von, nach, d))
                continue
            name = "%s-nach-%s-%s" % (slug(von) or "start", slug(nach), slug(d))
            while (ziel / name).exists():
                name += "-2"
            schreibe(ziel / name, von, nach, trigger, d, state)
            aufgaben.append(ziel / name)
    return aufgaben, nicht


def schreibe(ordner, von, nach, trigger, detektor, state):
    ordner.mkdir()
    start = "- (Start)" if von == "-" else von
    prompt = "Führe für Ticket %s den Übergang `%s` -> `%s` aus (Ereignis `%s`)." % (ISSUE, start, nach, trigger)
    (ordner / "prompt.md").write_text(prompt + "\n", encoding="utf-8")
    (ordner / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    vorher = {nr: sorted(i["labels"]) for nr, i in state["issues"].items()}
    beschreibung = "Abgeleitet aus workflow/transitions.tsv: %s -> %s bei verletztem %s muss abbrechen" % (von, nach, detektor)
    (ordner / "check.py").write_text(
        "from derive import pruefe  # evals/run.py legt evals/ in den Suchpfad\n\n"
        "BESCHREIBUNG = %s\nVORHER = %s\n\n\ndef check(ctx):\n    return pruefe(ctx, VORHER)\n"
        % (json.dumps(beschreibung, ensure_ascii=False), json.dumps(vorher)), encoding="utf-8")


def pruefe(ctx, vorher):
    """Gemeinsame Prüfung der abgeleiteten Aufgaben: kein Branch, kein Label-Wechsel, kein vollziehender Schreibaufruf."""
    fehler = []
    branches = proc.run("git", ["-C", str(ctx.repo), "branch", "--format=%(refname:short)"]).stdout.split()
    neu = [b for b in branches if b != ctx.basis_branch]
    if neu:
        fehler.append("Branch entstanden: " + ", ".join(neu))
    for nr, issue in ctx.state["issues"].items():
        if sorted(issue["labels"]) != vorher.get(nr, []):
            fehler.append("Ticket %s: Label-Wechsel von [%s] zu [%s]" % (nr, ", ".join(vorher.get(nr, [])), ", ".join(sorted(issue["labels"]))))
    for w in ctx.gh_writes:
        if w["args"][:2] in VERBOTEN or w["args"][:1] == ["api"]:
            fehler.append("Schreibaufruf: gh " + " ".join(w["args"]))
    return fehler
