"""Убирает из data/pool.json «не фразы»: именные группы и обрывки (Wiktionary / Common Voice).

Фраза = предложение. Tatoeba оставляем как есть. Остальные оставляем, если
  - перевод не начинается с «to …» / строчной буквы (признак глоссы-словаря), и
  - китайский текст кончается на 。！？ или в английском переводе есть подлежащее/вспомогательный глагол.
Запуск после fetch_*.py: python3 -I scripts/clean_pool.py
"""
import json
import re
from pathlib import Path

POOL = Path(__file__).resolve().parent.parent / "data/pool.json"
V = set("""i you he she we they it me him her us them my your his our their is are was were be been am isn't aren't
wasn't weren't have has had do does did don't doesn't didn't will won't would can can't cannot could should must
may might let please there here what who where when why how this that these those not no""".split())
CONTR = re.compile(r"^(i|you|he|she|we|they|it|that|there|what|who)('m|'re|'s|'ll|'ve|'d)$")
END = re.compile(r"[。！？!?]$")


def is_phrase(x):
    if (x.get("source") or "").startswith("tatoeba"):
        return True
    en = (x.get("en") or "").strip()
    if not en or re.match(r"^to ", en, re.I) or en[:1].islower():
        return False
    if END.search(x["zh"]):
        return True
    toks = re.findall(r"[a-z']+", en.lower())
    return any(t in V or CONTR.match(t) for t in toks)


def main():
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    keep = [x for x in pool if is_phrase(x)]
    POOL.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"pool: {len(pool)} -> {len(keep)}")


if __name__ == "__main__":
    main()
