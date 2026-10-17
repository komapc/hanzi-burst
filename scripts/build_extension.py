#!/usr/bin/env python3
"""Build the Chrome extension: copy lookup data from site/data, make icons, zip.

Usage: python3 scripts/build_extension.py [--zip]
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SITE, EXT = ROOT / "site", ROOT / "extension"


def main():
    data = EXT / "data"
    if data.exists():
        shutil.rmtree(data)
    for kind in ("chars", "words"):          # glyphs (stroke SVG, 24 MB) are not needed for text cards
        shutil.copytree(SITE / "data" / kind, data / kind)
    shutil.copy(SITE / "data" / "trad.json", data / "trad.json")
    core = json.loads((SITE / "phrase.json").read_text(encoding="utf-8"))["chars"]   # the same core set the site offers
    (data / "core.json").write_text(json.dumps(sorted(core), ensure_ascii=False), encoding="utf-8")
    icons = EXT / "icons"
    icons.mkdir(exist_ok=True)
    src = Image.open(SITE / "apple-touch-icon.png").convert("RGBA")
    for s in (16, 48, 128):
        src.resize((s, s), Image.LANCZOS).save(icons / f"{s}.png")
    size = sum(f.stat().st_size for f in data.rglob("*.json")) / 1e6
    print(f"data copied: {size:.1f} MB")
    if "--zip" in sys.argv:
        out = ROOT / "hanzi-burst-extension.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(EXT.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(EXT))
        print(f"{out.name}: {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
