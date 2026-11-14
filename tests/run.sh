#!/bin/sh
# Führt alle Tests aus und endet mit Fehlercode, sobald einer rot ist: sh tests/run.sh
cd "$(dirname "$0")" || exit 1
FAIL=0
sh ../site/tests/run.sh || FAIL=1
# Python-Tests (scripts/flow.py, scripts/setup.py), nur Standardbibliothek, Python 3.11 oder neuer
if command -v python3 >/dev/null 2>&1; then
  echo "== Python-Tests"
  python3 -m unittest discover -s . -p "test_*.py" || FAIL=1
else
  echo "übersprungen: Python-Tests (python3 nicht gefunden)"
fi
exit $FAIL
