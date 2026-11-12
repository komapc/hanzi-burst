"""Разбор китайской фразы: слова (CC-CEDICT) + иероглифы, рекурсивно на компоненты (Make Me a Hanzi).

Использование:
  python3 -I scripts/breakdown.py data/phrases.json site/phrase.json [data/pool.json]   # список фраз [{zh, ru, en}] + пул для «новой фразы»
  python3 -I scripts/breakdown.py "我想学汉字" [out.json]                # одна фраза

Рядом с out.json кладётся glyphs.json (контуры черт из Make Me a Hanzi, чтобы рисовать иероглифы SVG,
а не шрифтом: шрифты с фолбэком иногда теряют черты). Переводы: data/translations/ru.json {en: ru}.

Формат результата:
  phrases: [{zh, ru, en, words: [{word, punct?, cedict?, chars?: [ch, ...], pinyin?: [слог на иероглиф]}]}]
  chars:  {ch: {pinyin, definition, radical, decomposition, etymology, components: [ch, ...]}}
  usage:  (отдельный файл usage.json, грузится после старта) {ch: {words: [{w, pinyin, def}], chars: [ch, ...]}}  # только для иероглифов и компонентов фразы
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


sys.path.insert(0, str(Path(__file__).resolve().parent))
import hsk  # noqa: E402
HSK_LEVELS = hsk.load_levels()
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
    fill_holes(chars)
    return chars


IDS_FILE = ROOT / "data/raw/ids/ids.txt"   # cjkvi-ids (производное от CHISE IDS, GPL): только для заполнения «？» в MMH


def load_ids():
    ids = {}
    if not IDS_FILE.exists():
        return ids
    for line in IDS_FILE.read_text(encoding="utf-8").splitlines():
        p = line.split("\t")
        if line.startswith("#") or len(p) < 3:
            continue
        ids[p[1]] = re.sub(r"\[[^\]]*\]", "", p[2])   # первый вариант без пометок [GTKV]
    return ids


def _usable(c):
    return c in IDS_OPS or 0x4E00 <= ord(c) <= 0x9FFF or 0x2E80 <= ord(c) <= 0x2FDF


def fill_holes(mmh):
    """У части знаков MMH пишет «？» вместо одного из компонентов (曷 = ⿱日？). Берём разбор из IDS,
    если все его части — обычные унифицированные иероглифы или радикалы (их можно показать шрифтом).
    Знаки, у которых «？» — всё разбиение (простые части), не трогаем."""
    ids = load_ids()
    filled = []
    for ch, d in list(mmh.items()):
        dec = d.get("decomposition", "")
        if "？" not in dec or not dec.strip("？"):
            continue
        new = ids.get(ch)
        if not new or new == ch or not all(_usable(c) for c in new):
            continue
        d["decomposition"] = new
        filled.append(ch)
        stack = [c for c in new if c not in IDS_OPS]
        while stack:  # новые части, которых нет в MMH: добавляем разбор из IDS (без определения и контуров)
            c = stack.pop()
            if c in mmh or c not in ids or ids[c] == c or not all(_usable(x) for x in ids[c]):
                continue
            mmh[c] = {"character": c, "decomposition": ids[c], "pinyin": [], "added": True}
            stack.extend(x for x in ids[c] if x not in IDS_OPS)
    return filled


READINGS = {}   # иероглиф -> [(пиньинь, [значения])], если чтений несколько (多音字: 着 zhe/zháo/zhāo/zhuó); заполняет load_cedict


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
    # порядок статей: первая даёт пиньинь и значение слова во фразе. Для одного иероглифа сначала основное чтение
    # (первое в MMH/Unihan: 着 zhe, 要 yào, а не zhāo, yāo по алфавиту); «variant of …» и фамилии — в конец
    main_py = {}
    for line in MMH.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("pinyin"):
            main_py[d["character"]] = d["pinyin"][0]
    main_py.update({"长": "cháng", "得": "de"})   # во фразах чаще «длинный» и служебное 得, чем первое чтение MMH
    variant = re.compile(r"^(old |archaic |Japanese |erroneous |unofficial )?variant of |^used in ")
    for simp, es in words.items():
        if len(es) > 1:
            es.sort(key=lambda e: (all(variant.match(x) for x in e["defs"]),
                                   len(simp) == 1 and e["pinyin"].lower() != main_py.get(simp, e["pinyin"]).lower(),
                                   e["pinyin"][:1].isupper()))
    for ch, es in words.items():
        if len(ch) != 1:
            continue
        by_py = {}
        for e in es:
            defs = [d for d in e["defs"] if not d.startswith("CL:")]
            if e["pinyin"][:1].isupper() or not defs or all(variant.match(d) for d in defs):
                continue
            defs = [re.sub(r"\s*\((Taiwan |also )?pr\. \[[^\]]*\]\)|\|[^\[\s]*\[[^\]]*\]|\[[a-zA-Z]+\d[^\]]*\]", "", d).strip() for d in defs]
            by_py.setdefault(e["pinyin"].lower(), [d for d in defs if d and len(d) <= 70][:2] or [defs[0][:70].rsplit(" ", 1)[0] + "…"])
        if len(by_py) > 1:
            READINGS[ch] = list(by_py.items())
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
    dec = d.get("decomposition", "")
    if "？" in dec and dec.strip("？"):  # неполный разбор (书 = ⿻？丨): одну найденную часть не показываем как весь состав
        return []
    comps = [c for c in dec if c not in IDS_OPS and c != "？" and c != ch]
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
        return (f"variant of {base} ({g}) with {extra} extra stroke{'s' if extra != 1 else ''}",
                f"вариант {base} ({{{{{g}}}}}), доп. черт: {extra}", "unihan-radical")
    rad = mmh.get(ch, {}).get("radical")
    if rad and rad != ch and mmh.get(rad, {}).get("definition"):
        g = mmh[rad]["definition"]
        return f"contains radical {rad}: {g}", f"содержит радикал {rad}: {{{{{g}}}}}", "mmh-radical"
    return None


# в MMH у этих частей бесполезное определение (丷 и 乛 = «kwukyel», корейская пометка к тексту)
DEFINITION_OVERRIDES = {
    "丷": ("two short strokes on top (like a small 八)", "две короткие черты сверху (как маленькое 八)"),
    "乛": ("short stroke with a hook (a stroke component)", "короткая черта с изгибом (элемент-черта)"),
    "丨": ("vertical stroke (a stroke component)", "вертикальная черта (элемент-черта)"),   # в MMH «number one; line»: «один» это 一
    # HSK 1–2: в MMH первым идёт редкое или неверное значение
    "机": ("machine; opportunity, chance; aircraft", "машина, механизм; случай, шанс; самолёт"),   # в MMH «desk»
    "着": ("aspect particle: ongoing action or state (-ing); to touch; to wear", "частица длительного действия или состояния; касаться; носить (одежду)"),
    "眼": ("eye; eyelet, hole, opening", "глаз; ушко, дырка, отверстие"),
    "离": ("to leave, to part from; away from, distant from", "покидать, расставаться; от (о расстоянии), вдали от"),   # в MMH «rare beast»
    "干": ("dry; to do, to work; trunk, main part", "сухой; делать, работать; ствол, основа"),
    "会": ("can, to know how to; to meet; meeting; association", "уметь, мочь; встречаться; собрание; общество"),
    "要": ("to want; to need; must, should; important, essential", "хотеть; нуждаться; надо, следует; важный, главный"),
    "想": ("to think; to want, would like to; to miss", "думать; хотеть; скучать по"),
    "他": ("he, him; other, another", "он, его; другой, иной"),
    "的": ("possessive or attributive particle; of; aim, target", "частица принадлежности или определения; цель, мишень"),
    "了": ("particle of completed action or change; to finish; clear", "частица завершённого действия или изменения; заканчивать; ясный"),
    "呢": ("interrogative or emphatic final particle; wool fabric", "вопросительная или усилительная конечная частица; шерстяная ткань"),
    "几": ("how many; a few, some; small table", "сколько; несколько; столик"),
    "教": ("to teach; teaching, religion", "учить, преподавать; учение, религия"),
    "觉": ("to feel, to sense; to wake up; sleep, nap", "чувствовать, ощущать; просыпаться; сон"),
    "兴": ("interest, excitement; to thrive, to prosper", "интерес, увлечение; процветать, расцветать"),
    "生": ("to be born, to give birth; life; raw; student", "рождаться, рожать; жизнь; сырой; ученик"),
    "放": ("to put, to place; to release, to let go; to set off", "класть, ставить; отпускать, освобождать; запускать"),
    "为": ("for, because of; to do, to act; to be, to become", "для, ради; делать, действовать; быть, становиться"),
    "当": ("to serve as, to act as; when, at the time; appropriate", "быть в качестве, служить; когда, в то время; подходящий"),
    "长": ("long; to grow; chief, head", "длинный; расти; начальник, глава"),
    "占": ("to occupy, to take up; to divine", "занимать; гадать"),
    "周": ("week; circumference, around; Zhou dynasty", "неделя; окружность, вокруг; династия Чжоу"),
    "春": ("spring (season); vitality; love", "весна; жизненная сила; любовь"),
    "适": ("suitable, fitting; comfortable", "подходящий, уместный; удобный"),
}


# английские определения MMH, для которых нет русского перевода
TRANSLATION_FIXES = {
    "death, destruction; to lose, to perish": "смерть, гибель; терять, погибать",
}


def info(ch, mmh, maps=None, tr=None):
    tr = dict(tr or {})
    for k, v in TRANSLATION_FIXES.items():
        tr.setdefault(k, v)
    d = mmh.get(ch, {})
    if ch in DEFINITION_OVERRIDES:
        d = dict(d, definition=DEFINITION_OVERRIDES[ch][0])
        tr = dict(tr, **{DEFINITION_OVERRIDES[ch][0]: DEFINITION_OVERRIDES[ch][1]})
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
    # русский — только если переведены все значения (иначе смесь «chief; голова; elder»)
    readings = [[py, "; ".join(defs)] + (["; ".join(tr[x] for x in defs)] if all(x in tr for x in defs) else [])
                for py, defs in READINGS.get(ch, [])]
    return {
        **({"readings": readings} if readings else {}),
        "pinyin": d.get("pinyin") or [],
        "definition": definition,
        "definition_ru": definition_ru,
        "definition_source": source,
        "radical": d.get("radical"),
        **({"kx": maps[1][ch][0]} if maps and ch in maps[1] else {}),   # номер ключа Канси (kRSUnicode) — для ссылки на /r/
        "decomposition": d.get("decomposition"),
        "etymology": etymology,
        "atomic": ch in ATOMIC,
        "incomplete": ch not in ATOMIC and "？" in (d.get("decomposition") or "") and bool((d.get("decomposition") or "").strip("？")),
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
            if HSK_LEVELS:
                item["hsk"] = hsk.sentence_level([w["word"] for w in parsed if not w.get("punct")], HSK_LEVELS)
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
    result = {"phrases": phrases, "chars": chars}
    text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if len(sys.argv) > 2:
        out = Path(sys.argv[2])
        out.write_text(text, encoding="utf-8")
        (out.parent / "usage.json").write_text(json.dumps(usage, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        (out.parent / "pool.json").write_text(json.dumps(pool, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        glyphs = load_glyphs(set(chars))
        (out.parent / "glyphs.json").write_text(json.dumps(glyphs, ensure_ascii=False), encoding="utf-8")
    print(f"phrases={len(phrases)} pool={len(pool)} core={len(core)} chars={len(chars)} bytes={len(text.encode())}")


if __name__ == "__main__":
    main()
