"""Статические страницы 214 ключей Канси (вызывается из build_static.py):
  site/r/<hex кодпоинта>.html, site/en/r/<hex>.html — ключ: порядок черт (SVG из Make Me a Hanzi, черты пронумерованы),
      номер, число черт, пиньинь, название, варианты написания, иероглифы HSK с этим ключом, соседние ключи
  site/radicals.json — данные для игры site/radicals-game.html
  site/r/poster.html, site/en/r/poster.html, site/eo/r/poster.html — страница плаката (radicals_poster.py)
  site/r/index.html, site/en/r/index.html — указатель: сначала частые ключи (top в data/radicals.json),
      остальные под «Показать ещё», по числу черт
Данные: data/radicals.json (scripts/build_radicals.py), data/raw/mmh/graphics.txt (контуры и медианы черт).
"""
import json, shutil
from pathlib import Path

from radical_names import SUPPLEMENT
import palladius

ROOT = Path(__file__).resolve().parent.parent
GRAPHICS = ROOT / "data/raw/mmh/graphics.txt"
RADICALS = ROOT / "data/radicals.json"
IMAGES = {}   # адрес страницы → картинки для image sitemap (заполняет build)

# Страница плаката (scripts/radicals_poster.py): /r/poster, /en/r/poster, /eo/r/poster — описание, превью, скачивание.
# Сам PDF поисковик показывает голым файлом; страница даёт ему заголовок, описание, картинку и hreflang.
POSTER = {
    "ru": dict(path="/r/poster", hub="/r/", hub_name="Ключи", crumb="Плакат",
               title="Плакат 214 ключей китайских иероглифов: PDF для печати (A2, A3, A4) | Hanzi Burst",
               desc=("Бесплатный плакат со всеми 214 ключами (радикалами) Канси на одном листе: номер, варианты написания, пиньинь, "
                     "значение и примеры иероглифов. 60 частых ключей выделены. PDF для печати на A2, A3 или A4."),
               h1="Плакат: 214 ключей китайских иероглифов",
               lead=("Все 214 ключей (радикалов) Канси на одном листе — повесить над столом и сверяться, пока учите иероглифы. "
                     "Плакат бесплатный, PDF векторный: печатается чётко на любом формате."),
               dl="Скачать PDF (A2, 1,1 МБ)", alt="Плакат «214 ключей китайских иероглифов»: таблица ключей Канси по числу черт",
               what="Что на плакате",
               items=["все 214 ключей Канси, по числу черт — в том же порядке, что в словарях;",
                      "у каждого ключа номер, варианты написания (氵氺 у 水, 亻 у 人, 扌 у 手), пиньинь (цветом показан тон) и значение, слева — три иероглифа с этим ключом;",
                      "60 самых частых ключей отмечены красной точкой: в {p}% иероглифов HSK есть один из них — с них стоит начать;",
                      "легенда и QR-код на страницы ключей: там порядок черт и все иероглифы с каждым ключом."],
               print_h="Как напечатать",
               print_t=("Лист A2 (42 × 59,4 см) — в копицентре или типографии. На домашнем принтере печатайте на A3 или A4 "
                        "с масштабом «по размеру страницы»: на A4 знаки ключей около 5 мм, их всё ещё хорошо видно."),
               other_h="Плакат на других языках", more_h="Ещё про ключи",
               more=[("/r/", "Список 214 ключей со значениями и порядком черт"), ("/radicals-game?lang=ru", "Игра: учим ключи"),
                     ("/radicals-ru.pdf", "Карточки для печати (PDF, 214 ключей, 12 на лист)")],
               names={"ru": "по-русски", "en": "по-английски", "eo": "на эсперанто"}),
    "en": dict(path="/en/r/poster", hub="/en/r/", hub_name="Radicals", crumb="Poster",
               title="Chinese radicals poster: all 214 Kangxi radicals, printable PDF (A2, A3, A4) | Hanzi Burst",
               desc=("Free one-page chart of all 214 Kangxi radicals: number, variant forms, pinyin (coloured by tone), meaning and example characters. "
                     "The 60 most common radicals are highlighted. Printable PDF for A2, A3 or A4."),
               h1="Chinese radicals poster: the 214 Kangxi radicals",
               lead=("All 214 Kangxi radicals on a single sheet, to hang above your desk while you learn Chinese characters. "
                     "The poster is free and the PDF is vector, so it prints sharp at any size."),
               dl="Download the PDF (A2, 1.1 MB)", alt="Poster of the 214 Chinese radicals: Kangxi radicals chart by stroke count",
               what="What's on the poster",
               items=["all 214 Kangxi radicals by stroke count, in dictionary order;",
                      "for each radical: its number, variant forms (氵氺 for 水, 亻 for 人, 扌 for 手), pinyin (coloured by tone) and meaning, with three characters that use it on the left;",
                      "the 60 most common radicals are marked with a red dot: {p}% of HSK characters contain one of them, so start there;",
                      "a legend and a QR code to the radical pages, with stroke order and every character that uses each radical."],
               print_h="How to print",
               print_t=("A2 (420 × 594 mm) at a print shop. On a home printer, print on A3 or A4 (or Letter) with “fit to page”: "
                        "on A4 the radicals are about 5 mm tall and still easy to read."),
               other_h="The poster in other languages", more_h="More on radicals",
               more=[("/en/r/", "List of the 214 radicals with meanings and stroke order"), ("/radicals-game?lang=en", "Radicals game"),
                     ("/radicals-en.pdf", "Printable flashcards (PDF, 214 radicals, 12 per page)")],
               names={"ru": "Russian", "en": "English", "eo": "Esperanto"}),
    "eo": dict(path="/eo/r/poster", hub="/en/r/", hub_name="Radikaloj", crumb="Afiŝo",
               title="Afiŝo de la 214 ĉinaj radikaloj: PDF por presi (A2, A3, A4) | Hanzi Burst",
               desc=("Senpaga afiŝo kun ĉiuj 214 Kangxi-radikaloj sur unu folio: numero, variantoj, pinjino, signifo kaj ekzemplaj signoj. "
                     "La 60 plej oftaj radikaloj estas emfazitaj. PDF por presi en A2, A3 aŭ A4."),
               h1="Afiŝo: la 214 ĉinaj radikaloj",
               lead=("Ĉiuj 214 Kangxi-radikaloj de la ĉina skribo sur unu folio, por pendigi super la skribotablo dum vi lernas "
                     "ĉinajn signojn. La afiŝo estas senpaga, kaj la vektora PDF presiĝas klare en ĉiu formato."),
               dl="Elŝuti la PDF-on (A2, 1.1 MB)", alt="Afiŝo de la 214 ĉinaj radikaloj: tabelo de la Kangxi-radikaloj laŭ nombro de strekoj",
               what="Kio estas sur la afiŝo",
               items=["ĉiuj 214 Kangxi-radikaloj laŭ nombro de strekoj, en la vortara ordo;",
                      "ĉe ĉiu radikalo: numero, variantoj (氵氺 de 水, 亻 de 人, 扌 de 手), pinjino (la koloro montras la tonon) kaj signifo, maldekstre tri signoj kun la radikalo;",
                      "la 60 plej oftaj radikaloj estas markitaj per ruĝa punkto: {p}% de la HSK-signoj enhavas unu el ili — komencu per ili;",
                      "klarigo kaj QR-kodo al la paĝoj de la radikaloj (angle), kun strekordo kaj ĉiuj signoj kun ĉiu radikalo."],
               print_h="Kiel presi",
               print_t=("A2 (420 × 594 mm) en presejo. Per hejma presilo presu en A3 aŭ A4 kun «adapti al la paĝo»: "
                        "en A4 la radikaloj estas ĉirkaŭ 5 mm altaj kaj ankoraŭ bone legeblaj."),
               other_h="La afiŝo en aliaj lingvoj", more_h="Pli pri la radikaloj (angle)",
               more=[("/en/r/", "Listo de la 214 radikaloj kun signifoj kaj strekordo"), ("/radicals-game?lang=en", "Ludo por lerni la radikalojn"),
                     ("/radicals-en.pdf", "Kartoj por presi (PDF, 214 radikaloj)")],
               names={"ru": "ruse", "en": "angle", "eo": "Esperante"}),
}
POSTER_CSS = """<style>.pv{display:block;max-width:420px;margin:16px 0}.pv img{width:100%;height:auto;border:1px solid var(--line);border-radius:6px}
.dl{display:inline-block;margin:6px 0 4px;padding:10px 18px;border-radius:8px;background:var(--accent);color:var(--bg);text-decoration:none;font-weight:600}</style>"""


