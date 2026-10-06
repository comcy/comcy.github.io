#!/bin/sh
# Baut die statische Seite aus Markdown nach ./public
# Benötigt: POSIX-Shell, pandoc. Entwürfe mitbauen: DRAFTS=1 ./build.sh
set -eu

cd "$(dirname "$0")"
. ./site.conf

OUT=public
BASE=$(printf '%s' "$SITE_URL" | sed 's|^[a-z]*://[^/]*||')
YEAR=$(date +%Y)
# Prüfsumme von CSS und JS als Cache-Buster, damit Browser nach Änderungen sofort die neuen Dateien laden
ASSET_V=$(cat static/style.css static/site.js | cksum | cut -d' ' -f1)
TL_MAX=8  # Einträge der Timeline auf der Startseite; mehr führen zum Link "Alles ansehen" (README und tests/timeline-check.sh nennen den Wert)
US=$(printf '\037')  # Feldtrenner im Index (kein Whitespace, damit leere Felder erhalten bleiben)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

rm -rf "$OUT"
mkdir -p "$OUT"
cp -R static/. "$OUT"/

# pandoc mit gemeinsamen Variablen: render <eingabe> <ausgabe> [weitere Optionen]
render() {
  in=$1; out=$2; shift 2
  mkdir -p "$(dirname "$out")"
  pandoc "$in" --from markdown --to html5 --template templates/page.html \
    -V site="$SITE_TITLE" -V v="$ASSET_V" -V base="$BASE" -V year="$YEAR" -V author="$SITE_AUTHOR" \
    "$@" -o "$out"
}

# Zeichen escapen, die in Markdown-Links stören
md_escape() { printf '%s' "$1" | sed 's/[][\\*_`<>]/\\&/g'; }
# Zeichen escapen, die in XML stören
xml_escape() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

# Prüft ein Datum (YYYY, YYYY-MM oder YYYY-MM-DD), sonst Abbruch mit Dateiname: check_date <datum> <datei>
# ponytail: Monatslängen werden nicht geprüft (2026-02-30 gilt), bei Bedarf mit date(1) ergänzen
check_date() {
  printf '%s' "$1" | grep -Eq '^[0-9]{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01]))?)?$' ||
    { echo "Ungültiges Datum '$1' in $2" >&2; exit 1; }
}

# Normalisiert ein gültiges Datum auf JJJJ-MM-TT, ein fehlender Monat oder Tag zählt als der erste: norm_date <datum>
norm_date() {
  case ${#1} in 4) printf '%s-01-01' "$1" ;; 7) printf '%s-01' "$1" ;; *) printf '%s' "$1" ;; esac
}

# Feld <n> der Metadaten in $meta (tabgetrennt). cut statt read, weil read leere Felder bei Whitespace-IFS verschluckt: meta_field <n>
meta_field() { printf '%s' "$meta" | cut -f"$1"; }

# Timeline-Eintrag (liest Felder aus $kind $slug $date $end $title $desc): Beitrag mit Link, Bookmark ohne Seite
timeline_item() {
  case $kind in
    post|page)
      [ "$kind" = post ] && href="$BASE/blog/$slug/" || href="$BASE/$slug/"
      printf '<li class="tl-item"><time datetime="%s">%s</time> <a href="%s">%s</a></li>\n' \
        "$date" "$date" "$href" "$(xml_escape "$title")" ;;
    *) range=
       if [ -n "$end" ]; then
         [ "$end" = now ] && endtxt=laufend || endtxt=$end
         range=$(printf '<p class="tl-range">%s – %s</p>' "$date" "$endtxt")
       fi
       printf '<li class="tl-item" data-kind="bookmark"><details><summary><time datetime="%s">%s</time> %s</summary><p>%s</p>%s</details></li>\n' \
         "$date" "$date" "$(xml_escape "$title")" "$(xml_escape "$desc")" "$range" ;;
  esac
}

# Listeneintrag für einen Post (liest Felder aus $date $slug $title $desc)
post_item() {
  printf -- '- [%s](%s/blog/%s/)  \n  [%s]{.date} %s\n' \
    "$(md_escape "$title")" "$BASE" "$slug" "$date" "$(md_escape "$desc")"
}

