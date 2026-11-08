"""Статические страницы кандзи для поисковиков (вызывается из build_static.py):
  site/k/<hex кодпоинта>.html — кандзи из списка дзёё (школьные классы 1–6 и средняя школа):
      чтения он/кун (кана + кириллица по Поливанову), значения, класс, число черт, состав по KanjiVG,
      кандзи с этой частью, похожие, частые слова JMdict, фразы Tatoeba, ссылка на китайскую страницу /c/
  site/k/index.html — хаб по школьным классам
Данные: site/data/kanji/ (build_kanji_shards.py), site/data/ja/ (build_ja_shards.py), site/pool-ja.json.
Только русские страницы; английских версий пока нет.
"""
import glob, json, re, shutil
from collections import Counter
from urllib.parse import quote

TOP_WORDS, TOP_PHRASES, TOP_PARENTS, TOP_SIMILAR = 10, 8, 20, 12
JA = lambda s: f'<span lang="ja">{s}</span>'
HIRA_ONLY = re.compile(r"^[぀-ゟ一-鿿々]+$")

# ---------- кана → кириллица (Поливанов), как transcribe() в site/ja.js ----------
_ROW = {'': 'あいうえお', 'k': 'かきくけこ', 's': 'さしすせそ', 't': 'たちつてと', 'n': 'なにぬねの', 'h': 'はひふへほ',
        'm': 'まみむめも', 'r': 'らりるれろ', 'g': 'がぎぐげご', 'z': 'ざじずぜぞ', 'd': 'だぢづでど', 'b': 'ばびぶべぼ', 'p': 'ぱぴぷぺぽ'}
_CC = {'': '', 'k': 'к', 's': 'с', 't': 'т', 'n': 'н', 'h': 'х', 'm': 'м', 'r': 'р', 'g': 'г', 'z': 'дз', 'd': 'д', 'b': 'б', 'p': 'п'}
CYR = {k: _CC[c] + 'аиуэо'[i] for c, row in _ROW.items() for i, k in enumerate(row)}
CYR.update({'し': 'си', 'ち': 'ти', 'つ': 'цу', 'ふ': 'фу', 'じ': 'дзи', 'ぢ': 'дзи', 'づ': 'дзу', 'ず': 'дзу', 'す': 'су',
            'や': 'я', 'ゆ': 'ю', 'よ': 'ё', 'わ': 'ва', 'を': 'о', 'ん': 'н', 'ゐ': 'и', 'ゑ': 'э', 'ゔ': 'ву'})
SMALL = {'ゃ': 'я', 'ゅ': 'ю', 'ょ': 'ё'}
SMALLV = {'ぁ': 'а', 'ぃ': 'и', 'ぅ': 'у', 'ぇ': 'э', 'ぉ': 'о'}
MAC = '̄'


def hira(s):
    return "".join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def cyr(kana):
    s, syl, i = hira(kana), [], 0
    while i < len(s):
        c, n = s[i], s[i + 1] if i + 1 < len(s) else ''
        if c == 'ー':
            if syl and syl[-1] != 'Q': syl[-1] += MAC
        elif c == 'っ':
            syl.append('Q')
        elif c not in CYR:
            syl.append(c)
        elif n in SMALL:
            syl.append(CYR[c][:-1] + SMALL[n]); i += 1
        elif n in SMALLV:
            syl.append(CYR[c][:-1] + SMALLV[n]); i += 1
        else:
            syl.append(CYR[c])
        i += 1
    out = ''
    for j, x in enumerate(syl):
        nx = syl[j + 1] if j + 1 < len(syl) else ''
        if x == 'Q':
            if nx and nx != 'Q': out += nx[0]
            continue
        if x == 'н' and nx and nx != 'Q':
            if nx[0] in 'аиуэояюё': x = 'нъ'
            elif nx[0] in 'мбп': x = 'м'
        if x == 'и' and j > 0 and syl[j - 1] != 'Q' and re.search('[ауэояюё]' + MAC + '?$', out): x = 'й'
        out += x
    for a, b in (('оу', 'о'), ('уу', 'у'), ('ёу', 'ё'), ('юу', 'ю'), ('оо', 'о')):
        out = out.replace(a, b + MAC)
    return out


def strokes(n):
    w = "черта" if n % 10 == 1 and n % 100 != 11 else "черты" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "черт"
    return f"{n} {w}"


def norm(s):
    return {re.sub(r"^(to|a|an|the) ", "", re.sub(r"\(.*?\)", "", x)).strip().lower() for x in re.split(r"[;,]", s or "")} - {""}


def grade_name(g):
    return f"{g} класс" if g <= 6 else "средняя школа"


