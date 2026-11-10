"""Статические страницы 214 ключей Канси (вызывается из build_static.py):
  site/r/<hex кодпоинта>.html, site/en/r/<hex>.html — ключ: порядок черт (SVG из Make Me a Hanzi, черты пронумерованы),
      номер, число черт, пиньинь, название, варианты написания, иероглифы HSK с этим ключом, соседние ключи
  site/r/index.html, site/en/r/index.html — указатель: сначала частые ключи (top в data/radicals.json),
      остальные под «Показать ещё», по числу черт
Данные: data/radicals.json (scripts/build_radicals.py), data/raw/mmh/graphics.txt (контуры и медианы черт).
"""
import json, shutil
from pathlib import Path

from radical_names import SUPPLEMENT

ROOT = Path(__file__).resolve().parent.parent
GRAPHICS = ROOT / "data/raw/mmh/graphics.txt"
RADICALS = ROOT / "data/radicals.json"

CSS = """<style>
.rsvg{width:220px;height:220px;display:block}.rsvg text{font:bold 64px system-ui,sans-serif;fill:var(--fg);paint-order:stroke;stroke:var(--bg);stroke-width:14px}
.vsvg{width:64px;height:64px;vertical-align:middle}.vars span{display:inline-block;margin-right:14px;text-align:center}
.vars .f{font:52px/64px 'Noto Serif SC',serif}
.facts{display:grid;grid-template-columns:max-content 1fr;gap:2px 14px;margin:8px 0}.facts dt{color:var(--muted)}.facts dd{margin:0}
.rg{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:8px;padding:0;list-style:none}
.rg a{display:block;position:relative;padding:6px 4px;border:1px solid var(--line);border-radius:8px;text-align:center;text-decoration:none;color:var(--fg)}
.rg a:hover{border-color:var(--accent)}.rg .c{font:34px/1.2 'Noto Serif SC',serif;color:var(--accent)}.rg .v{font-size:18px;margin-left:4px;color:var(--muted)}
.rg small{display:block;font-size:12.5px;color:var(--muted);line-height:1.25}
details.more{margin:18px 0}details.more summary{cursor:pointer;font-weight:600;color:var(--accent)}
.pn{display:flex;justify-content:space-between;margin-top:20px}
</style>"""

T = {
    "ru": dict(radical="Ключ", hub="Ключи", all214="214 ключей китайских иероглифов", n="Номер", strokes="Черт", pinyin="Пиньинь",
               meaning="Значение", variants="Варианты написания", order="Порядок черт", examples="Иероглифы с этим ключом",
               as_char="Этот знак как иероглиф", top="Частые ключи", more="Показать ещё {k} ключей", by_strokes="{s} черт",
               none="Среди иероглифов HSK этого ключа нет: он встречается в редких и старых знаках.", prev="← Ключ", next="Ключ →",
               hsk="знаков HSK с этим ключом: {k}", interactive="Разобрать интерактивно →"),
    "en": dict(radical="Radical", hub="Radicals", all214="The 214 Kangxi radicals", n="Number", strokes="Strokes", pinyin="Pinyin",
               meaning="Meaning", variants="Variant forms", order="Stroke order", examples="Characters with this radical",
               as_char="This sign as a character", top="Common radicals", more="Show {k} more radicals", by_strokes="{s} strokes",
               none="No HSK characters use this radical: it appears in rare and old characters.", prev="← Radical", next="Radical →",
               hsk="HSK characters with this radical: {k}", interactive="Break it down interactively →"),
}


def strokes_word(n):
    """«черта/черты/черт» для русского."""
    if n % 10 == 1 and n % 100 != 11: return "черта"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14: return "черты"
    return "черт"


def load_graphics(need):
    g = {}
    for line in open(GRAPHICS, encoding="utf-8"):
        d = json.loads(line)
        if d["character"] in need:
            g[d["character"]] = d
    return g


def svg(d, cls="rsvg", numbers=True, label=""):
    """Контуры MMH: viewBox 1024, ось Y вверх (как hz() в index.html). Цвет черты темнеет от первой к последней, номера у начала медиан."""
    n = len(d["strokes"])
    paths = "".join(
        f'<path d="{p}" fill="hsl(10,{55 + 10 * i // max(n - 1, 1)}%,{62 - 30 * i // max(n - 1, 1)}%)"/>' for i, p in enumerate(d["strokes"]))
    nums = ""
    if numbers:
        placed = []
        for i, m in enumerate(d["medians"]):
            x, y = m[0][0], 900 - m[0][1]
            while any(abs(x - a) < 70 and abs(y - b) < 70 for a, b in placed):   # начала черт совпадают (口, 言): сдвигаем номер
                x += 70
            placed.append((x, y))
            nums += f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle">{i + 1}</text>'
    aria = f' role="img" aria-label="{label}"' if label else ' aria-hidden="true"'
    return (f'<svg class="{cls}" viewBox="0 0 1024 1024"{aria}><g transform="scale(1,-1) translate(0,-900)">{paths}</g>{nums}</svg>')