# --- Posts ------------------------------------------------------------------
# Index: datum, slug, titel, tags, beschreibung (getrennt durch $US)
: > "$TMP/index"
for f in posts/*.md; do
  [ -e "$f" ] || continue
  slug=$(basename "$f" .md)
  slug=${slug#[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-}
  meta=$(pandoc "$f" --to plain --wrap=none --template templates/meta.txt)
  check_date "$(meta_field 1)" "$f"
  draft=$(meta_field 3)
  if [ "$draft" = draft ] && [ "${DRAFTS:-0}" != 1 ]; then
    echo "Entwurf übersprungen: $f"
    continue
  fi
  printf '%s\t%s\n' "$slug" "$meta" |
    awk -F'\t' -v OFS="$US" '{print $2, $1, $3, $5, $6}' >> "$TMP/index"
  render "$f" "$OUT/blog/$slug/index.html" -M post=true -M pagetitle="$(meta_field 2)"
  # Bilder und andere Dateien neben dem Post: posts/<dateiname>/ wird mitkopiert
  [ -d "${f%.md}" ] && cp -R "${f%.md}/." "$OUT/blog/$slug/"
  echo "Post: $slug"
done
LC_ALL=C sort -r "$TMP/index" > "$TMP/sorted"

# --- Timeline-Index: Beiträge, Seiten und Bookmarks (key, art, slug, datum, ende, titel, beschreibung); der Schlüssel ist das normalisierte Datum, bei Gleichstand entscheiden Art und Slug ----------
: > "$TMP/tl"
while IFS=$US read -r date slug title tags desc; do
  printf '%s\037post\037%s\037%s\037\037%s\037%s\n' "$(norm_date "$date")" "$slug" "$date" "$title" "$desc" >> "$TMP/tl"
done < "$TMP/sorted"
# Seiten mit date: (außer Startseite und Galerie) und Bookmarks aus timeline/; Entwürfe wie im Blog
for f in pages/*.md timeline/*.md; do
  [ -e "$f" ] || continue
  slug=$(basename "$f" .md); kind=bookmark
  case $f in pages/*) kind=page; case $slug in index|gallery) continue ;; esac ;; esac
  meta=$(pandoc "$f" --to plain --wrap=none --template templates/timeline-meta.txt)
  date=$(meta_field 1); end=$(meta_field 2); title=$(meta_field 3); desc=$(meta_field 4)
  [ "$kind" = page ] && [ -z "$date" ] && continue
  [ "$(meta_field 5)" = draft ] && [ "${DRAFTS:-0}" != 1 ] && continue
  check_date "$date" "$f"
  [ -n "$title" ] || { echo "Titel fehlt in $f" >&2; exit 1; }
  if [ -n "$end" ] && [ "$end" != now ]; then
    check_date "$end" "$f"
    # normalisiert verglichen: gleiches Datum in anderer Schreibweise ist kein Fehler
    awk -v a="$(norm_date "$end")" -v b="$(norm_date "$date")" 'BEGIN { exit !(a < b) }' && { echo "Ende vor Start in $f" >&2; exit 1; }
  fi
  printf '%s\037%s\037%s\037%s\037%s\037%s\037%s\n' "$(norm_date "$date")" "$kind" "$slug" "$date" "$end" "$title" "$desc" >> "$TMP/tl"
done
LC_ALL=C sort -r "$TMP/tl" > "$TMP/tl.sorted"

# --- Blog-Übersicht und Startseite ----------------------------------------------
{
  printf -- '---\ntitle: Blog\n---\n\n::: posts\n'
  while IFS=$US read -r date slug title tags desc; do post_item; done < "$TMP/sorted"
  printf ':::\n'
} > "$TMP/blog.md"
render "$TMP/blog.md" "$OUT/blog/index.html" -M pagetitle=Blog

{
  if [ -f pages/index.md ]; then cat pages/index.md; else printf -- '---\ntitle: %s\n---\n' "$SITE_TITLE"; fi
  printf '\n## Neueste Beiträge\n\n::: posts\n'
  head -n 5 "$TMP/sorted" | while IFS=$US read -r date slug title tags desc; do post_item; done
  printf ':::\n\n[Alle Beiträge →](%s/blog/)\n' "$BASE"
  # Timeline als rohes HTML, die Spalte liegt per CSS neben dem Inhalt (ohne Einträge entfällt sie)
  if [ -s "$TMP/tl.sorted" ]; then
    printf '\n```{=html}\n<aside class="timeline" aria-label="Timeline">\n<h2>Timeline</h2>\n<div class="timeline-scroll">\n<ol class="timeline-list">\n'
    head -n "$TL_MAX" "$TMP/tl.sorted" | while IFS=$US read -r key kind slug date end title desc; do timeline_item; done
    printf '</ol>\n</div>\n'
    # ab dem Eintrag TL_MAX+1 führt ein Link auf die vollständige Seite
    [ "$(wc -l < "$TMP/tl.sorted")" -gt "$TL_MAX" ] && printf '<p class="timeline-more"><a href="%s/timeline/">Alles ansehen →</a></p>\n' "$BASE"
    printf '</aside>\n```\n'
  fi
} > "$TMP/home.md"
# Die Klasse home (breite Startseite mit Spalte) gilt nur mit Timeline, sonst bliebe die Spalte leer
home_opt=; [ -s "$TMP/tl.sorted" ] && home_opt="-M home=true"
render "$TMP/home.md" "$OUT/index.html" $home_opt -M pagetitle=Start --metadata description="$SITE_DESCRIPTION"

# --- Timeline-Seite: alle Einträge, ohne Container (entfällt ohne Einträge) ---------------------------
if [ -s "$TMP/tl.sorted" ]; then
  {
    printf -- '---\ntitle: Timeline\n---\n\n```{=html}\n<section class="timeline timeline-full">\n<ol class="timeline-list">\n'
    while IFS=$US read -r key kind slug date end title desc; do timeline_item; done < "$TMP/tl.sorted"
    printf '</ol>\n</section>\n```\n'
  } > "$TMP/timeline.md"
  render "$TMP/timeline.md" "$OUT/timeline/index.html" -M pagetitle=Timeline
fi

# --- Themen (Tags) ------------------------------------------------------------
cut -d "$US" -f4 "$TMP/sorted" | tr ' ' '\n' | sed '/^$/d' | sort -u > "$TMP/tags"
{
  printf -- '---\ntitle: Themen\n---\n\n'
  while read -r tag; do
    n=$(awk -F "$US" -v t="$tag" '{ split($4, a, " "); for (i in a) if (a[i] == t) c++ } END { print c+0 }' "$TMP/sorted")
    printf -- '- [#%s](%s/tags/%s/) (%s)\n' "$tag" "$BASE" "$tag" "$n"
  done < "$TMP/tags"
} > "$TMP/tags.md"
render "$TMP/tags.md" "$OUT/tags/index.html" -M pagetitle=Themen

while read -r tag; do
  {
    printf -- '---\ntitle: "#%s"\n---\n\n::: posts\n' "$tag"
    awk -F "$US" -v t="$tag" '{ split($4, a, " "); for (i in a) if (a[i] == t) { print; next } }' "$TMP/sorted" |
      while IFS=$US read -r date slug title tags desc; do post_item; done
    printf ':::\n'
  } > "$TMP/tag.md"
  render "$TMP/tag.md" "$OUT/tags/$tag/index.html" -M pagetitle="#$tag"
done < "$TMP/tags"

# --- Galerie ------------------------------------------------------------------
# Bilder in gallery/, optionale Bildunterschrift in gallery/<bild>.txt
mkdir -p "$OUT/gallery"
{
  if [ -f pages/gallery.md ]; then cat pages/gallery.md; else printf -- '---\ntitle: Galerie\n---\n'; fi
  printf '\n::: gallery\n'
  for img in gallery/*; do
    case $img in *.jpg|*.jpeg|*.png|*.webp|*.gif|*.svg) ;; *) continue ;; esac
    name=$(basename "$img")
    cp "$img" "$OUT/gallery/$name"
    caption=${name%.*}
    [ -f "$img.txt" ] && caption=$(cat "$img.txt")
    printf '\n![%s](%s/gallery/%s){loading=lazy}\n' "$(md_escape "$caption")" "$BASE" "$name"
  done
  printf '\n:::\n'
} > "$TMP/gallery.md"
render "$TMP/gallery.md" "$OUT/gallery/index.html" -M pagetitle=Galerie

# --- Weitere Seiten (pages/*.md außer index/gallery) ----------------------------
for f in pages/*.md; do
  [ -e "$f" ] || continue
  name=$(basename "$f" .md)
  case $name in index|gallery) continue ;; esac
  render "$f" "$OUT/$name/index.html"
  echo "Seite: $name"
done

# --- Atom-Feed ----------------------------------------------------------------
{
  updated=$(head -n 1 "$TMP/sorted" | cut -d "$US" -f1)
  printf '<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n'
  printf '<title>%s</title>\n<link href="%s/"/>\n<link rel="self" href="%s/feed.xml"/>\n' \
    "$(xml_escape "$SITE_TITLE")" "$SITE_URL" "$SITE_URL"
  printf '<id>%s/</id>\n<updated>%sT00:00:00Z</updated>\n<author><name>%s</name></author>\n' \
    "$SITE_URL" "${updated:-$(date +%Y-%m-%d)}" "$(xml_escape "$SITE_AUTHOR")"
  while IFS=$US read -r date slug title tags desc; do
    printf '<entry>\n<title>%s</title>\n<link href="%s/blog/%s/"/>\n<id>%s/blog/%s/</id>\n' \
      "$(xml_escape "$title")" "$SITE_URL" "$slug" "$SITE_URL" "$slug"
    printf '<updated>%sT00:00:00Z</updated>\n<summary>%s</summary>\n</entry>\n' "$date" "$(xml_escape "$desc")"
  done < "$TMP/sorted"
  printf '</feed>\n'
} > "$OUT/feed.xml"

echo "Fertig. Veröffentlichte Posts: $(wc -l < "$TMP/sorted" | tr -d ' '), Ausgabe in $OUT/"
