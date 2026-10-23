## Context

`starte_agent` ruft den Adapter über `proc.run` auf. Isolation von Nutzer-Einstellungen gibt es (`--setting-sources`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY`), eine Beschränkung des Dateisystems nicht. `claude --restricted` entfernt `Bash`, das die Aufgaben brauchen (`git`, `gh`).

## Decisions

- **bwrap vor dem Adapter**: `bwrap --ro-bind / / --dev /dev --proc /proc --bind <work> <work> --bind ~/.claude ~/.claude --bind ~/.claude.json ~/.claude.json --unshare-pid --die-with-parent -- <adapter-befehl>`. `<work>` ist das Arbeitsverzeichnis des Laufs (Wegwerf-Repo, Stub-Zustand). Das Netz wird nicht getrennt (der Agent braucht die API). Weitere nötige Pfade werden gemessen (ein echter Probelauf mit einer Aufgabe), nicht geraten.
- **`--sandbox auto|bwrap|none`**: `auto` = `bwrap` wenn `shutil.which("bwrap")`, sonst Abbruch mit Meldung (Exit 2). `none` läuft ohne Sandbox; der Bericht-Kopf nennt `Sandbox: keine`. `bwrap` verlangt bwrap und bricht sonst ab.
- **Für jeden Adapter**: Der Runner baut den Befehl, der Adapter bleibt unverändert.
- **Test**: Ein Fake-Adapter versucht, in einen Ordner außerhalb von `<work>` zu schreiben. Unter `bwrap` scheitert der Schreibversuch und die Datei existiert nicht; der Test wird übersprungen, wenn `bwrap` fehlt. Ein portabler Test prüft den gebauten Befehl.

## Risks / Trade-offs

- `bwrap` kann je nach Kernel (User-Namespaces) scheitern: dann Abbruch mit Meldung, `none` bleibt als Ausweg.
- Beschreibbares `~/.claude` bleibt eine Lücke: Der Agent könnte dort schreiben. Akzeptiert, weil die Anmeldung es braucht; ein Folgeschritt könnte eine kopierte Konfiguration nutzen.
- Das Netz bleibt offen.

## Open Questions

- Welche Pfade braucht `claude` unter `bwrap` zusätzlich (z. B. `~/.cache`, `~/.config`)? Wird beim Probelauf gemessen.
