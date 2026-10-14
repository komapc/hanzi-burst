#!/usr/bin/env python3
"""Добавляет в пул предложения из Mozilla Common Voice (zh-CN, список предложений, CC0).

Берёт короткие предложения (4–16 знаков), целиком из иероглифов, уже имеющихся в site/phrase.json.
Переводов в источнике нет: ru/en — машинные, из data/translations/commonvoice.json {zh: {ru, en}}.
Сырые данные: data/raw/commonvoice/{cn,sentence-collector}.txt
  (github.com/common-voice/common-voice/server/data/zh-CN).

  python3 -I scripts/fetch_commonvoice.py --candidates out.json   # [{zh}] без перевода
  python3 -I scripts/fetch_commonvoice.py                         # дописать переведённые в data/pool.json
"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAN = re.compile(r'^[一-鿿，。？！、；：]+$')
IS_HAN = lambda c: '一' <= c <= '鿿'


def candidates():
    core = set(json.load(open(ROOT / "site/phrase.json", encoding="utf-8"))["chars"])
    have = {p["zh"] for p in json.load(open(ROOT / "data/phrases.json", encoding="utf-8"))}
    have |= {p["zh"] for p in json.load(open(ROOT / "data/pool.json", encoding="utf-8"))}
    out, seen = [], set()
    for f in ("cn.txt", "sentence-collector.txt"):
        for l in open(ROOT / "data/raw/commonvoice" / f, encoding="utf-8"):
            zh = l.strip()
            if zh in seen or zh in have or not (4 <= len(zh) <= 16) or not HAN.match(zh):
                continue
            if all(c in core for c in zh if IS_HAN(c)):
                seen.add(zh); out.append({"zh": zh})
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--candidates")
    a = ap.parse_args()
    cand = candidates()
    if a.candidates:
        json.dump(cand, open(a.candidates, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("candidates", len(cand)); return
    tr = json.load(open(ROOT / "data/translations/commonvoice.json", encoding="utf-8"))
    pool_path = ROOT / "data/pool.json"
    pool = json.load(open(pool_path, encoding="utf-8"))
    add = [{"zh": c["zh"], "ru": tr[c["zh"]]["ru"], "en": tr[c["zh"]]["en"], "source": "commonvoice", "mt": True}
           for c in cand if c["zh"] in tr]
    json.dump(pool + add, open(pool_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("pool", len(pool), "->", len(pool) + len(add))


if __name__ == "__main__":
    main()
