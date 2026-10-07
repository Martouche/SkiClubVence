#!/bin/sh
# Télécharge puis téléverse la galerie complète (liste source/gallery_full.txt).
cd "$(dirname "$0")/.." || exit 1
mkdir -p source/gallery
while read -r u; do
  f=$(echo "$u" | sed 's#.*/uploads/##; s#/#_#g')
  [ -s "source/gallery/$f" ] || curl -sf -A "Mozilla/5.0" -o "source/gallery/$f" "$u" || echo "FAIL $u"
done < source/gallery_full.txt
echo "download done: $(ls source/gallery | wc -l) fichiers"
PYTHONIOENCODING=utf-8 python tools/upload_media.py gallery=gallery_full.txt
