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
  W=$WORK/$1; mkdir -p "$W/posts" "$W/timeline"
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
# bm <dateiname-ohne-.md> <titel> <datum> [end] [beschreibung]: Bookmark in timeline/
bm() {
  # einfache Anführungszeichen: Backslashes bleiben wörtlich
  { printf -- "---\ntitle: '%s'\ndate: '%s'\n" "$2" "$3"
    [ -n "${4:-}" ] && printf "end: '%s'\n" "$4"
    [ -n "${5:-}" ] && printf "description: '%s'\n" "$5"
    [ "${6:-}" = draft ] && printf 'draft: true\n'
    printf -- '---\n'; } > "$W/timeline/$1.md"
}
# build: baut in $W, Ausgabe in $W/out.log und $W/err.log, gibt den Exit-Code zurück
build() { (cd "$W" && SITE_URL=http://localhost DRAFTS="${DRAFTS:-0}" sh build.sh >out.log 2>err.log); }
# must_build: Build muss gelingen, sonst ein eigener Fehlerfall mit dem Log (statt eines indirekten Folgefehlers)
must_build() { build || { no "Build schlägt fehl in $W: $(tail -n 2 "$W/err.log" | tr '\n' ' ')"; return 1; }; }
# build_with VAR=wert: Build mit gesetzter Umgebungsvariable, nur in einer Unter-Shell (Präfix vor einer Funktion ist in POSIX nicht eindeutig)
build_with() { ( export "$1"; must_build ); }
# TL_MAX: Einträge auf der Startseite, aus build.sh gelesen (eine Quelle)
TL_MAX=$(sed -n 's/^TL_MAX=\([0-9][0-9]*\).*/\1/p' "$ROOT/build.sh")
# timeline_html: nur der Timeline-Abschnitt der Startseite
timeline_html() { awk '/<aside class="timeline"/,/<\/aside>/' "$W/public/index.html"; }

# 1. Die Startseite zeigt eine Timeline mit den Beiträgen
fresh basis
post 2026-01-01-eins "Eins"; post 2026-01-02-zwei "Zwei"; post 2026-01-03-drei "Drei"
if build && [ "$(timeline_html | grep -c 'class="tl-item"')" = 3 ]; then ok "Startseite zeigt 3 Beiträge in der Timeline"; else no "Startseite zeigt 3 Beiträge in der Timeline"; fi

# TL_MAX muss lesbar sein und kleiner als die 12 Fixture-Beiträge
if [ -n "$TL_MAX" ] && [ "$TL_MAX" -lt 12 ]; then ok "TL_MAX=$TL_MAX aus build.sh gelesen"; else no "TL_MAX aus build.sh lesbar und kleiner als 12 (war: '$TL_MAX')"; exit 1; fi

# 2. Es erscheinen höchstens die TL_MAX neuesten, neueste zuerst
fresh viele
for i in 01 02 03 04 05 06 07 08 09 10 11 12; do post "2026-02-$i-p$i" "Beitrag $i"; done
must_build
got=$(timeline_html | grep -o 'blog/p[0-9]*/' | tr -d '/' | sed 's|blog||' | tr '\n' ' ')
want=; i=12; while [ "$i" -gt $((12 - TL_MAX)) ]; do want="$want$(printf 'p%02d ' "$i")"; i=$((i-1)); done
if [ "$got" = "$want" ]; then ok "$TL_MAX neueste, neueste zuerst"; else no "$TL_MAX neueste, neueste zuerst (war: $got, erwartet: $want)"; fi

# 3. Gleiches Datum: Reihenfolge ist unabhängig von der Locale gleich
fresh gleich
post 2026-03-01-a-b "Erster"; post 2026-03-01-ab "Zweiter"; post 2026-03-01-Ab "Dritter"
build_with LC_ALL=C; c=$(timeline_html | grep -o 'blog/[A-Za-z-]*/' | tr '\n' ' ')
for loc in en_US.UTF-8 de_DE.UTF-8; do
  if locale -a | grep -qi "^$(printf '%s' "$loc" | sed 's/UTF-8/utf8/')$"; then
    build_with LC_ALL=$loc; l=$(timeline_html | grep -o 'blog/[A-Za-z-]*/' | tr '\n' ' ')
    if [ "$c" = "$l" ]; then ok "gleiches Datum, Locale $loc wie C"; else no "gleiches Datum, Locale $loc weicht ab ($l statt $c)"; fi
  else
    echo "übersprungen: gleiches Datum, Locale $loc nicht installiert"
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
build_with DRAFTS=0; n0=$(timeline_html | grep -c 'class="tl-item"')
build_with DRAFTS=1; n1=$(timeline_html | grep -c 'class="tl-item"')
if [ "$n0" = 1 ] && [ "$n1" = 2 ]; then ok "Entwurf nur mit DRAFTS=1 (1 ohne, 2 mit)"; else no "Entwurf nur mit DRAFTS=1 (ohne: $n0, mit: $n1)"; fi

# 6. Ohne Einträge gibt es keine Timeline und keine leere Fläche
fresh leer
if build && ! grep -q 'class="timeline"' "$W/public/index.html"; then ok "ohne Beiträge keine Timeline"; else no "ohne Beiträge keine Timeline"; fi

# 7. Sonderzeichen im Titel werden escaped
fresh sonder
# pandoc entfernt rohes HTML im Titel, daher ein maskiertes <
post 2026-06-01-sonder "Tom & Jerry \\<3"
must_build
if timeline_html | grep -q 'Tom &amp; Jerry &lt;3'; then ok "Sonderzeichen im Titel escaped"; else no "Sonderzeichen im Titel escaped"; fi

# 8. Ein Bookmark aus timeline/ erscheint in der Timeline, ohne eigene Seite
fresh bookmark
post 2026-07-01-eins "Ein Beitrag"; bm 2024-05-vortrag "Vortrag zu Scrum" 2024-05 "" "Ein Satz zum Vortrag."
must_build
if timeline_html | grep -q 'Vortrag zu Scrum' && [ "$(timeline_html | grep -c 'class="tl-item"')" = 2 ] && [ -z "$(find "$W/public" -path '*vortrag*' 2>/dev/null)" ]; then ok "Bookmark erscheint ohne eigene Seite"; else no "Bookmark erscheint ohne eigene Seite"; fi

# 9. Ein Bookmark ist aufklappbar: Titel in <summary>, Beschreibung im aufgeklappten Teil
h=$(timeline_html | tr '\n' ' ')
if printf '%s' "$h" | grep -q '<details><summary>[^<]*<time[^>]*>2024-05</time> Vortrag zu Scrum</summary><p>Ein Satz zum Vortrag.</p>'; then ok "Bookmark als details mit Beschreibung"; else no "Bookmark als details mit Beschreibung"; fi

# 10. Reihenfolge nach normalisiertem Datum: fehlender Monat/Tag zählt als der erste
fresh mix
post 2026-10-03-beitrag "Beitrag 3. Oktober"; bm a-okt "Bookmark Oktober" 2026-10; bm b-jahr "Bookmark Jahr" 2026; post 2026-01-01-neujahr "Beitrag Neujahr"
must_build
got=$(timeline_html | grep -o '\(Beitrag 3. Oktober\|Bookmark Oktober\|Beitrag Neujahr\|Bookmark Jahr\)' | tr '\n' '|')
if [ "$got" = "Beitrag 3. Oktober|Bookmark Oktober|Beitrag Neujahr|Bookmark Jahr|" ]; then ok "Reihenfolge nach normalisiertem Datum"; else no "Reihenfolge nach normalisiertem Datum (war: $got)"; fi

# 11. Zeitraum: end wird als Zeitraum gezeigt, now als laufend, die Position bleibt durch date bestimmt
fresh zeitraum
post 2026-01-01-neu "Neuer Beitrag"; bm a-fest "Mit Ende" 2024-05 2024-11 "Text."; bm b-lauf "Laufend" 2023 now "Text."; bm c-spaet "Ende nach Beitrag" 2025-01 2027-12 "Text."
must_build; h=$(timeline_html | tr '\n' ' ')
if printf '%s' "$h" | grep -q '2024-05 – 2024-11' && printf '%s' "$h" | grep -q '2023 – laufend'; then ok "Zeitraum und laufend werden angezeigt"; else no "Zeitraum und laufend werden angezeigt"; fi
got=$(timeline_html | grep -o '\(Neuer Beitrag\|Mit Ende\|Laufend\|Ende nach Beitrag\)' | tr '\n' '|')
if [ "$got" = "Neuer Beitrag|Ende nach Beitrag|Mit Ende|Laufend|" ]; then ok "Position bleibt durch date bestimmt"; else no "Position bleibt durch date bestimmt (war: $got)"; fi

# 12. Fehlerhafte Bookmarks brechen den Build ab und nennen die Datei
fehler() { # <name> <frontmatter-zeilen>
  fresh fehler-$1; printf -- '---\n%b\n---\n' "$2" > "$W/timeline/kaputt.md"
  if build; then no "Bookmark $1 bricht den Build ab"
  elif grep -q "timeline/kaputt.md" "$W/err.log"; then ok "Bookmark $1 bricht ab und nennt die Datei"
  else no "Bookmark $1 bricht ab, nennt aber die Datei nicht"; fi
}
fehler ohne-datum 'title: "Titel"'
fehler ohne-titel 'date: "2024-05"'
fehler ungueltiges-datum 'title: "Titel"\ndate: "2024-13"'
fehler ungueltiges-ende 'title: "Titel"\ndate: "2024-05"\nend: "bald"'
fehler ende-vor-start 'title: "Titel"\ndate: "2024-05-10"\nend: "2024-05-01"'

# 13. Seiten mit date: erscheinen, ohne Datum nicht; Startseite und Galerie zählen nie
fresh seiten
printf -- '---\ntitle: Neue Seite\ndate: 2026-08-01\n---\n\nText.\n' > "$W/pages/neu.md"
printf -- '---\ntitle: Startseite\ndate: 2026-09-01\n---\n\nText.\n' > "$W/pages/index.md"
printf -- '---\ntitle: Galerie\ndate: 2026-09-02\n---\n\nText.\n' > "$W/pages/gallery.md"
must_build; h=$(timeline_html | tr '\n' ' ')
if printf '%s' "$h" | grep -q '<a href="/neu/">Neue Seite</a>' && ! printf '%s' "$h" | grep -q 'Über mich\|Startseite\|Galerie'; then ok "Seite mit Datum erscheint, ohne Datum nicht, index und gallery nie"; else no "Seite mit Datum erscheint, ohne Datum nicht, index und gallery nie (war: $h)"; fi

# 14. Bookmark-Entwürfe nur mit DRAFTS=1, Sonderzeichen in Titel und Beschreibung werden escaped
fresh bm-extra
bm skizze "Skizze" 2025-01 "" "Noch nicht fertig." draft
bm tom "Tom & Jerry \\<3" 2025-02 "" "Eins & zwei \\<drei"
build_with DRAFTS=0; a=$(timeline_html | grep -c 'class="tl-item"'); build_with DRAFTS=1; b=$(timeline_html | grep -c 'class="tl-item"')
if [ "$a" = 1 ] && [ "$b" = 2 ]; then ok "Bookmark-Entwurf nur mit DRAFTS=1"; else no "Bookmark-Entwurf nur mit DRAFTS=1 (ohne: $a, mit: $b)"; fi
if timeline_html | grep -q 'Tom &amp; Jerry &lt;3' && timeline_html | grep -q 'Eins &amp; zwei &lt;drei'; then ok "Sonderzeichen im Bookmark escaped"; else no "Sonderzeichen im Bookmark escaped"; fi

# 15. /timeline/ zeigt alle Einträge in der Reihenfolge der Startseite, ohne Container
fresh voll
for i in 01 02 03 04 05 06 07 08 09 10 11 12; do post "2026-02-$i-p$i" "Beitrag $i"; done
must_build
full() { cat "$W/public/timeline/index.html" 2>/dev/null; }
n=$(full | grep -c 'class="tl-item"')
home=$(timeline_html | grep -o 'blog/p[0-9]*/' | tr '\n' ' '); all=$(full | grep -o 'blog/p[0-9]*/' | tr '\n' ' ')
case $all in "$home"*) pre=ja ;; *) pre=nein ;; esac
if [ "$n" = 12 ] && [ "$pre" = ja ] && ! full | grep -q 'timeline-scroll'; then ok "/timeline/ zeigt alle 12 in Reihenfolge, ohne Container"; else no "/timeline/ zeigt alle 12 in Reihenfolge, ohne Container (Einträge: $n, Präfix: $pre)"; fi

