#!/usr/bin/env python3
"""Генерирует статические страницы для поисковиков из site/phrase.json:
  site/c/<hex кодпоинта>.html — иероглиф (уровень HSK, разбор, слова, фразы, где встречается, похожие)
  site/p/<sha1(zh)[:8]>.html  — фраза (перевод, иероглифы)
  site/hsk/<1–7>.html          — знаки уровня HSK 3.0 (7 = уровни 7–9) с чтением и значением
  site/c/index.html, site/p/index.html, site/hsk/index.html — хабы со ссылками
  site/k/ — кандзи (scripts/kanji_pages.py)
  site/r/, site/en/r/ — 214 ключей Канси (scripts/radical_pages.py), плакат /r/poster, /en/r/poster, /eo/r/poster
  site/en/c/, site/en/p/, site/en/hsk/ — английские версии страниц иероглифов, фраз и HSK со взаимными hreflang ru↔en (x-default = ru)
  site/sitemap.xml
Интерактивная версия: /?open=<иероглиф> и /?z=<фраза>. Запускается из wrangler.toml [build].
Сгенерированное не коммитится (см. .gitignore).
Основной язык страниц русский (lang="ru"); английские дубли помечены lang="en", китайский текст lang="zh".
"""
import glob, hashlib, html, json, re, shutil, sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hsk as hsklib
import palladius
import kanji_pages
import radical_pages
import redirects

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://hanzi.lipu.dev"
BRAND = "Hanzi Burst"
E = html.escape
IS_HAN = lambda c: '一' <= c <= '鿿'
cid = lambda ch: f"{ord(ch):x}"
pid = lambda zh: hashlib.sha1(zh.encode()).hexdigest()[:8]
def first(s): return (s or "").split(";")[0].strip()
# Pages are aimed at beginners (and indexed by SafeSearch-filtering engines):
# keep crude/vulgar glosses out of the word lists.
VULGAR = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|cunt|dick|cock|pussy|whore|slut|asshole|my ass|bastard|nigg\w*)\b", re.I)
def clean_word(w): return not VULGAR.search(f"{w.get('def') or ''} {w.get('def_ru') or ''}")
# словарные пометки, а не значения: такие слова на странице бесполезны
SKIP = re.compile(r"^(surname|variant of|old variant|archaic variant|abbr\. for|see |erhua variant|used in|\(old\)|\(archaic\)|\(slang\)|\(neologism)", re.I)
def cell(href, ch, pys, g):
    """Ячейка сетки знаков (/hsk/N): знак, пиньинь, значение одной строкой (полное — в title)."""
    return (f'<li><a href="{href}" data-c="{ch}" title="{E(g)}"><span class="c" lang="zh">{ch}</span>'
            f'<small>{E(pys)}</small><small>{E(g)}</small></a></li>')
TOP_WORDS, TOP_PHRASES, TOP_PARENTS, TOP_SIMILAR = 10, 8, 20, 12
EN = lambda s: f'<span lang="en">{s}</span>'
TYPE_RU = {"pictophonetic": "смысл + звук", "ideographic": "смысловая комбинация", "pictographic": "рисунок"}   # как в приложении
ZH = lambda s: f'<span lang="zh">{s}</span>'
def gloss(ru, en):
    """Перевод по-русски; если его нет, английский с lang="en"."""
    return E(ru) if ru else (f'<span lang="en">{E(en)}</span>' if en else "")
def ld_script(items): return "".join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>' for d in items)
def breadcrumbs(*pairs):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{BASE}{u}"} for i, (n, u) in enumerate(pairs)]}

