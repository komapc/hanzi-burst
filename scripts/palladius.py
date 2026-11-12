#!/usr/bin/env python3
"""Пиньинь → система Палладия (русская кириллическая запись китайского) с тоном: 想 xiǎng → ся̌н.

Тон — тот же знак, что в пиньине (ˉ ˊ ˇ ˋ), над главной гласной слога; лёгкий тон без знака.
Используется в build_static.py (строка «Палладий» на русских страницах /c/ и /r/) и для site/palladius.json:
таблица {слог пиньиня без тона (ü = v): слог Палладия} для главной (index.html, вариант «Палладий» в настройках
и поиск по кириллице «сян» → 想). Проверка: python3 scripts/palladius.py
"""
import re
import unicodedata

INI = {"b": "б", "p": "п", "m": "м", "f": "ф", "d": "д", "t": "т", "n": "н", "l": "л", "g": "г", "k": "к", "h": "х",
       "j": "цз", "q": "ц", "x": "с", "zh": "чж", "ch": "ч", "sh": "ш", "r": "ж", "z": "цз", "c": "ц", "s": "с"}
# финали после согласной (нормализованные: iu → iou, ui → uei, un → uen, ü → v)
FIN = {"a": "а", "o": "о", "e": "э", "ai": "ай", "ei": "эй", "ao": "ао", "ou": "оу", "an": "ань", "en": "энь",
       "ang": "ан", "eng": "эн", "ong": "ун", "er": "эр",
       "i": "и", "ia": "я", "ie": "е", "iao": "яо", "iou": "ю", "ian": "янь", "in": "инь", "iang": "ян", "ing": "ин", "iong": "юн",
       "u": "у", "ua": "уа", "uo": "о", "uai": "уай", "uei": "уй", "uan": "уань", "uen": "унь", "uang": "уан", "ueng": "ун",
       "v": "юй", "ve": "юэ", "van": "юань", "vn": "юнь"}
# слоги без согласной (y-, w-, гласная в начале)
ZERO = {"a": "а", "o": "о", "e": "э", "ê": "э", "ai": "ай", "ei": "эй", "ao": "ао", "ou": "оу", "an": "ань", "en": "энь",
        "ang": "ан", "eng": "эн", "er": "эр",
        "yi": "и", "ya": "я", "yo": "ё", "ye": "е", "yao": "яо", "you": "ю", "yan": "янь", "yin": "инь", "yang": "ян",
        "ying": "ин", "yong": "юн", "yu": "юй", "yue": "юэ", "yuan": "юань", "yun": "юнь",
        "wu": "у", "wa": "ва", "wo": "во", "wai": "вай", "wei": "вэй", "wan": "вань", "wen": "вэнь", "wang": "ван", "weng": "вэн"}
MARKS = {1: "̄", 2: "́", 3: "̌", 4: "̀"}
TONE_OF = {"̄": 1, "́": 2, "̌": 3, "̀": 4}
PRIORITY = "аяоёэеюуыи"   # на какую букву ставить знак тона: как в пиньине (a, o, e раньше i, u, ü)


def syllable(base):
    """Слог пиньиня без тона (латиница, ü как v или ü) → Палладий без тона; None, если это не слог."""
    b = base.lower().replace("ü", "v").replace("u:", "v")
    if b in ZERO:
        return ZERO[b]
    m = re.match(r"(zh|ch|sh|[bpmfdtnlgkhjqxrzcs])(.+)$", b)
    if not m:
        return None
    ini, fin = m.groups()
    if ini in "jqx":
        fin = re.sub(r"^u", "v", fin)
    if fin == "i" and ini in ("zh", "ch", "sh", "r"):
        return INI[ini] + "и"
    if fin == "i" and ini in ("z", "c", "s"):
        return INI[ini] + "ы"
    fin = {"iu": "iou", "ui": "uei", "un": "uen", "ue": "ve"}.get(fin, fin)
    if fin not in FIN:
        return None
    if ini in ("b", "p", "m", "f") and fin == "o":
        return INI[ini] + "о"
    return INI[ini] + FIN[fin]


def split_tone(syl):
    """xiǎng → ('xiang', 3); xiang3 → ('xiang', 3); без знака — тон 5."""
    d = unicodedata.normalize("NFD", syl)
    tone = next((t for m, t in TONE_OF.items() if m in d), 5)
    base = "".join(c for c in d if not unicodedata.combining(c) or c == "̈")
    base = unicodedata.normalize("NFC", base)
    if base and base[-1] in "12345":
        tone, base = int(base[-1]), base[:-1]
    return base, tone


def mark(cyr, tone):
    """Знак тона над главной гласной слога Палладия."""
    if tone not in MARKS:
        return cyr
    for v in PRIORITY:
        i = cyr.find(v)
        if i >= 0:
            return unicodedata.normalize("NFC", cyr[:i + 1] + MARKS[tone] + cyr[i + 1:])
    return cyr


def segment(tok):
    """Разбить слитный пиньинь на слоги (жадно, самый длинный слог слева, с откатом); None — не разбивается."""
    letters = [split_tone(c)[0] or c for c in unicodedata.normalize("NFC", tok)]

    def go(i):
        if i == len(tok):
            return []
        for j in range(min(len(tok), i + 6), i, -1):
            if syllable("".join(letters[i:j])):
                rest = go(j)
                if rest is not None:
                    return [tok[i:j]] + rest
        return None
    return go(0) if len(tok) == len(letters) else None


def plain(pinyin):
    """Палладий без знаков тона: так ищут в поисковиках («иероглиф сян»)."""
    return "".join(c for c in unicodedata.normalize("NFD", convert(pinyin)) if not unicodedata.combining(c) or c == "\u0308")


def convert(pinyin):
    """Строка пиньиня со знаками тона (слоги через пробел/дефис) → Палладий с тонами; нераспознанное — как есть."""
    def one(tok):
        base, tone = split_tone(tok)
        p = syllable(base)
        if p:
            return mark(p, tone)
        parts = segment(tok)   # слитное слово: běijīng → běi + jīng
        return "".join(one(x) for x in parts) if parts else tok
    return re.sub(r"[A-Za-zÀ-ɏüÜ:]+[1-5]?", lambda m: one(m.group(0)), pinyin)


if __name__ == "__main__":
    cases = {"xiǎng": "ся̌н", "Běijīng": "бе̌йцзӣн", "zhōng": "чжӯн", "shuǐ": "шу̌й", "nǚ": "ню̌й", "xué": "сюэ́", "yuè": "юэ̀",
             "rì": "жѝ", "zì": "цзы̀", "sī": "сы̄", "guó": "го́", "duì": "ду̀й", "jiǔ": "цзю̌", "yǒu": "ю̌", "lǜ": "лю̀й",
             "wǒ": "во̌", "ér": "э́р", "de": "дэ", "mā": "ма̄", "jūn": "цзю̄нь", "quán": "цюа́нь", "chī": "чӣ", "le": "лэ"}
    # Běijīng по Палладию «Бэйцзин»: проверяем по слогам
    cases["Běijīng"] = "бэ̌йцзӣн"
    N = lambda x: unicodedata.normalize("NFC", x)
    bad = {k: (convert(k), v) for k, v in cases.items() if N(convert(k).lower()) != N(v)}
    print("ok" if not bad else bad)
