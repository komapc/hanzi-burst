#!/usr/bin/env python3
"""Генерирует статические страницы для поисковиков из site/phrase.json:
  site/c/<hex кодпоинта>.html — иероглиф (разбор, слова, где встречается, фразы)
  site/p/<sha1(zh)[:8]>.html  — фраза (перевод, иероглифы)
  site/c/index.html, site/p/index.html — хабы со ссылками
  site/sitemap.xml
Интерактивная версия: /?open=<иероглиф> и /?z=<фраза>. Запускается из wrangler.toml [build].
Сгенерированное не коммитится (см. .gitignore).
"""
import hashlib, html, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://hanzi-burst.komapc.workers.dev"
E = html.escape
IS_HAN = lambda c: '一' <= c <= '鿿'
cid = lambda ch: f"{ord(ch):x}"
pid = lambda zh: hashlib.sha1(zh.encode()).hexdigest()[:8]
def first(s): return (s or "").split(";")[0].strip()

CSS = """<style>
:root{--bg:#faf7f2;--fg:#1f1b16;--muted:#7a7166;--accent:#c8402a;--line:#cfc6b6}
@media(prefers-color-scheme:dark){:root{--bg:#17140f;--fg:#f1ebe0;--muted:#9d9486;--accent:#ff7a5c;--line:#5a5144}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 60px}
a{color:var(--accent)}h1{font-size:28px;margin:.4em 0}h2{font-size:17px;margin:1.4em 0 .4em}
.big{font:96px/1.1 'Noto Serif SC',serif;color:var(--accent)}.m{color:var(--muted)}
ul{padding-left:20px}.cta{display:inline-block;margin:12px 0;padding:8px 14px;border:1px solid var(--accent);border-radius:8px;text-decoration:none}
.chs a{display:inline-block;margin:0 6px 6px 0;font-size:22px;text-decoration:none}
</style>"""


def page(title, desc, canon, body):
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{BASE}{canon}"><meta name="robots" content="index,follow">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{BASE}/og.png"><meta property="og:url" content="{BASE}{canon}">
{CSS}</head><body><main><p><a href="/">hanzi-burst</a> · <a href="/c/">Иероглифы / Characters</a> · <a href="/p/">Фразы / Phrases</a> · <a href="/about">О проекте / About</a></p>
{body}</main></body></html>"""


def main():
    D = json.load(open(SITE / "phrase.json", encoding="utf-8"))
    chars, usage = D["chars"], D["usage"]
    phrases = D["phrases"] + D["pool"]
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
    urls = [f"{BASE}/", f"{BASE}/about", f"{BASE}/c/", f"{BASE}/p/"]
    link = lambda ch: f'<a href="/c/{cid(ch)}">{ch}</a>' if ch in chars else ch

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
        if u.get("words"):
            li = "".join(f"<li>{E(w['w'])} <span class='m'>{E(w['pinyin'])}</span> — {E(w.get('def_ru') or w.get('def') or '')}</li>" for w in u["words"])
            body.append(f"<h2>Слова / Words</h2><ul>{li}</ul>")
        if u.get("chars"):
            body.append("<h2>Иероглифы с этой частью / Characters with this part</h2><p class='chs'>" + "".join(link(x) for x in u["chars"]) + "</p>")
        ps = by_char.get(ch, [])[:8]
        if ps:
            li = "".join(f'<li><a href="/p/{pid(p["zh"])}">{E(p["zh"])}</a> — {E(p.get("ru") or p.get("en") or "")}</li>' for p in ps)
            body.append(f"<h2>Фразы / Phrases</h2><ul>{li}</ul>")
        title = f"{ch} ({py}) — {first(dru or den)} | hanzi-burst"
        desc = f"{ch} ({py}): {first(dru) or first(den)}. Разбор иероглифа на радикалы, слова и фразы. Break down the character {ch} into radicals: {first(den)}."
        (SITE / "c" / f"{cid(ch)}.html").write_text(page(title, desc[:300], f"/c/{cid(ch)}", "\n".join(body)), encoding="utf-8")
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
        title = f"{zh} — {p.get('ru') or p.get('en')} | hanzi-burst"
        desc = f"{zh}: {p.get('ru') or ''} / {p.get('en') or ''}. Фраза с разбором иероглифов на радикалы."
        (SITE / "p" / f"{pid(zh)}.html").write_text(page(title, desc[:300], f"/p/{pid(zh)}", "\n".join(body)), encoding="utf-8")
        urls.append(f"{BASE}/p/{pid(zh)}")

    hub_c = "".join(link(ch) for ch in sorted(chars))
    (SITE / "c" / "index.html").write_text(page("Иероглифы / Characters | hanzi-burst",
        "Список иероглифов с разбором на радикалы / Characters broken down into radicals.", "/c/",
        f"<h1>Иероглифы / Characters</h1><p class='chs'>{hub_c}</p>"), encoding="utf-8")
    li = "".join(f'<li><a href="/p/{pid(p["zh"])}">{E(p["zh"])}</a> — {E(p.get("ru") or p.get("en") or "")}</li>' for p in phrases)
    (SITE / "p" / "index.html").write_text(page("Фразы / Phrases | hanzi-burst",
        "Простые китайские фразы с переводом и разбором / Simple Chinese phrases with translations.", "/p/",
        f"<h1>Фразы / Phrases</h1><ul>{li}</ul>"), encoding="utf-8")
    sm = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n', encoding="utf-8")
    print(f"static: chars={len(chars)} phrases={len(phrases)} urls={len(urls)}")


if __name__ == "__main__":
    main()
