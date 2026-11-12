#!/usr/bin/env python3
"""Плакат «214 ключей» на одну страницу: site/radicals-poster-{ru,en,eo}.pdf и превью site/radicals-poster-{ru,en,eo}.jpg
(запускается вручную, PDF и JPEG коммитятся; страницы плаката /r/poster собирает radical_pages.py).

Лист A2 (420 × 594 мм), вектор: печатается и на A3/A4 с уменьшением. Ключи сгруппированы по числу черт, как в словарях;
у каждого номер, варианты написания, пиньинь (цвет — тон, как «Тоны» на сайте), значение и три иероглифа с ним.
Стиль строгий: чёрный, каллиграфический шрифт; красные только печать 部首 и точки у 60 частых ключей (по числу знаков HSK). В шапке легенда, доля HSK-иероглифов с частыми ключами и QR-код на /r/.

Нужны: data/radicals.json, google-chrome, шрифт LXGW WenKai (OFL, github.com/lxgw/LxgwWenKai: LXGWWenKai-Medium.ttf
в ~/.local/share/fonts; без него — Noto Serif CJK).
QR-код — пакет segno, метаданные PDF — pypdf (pip install segno pypdf); без них плакат собирается без QR / без метаданных.
Превью — ImageMagick (convert).
  python3 scripts/radicals_poster.py
"""
import html, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radical_pages
from radical_pages import strokes_word

ROOT = Path(__file__).resolve().parent.parent
E = html.escape
COLS, ROWS = 12, 20

TXT = {
    "ru": dict(title="214 ключей китайских иероглифов",
               sub="Ключи (радикалы) Канси по числу черт: номер, варианты, пиньинь, значение и примеры",
               top="частый ключ", stat="{p}% иероглифов HSK содержат один из 60 частых ключей — начните с них",
               lg_n="номер", lg_var="варианты", lg_py="пиньинь", lg_mean="значение", lg_ex="примеры", lg_tone="цвет — тон",
               url="hanzi.lipu.dev/r/", qr="https://hanzi.lipu.dev/r/",
               more="Порядок черт, все варианты и иероглифы с каждым ключом — на сайте. Там же игра для запоминания.",
               src="Данные: Unicode Unihan (kRSUnicode), Make Me a Hanzi, HSK 3.0 · Hanzi Burst"),
    "en": dict(title="The 214 Chinese radicals",
               sub="Kangxi radicals by stroke count: number, variant forms, pinyin, meaning and examples",
               top="common radical", stat="{p}% of HSK characters contain one of the 60 common radicals — start with those",
               lg_n="number", lg_var="variants", lg_py="pinyin", lg_mean="meaning", lg_ex="examples", lg_tone="colour = tone",
               url="hanzi.lipu.dev/en/r/", qr="https://hanzi.lipu.dev/en/r/",
               more="Stroke order, every variant and the characters that use each radical are on the site, plus a game to learn them.",
               src="Data: Unicode Unihan (kRSUnicode), Make Me a Hanzi, HSK 3.0 · Hanzi Burst"),
    # эсперанто: страниц ключей на эсперанто нет, поэтому QR и адрес ведут на английские /en/r/
    "eo": dict(title="La 214 ĉinaj radikaloj",
               sub="Kangxi-radikaloj laŭ nombro de strekoj: numero, variantoj, pinjino, signifo kaj ekzemploj",
               top="ofta radikalo", stat="{p}% de la HSK-signoj enhavas unu el la 60 oftaj radikaloj — komencu per ili",
               lg_n="numero", lg_var="variantoj", lg_py="pinjino", lg_mean="signifo", lg_ex="ekzemploj", lg_tone="koloro = tono",
               url="hanzi.lipu.dev/en/r/", qr="https://hanzi.lipu.dev/en/r/",
               more="Strekordo, ĉiuj variantoj kaj la signoj kun ĉiu radikalo troviĝas en la retejo (angle), kun ludo por lerni ilin.",
               src="Datumoj: Unicode Unihan (kRSUnicode), Make Me a Hanzi, HSK 3.0 · Hanzi Burst"),
}
# метаданные PDF (заголовок, тема, ключевые слова): их показывает поисковик в выдаче по PDF
META = {
    "ru": dict(title="Плакат: 214 ключей китайских иероглифов (радикалы Канси)",
               kw="ключи китайских иероглифов, 214 ключей, радикалы Канси, плакат, таблица ключей, PDF, HSK, Hanzi Burst"),
    "en": dict(title="Chinese radicals poster: the 214 Kangxi radicals",
               kw="Chinese radicals, 214 Kangxi radicals, radicals chart, poster, printable, PDF, HSK, Hanzi Burst"),
    "eo": dict(title="Afiŝo: la 214 ĉinaj radikaloj (Kangxi-radikaloj)",
               kw="ĉinaj radikaloj, 214 Kangxi-radikaloj, ĉina skribo, afiŝo, tabelo, PDF, HSK, Hanzi Burst"),
}
STROKES = {"ru": strokes_word, "en": lambda k: "stroke" if k == 1 else "strokes", "eo": lambda k: "streko" if k == 1 else "strekoj"}

