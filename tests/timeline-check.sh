#!/bin/sh
# Prüft die Timeline über den Build (Black-Box): sh tests/timeline-check.sh
# Jeder Fall baut die Seite in einem temporären Klon mit eigenen Beiträgen und prüft public/.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
FAIL=0
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

ok() { echo "ok     $1"; }
no() { echo "FEHLER $1"; FAIL=1; }

# fresh <name>: leerer Klon ohne Beiträge, setzt W
fresh() {
  W=$WORK/$1; mkdir -p "$W/posts"
  for d in build.sh site.conf templates static pages; do cp -R "$ROOT/$d" "$W/"; done
}
# post <dateiname-ohne-.md> <titel> [draft]
post() {
  { printf -- '---\ntitle: %s\ndate: %s\n' "$2" "$(printf '%s' "$1" | cut -c1-10)"
    [ "${3:-}" = draft ] && printf 'draft: true\n'
    printf -- '---\n\nText.\n'; } > "$W/posts/$1.md"
}
# postd <dateiname-ohne-.md> <titel> <datum-wie-geschrieben>
postd() { printf -- '---\ntitle: %s\ndate: "%s"\n---\n\nText.\n' "$2" "$3" > "$W/posts/$1.md"; }
# build: baut in $W, Ausgabe in $W/out.log und $W/err.log, gibt den Exit-Code zurück
build() { (cd "$W" && SITE_URL=http://localhost DRAFTS="${DRAFTS:-0}" sh build.sh >out.log 2>err.log); }
# timeline_html: nur der Timeline-Abschnitt der Startseite
timeline_html() { awk '/<aside class="timeline"/,/<\/aside>/' "$W/public/index.html"; }

# 1. Die Startseite zeigt eine Timeline mit den Beiträgen
fresh basis
post 2026-01-01-eins "Eins"; post 2026-01-02-zwei "Zwei"; post 2026-01-03-drei "Drei"
if build && [ "$(timeline_html | grep -c 'class="tl-item"')" = 3 ]; then ok "Startseite zeigt 3 Beiträge in der Timeline"; else no "Startseite zeigt 3 Beiträge in der Timeline"; fi

# 2. Es erscheinen höchstens die 8 neuesten, neueste zuerst
fresh viele
for i in 01 02 03 04 05 06 07 08 09 10 11 12; do post "2026-02-$i-p$i" "Beitrag $i"; done
build
got=$(timeline_html | grep -o 'blog/p[0-9]*/' | tr -d '/' | sed 's|blog||' | tr '\n' ' ')
if [ "$got" = "p12 p11 p10 p09 p08 p07 p06 p05 " ]; then ok "8 neueste, neueste zuerst"; else no "8 neueste, neueste zuerst (war: $got)"; fi

# 3. Gleiches Datum: Reihenfolge ist unabhängig von der Locale gleich
fresh gleich
post 2026-03-01-a-b "Erster"; post 2026-03-01-ab "Zweiter"; post 2026-03-01-Ab "Dritter"
LC_ALL=C build; c=$(timeline_html | grep -o 'blog/[A-Za-z-]*/' | tr '\n' ' ')
for loc in en_US.UTF-8 de_DE.UTF-8; do
  if locale -a | grep -qi "^$(printf '%s' "$loc" | sed 's/UTF-8/utf8/')$"; then
    LC_ALL=$loc build; l=$(timeline_html | grep -o 'blog/[A-Za-z-]*/' | tr '\n' ' ')
    if [ "$c" = "$l" ]; then ok "gleiches Datum, Locale $loc wie C"; else no "gleiches Datum, Locale $loc weicht ab ($l statt $c)"; fi
  fi
done
if [ "$c" = "blog/ab/ blog/a-b/ blog/Ab/ " ]; then ok "gleiches Datum: feste Reihenfolge (absteigend nach Slug, C-Sortierung)"; else no "gleiches Datum: feste Reihenfolge (war: $c)"; fi

# 4. Datumsformate: YYYY, YYYY-MM, YYYY-MM-DD gelten, alles andere bricht den Build ab und nennt die Datei
fresh daten
postd 2026-04-01-jahr "Jahr" 2026; postd 2026-04-02-monat "Monat" 2026-03; postd 2026-04-03-tag "Tag" 2026-03-04
if build; then ok "gültige Datumsformate werden gebaut"; else no "gültige Datumsformate werden gebaut"; fi
for bad in 2026-13-01 2026-02-30x 26-02-01 gestern; do
  fresh ungueltig; postd 2026-04-04-kaputt "Kaputt" "$bad"
  if build; then no "ungültiges Datum '$bad' bricht den Build ab"
  elif grep -q "2026-04-04-kaputt.md" "$W/err.log"; then ok "ungültiges Datum '$bad' bricht ab und nennt die Datei"
  else no "ungültiges Datum '$bad' bricht ab, nennt aber die Datei nicht"; fi
done

# 5. Entwürfe erscheinen nur mit DRAFTS=1
fresh entwurf
post 2026-05-01-fertig "Fertig"; post 2026-05-02-skizze "Skizze" draft
DRAFTS=0 build; n0=$(timeline_html | grep -c 'class="tl-item"')
DRAFTS=1 build; n1=$(timeline_html | grep -c 'class="tl-item"')
if [ "$n0" = 1 ] && [ "$n1" = 2 ]; then ok "Entwurf nur mit DRAFTS=1 (1 ohne, 2 mit)"; else no "Entwurf nur mit DRAFTS=1 (ohne: $n0, mit: $n1)"; fi

# 6. Ohne Einträge gibt es keine Timeline und keine leere Fläche
fresh leer
if build && ! grep -q 'class="timeline"' "$W/public/index.html"; then ok "ohne Beiträge keine Timeline"; else no "ohne Beiträge keine Timeline"; fi

# 7. Sonderzeichen im Titel werden escaped
fresh sonder
# pandoc entfernt rohes HTML im Titel, daher ein maskiertes <
post 2026-06-01-sonder "Tom & Jerry \\<3"
build
if timeline_html | grep -q 'Tom &amp; Jerry &lt;3'; then ok "Sonderzeichen im Titel escaped"; else no "Sonderzeichen im Titel escaped"; fi

exit $FAIL