# 16. "Alles ansehen" nur bei mehr als TL_MAX Einträgen; ohne Einträge keine /timeline/-Seite
link() { timeline_html | grep -c 'href="/timeline/"[^>]*>Alles ansehen'; }
for n in 0 "$TL_MAX" $((TL_MAX + 1)); do
  fresh "grenze-$n"; i=0; while [ "$i" -lt "$n" ]; do i=$((i+1)); post "2026-04-$(printf '%02d' "$i")-g$i" "G $i"; done
  must_build; l=$(link); [ -f "$W/public/timeline/index.html" ] && seite=ja || seite=nein
  if [ "$n" = 0 ]; then
    [ "$seite" = nein ] && ok "ohne Einträge keine /timeline/-Seite" || no "ohne Einträge keine /timeline/-Seite"
  elif [ "$n" = "$TL_MAX" ]; then
    [ "$l" = 0 ] && ok "$n Einträge: kein Link Alles ansehen" || no "$n Einträge: kein Link Alles ansehen"
  else
    [ "$l" = 1 ] && ok "$n Einträge: Link Alles ansehen" || no "$n Einträge: Link Alles ansehen (Treffer: $l)"
  fi
done

# 17. Ohne Einträge keine leere Spalte: die Startseite bekommt die Klasse home nur mit Timeline
fresh leer-layout; must_build
if ! grep -q 'class="home"' "$W/public/index.html"; then ok "ohne Einträge keine Klasse home (kein leeres Grid)"; else no "ohne Einträge keine Klasse home (kein leeres Grid)"; fi
fresh voll-layout; post 2026-01-01-eins "Eins"; must_build
if grep -q '<body class="home">' "$W/public/index.html" && grep -q '<main class="home">' "$W/public/index.html"; then ok "mit Einträgen Klasse home an body und main"; else no "mit Einträgen Klasse home an body und main"; fi

