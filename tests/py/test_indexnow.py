"""IndexNow after a deploy: which sitemap pages to send. No network: fetch is a dict."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import indexnow  # noqa: E402

BASE = "https://hanzi.lipu.dev"


class ChangedUrls(unittest.TestCase):
    def test_lists_new_changed_and_gone_pages(self):
        with tempfile.TemporaryDirectory() as d:
            site = Path(d)
            pages = {"/": b"home", "/c/57fa": b"new text", "/r/": b"same", "/poster.pdf": b"pdf"}
            for path, body in pages.items():
                f = indexnow.page_file(site, BASE + path)
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(body)
            (site / "sitemap.xml").write_text("".join(f"<loc>{BASE}{p}</loc>" for p in pages), encoding="utf-8")
            live = {BASE + "/": b"home", BASE + "/c/57fa": b"old text", BASE + "/r/": b"same", BASE + "/poster.pdf": b"pdf",
                    BASE + "/sitemap.xml": f"<loc>{BASE}/</loc><loc>{BASE}/c/gone</loc>".encode()}
            changed = indexnow.changed_urls(site, fetch=live.get)
        self.assertEqual(changed, [BASE + "/c/57fa", BASE + "/c/gone"])

    def test_page_file(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "poster.pdf").write_bytes(b"pdf")
            self.assertEqual(indexnow.page_file(d, BASE + "/"), Path(d) / "index.html")
            self.assertEqual(indexnow.page_file(d, BASE + "/en/r/"), Path(d) / "en/r/index.html")
            self.assertEqual(indexnow.page_file(d, BASE + "/c/57fa"), Path(d) / "c/57fa.html")
            self.assertEqual(indexnow.page_file(d, BASE + "/poster.pdf"), Path(d) / "poster.pdf")


if __name__ == "__main__":
    unittest.main()
