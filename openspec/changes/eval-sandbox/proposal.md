## Why

Der Agent läuft in den Evals mit `Bash`, ohne Einschränkung des Dateisystems. Er kann außerhalb des Wegwerf-Repos schreiben. Die Spec `agent-evals` nimmt das bisher ausdrücklich aus ("Eine Betriebssystem-Sandbox ... ist nicht Teil dieser Spec"), das Folgeticket ist #103. Ohne Sandbox sollte kein fremder Agent und kein lokales Modell laufen.

## What Changes

- Neu: `evals/run.py --sandbox auto|bwrap|none` (Standard `auto`). Der Runner startet den Adapter unter `bwrap` (Linux): Dateisystem schreibgeschützt eingebunden, beschreibbar nur das Wegwerf-Arbeitsverzeichnis des Laufs und die Claude-Konfiguration (`~/.claude`, `~/.claude.json`, nötig für die Anmeldung); Netz bleibt offen.
- `auto` nimmt `bwrap`, wenn vorhanden. Fehlt es (andere Systeme), bricht der Runner mit klarer Meldung ab; `--sandbox none` erlaubt den Lauf ausdrücklich ohne Sandbox. Der Bericht nennt den Modus.
- Die Sandbox gilt für jeden Adapter (der Runner stellt den Befehl vor den Adapter).
- Nicht in diesem Change: Container (Docker, Podman), Sandbox für macOS und Windows, Netzbeschränkung.

## Capabilities

### New Capabilities
<!-- keine -->

### Modified Capabilities
- `agent-evals`: Anforderung "Isolierter Lauf" um die Sandbox erweitert, neue Anforderung "Sandbox-Modus im Bericht".

## Impact

- `evals/run.py` (Option, Befehl vor dem Adapter), Doku in `docs/workflow.md` und `docs/anleitung`.
- Abhängigkeit zur Laufzeit: `bwrap` (Bubblewrap), nur Linux.
