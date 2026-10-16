"""Пополняет data/pool.json фразами из Tatoeba с оценкой сложности по HSK.

Берём весь китайский Tatoeba (≈89 тыс. предложений), оставляем простые целые предложения:
  - только иероглифы и знаки 。，！？、; длина 4..16 иероглифов;
  - все знаки есть в Make Me a Hanzi, не «чисто традиционные», входят в топ-N по частоте корпуса;
  - есть английский перевод (русский желателен: с ним фраза в приоритете).
Каждой фразе ставим hsk = максимальный уровень слов (см. hsk.py). Отбираем по квотам на уровень,
внутри уровня: есть ru, длина 6..12, частотные знаки. Старые записи Tatoeba в пуле заменяются,
Wiktionary / Common Voice остаются. Курируемые фразы (data/phrases.json) пропускаем как дубли.

  python3 -I scripts/build_tatoeba_pool.py [--top 1300] [--dry-run]
После: python3 -I scripts/clean_pool.py && python3 -I scripts/breakdown.py data/phrases.json site/phrase.json data/pool.json
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import hsk  # noqa: E402
from breakdown import load_cedict, segment  # noqa: E402
from fetch_phrases import HAN, ALLOWED, MMH, read_tsv, traditional_only_chars  # noqa: E402

POOL = ROOT / "data/pool.json"
PHRASES = ROOT / "data/phrases.json"
# тяжёлые темы для учебной ленты: самоубийство, насилие, секс, наркотики
BLOCK = re.compile("自杀|杀|强奸|性交|妓|毒品|吸毒|死刑|尸|血腥|恐怖分子")
QUOTA = {1: 300, 2: 400, 3: 500, 4: 500, 5: 450, 6: 400, 7: 450}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=1300)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    norm = lambda t: "".join(c for c in t if HAN.match(c))
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    keep = [x for x in pool if not (x.get("source") or "").startswith("tatoeba")]
    have = {norm(p["zh"]) for p in json.loads(PHRASES.read_text(encoding="utf-8"))} | {norm(p["zh"]) for p in keep}
    have_sets = {frozenset(t) for t in have}

    levels = hsk.load_levels()
    words = load_cedict()
    mmh_chars = {json.loads(l)["character"] for l in MMH.read_text(encoding="utf-8").splitlines()}
    trad = traditional_only_chars()

    cmn = {i: t for i, lang, t in read_tsv("cmn_sentences.tsv.bz2")}
    freq = Counter(c for t in cmn.values() for c in t if HAN.match(c) and c not in trad)
    rank = {c: i for i, (c, _) in enumerate(freq.most_common())}
    allowed = {c for c, r in rank.items() if r < a.top}

    links_eng, links_rus = {}, {}
    for cid, tid in read_tsv("cmn-eng_links.tsv.bz2"):
        links_eng.setdefault(cid, []).append(tid)
    for cid, tid in read_tsv("cmn-rus_links.tsv.bz2"):
        links_rus.setdefault(cid, []).append(tid)
    need_e = {t for v in links_eng.values() for t in v}
    need_r = {t for v in links_rus.values() for t in v}
    eng = {i: t for i, lang, t in read_tsv("eng_sentences.tsv.bz2") if i in need_e}
    rus = {i: t for i, lang, t in read_tsv("rus_sentences.tsv.bz2") if i in need_r}
    shortest = lambda ids, tab: min((tab[i] for i in ids if i in tab), key=len, default=None)

    by_level = {n: [] for n in QUOTA}
    for cid, text in cmn.items():
        if not ALLOWED.match(text) or BLOCK.search(text):
            continue
        han = [c for c in text if HAN.match(c)]
        if not 4 <= len(han) <= 16 or any(c in trad or c not in mmh_chars or c not in allowed for c in han):
            continue
        key = norm(text)
        if key in have or frozenset(key) in have_sets:
            continue
        en = shortest(links_eng.get(cid, []), eng)
        if not en:
            continue
        ru = shortest(links_rus.get(cid, []), rus)
        ws = [w for w in segment(text, words) if HAN.match(w[0])]
        lv = hsk.sentence_level(ws, levels)
        avg_rank = sum(rank[c] for c in han) / len(han)
        ideal = abs(len(han) - 9)
        by_level[lv].append(((0 if ru else 1), ideal, avg_rank, cid, text, ru, en, key))

    picked = []
    for lv, items in by_level.items():
        items.sort()
        n = 0
        for _, _, _, cid, text, ru, en, key in items:
            if n >= QUOTA[lv]:
                break
            fs = frozenset(key)
            if key in have or fs in have_sets:
                continue
            have.add(key); have_sets.add(fs); n += 1
            picked.append({"zh": text, "ru": ru or None, "en": en, "source": f"tatoeba #{cid}"})
        print(f"HSK {lv}: кандидатов {len(items)}, взято {n}, с ru {sum(1 for p in picked[-n:] if p['ru']) if n else 0}")
    print(f"Tatoeba: {len(picked)}; остальные в пуле: {len(keep)}")
    if a.dry_run:
        for p in picked[::150]:
            print(" ", p["zh"], "|", p["ru"], "|", p["en"])
        return
    for p in picked:
        if not p["ru"]:
            del p["ru"]
    POOL.write_text(json.dumps(keep + picked, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"записано {len(keep) + len(picked)}")


if __name__ == "__main__":
    main()
