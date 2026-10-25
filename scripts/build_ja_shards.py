"""Шарды японского словаря (JMdict) для разбора японского текста на сайте.

site/data/ja/<key>.json — {написание: [[чтение, части речи, en, ru, common, own], ...]}
  own = 0, если это запись каной слова, которое обычно пишут кандзи (клиент такие совпадения штрафует).
  key: для слов на кану — "k" + кодпоинт первого знака (иначе вся кана попадёт в один шард),
       для остальных — кодпоинт первого знака >> 8, как у китайских шардов.
  части речи — коды JMdict через пробел (только нужные клиенту: глаголы, i-прилагательные, частицы).
Записи одного написания упорядочены: частые раньше; для написания каной — сначала слова,
которые и пишутся каной (нет кандзи или помета uk).

Источник: data/raw/jmdict/jmdict-{eng,rus}-*.json (jmdict-simplified, EDRDG, CC BY-SA 4.0).
Запуск: python3 -I scripts/build_ja_shards.py
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/jmdict"
OUT = ROOT / "site/data/ja"
KANA = re.compile(r"^[぀-ヿ]")
POS = re.compile(r"^(v1|v5|vk|vs|vz|adj-i|adj-ix|prt|aux-v|cop|exp)$|^(v5|vs-|v1-)")
MAX_PER_FORM = 3


def key(form):
    c = ord(form[0])
    return f"k{c:x}" if KANA.match(form) else format(c >> 8, "x")


def clean_ru(t):
    # русские глоссы JMdict: убрать примеры {～の}, отсылки (см.) …, нумерацию 1) 2)
    t = re.sub(r"\{[^}]*\}|\(\(.*?\)[^)]*\)|\(см\.\)\s*[^,;]*[,;]?|\b\d+[).]\s*", "", t)
    return re.sub(r"\s*[,;:]\s*(?=[,;:]|$)|^\s*[,;:]\s*", "", re.sub(r"\s+", " ", t)).strip(" ,;:")


def glosses(entry, n_senses=2, n_glosses=3):
    out = []
    for s in entry["sense"][:n_senses]:
        g = [clean_ru(x["text"]) if x["lang"] == "rus" else x["text"] for x in s["gloss"][:n_glosses]]
        g = [x for x in g if x]
        if g:
            out.append(", ".join(g))
    return "; ".join(out)


def load(lang):
    path = next(RAW.glob(f"jmdict-{lang}-*.json"), None)
    if not path:
        sys.exit(f"нет data/raw/jmdict/jmdict-{lang}-*.json: обновите снимок raw-data (README, «Обновление снимка»)")
    return json.loads(path.read_text(encoding="utf-8"))["words"]


def main():
    eng, rus = load("eng"), {w["id"]: w for w in load("rus")}
    if OUT.exists():
        shutil.rmtree(OUT)
    forms = {}
    for e in eng:
        pos = sorted({p for s in e["sense"] for p in s["partOfSpeech"] if POS.match(p)})
        uk = any("uk" in s["misc"] for s in e["sense"])
        en = glosses(e)
        ru = glosses(rus[e["id"]]) if e["id"] in rus else ""
        kana = [k for k in e["kana"] if "sk" not in k["tags"]]
        if not kana or not en:
            continue
        for ki, k in enumerate(e["kanji"]):
            if "sK" in k["tags"]:
                continue
            rd = next((r for r in kana if "*" in r["appliesToKanji"] or k["text"] in r["appliesToKanji"]), None)
            if rd:
                rank = (0 if k["common"] else 1, ki, 0)              # главное написание записи раньше: 本 — ほん, не もと (元)
                forms.setdefault(k["text"], []).append((rank, [rd["text"], " ".join(pos), en, ru, int(k["common"]), 1]))
        for r in kana:
            own = not e["kanji"] or uk or not r["appliesToKanji"]   # слово обычно пишется каной
            kc = sum(k["common"] for k in e["kanji"])                # частое написание кандзи — кана для него вторична
            rank = (0 if own else 1, 0 if r["common"] else 1, kc)
            forms.setdefault(r["text"], []).append((rank, [r["text"], " ".join(pos), en, ru, int(r["common"]), int(own)]))

    shards = {}
    for f, lst in forms.items():
        lst.sort(key=lambda x: x[0])
        shards.setdefault(key(f), {})[f] = [x[1] for x in lst[:MAX_PER_FORM]]
    OUT.mkdir(parents=True)
    for k, v in shards.items():
        (OUT / f"{k}.json").write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sizes = sorted(((p.stat().st_size, p.name) for p in OUT.iterdir()), reverse=True)
    print(f"ja: {len(forms)} forms, {len(sizes)} shards, {sum(s for s, _ in sizes) / 1e6:.1f} MB; "
          f"largest {sizes[0][1]} {sizes[0][0] / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
