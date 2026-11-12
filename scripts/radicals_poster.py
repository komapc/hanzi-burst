#!/usr/bin/env python3
"""Плакат «214 ключей» на одну страницу: site/radicals-poster-ru.pdf и site/radicals-poster-en.pdf
(запускается вручную, PDF коммитятся).

Лист A2 (420 × 594 мм), вектор: печатается и на A3/A4 с уменьшением. Ключи сгруппированы по числу черт, как в словарях;
у каждого номер, варианты написания, пиньинь, значение и пример иероглифа. 60 частых ключей (по числу знаков HSK)
выделены цветом и звёздочкой. В шапке легенда, доля HSK-иероглифов с частыми ключами и QR-код на /r/.

Нужны: data/radicals.json, data/raw/mmh/dictionary.txt (пиньинь примеров), google-chrome, шрифт Noto CJK.
QR-код — пакет segno (pip install segno); без него плакат собирается без QR.
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
               sub="Ключи (радикалы) Канси по числу черт: номер, варианты, пиньинь, значение и пример",
               top="частый ключ", stat="{p}% иероглифов HSK содержат один из 60 частых ключей — начните с них",
               lg_n="номер", lg_var="варианты", lg_py="пиньинь", lg_mean="значение", lg_ex="пример",
               url="hanzi.lipu.dev/r/", qr="https://hanzi.lipu.dev/r/",
               more="Порядок черт, все варианты и иероглифы с каждым ключом — на сайте. Там же игра для запоминания.",
               src="Данные: Unicode Unihan (kRSUnicode), Make Me a Hanzi, HSK 3.0 · Hanzi Burst"),
    "en": dict(title="The 214 Chinese radicals",
               sub="Kangxi radicals by stroke count: number, variant forms, pinyin, meaning and an example",
               top="common radical", stat="{p}% of HSK characters contain one of the 60 common radicals — start with those",
               lg_n="number", lg_var="variants", lg_py="pinyin", lg_mean="meaning", lg_ex="example",
               url="hanzi.lipu.dev/en/r/", qr="https://hanzi.lipu.dev/en/r/",
               more="Stroke order, every variant and the characters that use each radical are on the site, plus a game to learn them.",
               src="Data: Unicode Unihan (kRSUnicode), Make Me a Hanzi, HSK 3.0 · Hanzi Burst"),
}

# мягкие оттенки групп по числу черт: соседние группы различимы и в ч/б печати (разная светлота)
# группы по числу черт — по таблице Канси (первый номер каждой группы); в MMH у шести ключей современный счёт черт
# (廴 2 вместо 3, 瓦 4 вместо 5, 骨 и 鬼 9, 鼎 12, 龜 18), а в словарях ключи стоят по счёту Канси
KX_START = [1, 7, 30, 61, 95, 118, 147, 167, 176, 187, 195, 201, 205, 209, 211, 212, 214]
kx_strokes = lambda n: max(i + 1 for i, b in enumerate(KX_START) if b <= n)

HUES = [18, 200, 95, 280, 40, 160, 330, 230, 60, 120, 0, 260, 180, 300, 80, 210, 140]

CSS = """
@page{size:420mm 594mm;margin:0}
*{box-sizing:border-box}
html,body{margin:0}
body{width:420mm;height:593mm;overflow:hidden;padding:13mm 13mm 10mm;font-family:'Noto Sans CJK SC','Noto Sans',sans-serif;color:#1f1b16;background:#fbf8f3;
     display:flex;flex-direction:column;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.zh{font-family:'Noto Serif CJK SC',serif}
header{margin-bottom:5mm;display:grid;grid-template-columns:1fr auto;align-items:end;column-gap:8mm}
h1{font-size:40pt;line-height:1.05;margin:0 0 2mm;letter-spacing:-.3pt;grid-column:1 / -1}
h1 .zh{color:#c8402a;font-weight:700;margin-right:4mm}
.sub{font-size:13pt;color:#6b6257;margin:0}
.stat{display:inline-flex;align-items:center;gap:3mm;font-size:12pt;background:#fff;border:.4mm solid #e6c3b8;border-radius:3mm;padding:2mm 4mm}
.stat b{font-size:20pt;color:#c8402a}
.legend{display:flex;gap:5mm;align-items:center;background:#fff;border:.3mm solid #d8cfc0;border-radius:1.6mm;padding:2mm 4mm}
.legend .smp{height:100%;aspect-ratio:1.3;display:flex}.legend .smp .cell{flex:1}
.legend ul{list-style:none;margin:0;padding:0;font-size:8.5pt;line-height:1.45;color:#4a433b;white-space:nowrap}
.legend ul i{display:inline-block;width:17mm;color:#8a8073;font-style:normal}
.legend .more{flex:1;margin:0;font-size:9pt;line-height:1.4;color:#4a433b}
.legend .more b{color:#c8402a;font-size:11pt}
.qr{height:100%;aspect-ratio:1;display:flex}.qr svg{width:100%;height:100%}
.grid{flex:1;min-height:0;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-template-rows:repeat(20,minmax(0,1fr));gap:1.3mm}
.cell{position:relative;background:#fff;border:.3mm solid #ddd3c4;border-top:1.4mm solid hsl(var(--h) 45% 72%);border-radius:1.6mm;
      display:flex;flex-direction:column;align-items:center;justify-content:center;padding:1.2mm 1mm .8mm;overflow:hidden;text-align:center}
.cell.top{background:#fdf0ea;border-color:#e9b8a6;border-top-color:#c8402a}
.cell .n{position:absolute;top:.6mm;left:1.2mm;font-size:6.5pt;color:#8a8073}
.cell .st{position:absolute;top:.2mm;right:1mm;font-size:8pt;color:#c8402a}
.cell .ch{display:flex;align-items:baseline;justify-content:center;gap:1.2mm;line-height:1}
.cell .ch .m{font-size:27pt}
.cell.top .ch .m{color:#b0361f}
.cell .ch .v{font-size:11pt;color:#6b6257;letter-spacing:.4mm}
.cell .py{font-size:7.5pt;color:#6b6257;margin-top:.6mm;line-height:1.1}
.cell .mn{font-size:7.6pt;font-weight:700;line-height:1.12;margin-top:.3mm;max-height:2.3em;overflow:hidden}
.cell .ex{font-size:7pt;color:#8a8073;margin-top:.3mm;line-height:1.1}
.cell .ex .zh{font-size:9pt;color:#1f1b16}
.grp{border-radius:1.6mm;background:hsl(var(--h) 45% 72%);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#1f1b16}
.grp b{font-size:26pt;line-height:1}
.grp span{font-size:8pt;margin-top:.8mm}
footer{display:flex;justify-content:space-between;gap:6mm;margin-top:3mm;font-size:8.5pt;color:#8a8073}
footer b{color:#c8402a;font-weight:600}
"""


def qr_svg(url):
    try:
        import segno
    except ImportError:
        return ""
    import io
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", border=0, omitsize=True, dark="#1f1b16", xmldecl=False, svgns=True, nl=False)
    return buf.getvalue().decode()


def main():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        sys.exit("google-chrome / chromium not found")
    R = sorted(json.loads(radical_pages.RADICALS.read_text(encoding="utf-8")), key=lambda r: r["n"])
    ex_of = {r["n"]: r["examples"][0] for r in R if r["examples"]}
    py = {}
    for line in open(ROOT / "data/raw/mmh/dictionary.txt", encoding="utf-8"):
        d = json.loads(line)
        if d["character"] in ex_of.values():
            py[d["character"]] = (d.get("pinyin") or [""])[0]
    total = sum(r["hsk"] for r in R)
    pct = round(100 * sum(r["hsk"] for r in R if r["top"]) / total)

    for lang in ("ru", "en"):
        t = TXT[lang]
        sw = (lambda k: strokes_word(k)) if lang == "ru" else (lambda k: "stroke" if k == 1 else "strokes")

        def cell(r, h, sample=False):
            ex = ex_of.get(r["n"])
            vs = "".join(r["variants"][:3])
            return (f"<div class='cell{' top' if r['top'] else ''}' style='--h:{h}'>"
                    f"<span class='n'>{r['n']}</span>" + ("<span class='st'>★</span>" if r["top"] else "")
                    + f"<div class='ch zh'><span class='m'>{r['char']}</span>" + (f"<span class='v'>{vs}</span>" if vs else "") + "</div>"
                    f"<div class='py'>{E(r['pinyin'])}</div><div class='mn'>{E(r[lang])}</div>"
                    + (f"<div class='ex'><span class='zh'>{ex}</span> {E(py.get(ex, ''))}</div>" if ex else "") + "</div>")

        cells, gi, prev = [], -1, None
        for r in R:
            k = kx_strokes(r["n"])
            if k != prev:   # новая группа по числу черт
                gi, prev = gi + 1, k
                cells.append(f"<div class='grp' style='--h:{HUES[gi % len(HUES)]}'><b>{k}</b><span>{sw(k)}</span></div>")
            cells.append(cell(r, HUES[gi % len(HUES)]))
        sample = next(r for r in R if r["n"] == 85)
        q = qr_svg(t["qr"])
        # легенда и QR — в свободных клетках последнего ряда сетки (12 × 20 = 240 клеток, занято 214 + 17 заголовков групп)
        free = COLS * ROWS - len(cells)
        legend = (f"<div class='legend' style='grid-column:span {free}'><div class='smp'>{cell(sample, HUES[3])}</div><ul>"
                  f"<li><i>{t['lg_n']}</i>85 · <span style='color:#c8402a'>★</span> {t['top']}</li>"
                  f"<li><i>{t['lg_var']}</i><span class='zh'>{''.join(sample['variants'])}</span></li>"
                  f"<li><i>{t['lg_py']}</i>{sample['pinyin']}</li><li><i>{t['lg_mean']}</i>{E(sample[lang])}</li>"
                  f"<li><i>{t['lg_ex']}</i><span class='zh'>{ex_of[85]}</span> {E(py.get(ex_of[85], ''))}</li></ul>"
                  f"<p class='more'>{E(t['more'])}<br><b>{t['url']}</b></p>"
                  + (f"<div class='qr'>{q}</div>" if q else "") + "</div>")
        body = (f"<header><h1><span class='zh'>部首</span>{E(t['title'])}</h1><p class='sub'>{E(t['sub'])}</p>"
                f"<div class='stat'><b>{pct}%</b>{E(t['stat'].format(p=pct).split('% ', 1)[1])}</div></header>"
                f"<div class='grid'>{''.join(cells)}{legend}</div>"
                f"<footer><span>{E(t['src'])}</span><span>{t['url']}</span></footer>")
        doc = f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "poster.html"
            src.write_text(doc, encoding="utf-8")
            out = ROOT / "site" / f"radicals-poster-{lang}.pdf"
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp}/profile",
                            f"--print-to-pdf={out}", src.as_uri()], check=True, capture_output=True)
            if "--png" in sys.argv:   # превью для проверки глазами
                subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}/profile2",
                                "--window-size=1587,2245", f"--screenshot={Path(sys.argv[-1]) / f'poster-{lang}.png'}", src.as_uri()],
                               check=True, capture_output=True)
        print(f"{out.relative_to(ROOT)}: {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
