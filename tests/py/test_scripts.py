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
