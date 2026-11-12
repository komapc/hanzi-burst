#!/usr/bin/env python3
"""Версия плаката «214 ключей»: site/radicals-poster.json — что лежит в site/radicals-poster-{ru,en,eo}.pdf.

  version  — дата сборки и короткий хеш входов, напечатан в подвале плаката (v2026.11.12 · 1a2b3c4)
  inputs   — sha256 входов: data/radicals.json + скрипт плаката + palladius.py (MMH и шрифты не учитываются)
  files    — размер и sha256 каждого PDF

Пишет radicals_poster.py после сборки. Проверка (CI): python3 scripts/poster_version.py --check —
падает, если входы изменились, а плакат не пересобран, или PDF не совпадает с манифестом.
Задеплоенная версия: https://hanzi.lipu.dev/radicals-poster.json
"""
import datetime, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "site" / "radicals-poster.json"
INPUTS = ["data/radicals.json", "scripts/radicals_poster.py", "scripts/palladius.py"]
LANGS = ("ru", "en", "eo")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inputs_hash():
    h = hashlib.sha256()
    for f in INPUTS:
        h.update(f.encode() + b"\0" + (ROOT / f).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def new_version():
    return f"{datetime.date.today():%Y.%m.%d}-{inputs_hash()[:7]}"


def write(version):
    files = {l: {"bytes": (p := ROOT / "site" / f"radicals-poster-{l}.pdf").stat().st_size, "sha256": sha(p)} for l in LANGS}
    MANIFEST.write_text(json.dumps({"version": version, "inputs": inputs_hash(), "files": files}, indent=1) + "\n", encoding="utf-8")


def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None


def check():
    m, bad = load(), []
    if not m:
        sys.exit(f"{MANIFEST.relative_to(ROOT)} missing: run scripts/radicals_poster.py")
    if m["inputs"] != inputs_hash():
        bad.append("poster inputs changed since the last build (" + ", ".join(INPUTS) + "): run scripts/radicals_poster.py")
    for l in LANGS:
        if sha(ROOT / "site" / f"radicals-poster-{l}.pdf") != m["files"][l]["sha256"]:
            bad.append(f"radicals-poster-{l}.pdf differs from the manifest")
    print("\n".join(bad) or f"poster {m['version']} is up to date")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    check() if "--check" in sys.argv else print(load())
