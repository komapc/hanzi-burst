#!/usr/bin/env python3
"""Генерирует статические страницы для поисковиков из site/phrase.json:
  site/c/<hex кодпоинта>.html — иероглиф (разбор, слова, где встречается, фразы)
  site/p/<sha1(zh)[:8]>.html  — фраза (перевод, иероглифы)
  site/c/index.html, site/p/index.html — хабы со ссылками
  site/sitemap.xml
Интерактивная версия: /?open=<иероглиф> и /?z=<фраза>. Запускается из wrangler.toml [build].
Сгенерированное не коммитится (см. .gitignore).
"""
import datetime, hashlib, html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://hanzi.lipu.dev"
E = html.escape
IS_HAN = lambda c: '一' <= c <= '鿿'
cid = lambda ch: f"{ord(ch):x}"
pid = lambda zh: hashlib.sha1(zh.encode()).hexdigest()[:8]
def first(s): return (s or "").split(";")[0].strip()
TODAY = datetime.date.today().isoformat()
# Pages are aimed at beginners (and indexed by SafeSearch-filtering engines):
# keep crude/vulgar glosses out of the word lists.
VULGAR = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|cunt|dick|cock|pussy|whore|slut|asshole|my ass|bastard|nigg\w*)\b", re.I)
def clean_word(w): return not VULGAR.search(f"{w.get('def') or ''} {w.get('def_ru') or ''}")
def ld_script(items): return "".join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>' for d in items)
def breadcrumbs(*pairs):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{BASE}{u}"} for i, (n, u) in enumerate(pairs)]}

CSS = """<style>
:root{--bg:#faf7f2;--fg:#1f1b16;--muted:#7a7166;--accent:#c8402a;--line:#cfc6b6}
@media(prefers-color-scheme:dark){:root{--bg:#17140f;--fg:#f1ebe0;--muted:#9d9486;--accent:#ff7a5c;--line:#5a5144}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 60px}
a{color:var(--accent)}h1{font-size:28px;margin:.4em 0}h2{font-size:17px;margin:1.4em 0 .4em}
.big{font:96px/1.1 'Noto Serif SC',serif;color:var(--accent)}.m{color:var(--muted)}
ul{padding-left:20px}.cta{display:inline-block;margin:12px 0;padding:8px 14px;border:1px solid var(--accent);border-radius:8px;text-decoration:none}
.chs a{display:inline-block;position:relative;margin:0 6px 6px 0;font-size:22px;text-decoration:none}
:root{--ok:#2f8f5b;--info:#2f6fd0;--warn:#d09a1f}@media(prefers-color-scheme:dark){:root{--ok:#5fcf93;--info:#6aa6ff;--warn:#e8b84a}}
a.known::after,a.allp::after,a.somep::after{content:"";position:absolute;top:2px;right:-3px;width:7px;height:7px;border-radius:50%;background:var(--ok)}
a.allp::after{background:var(--info)}a.somep::after{background:var(--warn)}
.legend{font-size:14px}.legend .k{color:var(--ok)}.legend .a{color:var(--info);margin-left:10px}.legend .s{color:var(--warn);margin-left:10px}
</style>"""