# группы по числу черт — по таблице Канси (первый номер каждой группы); в MMH у шести ключей современный счёт черт
# (廴 2 вместо 3, 瓦 4 вместо 5, 骨 и 鬼 9, 鼎 12, 龜 18), а в словарях ключи стоят по счёту Канси
KX_START = [1, 7, 30, 61, 95, 118, 147, 167, 176, 187, 195, 201, 205, 209, 211, 212, 214]
kx_strokes = lambda n: max(i + 1 for i, b in enumerate(KX_START) if b <= n)

CSS = """
@page{size:420mm 594mm;margin:0}
*{box-sizing:border-box}
html,body{margin:0}
body{width:420mm;height:593mm;overflow:hidden;padding:13mm 14mm 10mm;font-family:'Noto Sans','Noto Sans CJK SC',sans-serif;color:#1f1b16;background:#fbf9f5;
     display:flex;flex-direction:column;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.zh{font-family:'LXGW WenKai','Noto Serif CJK SC',serif}
header{margin-bottom:6mm;display:grid;grid-template-columns:auto 1fr auto;align-items:end;column-gap:7mm}
.seal{writing-mode:vertical-rl;background:#b8322a;color:#fbf9f5;border-radius:1.2mm;font-size:24pt;line-height:1;letter-spacing:1.5mm;
      padding:3mm 2.6mm 1.5mm;transform:rotate(-3deg);align-self:center;box-shadow:inset 0 0 0 .7mm #b8322a,inset 0 0 0 1.1mm #fbf9f5}
h1{margin:0;line-height:1;font-weight:400}
h1 .zh{display:block;font-size:66pt;font-weight:500;letter-spacing:4mm}
h1 .tt{display:block;font-size:21pt;font-weight:600;margin-top:3mm;letter-spacing:.2pt}
.sub{font-size:11.5pt;color:#6b6257;margin:1.5mm 0 0}
.stat{max-width:95mm;font-size:11pt;line-height:1.35;color:#4a433b;text-align:right;padding-bottom:1mm}
.stat b{display:block;font-size:30pt;font-weight:600;color:#b8322a;line-height:1}
.legend{display:flex;gap:6mm;align-items:center;border-top:.3mm solid #1f1b16;padding:2mm 1mm 0}
.legend .smp{height:100%;aspect-ratio:1.2;display:flex}.legend .smp .cell{flex:1}
.legend ul{list-style:none;margin:0;padding:0;font-size:8.5pt;line-height:1.45;color:#4a433b;white-space:nowrap}
.legend ul i{display:inline-block;width:17mm;color:#8a8073;font-style:normal}
.legend .more{flex:1;margin:0;font-size:9pt;line-height:1.4;color:#4a433b}
.legend .more b{color:#1f1b16;font-size:11pt}
.qr{height:100%;aspect-ratio:1;display:flex}.qr svg{width:100%;height:100%}
.grid{flex:1;min-height:0;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-template-rows:repeat(20,minmax(0,1fr));gap:1.6mm 1.2mm}
.cell{position:relative;display:grid;grid-template-columns:5.2mm 1fr;grid-template-rows:1fr auto auto;column-gap:.6mm;padding:.4mm .6mm .6mm 0;overflow:hidden}
.cell .n{position:absolute;top:0;left:0;min-width:4.4mm;height:3.4mm;padding:0 .6mm;background:#1f1b16;color:#fbf9f5;font-size:6pt;font-weight:700;
         display:flex;align-items:center;justify-content:center;border-radius:.4mm}
.cell .dot{position:absolute;top:.85mm;left:5.4mm;width:1.7mm;height:1.7mm;border-radius:50%;background:#b8322a}
.cell .exs{grid-row:1 / 4;grid-column:1;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:.2mm;padding-top:3.6mm;
           font-size:8.6pt;line-height:1.08;color:#5d554b}
.cell .ch{grid-column:2;display:flex;align-items:center;justify-content:center;gap:.8mm;line-height:1;min-height:0}
.cell .ch .m{font-size:33pt;font-weight:500}
.cell .ch .v{display:flex;flex-direction:column;font-size:9.5pt;color:#7a7064;line-height:1.05}
.cell .py{grid-column:2;text-align:center;font-size:7.6pt;font-weight:600;line-height:1.1}
.cell .mn{grid-column:2;text-align:center;font-size:7.3pt;font-weight:700;line-height:1.1;max-height:2.2em;overflow:hidden;margin-top:.2mm}
.t1{color:#c4322a}.t2{color:#237a3c}.t3{color:#2f6fd0}.t4{color:#8b46c9}.t5{color:#8a8073}
.grp{display:flex;flex-direction:column;align-items:center;justify-content:center;border-left:.5mm solid #b8322a;color:#1f1b16}
.grp b{font-size:30pt;font-weight:400;line-height:1}
.grp span{font-size:7.5pt;margin-top:.6mm;color:#8a8073;letter-spacing:.3pt;text-transform:uppercase}
footer{display:flex;justify-content:space-between;gap:6mm;margin-top:3mm;font-size:8.5pt;color:#8a8073}
a{color:inherit;text-decoration:none}
"""


