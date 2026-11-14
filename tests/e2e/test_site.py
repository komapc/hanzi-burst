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


class Server(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):               # the browser closing a context mid-download
        import sys
        if not isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            super().handle_error(request, client_address)


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server(("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
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

    def open(self, query="", script="s", known=None, tour=False):
        """Load the home page with a clean profile: tour done (unless tour=True), consent declined, the chosen 简/繁."""
        init = ("" if tour else "localStorage.setItem('hanzi-tour','done');") + \
            f"localStorage.setItem('hanzi-consent','denied');localStorage.setItem('hanzi-script','{script}');"
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
    def test_without_javascript_the_footer_and_about_are_shown(self):
        # html:not(.ready) hides them until the data loads; without JS .ready never comes, <noscript> shows them
        ctx = self.browser.new_context(java_script_enabled=False)
        try:
            page = ctx.new_page()
            page.goto(self.base)
            self.assertTrue(page.locator(".foot").is_visible())
            self.assertTrue(page.locator("#introD > summary").is_visible())
        finally:
            ctx.close()

    def test_footer_shows_even_if_the_data_fails_to_load(self):
        self.page.route("**/phrase.json", lambda r: r.abort())
        self.page.goto(self.base)
        self.page.wait_for_selector("html.ready", state="attached")
        self.assertTrue(self.page.locator(".foot").is_visible())
        self.errors.clear()   # the failed fetch itself is reported as an uncaught rejection

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

    def test_switching_script_rebuilds_the_tree(self):
        self.open("?open=" + quote("学") + "&lang=en")
        self.assertEqual(self.tree()[0], "学")
        self.page.click("#set > summary")
        self.page.click('.scr label:has(input[value="t"])')
        self.page.wait_for_function("document.querySelector('#tree > .node').dataset.ch === '學'", timeout=10000)
        self.page.click('.scr label:has(input[value="s"])')
        self.page.wait_for_function("document.querySelector('#tree > .node').dataset.ch === '学'", timeout=10000)

    def test_traditional_search_from_url(self):                     # ?q= from other pages: used to race the s2t map
        self.open("?q=" + quote("学") + "&lang=en", script="t")
        self.assertEqual(self.tree()[0], "學")

    def test_copy_in_traditional_copies_what_is_shown(self):
        self.open("?lang=en", script="t")
        self.page.click("#copy > summary")
        self.page.click("#cpGo")
        self.page.wait_for_timeout(300)
        self.assertTrue(self.page.evaluate("navigator.clipboard.readText()").startswith("我想學漢字"))

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

    def test_own_phrase_without_characters_says_so(self):
        self.open("?t=hello&lang=en")
        self.page.wait_for_timeout(500)
        self.assertTrue(self.page.is_visible("#ownMsg"))
        self.assertIn("No characters", self.page.inner_text("#ownMsg"))

    def test_long_own_phrase_says_it_was_cut(self):
        self.open("?t=" + quote("我想学汉字。" * 20) + "&mode=zh&lang=en")
        self.assertLessEqual(self.page.locator("#phrase .ch").count(), 100)
        self.assertIn("first 100", self.page.inner_text("#trans"))

    def test_lang_switch_updates_the_url(self):                     # else a reload with ?lang=en brings English back
        self.open("?lang=en")
        self.page.click('.lang button[data-lang="ru"]')
        self.assertIn("lang=ru", self.page.url)

    # ---- /en/: the English copy of the home page (build_static.en_home) ----
    def test_en_home_is_english_even_if_russian_was_chosen(self):    # the address sets the language, not hanzi-lang
        bad = []
        ours = lambda u: u.startswith(self.base) and "/api/" not in u                    # not the beacon or GA4
        self.page.on("response", lambda r: r.status >= 400 and ours(r.url) and bad.append(f"{r.status} {r.url}"))
        self.page.on("requestfailed", lambda r: ours(r.url) and bad.append(r.url))
        self.page.add_init_script("localStorage.setItem('hanzi-lang','ru')")
        self.open("en/?open=" + quote("想"))
        self.assertEqual(self.page.evaluate("document.documentElement.lang"), "en")
        self.assertIn("radicals", self.page.inner_text("#h1"))
        self.assertIn("想", self.tree())
        self.assertEqual(bad, [], "requests that failed on /en/")

    def test_en_home_html_is_english_without_javascript(self):      # what crawlers and link previews read
        ctx = self.browser.new_context(java_script_enabled=False)
        try:
            page = ctx.new_page()
            page.goto(self.base + "en/")
            self.assertEqual(page.get_attribute("html", "lang"), "en")
            self.assertEqual(page.get_attribute('link[rel="canonical"]', "href"), "https://hanzi.lipu.dev/en/")
            self.assertEqual(page.get_attribute('meta[property="og:image"]', "content"), "https://hanzi.lipu.dev/og-en.png")
            self.assertIn("Where to start", page.text_content("#intro"))
            self.assertEqual(page.get_attribute("#snav a.on", "href"), "/en/")
        finally:
            ctx.close()

    def test_lang_switch_moves_between_root_and_en(self):          # no reload; ?open= and the open character stay
        self.open("en/?open=" + quote("想"))
        self.page.click('.lang button[data-lang="ru"]')
        self.assertEqual(self.page.evaluate("location.pathname"), "/")
        self.assertIn("open=", self.page.url)
        self.assertIn("С чего начать", self.page.text_content("#intro"))   # Russian intro, though the HTML of /en/ is English
        self.assertIn("Разбор", self.page.title())
        self.page.click('.lang button[data-lang="en"]')
        self.assertEqual(self.page.evaluate("location.pathname"), "/en/")
        self.assertIn("想", self.tree())

    def test_open_param_ignores_object_keys(self):                  # ?open=constructor used to throw
        self.open("?open=constructor&lang=en")
        self.assertFalse(self.page.is_visible("#card"))

    def test_japanese_mode_loads(self):
        self.open("?mode=ja&lang=en")
        self.assertGreater(self.page.locator("#phrase .ch").count(), 0)
        self.assertEqual(self.page.locator("#phrase .word.ja").count() > 0, True)
        self.assertIn("kanji", self.page.inner_text("#h1").lower())

    # ---- radicals game ----
    def game(self, query):
        self.page.add_init_script("localStorage.setItem('hanzi-consent','denied');")
        self.page.goto(self.base + "radicals-game" + query)
        self.page.wait_for_selector("#card .opts button", timeout=10000)

    def test_game_ignores_object_keys_in_lang(self):
        self.game("?lang=constructor")
        self.assertTrue(self.page.inner_text("#h1").strip())

    def test_game_counter_names_what_it_counts(self):
        self.game("?lang=en")
        self.assertIn("radicals", self.page.inner_text("#prog"))
        self.page.click('#mode button[data-v="find"]')
        self.assertIn("characters", self.page.inner_text("#prog"))

    def test_game_reset_asks_first(self):
        self.game("?lang=en")
        self.page.click("#card .opts button >> nth=0")
        self.assertTrue(self.page.evaluate("Object.keys(JSON.parse(localStorage.getItem('hanzi-radicals-srs'))).length") > 0)
        self.page.click("#reset")
        self.assertTrue(self.page.evaluate("Object.keys(JSON.parse(localStorage.getItem('hanzi-radicals-srs'))).length") > 0)
        self.page.click("#reset")
        self.assertEqual(self.page.evaluate("localStorage.getItem('hanzi-radicals-srs')"), "{}")

    def test_link_to_a_character_outside_the_phrase_data_loads_it(self):   # review 3: xref without loadChars
        self.open("?open=" + quote("马") + "&lang=en")
        self.page.click('#info a.xr[data-ch="馬"]')
        self.page.wait_for_selector('#info h2 [data-c="馬"]')
        self.assertEqual(self.tree()[0], "馬")
        self.assertIn("horse", self.page.inner_text("#info"))        # its data, not "no description"

    def test_escape_returns_focus_to_the_phrase(self):
        self.open("?lang=en")
        ch = self.page.locator("#phrase .ch").first
        ch.focus()
        self.page.keyboard.press("Enter")
        self.page.wait_for_selector("#card.open")
        self.page.focus("#explodeAll")                              # focus inside the card, which then hides
        self.page.keyboard.press("Escape")
        self.assertFalse(self.page.is_visible("#card"))
        self.assertEqual(self.page.evaluate("document.activeElement.dataset.ch"), ch.get_attribute("data-ch"))

    def test_close_button_on_desktop(self):
        self.open("?open=" + quote("想") + "&lang=en")
        self.page.click("#cardClose")
        self.assertFalse(self.page.is_visible("#card"))

    # ---- first visit ----
    def test_tour_tip_sits_on_top_of_the_card(self):                # desktop grid used to drop it below #info
        self.open("?lang=en", tour=True)
        self.page.click("#phrase .ch.pulse")
        tip = self.page.wait_for_selector("#tourTip:not([hidden])").bounding_box()
        bar = self.page.locator("#card .toolbar").bounding_box()
        self.assertLessEqual(tip["y"] + tip["height"], bar["y"] + 1)
        self.assertIn("+", self.page.inner_text("#tourTip"))

    def test_root_tile_buttons_are_not_clipped(self):               # ★ and +/− stick out 10px above the tile
        self.open("?open=" + quote("想") + "&lang=en")
        self.tree()
        star = self.page.locator("#tree > .node > .gw > .kbtn").bounding_box()
        box = self.page.locator("#tree").bounding_box()
        self.assertGreaterEqual(star["y"], box["y"])


if __name__ == "__main__":
    unittest.main()
