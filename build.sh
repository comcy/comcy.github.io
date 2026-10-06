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

# Timeline-Eintrag (liest Felder aus $date $end $kind $slug $title $desc): Beitrag mit Link, Bookmark ohne Seite
timeline_item() {
  case $kind in
    page) printf '<li class="tl-item"><time datetime="%s">%s</time> <a href="%s/%s/">%s</a></li>\n' \
            "$date" "$date" "$BASE" "$slug" "$(xml_escape "$title")" ;;
    post) printf '<li class="tl-item"><time datetime="%s">%s</time> <a href="%s/blog/%s/">%s</a></li>\n' \
            "$date" "$date" "$BASE" "$slug" "$(xml_escape "$title")" ;;
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
  check_date "$(printf '%s' "$meta" | cut -f1)" "$f"
  draft=$(printf '%s' "$meta" | cut -f3)
  if [ "$draft" = draft ] && [ "${DRAFTS:-0}" != 1 ]; then
    echo "Entwurf übersprungen: $f"
    continue
  fi
  printf '%s\t%s\n' "$slug" "$meta" |
    awk -F'\t' -v OFS="$US" '{print $2, $1, $3, $5, $6}' >> "$TMP/index"
  render "$f" "$OUT/blog/$slug/index.html" -M post=true -M pagetitle="$(printf '%s' "$meta" | cut -f2)"
  # Bilder und andere Dateien neben dem Post: posts/<dateiname>/ wird mitkopiert
  [ -d "${f%.md}" ] && cp -R "${f%.md}/." "$OUT/blog/$slug/"
  echo "Post: $slug"
done
LC_ALL=C sort -r "$TMP/index" > "$TMP/sorted"

# --- Timeline-Index: Beiträge und Bookmarks (key, datum, ende, art, slug, titel, beschreibung) ----------
: > "$TMP/tl"
while IFS=$US read -r date slug title tags desc; do
  printf '%s\037%s\037\037post\037%s\037%s\037%s\n' "$date" "$date" "$slug" "$title" "$desc" >> "$TMP/tl"
done < "$TMP/sorted"
# Seiten mit date: (außer Startseite und Galerie) und Bookmarks aus timeline/; Entwürfe wie im Blog
for f in pages/*.md timeline/*.md; do
  [ -e "$f" ] || continue
  slug=$(basename "$f" .md); kind=bookmark
  case $f in pages/*) kind=page; case $slug in index|gallery) continue ;; esac ;; esac
  meta=$(pandoc "$f" --to plain --wrap=none --template templates/timeline-meta.txt)
  date=$(printf '%s' "$meta" | cut -f1); end=$(printf '%s' "$meta" | cut -f2)
  title=$(printf '%s' "$meta" | cut -f3); desc=$(printf '%s' "$meta" | cut -f4)
  [ "$kind" = page ] && [ -z "$date" ] && continue
  [ "$(printf '%s' "$meta" | cut -f5)" = draft ] && [ "${DRAFTS:-0}" != 1 ] && continue
  check_date "$date" "$f"
  [ -n "$title" ] || { echo "Titel fehlt in $f" >&2; exit 1; }
  if [ -n "$end" ] && [ "$end" != now ]; then
    check_date "$end" "$f"
    # ponytail: die drei Formate sind Präfixe voneinander, daher genügt der Zeichenvergleich (fehlender Teil = Anfang)
    awk -v a="$end" -v b="$date" 'BEGIN { exit !(a < b) }' && { echo "Ende vor Start in $f" >&2; exit 1; }
  fi
  printf '%s\037%s\037%s\037%s\037%s\037%s\037%s\n' "$date" "$date" "$end" "$kind" "$slug" "$title" "$desc" >> "$TMP/tl"
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
    head -n 8 "$TMP/tl.sorted" | while IFS=$US read -r key date end kind slug title desc; do timeline_item; done
    printf '</ol>\n</div>\n</aside>\n```\n'
  fi
} > "$TMP/home.md"
render "$TMP/home.md" "$OUT/index.html" -M home=true -M pagetitle=Start --metadata description="$SITE_DESCRIPTION"

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