def build(SITE, page, breadcrumbs, E, gloss, first, BRAND, BASE, zh_chars, zh_all, sitemap_grades=(1,)):
    """Пишет site/k/; возвращает (адреса для sitemap, множество знаков со страницей).
    zh_all — китайские словарные шарды {знак: {definition, definition_ru}}: их русский перевод курирован, а глосса JMdict —
    значение слова и бывает случайной (目 — «ячея»). Берём китайский, только если его английское значение есть среди значений
    KANJIDIC: так 机 (кит. «машина», яп. «стол») не получит китайского перевода."""
    first_ = first
    first = lambda s: re.sub(r"^(\d+[,.)]?\s*)+", "", first_(s))
    K = {}
    for f in glob.glob(str(SITE / "data" / "kanji" / "*.json")):
        K.update(json.load(open(f, encoding="utf-8")))
    joyo = {c: e for c, e in K.items() if 1 <= e.get("g", 0) <= 8}
    gr = lambda c: min(joyo[c]["g"], 7) if c in joyo else 99
    rank = lambda c: (gr(c), joyo.get(c, {}).get("f", 9999), c)
    out = SITE / "k"
    shutil.rmtree(out, ignore_errors=True); out.mkdir()
    cid = lambda ch: f"{ord(ch):x}"
    link = lambda ch: f'<a href="/k/{cid(ch)}" lang="ja">{ch}</a>' if ch in joyo else JA(ch)
    def ru_of(c):
        e, z = K.get(c) or {}, zh_all.get(c) or {}
        if z.get("definition_ru") and norm(z.get("definition")) & norm(";".join(e.get("en") or [])):
            return first(z["definition_ru"])
        return first(e.get("ru"))
    def meaning(c):
        e = K.get(c) or {}
        return ru_of(c), first(";".join(e.get("en") or []))

    # слова JMdict: частые (common), 2–4 знака, только кандзи дзёё и хирагана
    words = {}
    for f in glob.glob(str(SITE / "data" / "ja" / "*.json")):
        for form, ents in json.load(open(f, encoding="utf-8")).items():
            if not 2 <= len(form) <= 4 or not HIRA_ONLY.match(form):
                continue
            kj = [c for c in form if '一' <= c <= '鿿']
            if not kj or any(c not in joyo for c in kj):
                continue
            e = next((x for x in ents if x[4] and x[5]), None)
            if e:
                words[form] = e
    words_by = {}
    for w in words:
        for c in set(w):
            if c in joyo:
                words_by.setdefault(c, []).append(w)
    for c, ws in words_by.items():
        ws.sort(key=lambda w: (max(gr(x) for x in w if x in joyo), len(w), sum(gr(x) for x in w if x in joyo), w))

    pool = json.load(open(SITE / "pool-ja.json", encoding="utf-8"))
    phr_by = {}
    for p in sorted(pool, key=lambda p: (p.get("lv") or 0, len(p["ja"]))):
        for c in set(p["ja"]):
            if c in joyo and len(phr_by.setdefault(c, [])) < TOP_PHRASES:
                phr_by[c].append(p)

    parents = {}
    for c, e in joyo.items():
        for x in set(e.get("components") or []):
            if x != c:
                parents.setdefault(x, []).append(c)
    for v in parents.values():
        v.sort(key=rank)
    def similar(ch, comps):
        shared = Counter()
        for cp in set(comps):
            for x in parents.get(cp, []):
                if x != ch:
                    shared[x] += 1 / len(parents[cp])
        return sorted(shared, key=lambda x: (-shared[x], *rank(x)))[:TOP_SIMILAR]

    def kun_html(k):
        stem, dot, oku = k.partition(".")
        return E(stem) + (f'<span class="m">{E(oku)}</span>' if dot else "")
    def reading(r, kun):
        plain = r.replace(".", "").strip("-")
        return f'<li>{JA(kun_html(r) if kun else E(r))} <span class="m">{E(cyr(plain))}</span></li>'

    urls = []
    for ch, e in joyo.items():
        g, on, kun = e["g"], e.get("on") or [], e.get("kun") or []
        ru, en = e.get("ru") or "", ", ".join(e.get("en") or [])
        rd_short = ", ".join([*on[:2], *(k.replace(".", "").strip("-") for k in kun[:2])])
        body = [f'<div class="big" lang="ja">{ch}</div><h1>Кандзи {JA(ch)} — {JA(E(rd_short))}</h1>']
        mean = ru_of(ch)
        if mean: body.append(f"<p><b>{E(mean)}</b></p>")
        if en: body.append(f'<p class="m" lang="en">{E(en)}</p>')
        info = [f'<a class="badge" href="/k/#g{min(g, 7)}">{"Кёику" if g <= 6 else "Дзёё"} кандзи · {grade_name(g)}</a>']
        if e.get("sc"): info.append(f'<span class="badge">{strokes(e["sc"])}</span>')
        if e.get("j"): info.append(f'<span class="badge">JLPT (старый) {e["j"]}</span>')
        body.append("<p>" + " ".join(info) + "</p>")
        ps = phr_by.get(ch, [])
        if ps:
            body.append(f'<a class="cta" href="/?t={quote(ps[0]["ja"])}">Разобрать во фразе →</a>')
        if on:
            body.append("<h2>Онъёми (китайское чтение)</h2><ul>" + "".join(reading(r, False) for r in on) + "</ul>")
        if kun:
            body.append("<h2>Кунъёми (японское чтение)</h2><ul>" + "".join(reading(r, True) for r in kun) + "</ul>"
                        "<p class='m'>Серым — окуригана: окончание слова, которое пишут каной после кандзи.</p>")
        comps, orig = e.get("components") or [], e.get("orig") or []
        if comps:
            def comp(i, x):
                o = orig[i] if i < len(orig) else ""
                src = f" (от {link(o)})" if o and o != x else ""
                r, n = meaning(o or x)
                return f"<li>{link(x)}{src} — {gloss(r, n)}</li>"
            body.append("<h2>Состав</h2><ul>" + "".join(comp(i, x) for i, x in enumerate(comps)) + "</ul>")
        ws = words_by.get(ch, [])[:TOP_WORDS]
        if ws:
            def wli(w):
                rd, _, wen, wru, *_ = words[w]
                ws_ = "".join(link(x) if x != ch else x for x in w)
                return (f"<li>{JA(ws_)} {JA(E(rd))} <span class='m'>{E(cyr(rd))}</span> — "
                        f"{gloss(first(wru), first(wen))}</li>")
            body.append(f"<h2>Слова с {JA(ch)}</h2><ul>{''.join(wli(w) for w in ws)}</ul>")
        if ps:
            li = "".join(f'<li><a href="/?t={quote(p["ja"])}" lang="ja">{E(p["ja"])}</a> — {gloss(p.get("ru"), p.get("en"))}</li>' for p in ps)
            body.append(f"<h2>Примеры фраз</h2><ul>{li}</ul>")
        par = parents.get(ch, [])
        if par:
            body.append(f"<h2>Кандзи, в которых есть {JA(ch)}</h2><ul>" + "".join(
                f"<li>{link(x)} <span class='m'>{E(', '.join((joyo[x].get('on') or [])[:1]))}</span> — {gloss(*meaning(x))}</li>"
                for x in par[:TOP_PARENTS]) + "</ul>")
        sim = similar(ch, comps)
        if sim:
            body.append("<h2>Похожие по написанию</h2><p class='m'>Кандзи с теми же частями: " + "、".join(link(x) for x in sim) + "</p>")
        if ch in zh_chars:
            body.append(f"<p>Этот же знак в китайском: <a href='/c/{cid(ch)}' lang='zh'>{ch}</a> — пиньинь, разбор на ключи и китайские слова.</p>")
        mean = mean or first(en)
        on1 = ", ".join(f"{r} ({cyr(r)})" for r in on[:2])
        kun1 = ", ".join(f"{k.replace('.', '').strip('-')} ({cyr(k.replace('.', '').strip('-'))})" for k in kun[:2])
        title = f"Кандзи {ch} ({rd_short}): значение, чтения он и кун | {BRAND}"
        desc = f"Японский иероглиф (кандзи) {ch} — {mean}."
        if on1: desc += f" Онъёми: {on1}."
        if kun1: desc += f" Кунъёми: {kun1}."
        desc += f" {grade_name(g).capitalize()}" + (f", {strokes(e['sc'])}." if e.get("sc") else ".")
        if ws: desc += " Слова: " + ", ".join(ws[:3]) + "."
        ld = [breadcrumbs((BRAND, "/"), ("Кандзи", "/k/"), (ch, f"/k/{cid(ch)}")),
              {"@context": "https://schema.org", "@type": "DefinedTerm", "name": ch, "inLanguage": "ja",
               "description": " — ".join(x for x in (rd_short, mean) if x), "url": f"{BASE}/k/{cid(ch)}"}]
        (out / f"{cid(ch)}.html").write_text(page(title, desc[:300], f"/k/{cid(ch)}", "\n".join(body), ld), encoding="utf-8")
        if g in sitemap_grades:
            urls.append(f"{BASE}/k/{cid(ch)}")

    groups = {}
    for c in joyo:
        groups.setdefault(gr(c), []).append(c)
    secs = []
    for g in sorted(groups):
        cs = sorted(groups[g], key=rank)
        name = f"{g} класс" if g <= 6 else "Средняя школа"
        secs.append(f"<h2 id='g{g}'>{name} ({len(cs)})</h2><p class='chs' lang='ja'>" + "".join(link(c) for c in cs) + "</p>")
    nav = " · ".join(f"<a href='#g{g}'>{'Средняя школа' if g == 7 else f'{g} класс'}</a>" for g in sorted(groups))
    (out / "index.html").write_text(page(f"Японские иероглифы кандзи по классам ({len(joyo)}) | {BRAND}",
        f"Все {len(joyo)} кандзи дзёё по школьным классам: чтения он и кун с кириллицей, значение, разбор на части, слова и фразы.", "/k/",
        f"<h1>Кандзи по школьным классам</h1><p class='m'>{len(joyo)} кандзи из списка дзёё (常用漢字): {sum(len(v) for g, v in groups.items() if g <= 6)} "
        f"изучают в начальной школе (кёику кандзи, 1–6 класс), остальные — в средней. Внутри класса — от частых к редким. "
        f"Азбука — на странице <a href='/japanese/'>Кана</a>.</p><p>{nav}</p>" + "".join(secs),
        [breadcrumbs((BRAND, "/"), ("Кандзи", "/k/"))]), encoding="utf-8")
    return [f"{BASE}/k/", *urls], set(joyo)
