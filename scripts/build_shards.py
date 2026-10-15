"""Шарды данных для анализа вставленного текста (клиент грузит их лениво).

site/data/chars/<hh>.json  — как D.chars (hh = кодпоинт >> 8, hex)
site/data/glyphs/<hh>.json — контуры черт
site/data/words/<hh>.json  — слова CC-CEDICT по первому иероглифу: {слово: [pinyin, en, ru]}
site/data/s2t.json       — упрощённый -> традиционный (самый частый вариант)
site/data/trad.json        — традиционный -> упрощённый (однознаковые записи CEDICT)

Запуск: python3 -I scripts/build_shards.py
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import breakdown as bd

OUT = bd.ROOT / "site/data"
HAN = re.compile(r"[㐀-鿿]")
SKIP = re.compile(r"^(surname|variant of|old variant|archaic variant|abbr\. for|see |erhua variant)", re.I)


def shard(ch):
    return format(ord(ch) >> 8, "x")


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    mmh, words = bd.load_mmh(), bd.load_cedict()
    maps, tr = bd.load_radical_maps(), bd.load_translations()
    bd.ATOMIC.update(bd.compute_atomic(mmh, maps))
    if OUT.exists():
        shutil.rmtree(OUT)

    chars = {}
    for ch in mmh:
        if len(ch) == 1:
            chars.setdefault(shard(ch), {})[ch] = bd.info(ch, mmh, maps, tr)
    for k, v in chars.items():
        dump(OUT / "chars" / f"{k}.json", v)

    glyphs = {}
    with bd.GRAPHICS.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            glyphs.setdefault(shard(d["character"]), {})[d["character"]] = d["strokes"]
    for k, v in glyphs.items():
        dump(OUT / "glyphs" / f"{k}.json", v)

    ws = {}
    for w, entries in words.items():
        if len(w) < 2 or not HAN.match(w[0]):
            continue
        e = next((x for x in entries if not SKIP.match(x["defs"][0])), entries[0])
        defs = [d for d in e["defs"] if not d.startswith("CL:")][:3]
        if not defs:
            continue
        ru = "; ".join(tr.get(d, d) for d in defs)
        en = "; ".join(defs)
        ws.setdefault(shard(w[0]), {})[w] = [e["pinyin"], en] + ([ru] if ru != en else [])
    for k, v in ws.items():
        dump(OUT / "words" / f"{k}.json", v)

    trad = {}
    pat = re.compile(r"^(\S+) (\S+) \[")
    for line in bd.CEDICT.read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if m and len(m.group(1)) == 1 and m.group(1) != m.group(2):
            trad.setdefault(m.group(1), m.group(2))
    dump(OUT / "trad.json", trad)

    # упрощённый -> традиционный: самая частая пара по словам CEDICT одинаковой длины
    from collections import Counter, defaultdict
    cnt = defaultdict(Counter)
    for line in bd.CEDICT.read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if m and len(m.group(1)) == len(m.group(2)):
            for t, sm in zip(m.group(1), m.group(2)):
                cnt[sm][t] += 1   # t == sm тоже голос: знак одинаков в обеих системах
    s2t = {sm: c.most_common(1)[0][0] for sm, c in cnt.items() if c.most_common(1)[0][0] != sm}
    s2t["里"] = "裡"   # 里 как «внутри» (иначе побеждает 里 = ли, мера длины)
    dump(OUT / "s2t.json", s2t)
    n = sum(1 for _ in OUT.rglob("*.json"))
    size = sum(p.stat().st_size for p in OUT.rglob("*.json"))
    print(f"shards={n} bytes={size} trad={len(trad)}")


if __name__ == "__main__":
    main()
