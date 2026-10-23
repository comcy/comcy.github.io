#!/bin/sh
# Führt alle Shell-Tests unter tests/ aus und endet mit Fehlercode, sobald einer rot ist: sh tests/run.sh
cd "$(dirname "$0")" || exit 1
FAIL=0
for t in *-check.sh; do
  [ -e "$t" ] || continue
  echo "== $t"
  sh "$t" || FAIL=1
done
# Python-Tests (scripts/flow.py, scripts/setup.py), nur Standardbibliothek, Python 3.11 oder neuer
if command -v python3 >/dev/null 2>&1; then
  echo "== Python-Tests"
  python3 -m unittest discover -s . -p "test_*.py" || FAIL=1
else
  echo "übersprungen: Python-Tests (python3 nicht gefunden)"
fi
exit $FAIL
