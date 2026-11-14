"""Минификация JS сайта при деплое: встроенный <script> в site/index.html, site/en/index.html и site/*.js (terser через npx).

Правит файлы на месте, поэтому работает только в CI (переменная CI) или с --force и каталогом:
  python3 -I scripts/minify.py                 # в CI: site/
  python3 -I scripts/minify.py --force DIR     # проверить на копии сайта
Если terser недоступен или упал, файл остаётся как был: деплой не ломается.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

TERSER = ["npx", "--yes", "terser@5.36.0", "--compress", "--mangle", "--comments", "false"]


def terse(code):
    try:
        r = subprocess.run(TERSER, input=code, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"minify: terser failed ({e})")
        return None
    if r.returncode or not r.stdout.strip():
        print(f"minify: terser error: {r.stderr[:300]}")
        return None
    return r.stdout


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    if not os.environ.get("CI") and "--force" not in sys.argv:
        print("minify: skipped (not CI; use --force DIR)")
        return
    site = Path(args[0]) if args else Path(__file__).resolve().parent.parent / "site"
    before = after = 0
    for f in [site / "script.js", site / "ja.js", site / "footer.js", site / "nav.js"]:
        src = f.read_text(encoding="utf-8")
        out = terse(src)
        if out:
            f.write_text(out, encoding="utf-8")
            before, after = before + len(src), after + len(out)

    def sub(m):
        nonlocal before, after
        out = terse(m.group(2))
        if not out:
            return m.group(0)
        before, after = before + len(m.group(2)), after + len(out)
        return m.group(1) + out + m.group(3)

    # главная и её английская копия /en/ (build_static.en_home): только исполняемые встроенные скрипты, без src и не JSON-LD
    for page in [site / "index.html", site / "en" / "index.html"]:
        if page.exists():
            page.write_text(re.sub(r"(<script>)(.*?)(</script>)", sub, page.read_text(encoding="utf-8"), flags=re.S), encoding="utf-8")
    print(f"minify: {before} -> {after} bytes")


if __name__ == "__main__":
    main()