# 18. Ende gleich Start (normalisiert) ist erlaubt, nur ein Ende davor bricht ab
for paar in "2024-05-01 2024-05" "2024-05 2024-05-01" "2024 2024-01-01" "2024-05 2024-05"; do
  set -- $paar; fresh "gleich-$1-$2"; bm gleich "Gleich" "$1" "$2" "Text."
  if build; then ok "Ende $2 gleich Start $1 baut"; else no "Ende $2 gleich Start $1 baut"; fi
done
fresh davor; bm davor "Davor" 2024-05-10 2024-05 "Text."
if build; then no "Ende 2024-05 vor Start 2024-05-10 bricht ab"; else ok "Ende 2024-05 vor Start 2024-05-10 bricht ab"; fi

# 19. Gleiches normalisiertes Datum: Reihenfolge nach Art und Slug, nicht nach der Länge der Schreibweise
fresh gleichstand
post 2026-10-01-beitrag "Beitrag"; bm a-bm "Bookmark A" 2026-10-01 "" "Text."; bm z-bm "Bookmark Z" 2026-10 "" "Text."
must_build
got=$(timeline_html | grep -o '\(>Beitrag<\|Bookmark A\|Bookmark Z\)' | tr -d '<>' | tr '\n' '|')
if [ "$got" = "Beitrag|Bookmark Z|Bookmark A|" ]; then ok "Gleichstand nach Art und Slug"; else no "Gleichstand nach Art und Slug (war: $got)"; fi

