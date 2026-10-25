"""Шарды кандзи для японского режима: чтения, значения, разбор на части и черты.

site/data/kanji/<key>.json — {знак: {...}}, key = кодпоинт >> 8 (как у китайских шардов).
  on, kun   — онные (катакана) и кунные чтения (хирагана, «.» отделяет окуригану, «-» — аффикс)
  en        — значения KANJIDIC2 (английские)
  ru        — глосса JMdict для однознакового слова (это значение слова, а не знака; может отсутствовать)
  g, j, f, sc — школьный класс (1–6, 8 = средняя школа), старый уровень JLPT (4..1), ранг частоты, число черт
  p         — черты KanjiVG (координаты 109×109, обводка, не заливка)
  components, orig — части первого уровня по группам KanjiVG (kvg:element) и их исходные знаки (亻 → 人)
Кана KanjiVG тоже попадает в шарды (только черты), чтобы кана и кандзи рисовались одним стилем.

Источники: data/raw/kanjidic/kanjidic2.xml.gz (EDRDG, CC BY-SA 4.0),
           data/raw/kanjivg/kanjivg-*.xml.gz (KanjiVG, Ulrich Apel, CC BY-SA 3.0),
           data/raw/jmdict/jmdict-rus-*.json (JMdict, EDRDG, CC BY-SA 4.0).
Запуск: python3 -I scripts/build_kanji_shards.py
"""
import gzip
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_ja_shards import clean_ru  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
OUT = ROOT / "site/data/kanji"
KVG = "{http://kanjivg.tagaini.net}"
JP = re.compile(r"[぀-ヿ㐀-鿿]")


def need(path, what):
    if not path:
        sys.exit(f"нет {what}: обновите снимок raw-data (README, «Обновление снимка»)")
    return path


def kanjidic():
    path = need(next((RAW / "kanjidic").glob("kanjidic2.xml.gz"), None), "data/raw/kanjidic/kanjidic2.xml.gz")
    out = {}
    for ch in ET.parse(gzip.open(path)).getroot().iter("character"):
        lit = ch.findtext("literal")
        misc = ch.find("misc")
        e = {"on": [], "kun": [], "en": []}
        for r in ch.iter("reading"):
            if r.get("r_type") == "ja_on":
                e["on"].append(r.text)
            elif r.get("r_type") == "ja_kun":
                e["kun"].append(r.text)
        e["en"] = [m.text for m in ch.iter("meaning") if not m.get("m_lang")][:5]
        for tag, key in (("grade", "g"), ("jlpt", "j"), ("freq", "f"), ("stroke_count", "sc")):
            v = misc.findtext(tag)
            if v:
                e[key] = int(v)
        out[lit] = {k: v for k, v in e.items() if v not in ([], None)}
    return out


def parts(g):
    """Части первого уровня: группы с kvg:element; группы без него раскрываем; kvg:part (разорванная часть) — один раз."""
    found = []
    for c in g:
        if c.tag != "g":
            continue
        el = c.get(KVG + "element")
        if el:
            if all(el != x[0] for x in found):
                found.append((el, c.get(KVG + "original") or ""))
        else:
            found += [x for x in parts(c) if all(x[0] != y[0] for y in found)]
    return found


def kanjivg():
    path = need(next((RAW / "kanjivg").glob("kanjivg-*.xml.gz"), None), "data/raw/kanjivg/kanjivg-*.xml.gz")
    out = {}
    for k in ET.parse(gzip.open(path)).getroot().iter("kanji"):
        code = k.get("id").split("_")[1]
        if "-" in code:                      # варианты начертаний (kanji_05208-Kaisho): берём основной
            continue
        ch = chr(int(code, 16))
        top = k.find("g")
        comps = parts(top)
        if len(comps) == 1 and comps[0][0] == ch:   # единственная группа — сам знак
            comps = []
        out[ch] = {"p": [p.get("d").replace("\n", " ") for p in k.iter("path")],
                   "components": [c for c, _ in comps], "orig": [o for _, o in comps]}
    return out


