"""Browser tests of the built site (site/ with site/data from the build): Playwright + Chromium.

  python3 -m unittest discover -s tests/e2e -v        # needs: pip install playwright && playwright install chromium

CI runs them in deploy.yml after the build, before anything is deployed. Locally site/data must exist (see README
«Запуск»). The tests drive the page through the UI and URL parameters only: the inline script is minified in CI.
"""
import functools
import http.server
import os
import threading
import unittest
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[2] / "site"


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):                       # /extension -> extension.html, as on Cloudflare
        p = self.path.split("?")[0].split("#")[0]
        f = SITE / p.lstrip("/")
        if not f.exists() and (SITE / (p.lstrip("/") + ".html")).exists():
            self.path = p + ".html"
        return super().send_head()

    def log_message(self, *a):
        pass


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.ctx = self.browser.new_context(viewport={"width": 1200, "height": 900}, locale="en-US")
        self.ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        self.ctx.route("**/api/**", lambda r: r.fulfill(status=404, body="{}"))          # no backend here
        self.ctx.route("**googletagmanager**", lambda r: r.abort())
        self.errors = []
        self.page = self.ctx.new_page()
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))

    def tearDown(self):
        self.ctx.close()
        self.assertEqual(self.errors, [], "JS errors on the page")

    def open(self, query="", script="s", known=None):
        """Load the home page with a clean profile: tour done, consent declined, the chosen 简/繁."""
        init = f"localStorage.setItem('hanzi-tour','done');localStorage.setItem('hanzi-consent','denied');localStorage.setItem('hanzi-script','{script}');"
        if known is not None:
            init += f"localStorage.setItem('hanzi-known', JSON.stringify({list(known)!r}));"
        self.page.add_init_script(init)
        self.page.goto(self.base + query)
        self.page.wait_for_selector("html.ready", timeout=20000)
        self.page.wait_for_timeout(300)

    def tree(self):
        self.page.wait_for_selector("#tree .node", timeout=10000)
        return self.page.eval_on_selector_all("#tree .node", "ns => ns.map(n => n.dataset.ch)")

    def heading(self):
        return self.page.eval_on_selector("#info h2 [data-c]", "e => e.dataset.c")

    # ---- phrase and tree ----
    def test_home_renders_a_phrase(self):
        self.open("?lang=en")
        self.assertGreater(self.page.locator("#phrase .ch").count(), 0)
        self.assertTrue(self.page.inner_text("#trans").strip())

    def test_clicking_a_phrase_character_opens_its_tree(self):
        self.open("?lang=en")
        ch = self.page.locator("#phrase .ch").first
        c = ch.get_attribute("data-ch")
        ch.click()
        self.page.wait_for_selector("#card.open")
        self.assertEqual(self.tree()[0], c)

    def test_open_param_and_explode_all(self):
        self.open("?open=" + quote("想") + "&lang=en")
        self.assertEqual(self.tree()[:3], ["想", "相", "心"])
        self.page.click("#explodeAll")
        self.page.wait_for_timeout(500)
        self.assertTrue({"木", "目"} <= set(self.tree()))

    # ---- tile buttons (#90): glyph = explanation, + / − = parts, ★ = known ----
    def test_glyph_click_opens_once_and_never_closes(self):
        self.open("?open=" + quote("想") + "&lang=en")
        g = self.page.locator('#tree .node[data-ch="相"] > .gw > .glyph')
        g.click()
        self.page.wait_for_timeout(400)
        self.assertEqual(self.heading(), "相")
        n = len(self.tree())
        self.assertGreater(n, 3)
        g.click()                                   # second click: explanation only, the parts stay
        self.page.wait_for_timeout(400)
        self.assertEqual(len(self.tree()), n)

    def test_plus_minus_toggles_parts(self):
        self.open("?open=" + quote("想") + "&lang=en")
        x = self.page.locator('#tree .node[data-ch="相"] > .gw > .xbtn')
        self.assertEqual(x.inner_text(), "+")
        x.click()
        self.page.wait_for_timeout(400)
        self.assertEqual(x.inner_text(), "−")
        self.assertIn("木", self.tree())
        x.click()
        self.page.wait_for_timeout(400)
        self.assertNotIn("木", self.tree())
        self.assertEqual(self.page.locator('#tree .node[data-ch="心"] > .gw > .xbtn').count(), 0)   # leaf: no button

    def test_star_marks_known(self):
        self.open("?open=" + quote("想") + "&lang=en", known=[])
        self.page.click('#tree .node[data-ch="心"] > .gw > .kbtn')
        self.page.wait_for_timeout(300)
        self.assertIn("心", self.page.evaluate("JSON.parse(localStorage.getItem('hanzi-known'))"))
        self.assertIn("on", self.page.get_attribute('#tree .node[data-ch="心"] > .gw > .kbtn', "class"))

    # ---- card ----
    def test_characters_in_the_description_are_links(self):        # #88: "compare 左"
        self.open("?open=" + quote("又") + "&lang=en")
        link = self.page.locator('#info a.xr[data-ch="左"]')
        self.assertEqual(link.count(), 1)
        link.click()
        self.page.wait_for_timeout(600)
        self.assertEqual(self.tree()[0], "左")

    def test_copy_button_copies_the_character(self):              # #91
        self.open("?open=" + quote("你") + "&lang=en")
        self.page.click('#tree .node[data-ch="尔"] > .gw > .glyph')
        self.page.click("#cpChBtn")
        self.page.wait_for_timeout(300)
        self.assertEqual(self.page.evaluate("navigator.clipboard.readText()"), "尔")

    # ---- 简 / 繁 (#80, #91, #93) ----
    def test_traditional_phrase_is_converted(self):
        self.open("?open=" + quote("学") + "&lang=en", script="t")
        self.assertEqual(self.tree()[0], "學")                    # the traditional form is broken down
        self.assertIn("學", self.page.inner_text("#gloss"))

    def test_traditional_mode_does_not_convert_the_parts(self):
        """你 = 亻 + 尔 in both modes: 尔 must not be drawn as 爾 (its traditional form) in the tree or the card."""
        paths = {}
        for script in ("s", "t"):
            self.open("?open=" + quote("你") + "&lang=en", script=script)
            self.assertEqual(self.tree()[:3], ["你", "亻", "尔"])
            paths[script] = self.page.inner_html('#tree .node[data-ch="尔"] > .gw > .glyph svg')
            self.page.click('#tree .node[data-ch="尔"] > .gw > .glyph')
            self.page.wait_for_timeout(300)
            self.assertEqual(self.page.inner_html("#info h2 svg"), paths[script])
            self.assertNotIn("爾", self.page.inner_text("#info"))
            self.page.click('#tree .node[data-ch="你"] > .gw > .glyph')
            self.page.wait_for_timeout(300)
            self.assertIn("尔", self.page.inner_text("#info"))     # "Pronoun 尔 for a person 亻"
        self.assertEqual(paths["s"], paths["t"])

    # ---- links from other pages and the extension ----
    def test_own_phrase_from_url(self):                            # extension link ?t=
        self.open("?t=" + quote("最近的地铁站在哪里？") + "&mode=zh&lang=en")
        chars = self.page.eval_on_selector_all("#phrase .ch", "bs => bs.map(b => b.dataset.ch).join('')")
        self.assertEqual(chars, "最近的地铁站在哪里")

    def test_japanese_mode_loads(self):
        self.open("?mode=ja&lang=en")
        self.assertGreater(self.page.locator("#phrase .ch").count(), 0)
        self.assertEqual(self.page.locator("#phrase .word.ja").count() > 0, True)


if __name__ == "__main__":
    unittest.main()
