"""Uncommittete Änderung mit Token-Muster. Der Wert wird erst hier zusammengesetzt, damit der Secret-Scan des echten Repos nicht anschlägt."""
WERT = "gh" + "p_" + "a1B2c3D4e5" * 3 + "f6G7h8"  # 36 Zeichen nach ghp_


def setup(repo):
    (repo / "config.txt").write_text("deploy_token = %s\n" % WERT, encoding="utf-8")