def tone(p):
    """Номер тона по знаку над гласной пиньиня (1–4; без знака — 5, лёгкий)."""
    import unicodedata
    d = unicodedata.normalize("NFD", p)
    return next((t for m, t in (("\u0304", 1), ("\u0301", 2), ("\u030c", 3), ("\u0300", 4)) if m in d), 5)


def PY(p):   # пиньинь, раскрашенный по тону (как «Тоны» на сайте)
    return f"<span class='t{tone(p)}'>{E(p)}</span>"


def qr_svg(url):
    try:
        import segno
    except ImportError:
        return ""
    import io
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", border=0, omitsize=True, dark="#1f1b16", xmldecl=False, svgns=True, nl=False)
    return buf.getvalue().decode()


def set_meta(pdf, lang, subject):
    """Автор, тема, ключевые слова и язык документа (Chrome пишет только Title из <title>). Нужен pypdf; без него пропускаем."""
    try:
        from pypdf import PdfWriter
        from pypdf.generic import NameObject, TextStringObject
    except ImportError:
        print("pypdf not installed: PDF metadata skipped")
        return
    w = PdfWriter(clone_from=pdf)
    w.add_metadata({"/Title": META[lang]["title"], "/Author": "Hanzi Burst (hanzi.lipu.dev)", "/Subject": subject,
                    "/Keywords": META[lang]["kw"], "/Creator": "Hanzi Burst, scripts/radicals_poster.py"})
    w._root_object[NameObject("/Lang")] = TextStringObject(lang)
    w.write(pdf)