def page(title, desc, canon, body, ld=()):
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{BASE}{canon}"><meta name="robots" content="index,follow">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{BASE}/og.png"><meta property="og:url" content="{BASE}{canon}">
{ld_script(ld)}{CSS}</head><body><main><p><a href="/">hanzi-burst</a> · <a href="/c/">Иероглифы / Characters</a> · <a href="/p/">Фразы / Phrases</a> · <a href="/about">О проекте / About</a> · <a href="/privacy">Privacy</a></p>
{body}</main><script src="/static.js" defer></script></body></html>"""


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

    for d in ("c", "p"):
        shutil.rmtree(SITE / d, ignore_errors=True); (SITE / d).mkdir()
    urls = [f"{BASE}/", f"{BASE}/about", f"{BASE}/privacy", f"{BASE}/extension", f"{BASE}/c/", f"{BASE}/p/", f"{BASE}/japanese/"]
    link = lambda ch: f'<a href="/c/{cid(ch)}" data-c="{ch}">{ch}</a>' if ch in chars else ch

    for ch, c in chars.items():
        py = ", ".join(c.get("pinyin") or [])
        den, dru = c.get("definition") or "", c.get("definition_ru") or ""
        et = c.get("etymology") or {}
        body = [f'<div class="big">{ch}</div><h1>{ch} — {E(py)}</h1>']
        if dru: body.append(f"<p><b>{E(dru)}</b></p>")
        if den: body.append(f'<p class="m">{E(den)}</p>')
        body.append(f'<a class="cta" href="/?open={ch}&explode=1">Разобрать интерактивно / Break it down →</a>')
        comps = c.get("components") or []
        if comps:
            def comp(x):
                cx = chars.get(x) or {}
                p0 = (cx.get("pinyin") or [""])[0]
                return f"<li>{link(x)} {E(p0)} — {E(first(cx.get('definition_ru') or cx.get('definition')))}</li>"
            items = "".join(comp(x) for x in comps)
            body.append(f"<h2>Состав / Components</h2><ul>{items}</ul>")
        if c.get("radical"):
            body.append(f"<p class='m'>Ключ / radical: {link(c['radical'])}</p>")
        hint = et.get("hint_ru") or et.get("hint")
        if et.get("type") or hint:
            body.append(f"<p class='m'>{E(et.get('type') or '')} {E(hint or '')}</p>")
        u = usage.get(ch) or {}
        words = [w for w in (u.get("words") or []) if clean_word(w)]
        if words:
            li = "".join(f"<li>{E(w['w'])} <span class='m'>{E(w['pinyin'])}</span> — {E(w.get('def_ru') or w.get('def') or '')}</li>" for w in words)
            body.append(f"<h2>Слова / Words</h2><ul>{li}</ul>")
        if u.get("chars"):
            body.append("<h2>Иероглифы с этой частью / Characters with this part</h2><p class='chs'>" + "".join(link(x) for x in u["chars"]) + "</p>")
        ps = by_char.get(ch, [])[:8]
        if ps:
            li = "".join(f'<li><a href="/p/{pid(p["zh"])}">{E(p["zh"])}</a> — {E(p.get("ru") or p.get("en") or "")}</li>' for p in ps)
            body.append(f"<h2>Фразы / Phrases</h2><ul>{li}</ul>")
        title = f"{ch} ({py}) — {first(dru or den)} | hanzi-burst"
        desc = f"{ch} ({py}): {first(dru) or first(den)}. Разбор иероглифа на радикалы, слова и фразы. Break down the character {ch} into radicals: {first(den)}."
        ld = [breadcrumbs(("hanzi-burst", "/"), ("Иероглифы", "/c/"), (ch, f"/c/{cid(ch)}")),
              {"@context": "https://schema.org", "@type": "DefinedTerm", "name": ch, "inLanguage": "zh",
               "description": " — ".join(x for x in (py, first(dru) or first(den)) if x),
               "url": f"{BASE}/c/{cid(ch)}"}]
        (SITE / "c" / f"{cid(ch)}.html").write_text(page(title, desc[:300], f"/c/{cid(ch)}", "\n".join(body), ld), encoding="utf-8")
        urls.append(f"{BASE}/c/{cid(ch)}")

    for p in phrases:
        zh = p["zh"]
        pyl = " ".join(" ".join(w.get("pinyin") or []) if w.get("pinyin") else "" for w in p["words"] if not w.get("punct"))
        cs = []
        for w in p["words"]:
            for c in (w.get("chars") or []):
                if c not in cs: cs.append(c)
        body = [f"<h1>{E(zh)}</h1><p class='m'>{E(pyl)}</p>"]
        if p.get("ru"): body.append(f"<p><b>{E(p['ru'])}</b></p>")
        if p.get("en"): body.append(f"<p class='m'>{E(p['en'])}</p>")
        body.append(f'<a class="cta" href="/?z={E(zh)}">Разобрать по иероглифам / Open interactive →</a>')
        body.append("<h2>Иероглифы / Characters</h2><p class='chs'>" + "".join(link(c) for c in cs) + "</p>")
        rows = []
        for c in cs:
            cx = chars.get(c)
            if cx:
                rows.append(f"<li>{link(c)} <span class='m'>{E((cx.get('pinyin') or [''])[0])}</span> — "
                            f"{E(first(cx.get('definition_ru') or cx.get('definition')))}</li>")
        if rows:
            body.append("<h2>Слово за словом / Character by character</h2><ul>" + "".join(rows) + "</ul>")
        title = f"{zh} — {p.get('ru') or p.get('en')} | hanzi-burst"
        desc = f"{zh}: {p.get('ru') or ''} / {p.get('en') or ''}. Фраза с разбором иероглифов на радикалы."
        ld = [breadcrumbs(("hanzi-burst", "/"), ("Фразы", "/p/"), (zh, f"/p/{pid(zh)}"))]
        (SITE / "p" / f"{pid(zh)}.html").write_text(page(title, desc[:300], f"/p/{pid(zh)}", "\n".join(body), ld), encoding="utf-8")
        urls.append(f"{BASE}/p/{pid(zh)}")

    comps = {c: "".join(v.get("components") or []) for c, v in chars.items() if v.get("components")}
    (SITE / "comps.json").write_text(json.dumps(comps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    hub_c = "".join(link(ch) for ch in sorted(chars))
    (SITE / "c" / "index.html").write_text(page("Иероглифы / Characters | hanzi-burst",
        "Список иероглифов с разбором на радикалы / Characters broken down into radicals.", "/c/",
        f"<h1>Иероглифы / Characters</h1><p class='chs'>{hub_c}</p>",
        [breadcrumbs(("hanzi-burst", "/"), ("Иероглифы", "/c/"))]), encoding="utf-8")
    li = "".join(f'<li><a href="/p/{pid(p["zh"])}">{E(p["zh"])}</a> — {E(p.get("ru") or p.get("en") or "")}</li>' for p in phrases)
    (SITE / "p" / "index.html").write_text(page("Фразы / Phrases | hanzi-burst",
        "Простые китайские фразы с переводом и разбором / Simple Chinese phrases with translations.", "/p/",
        f"<h1>Фразы / Phrases</h1><ul>{li}</ul>",
        [breadcrumbs(("hanzi-burst", "/"), ("Фразы", "/p/"))]), encoding="utf-8")
    sm = "".join(f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>" for u in urls)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n', encoding="utf-8")
    print(f"static: chars={len(chars)} phrases={len(phrases)} urls={len(urls)}")


if __name__ == "__main__":
    main()
