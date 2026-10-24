#!/bin/sh
# Prüft die Aufteilung des Repos (Spec repo-layout): sh site/tests/layout-check.sh
# Inhalt unter content/, Bauwerkzeug unter site/, nichts davon im Wurzelverzeichnis.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
FAIL=0
ok() { echo "ok     $1"; }
no() { echo "FEHLER $1"; FAIL=1; }

for p in content/posts content/pages content/timeline content/gallery content/site.conf site/build.sh site/templates site/static; do
  if [ -e "$ROOT/$p" ]; then ok "$p vorhanden"; else no "$p fehlt"; fi
done
for p in posts pages timeline gallery site.conf build.sh templates static; do
  if [ ! -e "$ROOT/$p" ]; then ok "$p nicht im Wurzelverzeichnis"; else no "$p liegt noch im Wurzelverzeichnis"; fi
done
# Der Build läuft von überall und schreibt nach <Wurzel>/public
OUT=$(mktemp -d); trap 'rm -rf "$OUT"' EXIT
cp -R "$ROOT/site" "$ROOT/content" "$OUT/"
(cd "$OUT" && SITE_URL=http://localhost sh site/build.sh >/dev/null 2>&1 && cd / && sh "$OUT/site/build.sh" >/dev/null 2>&1) || no "Build scheitert (im Wurzelverzeichnis oder von anderem Ordner)"
[ -f "$OUT/public/index.html" ] && ok "public/index.html unter der Wurzel gebaut" || no "public/index.html fehlt"
exit $FAIL