def top_split(t):
    """Делит по «,» и «;» вне скобок: «во время (чего-л., кого-л.)» остаётся целым."""
    out, depth, cur = [], 0, ""
    for c in t:
        depth += (c in "([") - (c in ")]")
        if c in ",;" and depth <= 0:
            out.append(cur); cur = ""
        else:
            cur += c
    return out + [cur]


def ru_glosses(kd):
    """Русское значение знака = значение слова JMdict, которое пишется этим знаком и читается его кун-чтением
    (山 — やま «гора», 来 — 来る くる «приходить»); если такого нет — частое однознаковое слово с он-чтением."""
    path = need(next((RAW / "jmdict").glob("jmdict-rus-*.json"), None), "data/raw/jmdict/jmdict-rus-*.json")
    by_form = {}                                # написание → [(common, {чтения}, глосса)]
    for w in json.loads(path.read_text(encoding="utf-8"))["words"]:
        g = [x["text"] for s in w["sense"][:1] for x in s["gloss"] if x["lang"] == "rus"]
        g = [re.sub(r"^(\([^)]*\)\s*)+", "", y.strip()) for x in g for y in top_split(clean_ru(x))]
        g = [y for y in g if y and not JP.search(y) and not re.match(r"^[\d(]", y)]   # без помет «(неперех.)», «(суф. …»
        if not g:
            continue
        gloss = ", ".join(list(dict.fromkeys(g))[:3])
        for k in w["kanji"]:
            if 1 <= len(k["text"]) <= 4:
                rd = {r["text"] for r in w["kana"] if "*" in r["appliesToKanji"] or k["text"] in r["appliesToKanji"]}
                by_form.setdefault(k["text"], []).append((k["common"], rd, gloss))
    hira = lambda s: "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)
    out = {}
    for ch, e in kd.items():
        cands = []
        for i, kun in enumerate(e.get("kun", [])):
            kun = kun.strip("-")
            stem, _, oku = kun.partition(".")
            cands += [(not c, i, gl) for c, rd, gl in by_form.get(ch + oku, []) if stem + oku in rd]
        if not cands:
            cands = [(not c, 0, gl) for c, rd, gl in by_form.get(ch, []) if c and rd & {hira(o) for o in e.get("on", [])}]
        if cands:
            out[ch] = min(cands, key=lambda x: x[:2])[2]
    return out


def main():
    kd, kv = kanjidic(), kanjivg()
    ru = ru_glosses(kd)
    if OUT.exists():
        shutil.rmtree(OUT)
    data = {}
    for ch in set(kd) | set(kv):
        e = dict(kd.get(ch, {}))
        if ch in kv:
            e["p"] = kv[ch]["p"]
            if kv[ch]["components"]:
                e["components"] = kv[ch]["components"]
                if any(kv[ch]["orig"]):
                    e["orig"] = kv[ch]["orig"]
        if ch in ru:
            e["ru"] = ru[ch]
        if ch in kd and not (e.get("p") or e.get("g") or e.get("f") or e.get("j")):
            continue                        # редкие знаки без черт и без класса/частоты: не нужны
        data[ch] = e
    missing = {c for e in data.values() for c in e.get("components", []) if c not in data}
    shards = {}
    for ch, e in data.items():
        shards.setdefault(format(ord(ch) >> 8, "x"), {})[ch] = e
    OUT.mkdir(parents=True)
    for k, v in shards.items():
        (OUT / f"{k}.json").write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sizes = sorted(((p.stat().st_size, p.name) for p in OUT.iterdir()), reverse=True)
    print(f"kanji: {len(data)} chars ({sum('p' in e for e in data.values())} with strokes, {sum('ru' in e for e in data.values())} ru), "
          f"{len(missing)} parts without own entry; {len(sizes)} shards, {sum(s for s, _ in sizes) / 1e6:.1f} MB; "
          f"largest {sizes[0][1]} {sizes[0][0] / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
