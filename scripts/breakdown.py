"""Разбор китайской фразы: слова (CC-CEDICT) + иероглифы, рекурсивно на компоненты (Make Me a Hanzi).

Использование:
  python3 -I scripts/breakdown.py data/phrases.json site/phrase.json [data/pool.json]   # список фраз [{zh, ru, en}] + пул для «новой фразы»
  python3 -I scripts/breakdown.py "我想学汉字" [out.json]                # одна фраза

Рядом с out.json кладётся glyphs.json (контуры черт из Make Me a Hanzi, чтобы рисовать иероглифы SVG,
а не шрифтом: шрифты с фолбэком иногда теряют черты). Переводы: data/translations/ru.json {en: ru}.

Формат результата:
  phrases: [{zh, ru, en, words: [{word, punct?, cedict?, chars?: [ch, ...], pinyin?: [слог на иероглиф]}]}]
  chars:  {ch: {pinyin, definition, radical, decomposition, etymology, components: [ch, ...]}}
  usage:  {ch: {words: [{w, pinyin, def}], chars: [ch, ...]}}  # только для иероглифов и компонентов фразы
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MMH = ROOT / "data/raw/mmh/dictionary.txt"
CEDICT = ROOT / "data/raw/cedict/cedict_ts.u8"
RADICALS = ROOT / "data/raw/unicode/CJKRadicals.txt"
UNIHAN_DIR = ROOT / "data/raw/unihan"
GRAPHICS = ROOT / "data/raw/mmh/graphics.txt"
TRANSLATIONS = ROOT / "data/translations/ru.json"
IDS_OPS = set("⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻")
TOP_WORDS, TOP_CHARS = 8, 10


ATOMIC = set()  # части, которые не делим дальше (заполняется в main)


def compute_atomic(mmh, maps):
    """Что считаем неделимым.

    Делить 目 на 口+二 бессмысленно: это рисунок глаза, а не «рот и два». Поэтому стоп, если часть:
      - сама радикал или его вариант (kRSUnicode без добавочных штрихов: 目, 木, 氵, 心 ...);
      - пиктограмма по этимологии (этот рисунок целиком);
      - слишком простая: до 3 черт.
    """
    num2char, char2num = maps
    strokes = {}
    with GRAPHICS.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            strokes[d["character"]] = len(d["strokes"])
    out = set()
    for ch, d in mmh.items():
        rs = char2num.get(ch)
        if rs and rs[1] == 0:
            out.add(ch)
        elif (d.get("etymology") or {}).get("type") == "pictographic":
            out.add(ch)
        elif 0 < strokes.get(ch, 99) <= 3:
            out.add(ch)
    return out


def load_translations():
    return json.loads(TRANSLATIONS.read_text(encoding="utf-8")) if TRANSLATIONS.exists() else {}


def load_glyphs(needed):
    out = {}
    with GRAPHICS.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["character"] in needed:
                out[d["character"]] = d["strokes"]
    return out


def load_mmh():
    chars = {}
    for line in MMH.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        chars[d["character"]] = d
    return chars


def load_cedict():
    words = {}
    pat = re.compile(r"^(\S+) (\S+) \[([^\]]+)\] /(.+)/$")
    for line in CEDICT.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        m = pat.match(line)
        if not m:
            continue
        _, simp, pinyin, defs = m.groups()
        words.setdefault(simp, []).append({"pinyin": numeric_to_marks(pinyin), "defs": defs.split("/")})
    return words


TONES = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}


def numeric_to_marks(pinyin):
    def one(syl):
        m = re.match(r"^([a-zA-Z:]+?)([1-5])$", syl)
        if not m:
            return syl
        base, tone = m.group(1).replace("u:", "ü").replace("U:", "Ü"), int(m.group(2))
        if tone == 5:
            return base
        low = base.lower()
        idx = None
        for v in "ae":
            if v in low:
                idx = low.index(v)
                break
        if idx is None and "ou" in low:
            idx = low.index("o")
        if idx is None:
            for i in range(len(low) - 1, -1, -1):
                if low[i] in "iouü":
                    idx = i
                    break
        if idx is None:
            return base
        return base[:idx] + TONES[low[idx]][tone - 1] + base[idx + 1 :]
    return " ".join(one(s) for s in pinyin.split())


def segment(text, words, maxlen=4):
    out, i = [], 0
    while i < len(text):
        for n in range(min(maxlen, len(text) - i), 0, -1):
            w = text[i : i + n]
            if w in words or n == 1:
                out.append(w)
                i += n
                break
    return out


def components(ch, mmh):
    d = mmh.get(ch)
    if not d:
        return []
    comps = [c for c in d.get("decomposition", "") if c not in IDS_OPS and c != "？" and c != ch]
    seen, out = set(), []
    for c in comps:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def load_radical_maps():
    """Номер радикала Кансi -> иероглиф; иероглиф -> номер радикала (Unihan kRSUnicode)."""
    num2char = {}
    for line in RADICALS.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        num, _kangxi, uni = [x.strip() for x in line.split(";")]
        if num.isdigit() and uni:
            num2char[int(num)] = chr(int(uni, 16))
    char2num = {}  # иероглиф -> (номер радикала, добавочных штрихов)
    for f in UNIHAN_DIR.glob("Unihan_*.txt"):  # kRSUnicode лежит в разных файлах в разных версиях
        for line in f.read_text(encoding="utf-8").splitlines():
            if "\tkRSUnicode\t" not in line:
                continue
            parts = line.split("\t")
            m = re.match(r"(\d+)'*\.(-?\d+)", parts[2].split()[0])
            if m:
                char2num[chr(int(parts[0][2:], 16))] = (int(m.group(1)), int(m.group(2)))
    return num2char, char2num


NAME_SUFFIX = re.compile(r"\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|SIMPLIFIED|[A-Z]?\d+)$")


def unicode_radical_name(ch):
    """'CJK RADICAL KNIFE ONE' -> 'knife'. Только для блоков радикалов."""
    cp = ord(ch)
    if not (0x2E80 <= cp <= 0x2EFF or 0x2F00 <= cp <= 0x2FDF):
        return None
    name = unicodedata.name(ch, "")
    name = re.sub(r"^(CJK|KANGXI) RADICAL ", "", name)
    name = NAME_SUFFIX.sub("", name).strip().lower()
    return name or None


def fill_ru(text, tr):
    """Подставляет перевод в шаблон «{{english gloss}}»; без перевода оставляет английский."""
    return re.sub(r"\{\{(.+?)\}\}", lambda m: tr.get(m.group(1), m.group(1)), text)


def fallback_definition(ch, mmh, num2char, char2num):
    """Описание для частей, которых нет в словаре.

    Возвращает (en, ru-шаблон, источник) или None. В ru-шаблоне английские глоссы обёрнуты в {{…}}.
    """
    name = unicode_radical_name(ch)
    if name:
        return f"variant of radical: {name}", f"вариант радикала: {{{{{name}}}}}", "unicode-name"
    num, extra = char2num.get(ch, (None, 0))
    base = num2char.get(num) if num else None
    if base and base != ch and mmh.get(base, {}).get("definition"):
        g = mmh[base]["definition"]
        if extra == 0:
            return f"variant of radical {base}: {g}", f"вариант радикала {base}: {{{{{g}}}}}", "unihan-radical"
        return (f"form based on radical {base} ({g}) + {extra} stroke(s)",
                f"форма на основе радикала {base} ({{{{{g}}}}}) + {extra} шт.", "unihan-radical")
    rad = mmh.get(ch, {}).get("radical")
    if rad and rad != ch and mmh.get(rad, {}).get("definition"):
        g = mmh[rad]["definition"]
        return f"contains radical {rad}: {g}", f"содержит радикал {rad}: {{{{{g}}}}}", "mmh-radical"
    return None


def info(ch, mmh, maps=None, tr=None):
    tr = tr or {}
    d = mmh.get(ch, {})
    definition, source = d.get("definition"), "mmh" if d.get("definition") else None
    definition_ru = tr.get(definition) if definition else None
    if not definition and maps:
        fb = fallback_definition(ch, mmh, *maps)
        if fb:
            definition, definition_ru, source = fb
            definition_ru = fill_ru(definition_ru, tr)
    hint = (d.get("etymology") or {}).get("hint")
    etymology = dict(d["etymology"]) if d.get("etymology") else None
    if etymology and hint and tr.get(hint):
        etymology["hint_ru"] = tr[hint]
    return {
        "pinyin": d.get("pinyin") or [],
        "definition": definition,
        "definition_ru": definition_ru,
        "definition_source": source,
        "radical": d.get("radical"),
        "decomposition": d.get("decomposition"),
        "etymology": etymology,
        "atomic": ch in ATOMIC,
        "components": [] if ch in ATOMIC else components(ch, mmh),
    }


def closure(seed, mmh, out, maps=None, tr=None):
    stack = list(seed)
    while stack:
        c = stack.pop()
        if c in out:
            continue
        out[c] = info(c, mmh, maps, tr)
        stack.extend(out[c]["components"])


def main():
    arg = sys.argv[1]
    if arg.endswith(".json"):
        phrase_defs = json.loads(Path(arg).read_text(encoding="utf-8"))
    else:
        phrase_defs = [{"zh": arg}]
    pool_defs = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")) if len(sys.argv) > 3 else []
    mmh, words = load_mmh(), load_cedict()
    maps = load_radical_maps()
    tr = load_translations()
    ATOMIC.update(compute_atomic(mmh, maps))

    # частотный прокси: в скольких словах CEDICT встречается иероглиф
    freq = {}
    for w in words:
        for c in set(w):
            freq[c] = freq.get(c, 0) + 1

    seed = []

    def build(defs, slim):
        out = []
        for pd in defs:
            parsed = []
            for w in segment(pd["zh"], words):
                if not re.match(r"[\u4e00-\u9fff]", w[0]):
                    parsed.append({"word": w, "punct": True})
                    continue
                entry = {"word": w, "chars": list(w)}
                if not slim:
                    entry["cedict"] = [dict(e, defs_ru=[tr.get(x, x) for x in e["defs"]]) for e in words.get(w, [])[:2]]
                syl = words[w][0]["pinyin"].split() if w in words else []
                if len(syl) == len(w):  # чтение в контексте слова (好 hǎo/hào, 了 le/liǎo)
                    entry["pinyin"] = syl
                parsed.append(entry)
                seed.extend(w)
            item = {"zh": pd["zh"], "ru": pd.get("ru"), "en": pd.get("en"), "words": parsed}
            if pd.get("mt"):
                item["mt"] = True   # машинный перевод (Common Voice)
            src = (pd.get("source") or "").split(" ")[0]
            if src in ("wiktionary", "commonvoice"):
                item["src"] = src   # приоритет при выборе фразы: tatoeba/ручные > wiktionary > commonvoice
            out.append(item)
        return out

    phrases = build(phrase_defs, slim=False)
    pool = build(pool_defs, slim=True)

    chars = {}
    closure(seed, mmh, chars, maps, tr)
    core = list(chars)

    # какие иероглифы содержат компонент напрямую
    parents = {}
    for c in mmh:
        if c in ATOMIC:
            continue
        for comp in components(c, mmh):
            parents.setdefault(comp, []).append(c)

    usage = {}
    in_data = set(core)   # «иероглифы с этой частью» только из тех, что есть во фразах: данные не раздуваются
    for c in core:
        ws = [w for w in words if c in w and w != c and 2 <= len(w) <= 4]
        ws.sort(key=lambda w: (-min(freq.get(x, 0) for x in w), len(w)))
        usage[c] = {
            "words": [
                {"w": w, "pinyin": words[w][0]["pinyin"], "def": "; ".join(words[w][0]["defs"][:2]),
                 "def_ru": "; ".join(tr.get(x, x) for x in words[w][0]["defs"][:2])}
                for w in ws[:TOP_WORDS]
            ],
            "chars": sorted(
                (p for p in parents.get(c, []) if p in in_data),
                key=lambda p: -freq.get(p, 0),
            )[:TOP_CHARS],
        }

    # пул (~0,9 МБ) лежит отдельным файлом: клиент грузит его лениво
    result = {"phrases": phrases, "chars": chars, "usage": usage}
    text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if len(sys.argv) > 2:
        out = Path(sys.argv[2])
        out.write_text(text, encoding="utf-8")
        (out.parent / "pool.json").write_text(json.dumps(pool, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        glyphs = load_glyphs(set(chars))
        (out.parent / "glyphs.json").write_text(json.dumps(glyphs, ensure_ascii=False), encoding="utf-8")
    print(f"phrases={len(phrases)} pool={len(pool)} core={len(core)} chars={len(chars)} bytes={len(text.encode())}")


if __name__ == "__main__":
    main()
