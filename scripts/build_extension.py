#!/usr/bin/env python3
"""Build the browser extension: copy lookup data from site/data, make icons, zip.

Usage: python3 scripts/build_extension.py [--zip]
  --zip  site/hanzi-burst-extension.zip (Chrome) and site/hanzi-burst-firefox.zip (Firefox: background
         scripts instead of a service worker, gecko id); data and code are the same.
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
    shutil.copytree(SITE / "data" / "ja", data / "ja")       # Japanese: JMdict words for site/ja.js
    shutil.copy(SITE / "ja.js", EXT / "ja.js")
    for f in (SITE / "data" / "kanji").glob("*.json"):       # kanji readings and meanings, without stroke paths
        d = {c: {k: v for k, v in e.items() if k != "p"} for c, e in json.loads(f.read_text(encoding="utf-8")).items() if "on" in e or "kun" in e}
        if d:
            (data / "kanji").mkdir(exist_ok=True)
            (data / "kanji" / f.name).write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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
        manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
        firefox = {**manifest, "background": {"scripts": ["common.js", "ja.js", "background.js"]},
                   "browser_specific_settings": {"gecko": {"id": "hanzi-burst@lipu.dev", "strict_min_version": "121.0",
                                                         "data_collection_permissions": {"required": ["none"]}}}}   # nothing leaves the browser
        # served from hanzi.lipu.dev/hanzi-burst-extension.zip and /hanzi-burst-firefox.zip
        for name, mf in (("hanzi-burst-extension.zip", manifest), ("hanzi-burst-firefox.zip", firefox)):
            out = SITE / name
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for f in sorted(EXT.rglob("*")):
                    if f.is_file() and f.name != "manifest.json":
                        z.write(f, f.relative_to(EXT))
                z.writestr("manifest.json", json.dumps(mf, ensure_ascii=False, indent=2))
            print(f"{out.name}: {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