# 20. Beiträge mit Monat oder Jahr werden so angezeigt, wie geschrieben
fresh anzeige
postd 2026-03-monat "Monatsbeitrag" 2026-03; postd 2026-01-jahr "Jahresbeitrag" 2026
must_build; h=$(timeline_html | tr '\n' ' ')
if printf '%s' "$h" | grep -q '<time datetime="2026-03">2026-03</time>' && printf '%s' "$h" | grep -q '<time datetime="2026">2026</time>'; then ok "Beiträge mit Monat und Jahr wie geschrieben"; else no "Beiträge mit Monat und Jahr wie geschrieben"; fi

# 21. Der Zeitraum steht im aufgeklappten Teil, nicht in der Titelzeile
fresh bereich
bm zeit "Mit Zeitraum" 2024-05 2024-11 "Text."
must_build; h=$(timeline_html | tr '\n' ' ')
if printf '%s' "$h" | grep -q '</summary><p>Text.</p><p class="tl-range">2024-05 – 2024-11</p></details>' && ! printf '%s' "$h" | grep -q '<summary>[^<]*<time[^>]*>[^<]*</time>[^<]*2024-11'; then ok "Zeitraum im aufgeklappten Teil"; else no "Zeitraum im aufgeklappten Teil"; fi

# 22. Jede Seite mit Datum hat den Pfad /<slug>/
fresh seiten2
for n in eins zwei; do printf -- '---\ntitle: Seite %s\ndate: 2026-08-0%s\n---\n\nText.\n' "$n" "$([ $n = eins ] && echo 1 || echo 2)" > "$W/pages/$n.md"; done
must_build; h=$(timeline_html | tr '\n' ' ')
if printf '%s' "$h" | grep -q 'href="/eins/">Seite eins' && printf '%s' "$h" | grep -q 'href="/zwei/">Seite zwei'; then ok "Seiten mit Datum verlinken auf /<slug>/"; else no "Seiten mit Datum verlinken auf /<slug>/"; fi

