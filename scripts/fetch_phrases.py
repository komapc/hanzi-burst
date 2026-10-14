"""Подбор новых фраз из Tatoeba для data/phrases.json.

Фразы выбираются как учебная программа: каждая следующая вводит мало новых иероглифов
(относительно уже имеющихся фраз) и переиспользует знакомые, поэтому «этот радикал/иероглиф уже был» работает.

Использование:
  python3 -I scripts/fetch_phrases.py [--count 40] [--max-new 2] [--top 900] [--min-len 3] [--max-len 10] [--dry-run]

Сырые данные: data/raw/tatoeba/ (экспорты per_language с downloads.tatoeba.org), CC BY 2.0 FR.
После добавления: python3 -I scripts/breakdown.py data/phrases.json site/phrase.json
"""
import argparse
import bz2
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/tatoeba"
PHRASES = ROOT / "data/phrases.json"
CEDICT = ROOT / "data/raw/cedict/cedict_ts.u8"
MMH = ROOT / "data/raw/mmh/dictionary.txt"
HAN = re.compile(r"[一-鿿]")
ALLOWED = re.compile(r"^[一-鿿，。！？、]+$")


def read_tsv(name):
    with bz2.open(RAW / name, "rt", encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\n").split("\t")


def traditional_only_chars():
    """Иероглифы, которые встречаются только как традиционные формы (есть упрощённый аналог)."""
    out = set()
    for line in CEDICT.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        parts = line.split(" ", 2)
        if len(parts) < 3 or len(parts[0]) != len(parts[1]):
            continue
        trad, simp = parts[0], parts[1]
        for t, s in zip(trad, simp):
            if t != s:
                out.add(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--max-new", type=int, default=2, help="максимум новых иероглифов во фразе")
    ap.add_argument("--top", type=int, default=900, help="брать иероглифы из топ-N по частоте в корпусе")
    ap.add_argument("--min-len", type=int, default=3)
    ap.add_argument("--max-len", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    existing = json.loads(PHRASES.read_text(encoding="utf-8"))
    norm = lambda t: "".join(c for c in t if HAN.match(c))
    have_text = {norm(p["zh"]) for p in existing}
    have_sets = {frozenset(norm(p["zh"])) for p in existing}   # «我想你» и «我很想你。» считаем разными, «今天是我生日» дублем «今天是我的生日» нет
    known = {c for p in existing for c in p["zh"] if HAN.match(c)}

    mmh_chars = {json.loads(l)["character"] for l in MMH.read_text(encoding="utf-8").splitlines()}
    trad = traditional_only_chars()

    cmn = {i: t for i, lang, t in read_tsv("cmn_sentences.tsv.bz2")}
    freq = Counter(c for t in cmn.values() for c in t if HAN.match(c) and c not in trad)
    allowed = {c for c, _ in freq.most_common(a.top)}

    links_eng, links_rus = {}, {}
    for cid, tid in read_tsv("cmn-eng_links.tsv.bz2"):
        links_eng.setdefault(cid, []).append(tid)
    for cid, tid in read_tsv("cmn-rus_links.tsv.bz2"):
        links_rus.setdefault(cid, []).append(tid)
    need_eng = {t for v in links_eng.values() for t in v}
    need_rus = {t for v in links_rus.values() for t in v}
    eng = {i: t for i, lang, t in read_tsv("eng_sentences.tsv.bz2") if i in need_eng}
    rus = {i: t for i, lang, t in read_tsv("rus_sentences.tsv.bz2") if i in need_rus}

    def shortest(ids, table):
        c = [table[i] for i in ids if i in table]
        return min(c, key=len) if c else None

    cands = []
    for cid, text in cmn.items():
        if not ALLOWED.match(text) or norm(text) in have_text or frozenset(norm(text)) in have_sets:
            continue
        han = [c for c in text if HAN.match(c)]
        if not (a.min_len <= len(han) <= a.max_len):
            continue
        if any(c in trad or c not in mmh_chars or c not in allowed for c in han):
            continue
        ru, en = shortest(links_rus.get(cid, []), rus), shortest(links_eng.get(cid, []), eng)
        if not ru or not en:   # нужны оба перевода: ручной перевод не требуется
            continue
        cands.append({"id": cid, "zh": text, "ru": ru, "en": en, "han": set(han)})

    picked = []
    for _ in range(a.count):
        best, best_key = None, None
        for c in cands:
            new = c["han"] - known
            if len(new) > a.max_new:
                continue
            reuse = len(c["han"] & known)
            # меньше новых, больше знакомых, чуть длиннее лучше
            key = (len(new), -reuse, -len(c["zh"]))
            if best_key is None or key < best_key:
                best, best_key = c, key
        if not best:
            break
        picked.append(best)
        known |= best["han"]
        have_sets.add(frozenset(best["han"]))
        cands = [c for c in cands if c is not best and frozenset(c["han"]) not in have_sets]

    print(f"кандидатов после фильтров: {len(cands) + len(picked)}, выбрано: {len(picked)}")
    for p in picked:
        print(f"  {p['zh']}  |  {p['ru']}  |  {p['en']}")
    if a.dry_run:
        return
    for p in picked:
        existing.append({"zh": p["zh"], "ru": p["ru"], "en": p["en"], "source": f"tatoeba #{p['id']}"})
    PHRASES.write_text(json.dumps(existing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"всего фраз: {len(existing)}")


main()
