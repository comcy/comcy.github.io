#!/bin/sh
# Führt alle Shell-Tests unter tests/ aus und endet mit Fehlercode, sobald einer rot ist: sh tests/run.sh
cd "$(dirname "$0")" || exit 1
FAIL=0
for t in *-check.sh; do
  [ -e "$t" ] || continue
  echo "== $t"
  sh "$t" || FAIL=1
done
exit $FAIL
