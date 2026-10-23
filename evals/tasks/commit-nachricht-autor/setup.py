"""Uncommittete Änderung an a.txt."""


def setup(repo):
    (repo / "a.txt").write_text("neue Zeile\n", encoding="utf-8")
