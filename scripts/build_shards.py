"""Шарды данных для анализа вставленного текста (клиент грузит их лениво).

site/data/chars/<hh>.json  — как D.chars (hh = кодпоинт >> 8, hex)
site/data/g/<hhh>.json    — контуры черт, по 16 знаков (кодпоинт >> 4, hex)
site/data/words/<hh>.json  — слова CC-CEDICT по первому иероглифу: {слово: [pinyin, en, ru]}
site/data/s2t.json       — упрощённый -> традиционный (самый частый вариант)
site/data/trad.json        — традиционный -> упрощённый (однознаковые записи CEDICT)
site/data/pyindex.json     — поиск по пиньиню: слог(+тон) -> знаки
site/data/hsk.json         — знаки по уровням HSK 3.0: {"1": "爱八爸…", …, "7": …}

Запуск: python3 -I scripts/build_shards.py
"""
import json
import unicodedata
from collections import Counter, defaultdict
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import breakdown as bd
import hsk

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

    # поиск по пиньиню: слог с номером тона -> знаки, частые первыми (частота = в скольких словах CEDICT есть знак)
    freq = Counter(c for w in words for c in set(w))
    marks = {"\u0304": "1", "\u0301": "2", "\u030c": "3", "\u0300": "4"}
    trad_only = set()                      # традиционные формы (響 при 响) в выдачу не берём: данные сайта упрощённые
    for line in bd.CEDICT.read_text(encoding="utf-8").splitlines():
        t, sm = (line.split(" ", 2) + ["", ""])[:2]
        if len(t) == len(sm):
            trad_only.update(a for a, b in zip(t, sm) if a != b)
    trad_only -= {c for line in bd.CEDICT.read_text(encoding="utf-8").splitlines() for c in (line.split(" ", 2) + ["", ""])[1]}
    pyidx = defaultdict(list)
    for ch, d in mmh.items():
        if len(ch) != 1 or not HAN.match(ch) or ch in trad_only:
            continue
        for p in d.get("pinyin") or []:
            n = unicodedata.normalize("NFD", p.lower()).replace("u\u0308", "v")
            tone = next((marks[c] for c in n if c in marks), "5")
            base = "".join(c for c in n if c.isascii() and c.isalpha())
            if base and ch not in pyidx[base + tone]:
                pyidx[base + tone].append(ch)
    for k in list(pyidx):                  # без тона: все тоны вместе (xiang -> 想 像 向 相…)
        pyidx.setdefault(k[:-1], []).extend(c for c in pyidx[k] if c not in pyidx[k[:-1]])
    pyidx = {k: "".join(sorted(v, key=lambda c: -freq[c])[:24]) for k, v in pyidx.items()}
    dump(OUT / "pyindex.json", pyidx)

    # знаки по уровням HSK 3.0: уровень знака = самый низкий уровень слова, где он встречается (1–6, 7 = 7–9);
    # так выходит почти ровно официальный список знаков (по 300 на уровни 1–5). Частые первыми.
    clv = {}
    for w, lv in hsk.load_levels().items():
        for c in w:
            if HAN.match(c):
                clv[c] = min(clv.get(c, 9), lv)
    dump(OUT / "hsk.json", {str(lv): "".join(sorted((c for c, l in clv.items() if l == lv), key=lambda c: -freq[c])) for lv in range(1, 8)})

    # контуры мелкими шардами по 16 знаков (кодпоинт >> 4): страница грузит только то, что показывает (~7 КБ на шард)
    glyphs = {}
    with bd.GRAPHICS.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            glyphs.setdefault(format(ord(d["character"]) >> 4, "x"), {})[d["character"]] = d["strokes"]
    for k, v in glyphs.items():
        dump(OUT / "g" / f"{k}.json", v)

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
