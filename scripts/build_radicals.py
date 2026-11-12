#!/usr/bin/env python3
"""Собирает data/radicals.json — 214 ключей Канси (запускается вручную, результат коммитится).

Источники: data/raw/unicode/CJKRadicals.txt (номер → знак), Unihan kRSUnicode (ключ каждого знака),
Make Me a Hanzi (пиньинь, число черт), data/raw/hsk/complete.json (уровни и частота), scripts/radical_names.py (названия, варианты).

Поля записи: n, char, variants, strokes, pinyin, en, ru, eo, hsk (сколько знаков HSK с этим ключом), top (частый),
examples (до 12 знаков HSK с этим ключом: сначала по уровню, затем по частоте).
Частые («top») — первые TOP ключей по числу знаков HSK; на сайте, в игре и в PDF они идут первыми.
"""
import json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import breakdown
from radical_names import NAMES, PINYIN

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "radicals.json"
TOP, EXAMPLES = 60, 12


def main():
    num2char, char2num = breakdown.load_radical_maps()
    mmh = {}
    for line in open(breakdown.MMH, encoding="utf-8"):
        d = json.loads(line)
        mmh[d["character"]] = d
    strokes = {}
    for line in open(breakdown.GRAPHICS, encoding="utf-8"):
        d = json.loads(line)
        strokes[d["character"]] = len(d["strokes"])

    # уровень и частота знака: одиночная запись HSK, иначе минимальный уровень слов с этим знаком
    level, rank = {}, {}
    for e in json.load(open(ROOT / "data/raw/hsk/complete.json", encoding="utf-8")):
        lv = [int(t.split("-")[1]) for t in e.get("level", []) if t.startswith("new-")] or \
             [int(t.split("-")[1]) for t in e.get("level", []) if t.startswith("old-")]
        if not lv:
            continue
        w = e["simplified"]
        for c in w:
            level[c] = min(level.get(c, 9), min(lv))
        if len(w) == 1:
            rank[w] = min(rank.get(w, 10**9), e.get("frequency") or 10**9)

    by_rad = {}
    for c in level:
        n = char2num.get(c, (None, 0))[0]
        if n:
            by_rad.setdefault(n, []).append(c)
    count = Counter({n: len(cs) for n, cs in by_rad.items()})
    top = {n for n, _ in sorted(count.items(), key=lambda x: (-x[1], x[0]))[:TOP]}

    out = []
    for n in range(1, 215):
        ch = num2char[n]
        en, ru, variants, eo = NAMES[n]
        d = mmh.get(ch, {})
        exs = sorted((c for c in by_rad.get(n, []) if c != ch and c not in variants),
                     key=lambda c: (level[c], rank.get(c, 10**9), c))[:EXAMPLES]
        out.append({"n": n, "char": ch, "variants": list(variants), "strokes": strokes.get(ch) or 0,
                    "pinyin": PINYIN.get(n) or (d.get("pinyin") or [""])[0], "en": en, "ru": ru, "eo": eo,
                    "hsk": count.get(n, 0), "top": n in top, "examples": exs})
    OUT.write_text("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n]\n", encoding="utf-8")
    missing = [r["char"] for r in out if not r["strokes"] or not r["pinyin"]]
    print(f"radicals: {len(out)}, top={len(top)}, no strokes/pinyin: {''.join(missing) or '-'}")


if __name__ == "__main__":
    main()
