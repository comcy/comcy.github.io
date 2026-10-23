#!/bin/sh
# Prüft den Footer über den Build (Black-Box): sh tests/footer-check.sh
# Der Footer jeder Seite enthält den Link "Quellcode" auf das GitHub-Repo.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
FAIL=0
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

ok() { echo "ok     $1"; }
no() { echo "FEHLER $1"; FAIL=1; }

W=$WORK/site; mkdir -p "$W/posts"
for d in build.sh site.conf templates static pages; do cp -R "$ROOT/$d" "$W/"; done
printf -- '---\ntitle: Probe\ndate: 2026-01-02\n---\n\nText.\n' > "$W/posts/2026-01-02-probe.md"
(cd "$W" && sh build.sh >/dev/null 2>&1) || no "Build läuft nicht"

URL='https://github.com/comcy/comcy.github.io'
for f in public/index.html public/blog/probe/index.html public/about/index.html; do
  if [ -f "$W/$f" ]; then
    if grep -q "<a href=\"$URL\">Quellcode</a>" "$W/$f"; then ok "Footer-Link in $f"; else no "Footer-Link fehlt in $f"; fi
  else
    no "$f wurde nicht gebaut"
  fi
done
exit $FAIL