def build(SITE, page, breadcrumbs, E, BASE, chars, allc, first):
    """Пишет site/r/ и site/en/r/. Возвращает (адреса для sitemap, {знак: [(номер ключа, знак ключа)]} — для ссылок со страниц /c/)."""
    R = json.loads(RADICALS.read_text(encoding="utf-8"))
    by_n = {r["n"]: r for r in R}
    need = {r["char"] for r in R} | {v for r in R for v in r["variants"]}
    G = load_graphics(need)
    cid = lambda ch: f"{ord(ch):x}"
    rad_of = {}
    for r in R:
        for c in [r["char"], *r["variants"]]:
            rad_of.setdefault(c, []).append((r["n"], r["char"]))
    for c, n in SUPPLEMENT.items():   # формы, которые MMH пишет в поле radical (⺼, ⺮…)
        rad_of.setdefault(c, []).append((n, by_n[n]["char"]))
    for d in ("r", "en/r"):
        shutil.rmtree(SITE / d, ignore_errors=True); (SITE / d).mkdir(parents=True)
    urls = [f"{BASE}/r/", f"{BASE}/en/r/"]

    def meaning(c, lang):
        x = allc.get(c) or (chars.get(c) or {})
        return first(x.get("definition_ru")) if lang == "ru" and x.get("definition_ru") else first(x.get("definition"))

    for lang in ("ru", "en"):
        t, pre = T[lang], ("/en" if lang == "en" else "")
        name = lambda r: r[lang]
        def ex_link(c):
            if c in chars:
                return f'<a href="{pre}/c/{cid(c)}" data-c="{c}" lang="zh">{c}</a>'
            return f'<a href="/?open={c}' + ("&amp;lang=en" if lang == "en" else "") + f'" data-c="{c}" lang="zh">{c}</a>'
        for r in R:
            ch, n = r["char"], r["n"]
            vs = "".join(r["variants"])
            body = [CSS]
            g = G.get(ch)
            body.append(svg(g, label=f"{t['order']} {ch}") if g else f'<div class="big" lang="zh">{ch}</div>')
            h1_extra = f" ({E('、'.join(r['variants']))})" if vs else ""
            body.append(f"<h1>{t['radical']} <span lang='zh'>{ch}</span>{h1_extra} — {E(name(r))}</h1>")
            sw = f"{r['strokes']} {strokes_word(r['strokes'])}" if lang == "ru" else f"{r['strokes']} stroke{'s' if r['strokes'] != 1 else ''}"
            body.append(f"<dl class='facts'><dt>{t['n']}</dt><dd>{n} / 214</dd><dt>{t['pinyin']}</dt><dd>{E(r['pinyin'])}</dd>"
                        f"<dt>{t['strokes']}</dt><dd>{sw}</dd><dt>{t['meaning']}</dt><dd>{E(name(r))}</dd></dl>")
            if r["variants"]:
                cells = "".join(f"<span>{svg(G[v], 'vsvg', False) if v in G else f'<span class=f>{v}</span>'}<br><span lang='zh'>{v}</span></span>"
                                for v in r["variants"])
                body.append(f"<h2>{t['variants']}</h2><p class='vars' lang='zh'>{cells}</p>")
            if r["examples"]:
                li = "".join(f"<li>{ex_link(c)} <span class='m'>{E(', '.join((allc.get(c) or {}).get('pinyin') or []))}</span> — "
                             f"{E(meaning(c, lang) or '')}</li>" for c in r["examples"])
                body.append(f"<h2>{t['examples']}</h2><p class='m'>{t['hsk'].format(k=r['hsk'])}</p><ul class='hl'>{li}</ul>")
            else:
                body.append(f"<h2>{t['examples']}</h2><p class='m'>{t['none']}</p>")
            own = [c for c in [ch, *r["variants"]] if c in chars]
            if own:
                body.append(f"<p>{t['as_char']}: " + " ".join(f'<a href="{pre}/c/{cid(c)}" data-c="{c}" lang="zh">{c}</a>' for c in own) + "</p>")
                body.append(f'<a class="cta" href="/?open={own[0]}&amp;explode=1' + ("&amp;lang=en" if lang == "en" else "") + f'">{t["interactive"]}</a>')
            pv, nx = by_n.get(n - 1), by_n.get(n + 1)
            body.append("<p class='pn'>" + (f'<a href="{pre}/r/{cid(pv["char"])}">{t["prev"]} {pv["char"]}</a>' if pv else "<span></span>")
                        + f'<a href="{pre}/r/">{t["hub"]}</a>'
                        + (f'<a href="{pre}/r/{cid(nx["char"])}">{nx["char"]} {t["next"]}</a>' if nx else "<span></span>") + "</p>")
            exs = "、".join(r["examples"][:6])
            if lang == "ru":
                title = f"Ключ {ch}{h1_extra} — {r['ru']} ({r['pinyin']}, №{n}): значение и иероглифы с ним | Hanzi Burst"
                desc = (f"Ключ (радикал) {ch} {r['pinyin']} — «{r['ru']}», №{n} из 214 ключей Канси, {sw}. Порядок черт"
                        + (f", варианты {'、'.join(r['variants'])}" if vs else "") + (f" и иероглифы с этим ключом: {exs}." if exs else "."))
            else:
                title = f"Radical {ch}{h1_extra} {r['pinyin']} ({r['en']}, No. {n}): meaning and characters | Hanzi Burst"
                desc = (f"Chinese radical {ch} {r['pinyin']}, \"{r['en']}\", Kangxi radical {n} of 214, {sw}. Stroke order"
                        + (f", variant forms {', '.join(r['variants'])}" if vs else "") + (f" and characters with this radical: {exs}." if exs else "."))
            path = f"{pre}/r/{cid(ch)}"
            ld = [breadcrumbs(("Hanzi Burst", "/"), (t["hub"], f"{pre}/r/"), (ch, path)),
                  {"@context": "https://schema.org", "@type": "DefinedTerm", "name": ch, "inLanguage": "zh",
                   "description": f"{r['pinyin']} — {name(r)}", "url": f"{BASE}{path}",
                   "inDefinedTermSet": f"{BASE}{pre}/r/"}]
            (SITE / path.lstrip("/")).with_suffix(".html").write_text(
                page(title, desc[:300], path, "\n".join(body), ld, lang=lang, alt=(f"/r/{cid(ch)}", f"/en/r/{cid(ch)}")), encoding="utf-8")
            urls.append(f"{BASE}{path}")

        def cell(r):
            v = f"<span class='v'>{''.join(r['variants'][:2])}</span>" if r["variants"] else ""
            return (f'<li><a href="{pre}/r/{cid(r["char"])}" data-c="{r["char"]}"><span class="c" lang="zh">{r["char"]}</span>{v}'
                    f"<small>{r['n']} · {E(name(r))}</small></a></li>")
        top = sorted((r for r in R if r["top"]), key=lambda r: (-r["hsk"], r["n"]))
        rest = [r for r in R if not r["top"]]
        groups = {}
        for r in rest:
            groups.setdefault(r["strokes"], []).append(r)
        more = "".join(f"<h3>{t['by_strokes'].format(s=s) if lang == 'en' else f'{s} {strokes_word(s)}'}</h3><ul class='rg'>{''.join(cell(r) for r in rs)}</ul>"
                       for s, rs in sorted(groups.items()))
        if lang == "ru":
            title, h1 = "214 ключей китайских иероглифов (радикалы Канси): список со значениями | Hanzi Burst", "214 ключей китайских иероглифов"
            intro = (f"Ключ (радикал) — часть иероглифа, по которой его ищут в словаре и которая часто подсказывает смысл: "
                     f"氵 — вода, 扌 — рука, 口 — рот. Сначала {len(top)} самых частых ключей: из них собрано большинство иероглифов HSK. "
                     f"Нажмите на ключ, чтобы увидеть порядок черт, варианты написания и иероглифы с ним.")
            desc = ("Все 214 ключей (радикалов) Канси: номер, значение, число черт, варианты написания (氵扌亻忄…) и порядок черт. "
                    f"Сначала {len(top)} самых частых ключей, затем остальные по числу черт.")
        else:
            title, h1 = "The 214 Kangxi radicals: list of Chinese radicals with meanings | Hanzi Burst", "The 214 Kangxi radicals"
            intro = (f"A radical is the part of a character used to look it up in a dictionary, and it often hints at the meaning: "
                     f"氵 water, 扌 hand, 口 mouth. The {len(top)} most common radicals come first: they build most HSK characters. "
                     f"Click a radical for its stroke order, variant forms and characters that use it.")
            desc = ("All 214 Kangxi radicals with number, meaning, stroke count, variant forms (氵扌亻忄…) and stroke order. "
                    f"The {len(top)} most common radicals first, the rest by stroke count.")
        body = (f"{CSS}<h1>{h1}</h1><p class='m'>{intro}</p><h2>{t['top']}</h2><ul class='rg'>{''.join(cell(r) for r in top)}</ul>"
                f"<details class='more'><summary>{t['more'].format(k=len(rest))}</summary>{more}</details>")
        ld = [breadcrumbs(("Hanzi Burst", "/"), (t["hub"], f"{pre}/r/")),
              {"@context": "https://schema.org", "@type": "DefinedTermSet", "name": h1, "url": f"{BASE}{pre}/r/", "inLanguage": lang}]
        (SITE / pre.lstrip("/") / "r" / "index.html").write_text(
            page(title, desc, f"{pre}/r/", body, ld, lang=lang, alt=("/r/", "/en/r/")), encoding="utf-8")
    return urls, rad_of
