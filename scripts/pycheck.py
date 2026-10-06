"""Prüft die Python-Version, bevor andere Module geladen werden. Läuft bewusst auch auf älterem Python."""
import sys

MINIMUM = (3, 11)


def require_python(version_info=None, minimum=MINIMUM):
    """Beendet mit einer Meldung, wenn Python zu alt ist (statt mit einem Syntaxfehler)."""
    installiert = tuple(version_info if version_info is not None else sys.version_info)[:2]
    if installiert < minimum:
        sys.exit("Python %d.%d oder neuer wird benötigt, installiert ist %d.%d"
                 % (minimum[0], minimum[1], installiert[0], installiert[1]))
