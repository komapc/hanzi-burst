"""Unit tests for the build scripts: python3 -m unittest discover -s tests/py
No data/raw needed: only pure functions, with small inputs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import breakdown  # noqa: E402
import palladius  # noqa: E402
from radical_names import NAMES, PICTURES  # noqa: E402
from radical_pages import ru_plural  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class Pinyin(unittest.TestCase):
    def test_numeric_to_marks(self):
        self.assertEqual(breakdown.numeric_to_marks("ni3 hao3"), "nǐ hǎo")
        self.assertEqual(breakdown.numeric_to_marks("xue2"), "xué")       # e before u
        self.assertEqual(breakdown.numeric_to_marks("gou3"), "gǒu")       # ou: on the o
        self.assertEqual(breakdown.numeric_to_marks("gui4"), "guì")       # last of i/u
        self.assertEqual(breakdown.numeric_to_marks("lu:4"), "lǜ")
        self.assertEqual(breakdown.numeric_to_marks("ma5"), "ma")         # neutral tone


class Segment(unittest.TestCase):
    def test_longest_word_first(self):
        words = {"我们", "汉字", "学汉"}
        self.assertEqual(breakdown.segment("我们学汉字", words), ["我们", "学汉", "字"])
        self.assertEqual(breakdown.segment("我想学", set()), ["我", "想", "学"])


class Components(unittest.TestCase):
    def test_parts_without_operators_or_duplicates(self):
        mmh = {"你": {"decomposition": "⿰亻尔"}, "炎": {"decomposition": "⿱火火"}}
        self.assertEqual(breakdown.components("你", mmh), ["亻", "尔"])
        self.assertEqual(breakdown.components("炎", mmh), ["火"])

    def test_incomplete_breakdown_is_not_shown_as_whole(self):
        self.assertEqual(breakdown.components("书", {"书": {"decomposition": "⿻？丨"}}), [])
        self.assertEqual(breakdown.components("X", {}), [])


class FillHoles(unittest.TestCase):
    def setUp(self):
        self._ids = breakdown.load_ids
        breakdown.load_ids = lambda: {"曷": "⿱日匃", "匃": "⿹勹亡"}

    def tearDown(self):
        breakdown.load_ids = self._ids

    def test_manual_fix_for_xue(self):
        mmh = {"學": {"decomposition": "⿳？冖子"}}
        breakdown.fill_holes(mmh)
        self.assertEqual(mmh["學"]["decomposition"], "⿳⿴臼爻冖子")

    def test_ids_fills_the_hole_and_adds_new_parts(self):
        mmh = {"曷": {"decomposition": "⿱日？"}}
        breakdown.fill_holes(mmh)
        self.assertEqual(mmh["曷"]["decomposition"], "⿱日匃")
        self.assertEqual(mmh["匃"]["decomposition"], "⿹勹亡")    # missing part gets its own IDS breakdown

    def test_all_hole_is_left_alone(self):
        mmh = {"口": {"decomposition": "？"}}
        breakdown.fill_holes(mmh)
        self.assertEqual(mmh["口"]["decomposition"], "？")


class Palladius(unittest.TestCase):
    def test_plain(self):
        for py, cyr in [("nǐ hǎo", "ни хао"), ("xièxie", "сесе"), ("Zhōngguó", "чжунго"), ("shì", "ши"),
                        ("zhī", "чжи"), ("rén", "жэнь"), ("xué", "сюэ"), ("wǒ xiǎng xué hànzì", "во сян сюэ ханьцзы")]:
            self.assertEqual(palladius.plain(py), cyr, py)

    def test_tone_marks_kept(self):
        self.assertEqual(palladius.convert("rén"), "жэ́нь")


class RadicalPictures(unittest.TestCase):
    def test_entries(self):
        for n, (en, ru) in PICTURES.items():
            self.assertIn(n, NAMES)
            self.assertTrue(en.strip() and ru.strip(), n)
            self.assertNotEqual(ru, NAMES[n][1], f"{n}: picture = name, nothing to add")

    def test_hand_is_drawn_not_again(self):          # the case that started it: 又 means "again", depicts a hand
        self.assertEqual(NAMES[29][0], "again")
        self.assertEqual(PICTURES[29], ("a right hand", "правая рука"))


class RuPlural(unittest.TestCase):
    def test_forms(self):
        for n, w in [(1, "ключ"), (2, "ключа"), (5, "ключей"), (11, "ключей"), (12, "ключей"), (21, "ключ"), (154, "ключа")]:
            self.assertEqual(ru_plural(n, "ключ", "ключа", "ключей"), w, n)


class MainReading(unittest.TestCase):
    def test_overrides_put_the_main_reading_first(self):     # MMH lists the particle first: 地 de, 子 zi
        for ch, py in [("地", "dì"), ("子", "zǐ"), ("卜", "bǔ")]:
            self.assertEqual(breakdown.PINYIN_OVERRIDES[ch][0], py)

    def test_phrase_json_is_regenerated(self):
        import json
        chars = json.loads((ROOT / "site/phrase.json").read_text(encoding="utf-8"))["chars"]
        self.assertEqual(chars["地"]["pinyin"][0], "dì")
        self.assertEqual(chars["子"]["pinyin"][0], "zǐ")


if __name__ == "__main__":
    unittest.main()


class Redirects(unittest.TestCase):
    def test_permanent_redirects_for_the_built_site(self):
        import tempfile
        import redirects
        with tempfile.TemporaryDirectory() as t:
            site = Path(t)
            for f in ("index.html", "about.html", "404.html", "yandex_1.html", "googleabc.html",
                      "c/index.html", "c/6c34.html", "en/r/index.html", "en/r/53c8.html", "japanese/index.html",
                      "data/c/6c.json"):
                (site / f).parent.mkdir(parents=True, exist_ok=True)
                (site / f).write_text("x")
            r = redirects.rules(site)
            for rule in ("/index.html / 301", "/about.html /about 301", "/c /c/ 301", "/c/index.html /c/ 301",
                         "/c/:page.html /c/:page 301", "/en/r /en/r/ 301", "/en/r/:page.html /en/r/:page 301",
                         "/japanese /japanese/ 301"):
                self.assertIn(rule, r)
            # 404 and verification files are left alone; en/ itself has no pages; data/ has no pages
            self.assertFalse([x for x in r if "404" in x or "yandex" in x or "google" in x or x.startswith(("/en ", "/data"))])
            # Cloudflare applies the first match: every static rule comes before the first placeholder rule
            first_dynamic = next(i for i, x in enumerate(r) if ":" in x)
            self.assertFalse([x for x in r[first_dynamic:] if ":" not in x])
            # no rule sends a page to itself or to a path another rule redirects again (no chains or loops)
            src = {x.split()[0] for x in r}
            self.assertFalse([x for x in r if x.split()[1] in src])


class OgTags(unittest.TestCase):
    """Link previews of the generated pages: og:type, og:locale from the page language, og:image:alt for the
    image actually shown, twitter:card."""
    def meta(self, html, key):
        import re
        return re.findall(rf'<meta (?:property|name)="{re.escape(key)}" content="([^"]*)">', html)

    def test_page_head(self):
        import build_static
        from radical_pages import POSTER
        cases = [  # (page() arguments, og:type, og:locale, og:image, og:image:alt starts with)
            (dict(lang="ru", og_type="article"), "article", "ru_RU", "/og.png", "Hanzi Burst — иероглифы через радикалы"),
            (dict(lang="en"), "website", "en_US", "/og-en.png", "Hanzi Burst — learn Chinese characters"),
            (dict(lang="eo", image="/radicals-poster-eo.jpg", image_alt=POSTER["eo"]["alt"]), "website", "eo_EO",
             "/radicals-poster-eo.jpg", "Afiŝo de la 214"),
        ]
        for kw, typ, loc, img, alt in cases:
            with self.subTest(kw=kw):
                h = build_static.page("t", "d", "/x", "", **kw)
                self.assertEqual(self.meta(h, "og:type"), [typ])
                self.assertEqual(self.meta(h, "og:locale"), [loc])
                self.assertEqual(self.meta(h, "og:image"), [build_static.BASE + img])
                self.assertEqual(len(self.meta(h, "og:image:alt")), 1)
                self.assertTrue(self.meta(h, "og:image:alt")[0].startswith(alt))
                self.assertEqual(self.meta(h, "twitter:card"), ["summary_large_image"])

    def test_a_new_image_needs_its_own_alt(self):
        import build_static
        with self.assertRaises(KeyError):
            build_static.page("t", "d", "/x", "", image="/other.png")