def poster_pages(SITE, page, breadcrumbs, E, BASE, pct):
    """Страницы плаката на трёх языках со взаимными hreflang. Возвращает адреса для sitemap (страницы и PDF)."""
    alts = {l: v["path"] for l, v in POSTER.items()}
    urls = []
    for lang, t in POSTER.items():
        pdf, jpg = f"/radicals-poster-{lang}.pdf", f"/radicals-poster-{lang}.jpg"
        items = "".join(f"<li>{x.format(p=pct)}</li>" for x in t["items"])
        others = " · ".join(f'<a href="{POSTER[l]["path"]}" hreflang="{l}">{t["names"][l]}</a> '
                            f'(<a href="/radicals-poster-{l}.pdf" hreflang="{l}" type="application/pdf">PDF</a>)' for l in POSTER if l != lang)
        more = "".join(f'<li><a href="{h}">{E(x)}</a></li>' for h, x in t["more"])
        body = (f"{POSTER_CSS}<h1>{E(t['h1'])}</h1><p class='m'>{E(t['lead'])}</p>"
                f'<a class="dl" href="{pdf}" type="application/pdf" download>{E(t["dl"])}</a>'
                f'<a class="pv" href="{pdf}" type="application/pdf"><img src="{jpg}" width="1000" height="1414" alt="{E(t["alt"])}"></a>'
                f"<h2>{E(t['what'])}</h2><ul>{items}</ul><h2>{E(t['print_h'])}</h2><p>{E(t['print_t'])}</p>"
                f"<h2>{E(t['other_h'])}</h2><p>{others} · <a href=\"/posters\">hanzi.lipu.dev/posters</a></p><h2>{E(t['more_h'])}</h2><ul>{more}</ul>")
        org = {"@type": "Organization", "name": "Hanzi Burst", "url": f"{BASE}/"}
        ld = [breadcrumbs(("Hanzi Burst", "/"), (t["hub_name"], t["hub"]), (t["crumb"], t["path"])),
              {"@context": "https://schema.org", "@type": "DigitalDocument", "name": t["h1"], "description": t["desc"],
               "url": f"{BASE}{t['path']}", "inLanguage": lang, "isAccessibleForFree": True, "learningResourceType": "poster",
               "educationalLevel": "beginner", "about": "Kangxi radicals", "author": org, "publisher": org,
               "image": {"@type": "ImageObject", "contentUrl": f"{BASE}{jpg}", "caption": t["alt"], "width": 1000, "height": 1414,
                         "creator": org, "creditText": "Hanzi Burst", "copyrightNotice": "Hanzi Burst"},
               "encoding": {"@type": "MediaObject", "contentUrl": f"{BASE}{pdf}", "encodingFormat": "application/pdf"}}]
        out = SITE / t["path"].lstrip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".html").write_text(page(t["title"], t["desc"], t["path"], body, ld, lang=lang, alt=alts, image=jpg), encoding="utf-8")
        urls += [f"{BASE}{t['path']}", f"{BASE}{pdf}"]
        IMAGES[f"{BASE}{t['path']}"] = [f"{BASE}{jpg}"]
    urls.append(posters_hub(SITE, page, breadcrumbs, E, BASE))
    return urls


