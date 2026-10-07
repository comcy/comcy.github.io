"""`proc.utf8_output` stellt stdout und stderr auf UTF-8, auch wenn die Konsole eine andere Kodierung vorgibt (Windows-CI)."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / "scripts" / "lib"


class Utf8Ausgabe(unittest.TestCase):
    def test_stdout_und_stderr_sind_utf8(self):
        code = "import sys; sys.path.insert(0, sys.argv[1]); import proc; proc.utf8_output(); print('ü'); print('ü', file=sys.stderr)"
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        r = subprocess.run([sys.executable, "-c", code, str(LIB)], capture_output=True, env=env)
        self.assertEqual(r.stdout.decode("utf-8").strip(), "ü")
        self.assertEqual(r.stderr.decode("utf-8").strip(), "ü")


if __name__ == "__main__":
    unittest.main()