CSS = """<style>
:root{--bg:#faf7f2;--fg:#1f1b16;--muted:#6b6257;--accent:#c8402a;--line:#cfc6b6}
@media(prefers-color-scheme:dark){:root{--bg:#17140f;--fg:#f1ebe0;--muted:#a59c8e;--accent:#ff7a5c;--line:#5a5144}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 60px}
a{color:var(--accent)}h1{font-size:28px;margin:.4em 0}h2{font-size:17px;margin:1.4em 0 .4em}
.big{font:96px/1.1 'Noto Serif SC',serif;color:var(--accent)}.big:lang(ja){font-family:'Noto Serif JP','Noto Serif CJK JP',serif}.m{color:var(--muted)}
ul{padding-left:20px}.cta{display:inline-block;margin:12px 0;padding:8px 14px;border:1px solid var(--accent);border-radius:8px;text-decoration:none}
.chs a{display:inline-block;position:relative;margin:0 6px 6px 0;font-size:22px;text-decoration:none}
:root{--ok:#2f8f5b;--info:#2f6fd0;--warn:#d09a1f}@media(prefers-color-scheme:dark){:root{--ok:#5fcf93;--info:#6aa6ff;--warn:#e8b84a}}
a[data-c]{position:relative}a.known::after,a.allp::after,a.somep::after{content:"";position:absolute;top:2px;right:-2px;width:7px;height:7px;border-radius:50%;background:var(--ok)}
a.allp::after{background:var(--info)}a.somep::after{background:var(--warn)}
.hl{list-style:none;padding:0}.hl li{margin:2px 0}.hl a{font:24px/1.3 'Noto Serif SC',serif;text-decoration:none;margin-right:6px}
.badge{display:inline-block;margin:0 0 6px;padding:2px 10px;border:1px solid var(--line);border-radius:999px;font-size:14px;text-decoration:none}
.tn{display:flex;align-items:center;gap:10px;margin:0 0 14px;padding-bottom:10px;border-bottom:1px solid var(--line)}
.tn a{text-decoration:none;white-space:nowrap}.tb{font-weight:600;color:var(--fg)}
.ts{display:flex;gap:4px;flex:1;min-width:0;overflow-x:auto;scrollbar-width:none}.ts::-webkit-scrollbar{display:none}
.ts a{padding:3px 10px;border-radius:999px;font-size:15px}.ts a:hover{background:color-mix(in srgb,var(--accent) 10%,transparent)}
.ts a.on{background:var(--accent);color:var(--bg)}
.tn .lang{display:inline-flex;flex:none;padding:2px;border:1px solid var(--line);border-radius:999px}
.tn .lang a{padding:3px 9px;border-radius:999px;font-size:13px;color:var(--muted)}.tn .lang a.on{background:var(--accent);color:var(--bg)}
.tq{margin:0;display:flex}.tq input{width:34px;height:30px;box-sizing:border-box;padding:0 8px 0 28px;border:1px solid var(--line);border-radius:999px;
background:transparent url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2.4' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E") 9px 50%/15px no-repeat;
color:var(--fg);font:inherit;font-size:15px;transition:width .15s;cursor:pointer}
.tq input:focus,.tq input:not(:placeholder-shown){width:150px;outline:none;border-color:var(--accent);cursor:text}
.tq input::placeholder{color:transparent}.tq input:focus::placeholder{color:var(--muted)}.tq input::-webkit-search-cancel-button{display:none}
@media(pointer:coarse){.ts a{display:inline-flex;align-items:center;min-height:40px;box-sizing:border-box}.tq input{width:40px;height:40px}}
@media(max-width:520px){.tq input:focus,.tq input:not(:placeholder-shown){width:120px}.tn{gap:6px;flex-wrap:wrap}.tq{margin-left:auto}.tb{font-size:14px}.ts{order:9;flex:1 0 100%;-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent);mask-image:linear-gradient(90deg,#000 85%,transparent)}.ts a{padding:3px 8px;font-size:14px}.ts::after{content:"";flex:0 0 36px}}
.cg{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(76px,1fr));gap:6px}
.cg a{position:relative;display:flex;flex-direction:column;align-items:center;padding:4px 3px 5px;border:1px solid var(--line);border-radius:8px;text-decoration:none;color:var(--fg);text-align:center;min-width:0}
.cg a:hover{border-color:var(--accent)}.cg .c{font:30px/1.15 'Noto Serif SC',serif;color:var(--accent)}
.cg small{display:block;max-width:100%;font-size:12px;line-height:1.3;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
details.lv{border-top:1px solid var(--line);padding:8px 0}details.lv summary{cursor:pointer;font-weight:600;font-size:17px}
details.lv summary span{font-weight:400;color:var(--muted);font-size:15px}
.legend{font-size:14px}.legend .k{color:var(--ok)}.legend .a{color:var(--info);margin-left:10px}.legend .s{color:var(--warn);margin-left:10px}
</style>"""


# Cloudflare Web Analytics: без cookies, поэтому без согласия. Тег один, берём его из главной.
BEACON = re.search(r"<script defer src=\"https://static\.cloudflareinsights\.com/[^>]*></script>",
                   (SITE / "index.html").read_text(encoding="utf-8")).group(0)


