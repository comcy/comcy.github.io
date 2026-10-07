"""Programme aufrufen: ohne Shell, mit Zeitlimit und einheitlicher Kodierung (nur Standardbibliothek).

ponytail: Unter Windows laufen .cmd-Programme über cmd.exe, Argumente mit & | ^ % würden dort anders gedeutet. Unsere
Argumente (Labelnamen, Farben, Beschreibungen aus workflow/states.tsv) enthalten sie nicht, gh ist eine .exe. Kommen
solche Zeichen in die Daten, die Prüfung in flow validate ergänzen.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT = 60  # Sekunden; ein hängendes Programm soll das Setup nicht blockieren


class SetupError(Exception):
    """Ein Schritt ist fehlgeschlagen; die Meldung geht unverändert an die Ausgabe."""


def find(name: str) -> str | None:
    """Pfad eines Programms im PATH (unter Windows mit PATHEXT, also auch .cmd) oder None."""
    return shutil.which(name)


def run(exe: str, args: list[str] | tuple[str, ...] = (), cwd: Path | None = None,
        timeout: int = TIMEOUT, env: dict | None = None) -> subprocess.CompletedProcess:
    """Ruft ein Programm mit Argumentliste auf; fehlt es oder dauert es zu lange, gibt es einen SetupError."""
    pfad = exe if Path(exe).is_absolute() else find(exe)
    if pfad is None:
        raise SetupError(f"{exe} nicht gefunden")
    try:
        return subprocess.run([pfad, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              cwd=cwd, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as fehler:
        raise SetupError(f"{Path(pfad).name} {' '.join(args)} dauert länger als {timeout} Sekunden") from fehler
    except OSError as fehler:
        raise SetupError(f"{Path(pfad).name} lässt sich nicht aufrufen: {fehler}") from fehler


def utf8_output() -> None:
    """Ausgabe immer als UTF-8, damit sie unter Windows (Umleitung, CI) nicht von der Konsolenkodierung abhängt."""
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, "reconfigure"):
            strom.reconfigure(encoding="utf-8")
