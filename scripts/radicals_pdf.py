#!/usr/bin/env python3
"""Карточки 214 ключей для печати: site/radicals-ru.pdf и site/radicals-en.pdf (запускается вручную, PDF коммитятся).

Лист A4, 12 карточек (3 × 4). Лицевая сторона: ключ с пронумерованными чертами (Make Me a Hanzi) и варианты написания.
Оборот: номер, название, пиньинь, число черт, примеры иероглифов. Листы идут парами «лицо — оборот»; на обороте
столбцы зеркальны, поэтому при двусторонней печати (переворот по длинному краю) оборот попадает точно за лицо.
Сначала 60 частых ключей (по числу знаков HSK), затем остальные по номеру. Первый лист — обложка с инструкцией.

Нужны: data/radicals.json, data/raw/mmh/{graphics,dictionary}.txt, google-chrome (печать HTML в PDF), шрифт Noto CJK.
  python3 scripts/radicals_pdf.py
"""
import html, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radical_pages
from radical_pages import strokes_word

ROOT = Path(__file__).resolve().parent.parent
E = html.escape
COLS, ROWS = 3, 4
PER = COLS * ROWS

TXT = {
    "ru": dict(title="214 ключей китайских иероглифов", sub="Карточки для печати · Hanzi Burst",
               how=["Печатайте с двух сторон, переворот по длинному краю, масштаб 100 %.",
                    "На лицевой стороне ключ, цифры показывают порядок черт; на обороте значение и примеры.",
                    f"Первые листы — 60 частых ключей: из них собрано большинство иероглифов HSK. Дальше остальные по номеру.",
                    "Разрежьте по пунктиру. Страница каждого ключа и игра для запоминания: hanzi.lipu.dev/r/"],
               top="частый", rest="ключ", n="№", ex="Примеры"),
    "en": dict(title="The 214 Chinese radicals", sub="Printable flashcards · Hanzi Burst",
               how=["Print double-sided, flip on the long edge, scale 100%.",
                    "The front shows the radical with numbered strokes; the back has the meaning and example characters.",
                    "The first sheets hold the 60 common radicals, which build most HSK characters. The rest follow by number.",
                    "Cut along the dashed lines. A page for every radical and a game to learn them: hanzi.lipu.dev/en/r/"],
               top="common", rest="radical", n="No.", ex="Examples"),
}

CSS = """
@page{size:A4;margin:0}
*{box-sizing:border-box}
body{margin:0;font-family:'Noto Sans CJK SC','Noto Sans',sans-serif;color:#1f1b16}
.sheet{width:210mm;height:297mm;padding:10.5mm 9mm;page-break-after:always;display:grid;grid-template-columns:repeat(3,64mm);grid-template-rows:repeat(4,69mm);justify-content:center;align-content:center}
.card{border:0.3mm dashed #b8ae9e;padding:4mm;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;overflow:hidden}
.card .tag{position:absolute;top:2.5mm;left:3mm;font-size:7.5pt;color:#8a8073}
.card .num{position:absolute;top:2.5mm;right:3mm;font-size:7.5pt;color:#8a8073}
.front svg.main{width:40mm;height:40mm}
.front svg text{font:bold 70px sans-serif;fill:#1f1b16;paint-order:stroke;stroke:#fff;stroke-width:16px}
.front .vars{margin-top:2mm;font:20pt/1 'Noto Serif CJK SC',serif;color:#6b6257;letter-spacing:2mm}
.back .zh{font:30pt/1 'Noto Serif CJK SC',serif;color:#c8402a}
.back .name{font-size:14pt;font-weight:700;margin:2mm 0 1mm;text-align:center}
.back .py{font-size:11pt;color:#6b6257}
.back .ex{margin-top:3mm;font-size:9pt;text-align:center;line-height:1.5}
.back .ex b{font:15pt 'Noto Serif CJK SC',serif;font-weight:400}
.cover{display:block;padding:30mm 25mm}
.cover h1{font-size:28pt;margin:0 0 4mm}.cover .sub{color:#6b6257;font-size:13pt;margin-bottom:14mm}
.cover li{font-size:12pt;margin:3mm 0}
.cover .big{font:44pt 'Noto Serif CJK SC',serif;color:#c8402a;letter-spacing:3mm;white-space:nowrap;margin-top:20mm}
.blank{page-break-after:always;height:297mm}
"""


def main():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        sys.exit("google-chrome / chromium not found")
    R = json.loads(radical_pages.RADICALS.read_text(encoding="utf-8"))
    need = {r["char"] for r in R} | {c for r in R for c in r["examples"][:3]}
    G = radical_pages.load_graphics(need)
    py = {}
    for line in open(ROOT / "data/raw/mmh/dictionary.txt", encoding="utf-8"):
        d = json.loads(line)
        if d["character"] in need:
            py[d["character"]] = (d.get("pinyin") or [""])[0]
    order = sorted((r for r in R if r["top"]), key=lambda r: (-r["hsk"], r["n"])) + [r for r in R if not r["top"]]

    for lang in ("ru", "en"):
        t = TXT[lang]
        def front(r):
            g = G.get(r["char"])
            pic = radical_pages.svg(g, "main") if g else f"<div class='back'><div class='zh' style='font-size:80pt'>{r['char']}</div></div>"
            vs = f"<div class='vars'>{''.join(r['variants'])}</div>" if r["variants"] else ""
            return f"<div class='card front'><span class='tag'>{t['top'] if r['top'] else ''}</span><span class='num'>{r['n']}</span>{pic}{vs}</div>"
        def back(r):
            sw = f"{r['strokes']} {strokes_word(r['strokes'])}" if lang == "ru" else f"{r['strokes']} stroke{'s' if r['strokes'] != 1 else ''}"
            ex = "".join(f"<b>{c}</b> {E(py.get(c, ''))}<br>" for c in r["examples"][:3])
            return (f"<div class='card back'><span class='num'>{t['n']} {r['n']}</span><div class='zh'>{r['char']}{''.join(r['variants'][:2])}</div>"
                    f"<div class='name'>{E(r[lang])}</div><div class='py'>{E(r['pinyin'])} · {sw}</div>"
                    + (f"<div class='ex'>{ex}</div>" if ex else "") + "</div>")
        pages = [f"<div class='sheet cover'><h1>{t['title']}</h1><div class='sub'>{t['sub']}</div><ol>"
                 + "".join(f"<li>{E(x)}</li>" for x in t["how"]) + "</ol><div class='big'>氵扌口艹木亻</div></div>",
                 "<div class='blank'></div>"]
        for i in range(0, len(order), PER):
            chunk = order[i:i + PER]
            empty = "<div class='card' style='border-color:transparent'></div>"
            fr = [front(r) for r in chunk] + [empty] * (PER - len(chunk))
            bk = [back(r) for r in chunk] + [empty] * (PER - len(chunk))
            # оборот: в каждой строке столбцы в обратном порядке (переворот по длинному краю)
            bk = [bk[row * COLS + (COLS - 1 - c)] for row in range(ROWS) for c in range(COLS)]
            pages.append(f"<div class='sheet'>{''.join(fr)}</div>")
            pages.append(f"<div class='sheet'>{''.join(bk)}</div>")
        doc = f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(pages)}</body></html>"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "cards.html"
            src.write_text(doc, encoding="utf-8")
            out = ROOT / "site" / f"radicals-{lang}.pdf"
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp}/profile",
                            f"--print-to-pdf={out}", src.as_uri()], check=True, capture_output=True)
        print(f"{out.relative_to(ROOT)}: {out.stat().st_size // 1024} KB, {len(pages)} pages")


if __name__ == "__main__":
    main()
