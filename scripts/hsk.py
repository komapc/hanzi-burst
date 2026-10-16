"""Уровни HSK для слов: data/raw/hsk/complete.json (drkameleon/complete-hsk-vocabulary, MIT).

Берём HSK 3.0 («new-N», 1..6; 7 = уровни 7–9), если нет — HSK 2.0 («old-N»).
Слово вне списка: если все его знаки сами есть в списке — максимум по знакам, иначе 7.
"""
import json
from pathlib import Path

HSK = Path(__file__).resolve().parent.parent / "data/raw/hsk/complete.json"
UNKNOWN = 7


def load_levels():
    if not HSK.exists():
        return {}
    out = {}
    for e in json.loads(HSK.read_text(encoding="utf-8")):
        lv = {}
        for tag in e.get("level", []):
            kind, _, n = tag.partition("-")
            if n.isdigit() and kind in ("new", "old"):
                lv[kind] = min(lv.get(kind, 9), int(n))
        level = lv.get("new") or lv.get("old")
        if level:
            w = e["simplified"]
            out[w] = min(out.get(w, 9), level)
    return out


def word_level(w, levels):
    if w in levels:
        return levels[w]
    if len(w) > 1 and all(c in levels for c in w):
        return max(levels[c] for c in w)
    return UNKNOWN


def sentence_level(words, levels):
    ls = [word_level(w, levels) for w in words]
    return max(ls) if ls else UNKNOWN