def main():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        sys.exit("google-chrome / chromium not found")
    R = sorted(json.loads(radical_pages.RADICALS.read_text(encoding="utf-8")), key=lambda r: r["n"])
    total = sum(r["hsk"] for r in R)
    pct = round(100 * sum(r["hsk"] for r in R if r["top"]) / total)

    for lang in ("ru", "en", "eo"):
        t, sw = TXT[lang], STROKES[lang]

        def cell(r):
            exs = "".join(f"<span>{c}</span>" for c in r["examples"][:3])
            vs = "".join(f"<span>{v}</span>" for v in r["variants"][:2])
            return (f"<div class='cell'><span class='n'>{r['n']}</span>" + ("<span class='dot'></span>" if r["top"] else "")
                    + f"<div class='exs zh'>{exs}</div>"
                    + f"<div class='ch zh'><span class='m'>{r['char']}</span>" + (f"<span class='v'>{vs}</span>" if vs else "") + "</div>"
                    f"<div class='py'>{PY(r['pinyin'])}</div><div class='mn'>{E(r[lang])}</div></div>")

        cells, prev = [], None
        for r in R:
            k = kx_strokes(r["n"])
            if k != prev:   # новая группа по числу черт
                prev = k
                cells.append(f"<div class='grp'><b class='zh'>{k}</b><span>{sw(k)}</span></div>")
            cells.append(cell(r))
        sample = next(r for r in R if r["n"] == 85)
        q = qr_svg(t["qr"])
        # легенда и QR — в свободных клетках последнего ряда сетки (12 × 20 = 240 клеток, занято 214 + 17 заголовков групп)
        free = COLS * ROWS - len(cells)
        legend = (f"<div class='legend' style='grid-column:span {free}'><div class='smp'>{cell(sample)}</div><ul>"
                  f"<li><i>{t['lg_n']}</i>85 · <span style='color:#b8322a'>●</span> {t['top']}</li>"
                  f"<li><i>{t['lg_var']}</i><span class='zh'>{''.join(sample['variants'])}</span></li>"
                  f"<li><i>{t['lg_py']}</i>{PY(sample['pinyin'])} · {t['lg_tone']}: {PY('mā')} {PY('má')} {PY('mǎ')} {PY('mà')}</li><li><i>{t['lg_mean']}</i>{E(sample[lang])}</li>"
                  f"<li><i>{t['lg_ex']}</i><span class='zh'>{''.join(sample['examples'][:3])}</span></li></ul>"
                  f"<p class='more'>{E(t['more'])}<br><a href='{t['qr']}'><b>{t['url']}</b></a></p>"
                  + (f"<a class='qr' href='{t['qr']}'>{q}</a>" if q else "") + "</div>")
        # шапка: печать 部首 (единственное красное пятно, кроме точек частых ключей) и заголовок кистью
        body = (f"<header><div class='seal zh'>部首</div><div><h1><span class='zh'>康熙部首</span><span class='tt'>{E(t['title'])}</span></h1>"
                f"<p class='sub'>{E(t['sub'])}</p></div>"
                f"<div class='stat'><b>{pct}%</b>{E(t['stat'].format(p=pct).split('% ', 1)[1])}</div></header>"
                f"<div class='grid'>{''.join(cells)}{legend}</div>"
                f"<footer><span>{E(t['src'])}</span><a href='{t['qr']}'>{t['url']}</a></footer>")
        doc = f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><title>{E(META[lang]['title'])}</title><style>{CSS}</style></head><body>{body}</body></html>"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "poster.html"
            src.write_text(doc, encoding="utf-8")
            out = ROOT / "site" / f"radicals-poster-{lang}.pdf"
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp}/profile",
                            f"--print-to-pdf={out}", src.as_uri()], check=True, capture_output=True)
            # превью для страницы плаката (/r/poster) и og:image: JPEG 1000 px по ширине
            png = Path(tmp) / "poster.png"
            subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}/profile2",
                            "--window-size=1587,2245", f"--screenshot={png}", src.as_uri()], check=True, capture_output=True)
            if "--png" in sys.argv:   # полноразмерный PNG для проверки глазами
                shutil.copy(png, Path(sys.argv[-1]) / f"poster-{lang}.png")
                shutil.copy(src, Path(sys.argv[-1]) / f"poster-{lang}.html")
            subprocess.run(["convert", str(png), "-resize", "1000x", "-strip", "-quality", "82", "-sampling-factor", "4:2:0",
                            "-interlace", "JPEG", str(ROOT / "site" / f"radicals-poster-{lang}.jpg")], check=True)
        set_meta(out, lang, t["sub"])
        print(f"{out.relative_to(ROOT)}: {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
