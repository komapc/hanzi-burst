"""Пул японских фраз для режима 日 (кнопки «Новая фраза» и «Случайная»): site/pool-ja.json.

Берём японский Tatoeba и оставляем простые целые предложения:
  - только кана, кандзи из списка дзёё (в KANJIDIC2 есть школьный класс) и знаки 。、！？「」;
  - длина 5..22 знака; без латиницы и цифр; без частых имён корпуса (トム, メアリー…) и тяжёлых тем;
  - есть английский перевод (русский желателен: с ним фраза в приоритете).
Уровень lv = максимальный школьный класс кандзи (1–6, 7 = средняя школа; 0 — одна кана).
Разбор на слова и чтения делает клиент (site/ja.js) при показе фразы.

Источники: data/raw/tatoeba/jpn_sentences, jpn-eng_links, jpn-rus_links, eng/rus_sentences (CC BY 2.0 FR),
           data/raw/kanjidic/kanjidic2.xml.gz (EDRDG, CC BY-SA 4.0).
Запуск: python3 -I scripts/build_ja_pool.py   (результат коммитится, как site/pool.json)
"""
import gzip
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_phrases import read_tsv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site/pool-ja.json"
KANA = "぀-ゟ゠-ヿ"
PUNCT = "。、！？「」"
NAMES = re.compile("トム|メアリー|メアリ|ジョン|ボブ|ナンシー|ジム|ベス|ジェーン|ジャック|マイク|ケン|ビル|ルーシー|ベティ|アリス|マリア|"
                   "ポール|ジュディ|フレッド|ディック|クリス|リサ|ピーター|サム|ジョージ|ヘレン|ベン|スミス|ブラウン|ホワイト")
BLOCK = re.compile("殺|死|自殺|麻薬|強姦|セックス|売春|爆弾|銃|血|戦争|性的")
QUOTA = {0: 60, 1: 400, 2: 400, 3: 400, 4: 400, 5: 350, 6: 350, 7: 400}


def grades():
    root = ET.parse(gzip.open(ROOT / "data/raw/kanjidic/kanjidic2.xml.gz")).getroot()
    out = {}
    for ch in root.iter("character"):
        g = ch.find("misc").findtext("grade")
        if g and int(g) <= 8:                      # 1–6 начальная школа, 8 — остальные дзёё (9, 10 — имена)
            out[ch.findtext("literal")] = min(int(g), 7)
    return out


def main():
    gr = grades()
    allowed = re.compile(f"^[{KANA}{''.join(gr)}{PUNCT}]+$")
    jpn = {i: t.strip() for i, _, t in read_tsv("jpn_sentences.tsv.bz2")}
    links = {"eng": {}, "rus": {}}
    for l in links:
        for a, b in read_tsv(f"jpn-{l}_links.tsv.bz2"):
            links[l].setdefault(a, []).append(b)
    need = {l: {b for v in links[l].values() for b in v} for l in links}
    text = {l: {i: t for i, _, t in read_tsv(f"{l}_sentences.tsv.bz2") if i in need[l]} for l in links}

    seen, cands = set(), []
    for i, s in jpn.items():
        body = re.sub(f"[{PUNCT}]", "", s)
        if not allowed.match(s) or not 5 <= len(body) <= 22 or NAMES.search(s) or BLOCK.search(s) or body in seen:
            continue
        if s[-1] not in "。！？" or s.count("「") != s.count("」") or re.search("っ[。！？]", s):   # みじけっ。 — сленг
            continue
        tr = {l: min((text[l][b] for b in links[l].get(i, []) if b in text[l]), key=len, default=None) for l in links}
        if not tr["eng"]:
            continue
        seen.add(body)
        lv = max((gr[c] for c in body if c in gr), default=0)
        cands.append({"ja": s, "en": tr["eng"], **({"ru": tr["rus"]} if tr["rus"] else {}), "lv": lv})

    pool = []
    for lv, n in QUOTA.items():
        c = [p for p in cands if p["lv"] == lv]
        c.sort(key=lambda p: ("ru" not in p, abs(len(p["ja"]) - 11), p["ja"]))   # с русским, длина около 11
        pool += c[:n]
    OUT.write_text(json.dumps(pool, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"pool-ja: {len(pool)} of {len(cands)} candidates, {sum('ru' in p for p in pool)} with ru, "
          f"{OUT.stat().st_size / 1e3:.0f} KB; by level " + " ".join(f"{lv}:{sum(p['lv'] == lv for p in pool)}" for lv in QUOTA))


if __name__ == "__main__":
    main()
