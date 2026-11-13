#!/bin/sh
# Full site build (needs data/raw/ and Pillow): text-input shards (Chinese and Japanese), kanji for the Japanese
# mode, /c/ /p/ pages and sitemap.xml, the extension zip, then minify.py (in CI only).
set -e
python3 -I scripts/build_shards.py
python3 -I scripts/build_ja_shards.py
python3 -I scripts/build_kanji_shards.py
python3 -I scripts/build_static.py
python3 -I scripts/build_extension.py --zip
python3 -I scripts/minify.py