HUB = {"ru": ("Русский", "Плакат: 214 ключей китайских иероглифов", "Скачать PDF", "Подробнее"),
       "en": ("English", "Poster: the 214 Chinese radicals", "Download PDF", "About"),
       "eo": ("Esperanto", "Afiŝo: la 214 ĉinaj radikaloj", "Elŝuti PDF", "Pli")}


def posters_hub(SITE, page, breadcrumbs, E, BASE):
    """/posters — короткий адрес, чтобы делиться: все плакаты на всех языках на одной странице (якоря #ru, #en, #eo)."""
    cards = "".join(
        f'<li id="{l}" lang="{l}"><a class="pv" href="/radicals-poster-{l}.pdf" type="application/pdf">'
        f'<img src="/radicals-poster-{l}.jpg" width="1000" height="1414" loading="lazy" alt="{E(POSTER[l]["alt"])}"></a>'
        f'<b>{nm}</b><span>{E(h)}</span><a class="dl" href="/radicals-poster-{l}.pdf" type="application/pdf" download>{E(dl)}</a> '
        f'<a href="{POSTER[l]["path"]}">{E(more)}</a></li>' for l, (nm, h, dl, more) in HUB.items())
    css = POSTER_CSS + ("<style>.ph{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:20px}"
                        ".ph li{display:flex;flex-direction:column;gap:6px}.ph .pv{margin:0}.ph span{color:var(--muted);font-size:15px}"
                        ".ph .dl{align-self:flex-start}</style>")
    body = (f"{css}<h1>Posters · Плакаты · Afiŝoj</h1>"
            "<p class='m'>Free printable posters of the 214 Chinese (Kangxi) radicals: one page, A2/A3/A4. "
            "<span lang='ru'>Бесплатные плакаты 214 ключей китайских иероглифов на одном листе.</span> "
            "<span lang='eo'>Senpagaj afiŝoj de la 214 ĉinaj radikaloj por presi.</span></p>"
            f"<ul class='ph'>{cards}</ul>")
    title = "Chinese radicals posters (PDF): English, Русский, Esperanto | Hanzi Burst"
    desc = ("Free one-page posters of the 214 Kangxi radicals in English, Russian and Esperanto: number, variants, pinyin, "
            "meaning and an example for each radical. Printable PDF, A2/A3/A4.")
    ld = [breadcrumbs(("Hanzi Burst", "/"), ("Posters", "/posters")),
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Posters · Плакаты · Afiŝoj", "url": f"{BASE}/posters",
           "description": desc, "inLanguage": list(HUB), "hasPart": [f"{BASE}{POSTER[l]['path']}" for l in HUB]}]
    (SITE / "posters.html").write_text(page(title, desc, "/posters", body, ld, lang="en", image="/radicals-poster-en.jpg"), encoding="utf-8")
    IMAGES[f"{BASE}/posters"] = [f"{BASE}/radicals-poster-{l}.jpg" for l in HUB]
    return f"{BASE}/posters"

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
               hsk="знаков HSK с этим ключом: {k}",
               game="Учить ключи в игре →", game_q="?lang=ru",
               pdf="Карточки для печати (PDF, 214 ключей)", poster="Плакат: все 214 ключей на одном листе (PDF, A2/A3/A4)"),
    "en": dict(radical="Radical", hub="Radicals", all214="The 214 Kangxi radicals", n="Number", strokes="Strokes", pinyin="Pinyin",
               meaning="Meaning", variants="Variant forms", order="Stroke order", examples="Characters with this radical",
               as_char="This sign as a character", top="Common radicals", more="Show {k} more radicals", by_strokes="{s} strokes",
               none="No HSK characters use this radical: it appears in rare and old characters.", prev="← Radical", next="Radical →",
               hsk="HSK characters with this radical: {k}",
               game="Learn the radicals in a game →", game_q="?lang=en",
               pdf="Printable flashcards (PDF, 214 radicals)", poster="Poster: all 214 radicals on one page (PDF, A2/A3/A4)"),
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
    for d in ("r", "en/r", "eo"):
        shutil.rmtree(SITE / d, ignore_errors=True); (SITE / d).mkdir(parents=True)
    urls = [f"{BASE}/r/", f"{BASE}/en/r/", f"{BASE}/radicals-game"]
    pct = round(100 * sum(r["hsk"] for r in R if r["top"]) / sum(r["hsk"] for r in R))
    urls += poster_pages(SITE, page, breadcrumbs, E, BASE, pct)
    # данные для игры /radicals-game
    (SITE / "radicals.json").write_text(json.dumps(
        [{k: r[k] for k in ("n", "char", "variants", "pinyin", "en", "ru", "hsk", "top", "examples")} for r in R],
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

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
                        + (f"<dt>Палладий</dt><dd>{E(palladius.convert(r['pinyin']))}</dd>" if lang == "ru" else "")
                        + f"<dt>{t['strokes']}</dt><dd>{sw}</dd><dt>{t['meaning']}</dt><dd>{E(name(r))}</dd></dl>")
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
            body.append(f'<a class="cta" href="/radicals-game{t["game_q"]}">{t["game"]}</a> <a href="/radicals-{lang}.pdf">{t["pdf"]}</a> · <a href="{pre}/r/poster">{t["poster"]}</a>')
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
        body = (f"{CSS}<h1>{h1}</h1><p class='m'>{intro}</p><a class='cta' href='/radicals-game{t["game_q"]}'>{t['game']}</a><p><a href='{pre}/r/poster'>{t['poster']}</a><br><a href='/radicals-{lang}.pdf'>{t['pdf']}</a> <span class='m'>· {'другой язык' if lang == 'ru' else 'other language'}: <a href='/radicals-{'en' if lang == 'ru' else 'ru'}.pdf'>{'EN' if lang == 'ru' else 'RU'}</a></span></p><h2>{t['top']}</h2><ul class='rg'>{''.join(cell(r) for r in top)}</ul>"
                f"<details class='more'><summary>{t['more'].format(k=len(rest))}</summary>{more}</details>")
        ld = [breadcrumbs(("Hanzi Burst", "/"), (t["hub"], f"{pre}/r/")),
              {"@context": "https://schema.org", "@type": "DefinedTermSet", "name": h1, "url": f"{BASE}{pre}/r/", "inLanguage": lang}]
        (SITE / pre.lstrip("/") / "r" / "index.html").write_text(
            page(title, desc, f"{pre}/r/", body, ld, lang=lang, alt=("/r/", "/en/r/")), encoding="utf-8")
    return urls, rad_of