def page(title, desc, canon, body, ld=(), lang="ru", alt=None, image=None):
    """alt = (русский путь, английский путь) или {язык: путь}: взаимные hreflang (x-default — русская версия)
    и ссылки на другие языки в шапке. image — путь картинки для og:image (по умолчанию /og.png)."""
    alts = alt if isinstance(alt, dict) else ({"ru": alt[0], "en": alt[1]} if alt else {})
    hreflang = ("".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}{u}">' for l, u in alts.items())
                + f'<link rel="alternate" hreflang="x-default" href="{BASE}{alts["ru"]}">\n') if alts else ""
    # переключатель языка — как на главной: все языки страницы, текущий выделен
    others = ('<span class="lang">' + "".join(f'<a href="{u}" hreflang="{l}" lang="{l}"' + (' class="on" aria-current="true"' if l == lang else "")
                                              + f'>{l.upper()}</a>' for l, u in alts.items()) + "</span>") if alts else ""
    # шапка: бренд + разделы + другой язык; «О проекте» и «Конфиденциальность» — в футере.
    # На телефоне — одна строка с горизонтальной прокруткой, а не три строки ссылок.
    # разделы — те же, что в site/nav.js и UI.nav на главной (index.html): меняйте вместе
    if lang == "ru":
        links = [("/", "Фразы"), ("/r/", "Ключи"), ("/c/", "Иероглифы"), ("/hsk/", "HSK"), ("/radicals-game", "Игра"), ("/learned", "Мои иероглифы")]
        home = "/"
    else:   # en и eo (страниц на эсперанто, кроме плаката, нет — разделы английские)
        links = [("/?lang=en", "Phrases"), ("/en/r/", "Radicals"), ("/en/c/", "Characters"), ("/en/hsk/", "HSK"),
                 ("/radicals-game?lang=en", "Game"), ("/learned", "My characters")]
        home = "/?lang=en"
    cur = canon if canon.endswith("/") else canon.rsplit("/", 1)[0] + "/"
    if lang == "eo":
        cur = cur.replace("/eo/", "/en/", 1)
    def on(h):   # «Фразы» ведут на главную, но подсвечены и на страницах фраз /p/
        return cur.startswith(h) if h.endswith("/") and h != "/" else (h.split("?")[0] == "/" and cur.startswith(("/p/", "/en/p/")))
    items = "".join(f'<a href="{h}"' + (' class="on"' if on(h) else "") + f">{t}</a>" for h, t in links)
    # поиск знака: уходит на главную (/?q=), там тот же поиск по знаку и пиньиню
    search = (f'<form class="tq" action="/" role="search"><input type="search" name="q" placeholder="{"想, xiang, сян" if lang == "ru" else "想 / xiang"}" '
              f'aria-label="{"Найти иероглиф" if lang == "ru" else "Find a character"}" autocomplete="off" spellcheck="false" enterkeyhint="search">'
              + ("" if lang == "ru" else '<input type="hidden" name="lang" value="en">') + "</form>")
    nav = f'<nav class="tn" aria-label="{"Разделы сайта" if lang == "ru" else "Site sections"}"><a class="tb" href="{home}">Hanzi Burst</a><span class="ts">{items}</span>{search}{others}</nav>'
    # активный раздел — в поле зрения (на телефоне строка прокручивается)
    nav += '<script>(function(){var s=document.querySelector(".ts"),o=s&&s.querySelector(".on");if(o)s.scrollLeft=o.offsetLeft-s.offsetLeft-(s.clientWidth-o.offsetWidth)/2})()</script>'
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{BASE}{canon}"><meta name="robots" content="index,follow">
{hreflang}<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{BASE}{image or '/og.png'}"><meta property="og:site_name" content="{BRAND}"><meta property="og:url" content="{BASE}{canon}">
{ld_script(ld)}{CSS}{BEACON}</head><body><main>{nav}
{body}<div id="sitefoot"></div><script src="/footer.js" defer></script></main><script src="/static.js" defer></script></body></html>"""


def main():
    D = json.load(open(SITE / "phrase.json", encoding="utf-8"))
    chars = D["chars"]
    phrases = D["phrases"] + json.load(open(SITE / "pool.json", encoding="utf-8"))
    seen, uniq = set(), []
    for p in phrases:
        if p["zh"] not in seen:
            seen.add(p["zh"]); uniq.append(p)
    phrases = uniq
    by_char = {}
    for p in phrases:
        for ch in {c for w in p["words"] for c in (w.get("chars") or [])}:
            by_char.setdefault(ch, []).append(p)

    hsk = json.load(open(SITE / "data" / "hsk.json", encoding="utf-8"))
    # В sitemap только хабы, страницы HSK и знаки HSK 1–3: тысячи шаблонных страниц фраз и редких знаков
    # поисковик читает как малоценные. Остальные страницы не закрыты (index,follow) и находятся по ссылкам.
    sitemap_chars = set().union(*(hsk.get(lv, []) for lv in ("1", "2", "3")))
    for d in ("c", "p", "hsk"):
        shutil.rmtree(SITE / d, ignore_errors=True); (SITE / d).mkdir()
    shutil.rmtree(SITE / "en", ignore_errors=True)
    for d in ("c", "p", "hsk"):
        (SITE / "en" / d).mkdir(parents=True)
    # все знаки из словарных шардов (build_shards.py): значения и состав для знаков вне phrase.json
    allc = {}
    for f in glob.glob(str(SITE / "data" / "chars" / "*.json")):
        allc.update(json.load(open(f, encoding="utf-8")))
    k_urls, kanji = kanji_pages.build(SITE, page, breadcrumbs, E, gloss, first, BRAND, BASE, set(chars), allc)
    r_urls, rad_of = radical_pages.build(SITE, page, breadcrumbs, E, BASE, chars, allc, first)
    def rad_links(ch, pre="", bare=False):
        """Ссылки на страницы ключей /r/ для знака, который сам ключ или его вариант (阝 — два ключа).
        bare — без самого знака (он уже стоит рядом): «№38», а не «№38 女»."""
        return ", ".join(f'<a href="{pre}/r/{cid(rc)}">{"No. " if pre else "№"}{n}' + ("" if bare else f" {rc}") + "</a>"
                         for n, rc in rad_of.get(ch, []))
    char_lv = {c: int(lv) for lv, cs in hsk.items() for c in cs}
    lvname = lambda lv: "7–9" if str(lv) == "7" else str(lv)
    # слова CC-CEDICT из шардов (build_shards.py): {слово: [pinyin, en, ru?]}; частота знака = в скольких словах он есть
    dict_words = {}
    for f in glob.glob(str(SITE / "data" / "words" / "*.json")):
        dict_words.update(json.load(open(f, encoding="utf-8")))
    freq = Counter(c for w in dict_words for c in set(w))
    word_lv = hsklib.load_levels()
    words_by_char = {}
    for w, (wpy, wen, *wru) in dict_words.items():
        if not 2 <= len(w) <= 4 or SKIP.match(wen) or not clean_word({"def": wen, "def_ru": wru[0] if wru else ""}):
            continue
        for c in set(w):
            if c in chars:
                words_by_char.setdefault(c, []).append(w)
    def top_words(ch):
        """Слова со знаком: сначала из списка HSK (по уровню, короткие первыми), потом из знаков HSK, потом самые частые по знакам."""
        ws = words_by_char.get(ch, [])
        ws.sort(key=lambda w: (word_lv.get(w, 99), hsklib.word_level(w, word_lv), len(w), -min(freq[x] for x in w), w))
        return ws[:TOP_WORDS]
    # обратный индекс: в каких знаках (со страницей) встречается часть; всего — по всему словарю
    parents, parents_all = {}, Counter()
    for c, v in chars.items():
        if not IS_HAN(c):   # варианты радикалов (⺳, ⺍) — части, а не знаки для списков
            continue
        for x in set(v.get("components") or []):
            parents.setdefault(x, []).append(c)
    for c, v in allc.items():
        for x in set(v.get("components") or []):
            parents_all[x] += 1
    rank = lambda c: (char_lv.get(c, 99), -freq[c], c)
    for v in parents.values():
        v.sort(key=rank)
    def phrase_rank(p): return (p.get("hsk") or 9, len(p["zh"]))
    def similar(ch, comps):
        """Похожие по написанию: знаки с теми же частями; редкая общая часть весит больше частой (马 в 妈 важнее 口 в 中)."""
        shared = Counter()
        for cp in set(comps):
            for x in parents.get(cp, []):
                if x != ch:
                    shared[x] += 1 / len(parents[cp])
        return sorted(shared, key=lambda x: (-shared[x], *rank(x)))[:TOP_SIMILAR]
    urls = [f"{BASE}/", f"{BASE}/about", f"{BASE}/privacy", f"{BASE}/extension", f"{BASE}/c/", f"{BASE}/p/", f"{BASE}/hsk/", f"{BASE}/japanese/"]
    link = lambda ch: f'<a href="/c/{cid(ch)}" data-c="{ch}">{ch}</a>' if ch in chars else ch

    for ch, c in chars.items():
        py = ", ".join(c.get("pinyin") or [])
        den, dru = c.get("definition") or "", c.get("definition_ru") or ""
        et = c.get("etymology") or {}
        # знак, у которого есть страница ключа /r/, здесь называется иероглифом: «Ключ X» — заголовок страницы /r/
        kind = "Ключ" if c.get("radical") == ch and ch not in rad_of else "Иероглиф"
        body = [f'<div class="big" lang="zh">{ch}</div><h1>{kind} {ZH(ch)} — {E(py)}</h1>']
        pal = palladius.convert(py) if py else ""
        if pal:   # кириллицей по системе Палладия, со знаком тона: 想 — ся̌н
            body.append(f"<p class='m'>По-русски (система Палладия): <b>{E(pal)}</b></p>")
        if dru: body.append(f"<p><b>{E(dru)}</b></p>")
        if den: body.append(f'<p class="m" lang="en">{E(den)}</p>')
        lv = char_lv.get(ch)
        if lv:
            body.append(f'<p><a class="badge" href="/hsk/{lv}">HSK 3.0 · уровень {lvname(lv)}</a></p>')
        if c.get("components"): body.append(f'<a class="cta" href="/?open={ch}&explode=1">Разобрать интерактивно →</a>')
        if ch in rad_of:
            body.append(f"<p>{ZH(ch)} — ключ (радикал) {rad_links(ch)}: на странице ключа порядок черт, варианты написания и иероглифы с ним.</p>")
        comps = c.get("components") or []
        if comps:
            def comp(x):
                cx = chars.get(x) or {}
                p0 = (cx.get("pinyin") or [""])[0]
                return f"<li>{link(x)} {E(p0)} — {gloss(first(cx.get('definition_ru')), first(cx.get('definition')))}</li>"
            items = "".join(comp(x) for x in comps)
            body.append(f"<h2>Состав</h2><ul>{items}</ul>")
        if c.get("radical"):
            rl = rad_links(c["radical"], bare=True) if c["radical"] != ch else ""
            body.append(f"<p class='m'>Ключ: {link(c['radical'])}" + (f" — ключ Канси {rl}" if rl else "") + "</p>")
        hint = E(et["hint_ru"]) if et.get("hint_ru") else EN(E(et["hint"])) if et.get("hint") else ""
        kind = TYPE_RU.get(et.get("type"), et.get("type") or "").capitalize()
        if kind or hint:
            body.append("<p class='m'>" + ": ".join(x for x in (E(kind), hint) if x) + "</p>")
        words = top_words(ch)
        if words:
            def wli(w):
                wpy, wen, *wru = dict_words[w]
                tag = f" <span class='m'>· HSK {lvname(word_lv[w])}</span>" if w in word_lv else ""
                ws = "".join(link(x) if x != ch else x for x in w)
                return f"<li><span lang='zh'>{ws}</span> <span class='m'>{E(wpy)}</span> — {gloss(wru[0] if wru else '', wen)}{tag}</li>"
            body.append(f"<h2>Слова с {ZH(ch)}</h2><ul>{''.join(wli(w) for w in words)}</ul>")
        ps = sorted(by_char.get(ch, []), key=phrase_rank)[:TOP_PHRASES]
        if ps:
            li = "".join(f'<li><a href="/p/{pid(p["zh"])}" lang="zh">{E(p["zh"])}</a> — {gloss(p.get("ru"), p.get("en"))}</li>' for p in ps)
            body.append(f"<h2>Примеры фраз</h2><ul>{li}</ul>")
        par = parents.get(ch, [])
        if par:
            n_all = parents_all.get(ch, len(par))
            head = "Где встречается этот ключ" if kind == "Ключ" else f"Иероглифы, в которых есть {ZH(ch)}"
            more = f" (всего в словаре — {n_all})" if n_all > len(par[:TOP_PARENTS]) else ""
            body.append(f"<h2>{head}</h2>"
                        f"<p class='m'>{ZH(ch)} входит в состав этих знаков{more}, сначала простые по HSK:</p>"
                        "<ul>" + "".join(
                            f"<li>{link(x)} <span class='m'>{E((chars[x].get('pinyin') or [''])[0])}</span> — "
                            f"{gloss(first(chars[x].get('definition_ru')), first(chars[x].get('definition')))}</li>"
                            for x in par[:TOP_PARENTS]) + "</ul>")
        sim = similar(ch, comps)
        if sim:
            body.append(f"<h2>Похожие по написанию</h2>"
                        f"<p class='m'>Знаки с теми же частями: " + "、".join(
                            f"{link(x)} ({E((chars[x].get('pinyin') or [''])[0])})" for x in sim) + "</p>")
        if ch in kanji:
            body.append(f"<p>Этот же знак в японском: <a href='/k/{cid(ch)}' lang='ja'>{ch}</a> — чтения он и кун, японские слова.</p>")
        meaning = first(dru) or first(den)
        if kind == "Ключ":   # сам является ключом (радикалом), а своей страницы /r/ у него нет
            title = f"Ключ {ch} ({py}): значение и иероглифы с ним | Hanzi Burst"
            desc = f"Иероглиф и ключ {ch} ({py}): {meaning}. Пиньинь, значение, иероглифы с этим ключом (радикалом), слова и фразы."
        else:
            title = f"Иероглиф {ch} ({py}): значение и разбор на ключи | Hanzi Burst"
            desc = f"Иероглиф {ch} ({py}" + (f", по-русски {palladius.plain(py)}" if py else "") + f") — {meaning}. Разбор иероглифа на ключи (радикалы) и составные части, пиньинь, слова и фразы с ним."
        if lv:
            desc += f" HSK {lvname(lv)}."
        hsk_words = [w for w in words if w in word_lv][:3]
        if hsk_words:
            desc += " Слова: " + ", ".join(hsk_words) + "."
        ld = [breadcrumbs((BRAND, "/"), ("Иероглифы", "/c/"), (ch, f"/c/{cid(ch)}")),
              {"@context": "https://schema.org", "@type": "DefinedTerm", "name": ch, "inLanguage": "zh",
               "description": " — ".join(x for x in (py, first(dru) or first(den)) if x),
               "url": f"{BASE}/c/{cid(ch)}"}]
        (SITE / "c" / f"{cid(ch)}.html").write_text(page(title, desc[:300], f"/c/{cid(ch)}", "\n".join(body), ld, alt=(f"/c/{cid(ch)}", f"/en/c/{cid(ch)}")), encoding="utf-8")
        if ch in sitemap_chars:
            urls.append(f"{BASE}/c/{cid(ch)}")

    for p in phrases:
        zh = p["zh"]
        pyl = " ".join(" ".join(w.get("pinyin") or []) if w.get("pinyin") else "" for w in p["words"] if not w.get("punct"))
        cs = []
        for w in p["words"]:
            for c in (w.get("chars") or []):
                if c not in cs: cs.append(c)
        body = [f"<h1 lang='zh'>{E(zh)}</h1><p class='m'>{E(pyl)}</p>"]
        if p.get("ru"): body.append(f"<p><b>{E(p['ru'])}</b></p>")
        if p.get("en"): body.append(f"<p class='m' lang='en'>{E(p['en'])}</p>")
        body.append(f'<a class="cta" href="/?z={E(zh)}">Разобрать по иероглифам →</a>')
        body.append(f"<h2>Иероглифы</h2><p class='chs' lang='zh'>" + "".join(link(c) for c in cs) + "</p>")
        rows = []
        for c in cs:
            cx = chars.get(c)
            if cx:
                rows.append(f"<li>{link(c)} <span class='m'>{E((cx.get('pinyin') or [''])[0])}</span> — "
                            f"{gloss(first(cx.get('definition_ru')), first(cx.get('definition')))}</li>")
        if rows:
            body.append(f"<h2>Слово за словом</h2><ul>" + "".join(rows) + "</ul>")
        tr = p.get('ru') or p.get('en') or ''
        short = tr if len(tr) <= 40 else tr[:39].rstrip() + "…"
        title = f"{zh} — перевод и пиньинь: {short} | Hanzi Burst"
        desc = f"{zh} ({pyl}): {tr}. Китайская фраза с пиньинем, переводом и разбором иероглифов на ключи (радикалы)."
        ld = [breadcrumbs((BRAND, "/"), ("Фразы", "/p/"), (zh, f"/p/{pid(zh)}"))]
        (SITE / "p" / f"{pid(zh)}.html").write_text(page(title, desc[:300], f"/p/{pid(zh)}", "\n".join(body), ld, alt=(f"/p/{pid(zh)}", f"/en/p/{pid(zh)}")), encoding="utf-8")

    comps = {c: "".join(v.get("components") or []) for c, v in chars.items() if v.get("components")}
    (SITE / "comps.json").write_text(json.dumps(comps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    hub_c = "".join(link(ch) for ch in sorted(chars))
    (SITE / "c" / "index.html").write_text(page(f"Все иероглифы и ключи-радикалы ({len(chars)}) | Hanzi Burst",
        f"{len(chars)} китайских иероглифов и радикалов с пиньинем, значением и разбором на составные части. Нажмите на знак, чтобы открыть его страницу.", "/c/",
        f"<h1>Иероглифы и радикалы</h1><p class='m'>Всего знаков: {len(chars)} — все, что встречаются во фразах сайта, включая радикалы (ключи) и их варианты. "
        f"Списки по уровням — в разделе <a href='/hsk/'>HSK</a>, примеры употребления — во <a href='/p/'>фразах</a>.</p><p class='chs' lang='zh'>{hub_c}</p>",
        [breadcrumbs((BRAND, "/"), ("Иероглифы", "/c/"))], alt=("/c/", "/en/c/")), encoding="utf-8")
    def by_level(item, word):
        """Фразы по уровню HSK, каждый уровень свёрнут: страница короткая, а все ссылки остаются в HTML."""
        lv_of = lambda p: min(int(p.get("hsk") or 7), 7)
        out = ""
        for lv in sorted({lv_of(p) for p in phrases}):
            ps = [p for p in phrases if lv_of(p) == lv]
            out += (f"<details class='lv' id='hsk{lv}'><summary>HSK {lvname(lv)} <span>· {len(ps)} {word} · "
                    f"<span lang='zh'>{E(ps[0]['zh'])}</span>…</span></summary><ul>{''.join(item(p) for p in ps)}</ul></details>")
        return out
    li = by_level(lambda p: f'<li><a href="/p/{pid(p["zh"])}" lang="zh">{E(p["zh"])}</a> — {gloss(p.get("ru"), p.get("en"))}</li>', "фраз")
    (SITE / "p" / "index.html").write_text(page(f"Простые китайские фразы с переводом ({len(phrases)}) | Hanzi Burst",
        f"{len(phrases)} простых китайских фраз с переводом и разбором каждого иероглифа на радикалы. Подходит для начинающих.", "/p/",
        f"<h1>Китайские фразы с переводом</h1><p class='m'>{len(phrases)} фраз по уровню HSK 3.0. "
        f"Откройте уровень, чтобы увидеть фразы.</p>{li}",
        [breadcrumbs((BRAND, "/"), ("Фразы", "/p/"))], alt=("/p/", "/en/p/")), encoding="utf-8")
    # HSK: значения всех знаков уровня из словарных шардов allc (в phrase.json только знаки фраз)
    nav = " · ".join(f'<a href="/hsk/{lv}">HSK {lvname(lv)}</a>' for lv in hsk)
    for lv, cs in hsk.items():
        rows = []
        for ch in cs:
            cx = allc.get(ch) or {}
            href = f"/c/{cid(ch)}" if ch in chars else f"/?open={ch}"
            rows.append(cell(href, ch, ", ".join(cx.get("pinyin") or []), first(cx.get("definition_ru")) or first(cx.get("definition"))))
        title = f"Иероглифы HSK {lvname(lv)} ({len(cs)}) — список с чтением и значением | Hanzi Burst"
        desc = (f"Все {len(cs)} иероглифов уровня HSK {lvname(lv)} (HSK 3.0) с пиньинем и переводом, от частых к редким, "
                f"с разбором каждого знака на радикалы.")
        body = (f"<h1>Иероглифы HSK {lvname(lv)}</h1>"
                f"<p class='m'>{len(cs)} новых знаков уровня по стандарту HSK 3.0, от частых к редким. "
                f"Нажмите на знак, чтобы разобрать его на части.</p>"
                f"<p>{nav}</p><a class='cta' href='/learned'>Мой прогресс по HSK →</a><ul class='cg'>{''.join(rows)}</ul>")
        ld = [breadcrumbs((BRAND, "/"), ("HSK", "/hsk/"), (f"HSK {lvname(lv)}", f"/hsk/{lv}"))]
        (SITE / "hsk" / f"{lv}.html").write_text(page(title, desc, f"/hsk/{lv}", body, ld, alt=(f"/hsk/{lv}", f"/en/hsk/{lv}")), encoding="utf-8")
        urls.append(f"{BASE}/hsk/{lv}")
    li = "".join(f'<li><a href="/hsk/{lv}">HSK {lvname(lv)}</a> — {len(cs)} знаков: '
                 f'<span lang="zh">{"".join(cs[:12])}…</span></li>' for lv, cs in hsk.items())
    (SITE / "hsk" / "index.html").write_text(page("Иероглифы HSK 1–9 по уровням | Hanzi Burst",
        "Списки иероглифов HSK 3.0 по уровням 1–9 с пиньинем и переводом на русский. Каждый знак можно разобрать на радикалы.", "/hsk/",
        f"<h1>Иероглифы HSK по уровням</h1><ul>{li}</ul>",
        [breadcrumbs((BRAND, "/"), ("HSK", "/hsk/"))], alt=("/hsk/", "/en/hsk/")), encoding="utf-8")

    # Английские версии /en/c/, /en/p/ и /en/hsk/: те же данные, только английские значения, без подстановки русских.
    # В sitemap — по той же политике, что и русские: хабы, HSK и знаки HSK 1–3; страниц фраз там нет.
    # Ссылки «в приложение» с английских страниц добавляют lang=en.
    link_en = lambda ch: f'<a href="/en/c/{cid(ch)}" data-c="{ch}">{ch}</a>' if ch in chars else ch
    def en_gloss(s): return f" — {E(s)}" if s else ""
    for ch, c in chars.items():
        py = ", ".join(c.get("pinyin") or [])
        den = c.get("definition") or ""
        et = c.get("etymology") or {}
        is_radical = c.get("radical") == ch and ch not in rad_of
        kind = "Radical" if is_radical else "Character"
        body = [f'<div class="big" lang="zh">{ch}</div><h1>{kind} {ZH(ch)} — {E(py)}</h1>']
        if den: body.append(f"<p><b>{E(den)}</b></p>")
        lv = char_lv.get(ch)
        if lv:
            body.append(f'<p><a class="badge" href="/en/hsk/{lv}">HSK 3.0 · level {lvname(lv)}</a></p>')
        if c.get("components"): body.append(f'<a class="cta" href="/?open={ch}&amp;explode=1&amp;lang=en">Break it down interactively →</a>')
        if ch in rad_of:
            body.append(f"<p>{ZH(ch)} is a Kangxi radical, {rad_links(ch, '/en')}: its page shows the stroke order, variant forms and characters that use it.</p>")
        comps = c.get("components") or []
        if comps:
            def comp_en(x):
                cx = chars.get(x) or {}
                return f"<li>{link_en(x)} {E((cx.get('pinyin') or [''])[0])}{en_gloss(first(cx.get('definition')))}</li>"
            body.append(f"<h2>Components</h2><ul>{''.join(comp_en(x) for x in comps)}</ul>")
        if c.get("radical"):
            rl = rad_links(c["radical"], "/en", bare=True) if c["radical"] != ch else ""
            body.append(f"<p class='m'>Radical: {link_en(c['radical'])}" + (f" — Kangxi radical {rl}" if rl else "") + "</p>")
        if et.get("type") or et.get("hint"):
            body.append("<p class='m'>" + ": ".join(E(x) for x in ((et.get("type") or "").capitalize(), et.get("hint")) if x) + "</p>")
        words = top_words(ch)
        if words:
            def wli_en(w):
                wpy, wen, *_ = dict_words[w]
                tag = f" <span class='m'>· HSK {lvname(word_lv[w])}</span>" if w in word_lv else ""
                ws = "".join(link_en(x) if x != ch else x for x in w)
                return f"<li><span lang='zh'>{ws}</span> <span class='m'>{E(wpy)}</span> — {E(wen)}{tag}</li>"
            body.append(f"<h2>Words with {ZH(ch)}</h2><ul>{''.join(wli_en(w) for w in words)}</ul>")
        ps = [p for p in sorted(by_char.get(ch, []), key=phrase_rank) if p.get("en")][:TOP_PHRASES]
        if ps:
            li = "".join(f'<li><a href="/en/p/{pid(p["zh"])}" lang="zh">{E(p["zh"])}</a> — {E(p["en"])}</li>' for p in ps)
            body.append(f"<h2>Example phrases</h2><ul>{li}</ul>")
        par = parents.get(ch, [])
        if par:
            n_all = parents_all.get(ch, len(par))
            head = "Characters with this radical" if is_radical else f"Characters containing {ZH(ch)}"
            more = f" ({n_all} in the dictionary)" if n_all > len(par[:TOP_PARENTS]) else ""
            body.append(f"<h2>{head}</h2><p class='m'>{ZH(ch)} is part of these characters{more}, simplest HSK levels first:</p><ul>" + "".join(
                f"<li>{link_en(x)} <span class='m'>{E((chars[x].get('pinyin') or [''])[0])}</span>{en_gloss(first(chars[x].get('definition')))}</li>"
                for x in par[:TOP_PARENTS]) + "</ul>")
        sim = similar(ch, comps)
        if sim:
            body.append("<h2>Similar characters</h2><p class='m'>Characters with the same parts: " + "、".join(
                f"{link_en(x)} ({E((chars[x].get('pinyin') or [''])[0])})" for x in sim) + "</p>")
        meaning = first(den)
        if is_radical:
            title = f"Radical {ch} {py} — meaning and characters that use it | Hanzi Burst"
            desc = f"The Chinese radical {ch} ({py}): {meaning}. Pinyin, meaning, characters built with this radical, words and example phrases."
        else:
            title = f"{ch} {py} — meaning, radicals and components | Hanzi Burst"
            desc = f"The Chinese character {ch} ({py}): {meaning}. Breakdown into radicals and components, pinyin, words and example phrases."
        if lv:
            desc += f" HSK {lvname(lv)}."
        hsk_words = [w for w in words if w in word_lv][:3]
        if hsk_words:
            desc += " Words: " + ", ".join(hsk_words) + "."
        ld = [breadcrumbs((BRAND, "/"), ("Characters", "/en/c/"), (ch, f"/en/c/{cid(ch)}")),
              {"@context": "https://schema.org", "@type": "DefinedTerm", "name": ch, "inLanguage": "zh",
               "description": " — ".join(x for x in (py, meaning) if x), "url": f"{BASE}/en/c/{cid(ch)}"}]
        (SITE / "en" / "c" / f"{cid(ch)}.html").write_text(
            page(title, desc[:300], f"/en/c/{cid(ch)}", "\n".join(body), ld, lang="en", alt=(f"/c/{cid(ch)}", f"/en/c/{cid(ch)}")), encoding="utf-8")
        if ch in sitemap_chars:
            urls.append(f"{BASE}/en/c/{cid(ch)}")
    (SITE / "en" / "c" / "index.html").write_text(page(f"All Chinese characters and radicals ({len(chars)}) | Hanzi Burst",
        f"{len(chars)} Chinese characters and radicals with pinyin, meaning and a breakdown into components. Click a character to open its page.", "/en/c/",
        f"<h1>Characters and radicals</h1><p class='m'>{len(chars)} characters: all those used in the site's phrases, including radicals and their variants. "
        f"Lists by level are in the <a href='/en/hsk/'>HSK</a> section.</p><p class='chs' lang='zh'>{''.join(link_en(ch) for ch in sorted(chars))}</p>",
        [breadcrumbs((BRAND, "/"), ("Characters", "/en/c/"))], lang="en", alt=("/c/", "/en/c/")), encoding="utf-8")
    for p in phrases:
        zh = p["zh"]
        pyl = " ".join(" ".join(w.get("pinyin") or []) if w.get("pinyin") else "" for w in p["words"] if not w.get("punct"))
        cs = []
        for w in p["words"]:
            for c in (w.get("chars") or []):
                if c not in cs: cs.append(c)
        en = p.get("en") or ""
        body = [f"<h1 lang='zh'>{E(zh)}</h1><p class='m'>{E(pyl)}</p>"]
        if en: body.append(f"<p><b>{E(en)}</b></p>")
        body.append(f'<a class="cta" href="/?z={quote(zh)}&amp;lang=en">Break it down character by character →</a>')
        body.append("<h2>Characters</h2><p class='chs' lang='zh'>" + "".join(link_en(c) for c in cs) + "</p>")
        rows = [f"<li>{link_en(c)} <span class='m'>{E((chars[c].get('pinyin') or [''])[0])}</span>{en_gloss(first(chars[c].get('definition')))}</li>"
                for c in cs if c in chars]
        if rows:
            body.append("<h2>Character by character</h2><ul>" + "".join(rows) + "</ul>")
        short = en if len(en) <= 40 else en[:39].rstrip() + "…"
        title = f"{zh} — meaning and pinyin: {short} | Hanzi Burst" if en else f"{zh} — pinyin and characters | Hanzi Burst"
        desc = f"{zh} ({pyl})" + (f": {en}" if en else "") + ("" if en[-1:] in ".?!…" else ".") + " A Chinese phrase with pinyin, English translation and every character broken down into radicals."
        ld = [breadcrumbs((BRAND, "/"), ("Phrases", "/en/p/"), (zh, f"/en/p/{pid(zh)}"))]
        (SITE / "en" / "p" / f"{pid(zh)}.html").write_text(
            page(title, desc[:300], f"/en/p/{pid(zh)}", "\n".join(body), ld, lang="en", alt=(f"/p/{pid(zh)}", f"/en/p/{pid(zh)}")), encoding="utf-8")
    li = by_level(lambda p: f'<li><a href="/en/p/{pid(p["zh"])}" lang="zh">{E(p["zh"])}</a>{en_gloss(p.get("en"))}</li>', "phrases")
    (SITE / "en" / "p" / "index.html").write_text(page(f"Simple Chinese phrases with English translation ({len(phrases)}) | Hanzi Burst",
        f"{len(phrases)} simple Chinese phrases with pinyin, English translation and every character broken down into radicals. Made for beginners.", "/en/p/",
        f"<h1>Chinese phrases with translation</h1><p class='m'>{len(phrases)} phrases by HSK 3.0 level. "
        f"Open a level to see its phrases.</p>{li}",
        [breadcrumbs((BRAND, "/"), ("Phrases", "/en/p/"))], lang="en", alt=("/p/", "/en/p/")), encoding="utf-8")
    nav_en = " · ".join(f'<a href="/en/hsk/{lv}">HSK {lvname(lv)}</a>' for lv in hsk)
    for lv, cs in hsk.items():
        rows = []
        for ch in cs:
            cx = allc.get(ch) or {}
            href = f"/en/c/{cid(ch)}" if ch in chars else f"/?open={ch}&amp;lang=en"
            rows.append(cell(href, ch, ", ".join(cx.get("pinyin") or []), first(cx.get("definition"))))
        body = (f"<h1>HSK {lvname(lv)} characters</h1>"
                f"<p class='m'>{len(cs)} new characters of this level in the HSK 3.0 standard, from common to rare. "
                f"Click a character to break it down into parts.</p>"
                f"<p>{nav_en}</p><a class='cta' href='/learned'>My HSK progress →</a><ul class='cg'>{''.join(rows)}</ul>")
        (SITE / "en" / "hsk" / f"{lv}.html").write_text(page(f"HSK {lvname(lv)} characters ({len(cs)}): list with pinyin and meaning | Hanzi Burst",
            f"All {len(cs)} characters of HSK {lvname(lv)} (HSK 3.0) with pinyin and meaning, from common to rare, each with a breakdown into radicals.",
            f"/en/hsk/{lv}", body, [breadcrumbs((BRAND, "/"), ("HSK", "/en/hsk/"), (f"HSK {lvname(lv)}", f"/en/hsk/{lv}"))],
            lang="en", alt=(f"/hsk/{lv}", f"/en/hsk/{lv}")), encoding="utf-8")
        urls.append(f"{BASE}/en/hsk/{lv}")
    li = "".join(f'<li><a href="/en/hsk/{lv}">HSK {lvname(lv)}</a>: {len(cs)} characters: '
                 f'<span lang="zh">{"".join(cs[:12])}…</span></li>' for lv, cs in hsk.items())
    (SITE / "en" / "hsk" / "index.html").write_text(page("HSK 1–9 characters by level | Hanzi Burst",
        "HSK 3.0 character lists for levels 1–9 with pinyin and meaning. Every character can be broken down into radicals.", "/en/hsk/",
        f"<h1>HSK characters by level</h1><ul>{li}</ul>", [breadcrumbs((BRAND, "/"), ("HSK", "/en/hsk/"))], lang="en", alt=("/hsk/", "/en/hsk/")), encoding="utf-8")
    urls += [f"{BASE}/en/c/", f"{BASE}/en/p/", f"{BASE}/en/hsk/"] + k_urls + r_urls
    # lastmod не пишем: все страницы пересобираются при каждом деплое, настоящей даты изменения у них нет
    # у страниц плаката — превью в image sitemap (Google Картинки)
    img = lambda u: "".join(f"<image:image><image:loc>{i}</image:loc></image:image>" for i in radical_pages.IMAGES.get(u, ()))
    sm = "".join(f"<url><loc>{u}</loc>{img(u)}</url>" for u in urls)
    # таблица Палладия для главной: вариант чтения «Палладий» и поиск кириллицей (сян → 想)
    pyi = SITE / "data" / "pyindex.json"
    if pyi.exists():
        bases = sorted({re.sub(r"\d$", "", k) for k in json.loads(pyi.read_text(encoding="utf-8"))})
        pm = {b: palladius.syllable(b) for b in bases if palladius.syllable(b)}
        (SITE / "palladius.json").write_text(json.dumps(pm, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                                      f'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">{sm}</urlset>\n', encoding="utf-8")
    by = {}
    for u in urls:
        path = u[len(BASE):]
        en = path.startswith("/en/")
        rest = path[3:] if en else path
        k = ("en/" if en else "") + ("hub" if rest.count("/") < 2 or rest.endswith("/") else rest.split("/")[1])
        by[k] = by.get(k, 0) + 1
    print(f"static: chars={len(chars)} phrases={len(phrases)} sitemap urls={len(urls)} {by} redirects={redirects.write(SITE)}")


if __name__ == "__main__":
    main()
