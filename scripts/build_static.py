#!/usr/bin/env python3
"""Генерирует статические страницы для поисковиков из site/phrase.json:
  site/c/<hex кодпоинта>.html — иероглиф (разбор, слова, где встречается, фразы)
  site/p/<sha1(zh)[:8]>.html  — фраза (перевод, иероглифы)
  site/hsk/<1–7>.html          — знаки уровня HSK 3.0 (7 = уровни 7–9) с чтением и значением
  site/c/index.html, site/p/index.html, site/hsk/index.html — хабы со ссылками
  site/sitemap.xml
Интерактивная версия: /?open=<иероглиф> и /?z=<фраза>. Запускается из wrangler.toml [build].
Сгенерированное не коммитится (см. .gitignore).
Основной язык страниц русский (lang="ru"); английские дубли помечены lang="en", китайский текст lang="zh".
"""
import glob, hashlib, html, json, re, shutil
from pathlib import Path

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
EN = lambda s: f'<span lang="en">{s}</span>'
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
.big{font:96px/1.1 'Noto Serif SC',serif;color:var(--accent)}.m{color:var(--muted)}
ul{padding-left:20px}.cta{display:inline-block;margin:12px 0;padding:8px 14px;border:1px solid var(--accent);border-radius:8px;text-decoration:none}
.chs a{display:inline-block;position:relative;margin:0 6px 6px 0;font-size:22px;text-decoration:none}
:root{--ok:#2f8f5b;--info:#2f6fd0;--warn:#d09a1f}@media(prefers-color-scheme:dark){:root{--ok:#5fcf93;--info:#6aa6ff;--warn:#e8b84a}}
a.known::after,a.allp::after,a.somep::after{content:"";position:absolute;top:2px;right:-3px;width:7px;height:7px;border-radius:50%;background:var(--ok)}
a.allp::after{background:var(--info)}a.somep::after{background:var(--warn)}
.hl{list-style:none;padding:0}.hl li{margin:2px 0}.hl a{font:24px/1.3 'Noto Serif SC',serif;text-decoration:none;margin-right:6px}
.legend{font-size:14px}.legend .k{color:var(--ok)}.legend .a{color:var(--info);margin-left:10px}.legend .s{color:var(--warn);margin-left:10px}
</style>"""


def page(title, desc, canon, body, ld=()):
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{BASE}{canon}"><meta name="robots" content="index,follow">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{BASE}/og.png"><meta property="og:site_name" content="{BRAND}"><meta property="og:url" content="{BASE}{canon}">
{ld_script(ld)}{CSS}</head><body><main><p><a href="/">Hanzi Burst</a> · <a href="/c/">Иероглифы</a> · <a href="/p/">Фразы</a> · <a href="/hsk/">HSK</a> · <a href="/about">О проекте</a> · <a href="/privacy">Конфиденциальность</a></p>
{body}<div id="sitefoot"></div><script src="/footer.js" defer></script></main><script src="/static.js" defer></script></body></html>"""


def main():
    D = json.load(open(SITE / "phrase.json", encoding="utf-8"))
    chars, usage = D["chars"], json.load(open(SITE / "usage.json", encoding="utf-8"))
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
    urls = [f"{BASE}/", f"{BASE}/about", f"{BASE}/privacy", f"{BASE}/extension", f"{BASE}/c/", f"{BASE}/p/", f"{BASE}/hsk/", f"{BASE}/japanese/"]
    link = lambda ch: f'<a href="/c/{cid(ch)}" data-c="{ch}">{ch}</a>' if ch in chars else ch

    for ch, c in chars.items():
        py = ", ".join(c.get("pinyin") or [])
        den, dru = c.get("definition") or "", c.get("definition_ru") or ""
        et = c.get("etymology") or {}
        kind = "Ключ" if c.get("radical") == ch else "Иероглиф"
        body = [f'<div class="big" lang="zh">{ch}</div><h1>{kind} {ZH(ch)} — {E(py)}</h1>']
        if dru: body.append(f"<p><b>{E(dru)}</b></p>")
        if den: body.append(f'<p class="m" lang="en">{E(den)}</p>')
        body.append(f'<a class="cta" href="/?open={ch}&explode=1">Разобрать интерактивно →</a>')
        comps = c.get("components") or []
        if comps:
            def comp(x):
                cx = chars.get(x) or {}
                p0 = (cx.get("pinyin") or [""])[0]
                return f"<li>{link(x)} {E(p0)} — {gloss(first(cx.get('definition_ru')), first(cx.get('definition')))}</li>"
            items = "".join(comp(x) for x in comps)
            body.append(f"<h2>Состав / {EN("Components")}</h2><ul>{items}</ul>")
        if c.get("radical"):
            body.append(f"<p class='m'>Ключ / {EN("radical")}: {link(c['radical'])}</p>")
        hint = et.get("hint_ru") or et.get("hint")
        if et.get("type") or hint:
            body.append(f"<p class='m'>{EN(E(et['type'])) if et.get('type') else ''} {E(hint or '')}</p>")
        u = usage.get(ch) or {}
        words = [w for w in (u.get("words") or []) if clean_word(w)]
        if words:
            li = "".join(f"<li>{ZH(E(w['w']))} <span class='m'>{E(w['pinyin'])}</span> — {gloss(w.get('def_ru'), w.get('def'))}</li>" for w in words)
            body.append(f"<h2>Слова / {EN('Words')}</h2><ul>{li}</ul>")
        if u.get("chars"):
            body.append(f"<h2>Иероглифы с этой частью / {EN('Characters with this part')}</h2><p class='chs' lang='zh'>" + "".join(link(x) for x in u["chars"]) + "</p>")
        ps = by_char.get(ch, [])[:8]
        if ps:
            li = "".join(f'<li><a href="/p/{pid(p["zh"])}" lang="zh">{E(p["zh"])}</a> — {gloss(p.get("ru"), p.get("en"))}</li>' for p in ps)
            body.append(f"<h2>Фразы / {EN('Phrases')}</h2><ul>{li}</ul>")
        meaning = first(dru) or first(den)
        if c.get("radical") == ch:   # сам является ключом (радикалом)
            title = f"Ключ {ch} ({py}): значение и иероглифы с ним | Hanzi Burst"
            desc = f"Иероглиф и ключ {ch} ({py}): {meaning}. Пиньинь, значение, иероглифы с этим ключом (радикалом), слова и фразы."
        else:
            title = f"Иероглиф {ch} ({py}): значение и разбор на ключи | Hanzi Burst"
            desc = f"Иероглиф {ch} ({py}) — {meaning}. Разбор иероглифа на ключи (радикалы) и составные части, пиньинь, слова и фразы с ним."
        ld = [breadcrumbs((BRAND, "/"), ("Иероглифы", "/c/"), (ch, f"/c/{cid(ch)}")),
              {"@context": "https://schema.org", "@type": "DefinedTerm", "name": ch, "inLanguage": "zh",
               "description": " — ".join(x for x in (py, first(dru) or first(den)) if x),
               "url": f"{BASE}/c/{cid(ch)}"}]
        (SITE / "c" / f"{cid(ch)}.html").write_text(page(title, desc[:300], f"/c/{cid(ch)}", "\n".join(body), ld), encoding="utf-8")
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
        body.append(f"<h2>Иероглифы / {EN('Characters')}</h2><p class='chs' lang='zh'>" + "".join(link(c) for c in cs) + "</p>")
        rows = []
        for c in cs:
            cx = chars.get(c)
            if cx:
                rows.append(f"<li>{link(c)} <span class='m'>{E((cx.get('pinyin') or [''])[0])}</span> — "
                            f"{gloss(first(cx.get('definition_ru')), first(cx.get('definition')))}</li>")
        if rows:
            body.append(f"<h2>Слово за словом / {EN('Character by character')}</h2><ul>" + "".join(rows) + "</ul>")
        tr = p.get('ru') or p.get('en') or ''
        short = tr if len(tr) <= 40 else tr[:39].rstrip() + "…"
        title = f"{zh} — перевод и пиньинь: {short} | Hanzi Burst"
        desc = f"{zh} ({pyl}): {tr}. Китайская фраза с пиньинем, переводом и разбором иероглифов на ключи (радикалы)."
        ld = [breadcrumbs((BRAND, "/"), ("Фразы", "/p/"), (zh, f"/p/{pid(zh)}"))]
        (SITE / "p" / f"{pid(zh)}.html").write_text(page(title, desc[:300], f"/p/{pid(zh)}", "\n".join(body), ld), encoding="utf-8")

    comps = {c: "".join(v.get("components") or []) for c, v in chars.items() if v.get("components")}
    (SITE / "comps.json").write_text(json.dumps(comps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    hub_c = "".join(link(ch) for ch in sorted(chars))
    (SITE / "c" / "index.html").write_text(page(f"Все иероглифы и ключи-радикалы ({len(chars)}) | Hanzi Burst",
        f"{len(chars)} китайских иероглифов и радикалов с пиньинем, значением и разбором на составные части. Нажмите на знак, чтобы открыть его страницу.", "/c/",
        f"<h1>Иероглифы и радикалы</h1><p class='m'>Всего знаков: {len(chars)} — все, что встречаются во фразах сайта, включая радикалы (ключи) и их варианты. "
        f"Списки по уровням — в разделе <a href='/hsk/'>HSK</a>, примеры употребления — во <a href='/p/'>фразах</a>.</p><p class='chs' lang='zh'>{hub_c}</p>",
        [breadcrumbs((BRAND, "/"), ("Иероглифы", "/c/"))]), encoding="utf-8")
    li = "".join(f'<li><a href="/p/{pid(p["zh"])}" lang="zh">{E(p["zh"])}</a> — {gloss(p.get("ru"), p.get("en"))}</li>' for p in phrases)
    (SITE / "p" / "index.html").write_text(page(f"Простые китайские фразы с переводом ({len(phrases)}) | Hanzi Burst",
        f"{len(phrases)} простых китайских фраз с переводом и разбором каждого иероглифа на радикалы. Подходит для начинающих.", "/p/",
        f"<h1>Китайские фразы с переводом</h1><ul>{li}</ul>",
        [breadcrumbs((BRAND, "/"), ("Фразы", "/p/"))]), encoding="utf-8")
    # HSK: значения всех знаков уровня из словарных шардов (в phrase.json только знаки фраз)
    allc = {}
    for f in glob.glob(str(SITE / "data" / "chars" / "*.json")):
        allc.update(json.load(open(f, encoding="utf-8")))
    lvname = lambda lv: "7–9" if lv == "7" else lv
    nav = " · ".join(f'<a href="/hsk/{lv}">HSK {lvname(lv)}</a>' for lv in hsk)
    for lv, cs in hsk.items():
        rows = []
        for ch in cs:
            cx = allc.get(ch) or {}
            href = f"/c/{cid(ch)}" if ch in chars else f"/?open={ch}"
            rows.append(f'<li><a href="{href}" data-c="{ch}" lang="zh">{ch}</a> <span class="m">{E(", ".join(cx.get("pinyin") or []))}</span> — '
                        f'{gloss(first(cx.get("definition_ru")), first(cx.get("definition")))}</li>')
        title = f"Иероглифы HSK {lvname(lv)} ({len(cs)}) — список с чтением и значением | Hanzi Burst"
        desc = (f"Все {len(cs)} иероглифов уровня HSK {lvname(lv)} (HSK 3.0) с пиньинем и переводом, от частых к редким, "
                f"с разбором каждого знака на радикалы.")
        body = (f"<h1>Иероглифы HSK {lvname(lv)}</h1>"
                f"<p class='m'>{len(cs)} новых знаков уровня по стандарту HSK 3.0, от частых к редким. "
                f"Нажмите на знак, чтобы разобрать его на части.</p>"
                f"<p>{nav}</p><a class='cta' href='/learned'>Мой прогресс по HSK →</a><ul class='hl'>{''.join(rows)}</ul>")
        ld = [breadcrumbs((BRAND, "/"), ("HSK", "/hsk/"), (f"HSK {lvname(lv)}", f"/hsk/{lv}"))]
        (SITE / "hsk" / f"{lv}.html").write_text(page(title, desc, f"/hsk/{lv}", body, ld), encoding="utf-8")
        urls.append(f"{BASE}/hsk/{lv}")
    li = "".join(f'<li><a href="/hsk/{lv}">HSK {lvname(lv)}</a> — {len(cs)} знаков: '
                 f'<span lang="zh">{"".join(cs[:12])}…</span></li>' for lv, cs in hsk.items())
    (SITE / "hsk" / "index.html").write_text(page("Иероглифы HSK 1–9 по уровням | Hanzi Burst",
        "Списки иероглифов HSK 3.0 по уровням 1–9 с пиньинем и переводом на русский. Каждый знак можно разобрать на радикалы.", "/hsk/",
        f"<h1>Иероглифы HSK по уровням</h1><ul>{li}</ul>",
        [breadcrumbs((BRAND, "/"), ("HSK", "/hsk/"))]), encoding="utf-8")
    # lastmod не пишем: все страницы пересобираются при каждом деплое, настоящей даты изменения у них нет
    sm = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n', encoding="utf-8")
    by = {}
    for u in urls:
        path = u[len(BASE):]
        k = "hub" if path.count("/") < 2 or path.endswith("/") else path.split("/")[1]
        by[k] = by.get(k, 0) + 1
    print(f"static: chars={len(chars)} phrases={len(phrases)} sitemap urls={len(urls)} {by}")


if __name__ == "__main__":
    main()