# 23. Das Bookmark-Beispiel aus dem README baut wie beschrieben und zeigt den Zeitraum
fresh readme
awk '/^```markdown$/ { b = ""; inb = 1; next } /^```$/ { if (inb && b ~ /end: now/) { printf "%s", b; exit } inb = 0; next } inb { b = b $0 "\n" }' "$ROOT/README.md" > "$W/timeline/readme-beispiel.md"
if [ -s "$W/timeline/readme-beispiel.md" ] && build && timeline_html | tr '\n' ' ' | grep -q 'Entwicklungsprozess mit OpenSpec aufgesetzt.*2026-10-04 – laufend'; then ok "README-Beispiel baut und zeigt den Zeitraum"; else no "README-Beispiel baut und zeigt den Zeitraum"; fi

# 24. Fragmente zum Nachladen: Einträge ab TL_MAX+1, je 10, keine Dopplung, nichts fehlt
fresh chunks
i=0; while [ "$i" -lt 25 ]; do i=$((i+1)); post "2026-05-$(printf '%02d' "$i")-c$i" "C $i"; done
must_build
n1=$(grep -c 'class="tl-item"' "$W/public/timeline/chunk-1.html" 2>/dev/null); n2=$(grep -c 'class="tl-item"' "$W/public/timeline/chunk-2.html" 2>/dev/null)
rest=$((25 - TL_MAX)); want2=$((rest - 10))
if [ "$n1" = 10 ] && [ "$n2" = "$want2" ] && [ ! -e "$W/public/timeline/chunk-3.html" ]; then ok "25 Einträge: Fragmente mit 10 und $want2 Einträgen, kein drittes"; else no "25 Einträge: Fragmente mit 10 und $want2 Einträgen, kein drittes (war: $n1, $n2)"; fi
home=$(timeline_html | grep -o 'blog/c[0-9]*/' | tr '\n' ' ')
ch=$(cat "$W/public/timeline/chunk-1.html" "$W/public/timeline/chunk-2.html" 2>/dev/null | grep -o 'blog/c[0-9]*/' | tr '\n' ' ')
all=$(full | grep -o 'blog/c[0-9]*/' | tr '\n' ' ')
if [ "$home$ch" = "$all" ] && [ "$(printf '%s' "$all" | tr ' ' '\n' | sed '/^$/d' | sort | uniq -d | wc -l)" = 0 ]; then ok "Startseite plus Fragmente entsprechen der vollständigen Seite, ohne Doppelungen"; else no "Startseite plus Fragmente entsprechen der vollständigen Seite, ohne Doppelungen"; fi
if timeline_html | grep -q 'class="timeline-scroll"[^>]*data-chunks="2"[^>]*data-src="/timeline/chunk-"'; then ok "Container nennt Fragmentzahl und Quelle"; else no "Container nennt Fragmentzahl und Quelle"; fi

# 25. Keine Fragmente, wenn alles auf die Startseite passt oder genau ein Fragment reicht
fresh klein; i=0; while [ "$i" -lt "$TL_MAX" ]; do i=$((i+1)); post "2026-06-$(printf '%02d' "$i")-k$i" "K $i"; done
must_build
if [ ! -e "$W/public/timeline/chunk-1.html" ] && ! timeline_html | grep -q 'data-chunks'; then ok "bis TL_MAX Einträge: keine Fragmente, kein data-chunks"; else no "bis TL_MAX Einträge: keine Fragmente, kein data-chunks"; fi
fresh genau; i=0; while [ "$i" -lt $((TL_MAX + 10)) ]; do i=$((i+1)); post "2026-07-$(printf '%02d' "$i")-g$i" "G $i"; done
must_build
if [ -e "$W/public/timeline/chunk-1.html" ] && [ ! -e "$W/public/timeline/chunk-2.html" ] && timeline_html | grep -q 'data-chunks="1"'; then ok "TL_MAX+10 Einträge: genau ein Fragment"; else no "TL_MAX+10 Einträge: genau ein Fragment"; fi

exit $FAIL
