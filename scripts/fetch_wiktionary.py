#!/usr/bin/env python3
"""Добавляет в пул фразы-примеры из Wiktionary (kaikki.org, CC BY-SA).

Берёт только короткие предложения (4–16 знаков), целиком состоящие из иероглифов,
которые уже есть в site/phrase.json (chars), с английским переводом.
Русский перевод берётся из data/translations/wiktionary_ru.json {zh: ru}, если он есть.

  python3 -I scripts/fetch_wiktionary.py --candidates out.json   # только список кандидатов [{zh,en}]
  python3 -I scripts/fetch_wiktionary.py                         # дописать в data/pool.json

Сырые данные: data/raw/kaikki/zh_examples.jsonl (потоковая выжимка из
kaikki.org/dictionary/Chinese/kaikki.org-dictionary-Chinese.jsonl).
"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAN = re.compile(r'^[一-鿿，。？！、；：“”]+$')
IS_HAN = lambda c: '一' <= c <= '鿿'


def candidates():
    core = set(json.load(open(ROOT / "site/phrase.json", encoding="utf-8"))["chars"])
    have = {p["zh"] for p in json.load(open(ROOT / "data/phrases.json", encoding="utf-8"))}
    have |= {p["zh"] for p in json.load(open(ROOT / "data/pool.json", encoding="utf-8"))}
    seen, out = set(), []
    for l in open(ROOT / "data/raw/kaikki/zh_examples.jsonl", encoding="utf-8"):
        r = json.loads(l)
        zh, en = r["text"].strip(), (r["en"] or "").strip()
        if not en or zh in seen or zh in have or not (4 <= len(zh) <= 16) or not HAN.match(zh):
            continue
        if not all(c in core for c in zh if IS_HAN(c)):
            continue
        if not (zh[-1] in "。？！" or len(zh) >= 6):
            continue
        seen.add(zh)
        out.append({"zh": zh, "en": en})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates")
    a = ap.parse_args()
    cand = candidates()
    if a.candidates:
        json.dump(cand, open(a.candidates, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("candidates", len(cand))
        return
    tr_path = ROOT / "data/translations/wiktionary_ru.json"
    tr = json.load(open(tr_path, encoding="utf-8")) if tr_path.exists() else {}
    pool_path = ROOT / "data/pool.json"
    pool = json.load(open(pool_path, encoding="utf-8"))
    add = [{"zh": c["zh"], "ru": tr.get(c["zh"]), "en": c["en"], "source": "wiktionary"} for c in cand]
    json.dump(pool + add, open(pool_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("pool", len(pool), "->", len(pool) + len(add), "(без ru:", sum(1 for x in add if not x["ru"]), ")")


if __name__ == "__main__":
    main()
