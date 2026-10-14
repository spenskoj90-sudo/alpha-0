"""Validate exported public navigation targets without starting the Core."""
from html.parser import HTMLParser
from pathlib import Path
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ('features', 'games', 'modules', 'pricing', 'help', 'access')

class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.h1s = 0
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'a':
            self.links.append(values)
        if tag == 'h1':
            self.h1s += 1

class PublicRoutesTest(unittest.TestCase):
    def test_public_game_projection_matches_canonical_catalog(self):
        catalog = json.loads((ROOT / "server/app/data/game-capability-catalog.v1.json").read_text())
        expected = [{key: p[key] for key in ("id", "name", "platform", "patch", "implementation_status")} for p in catalog["profiles"]]
        self.assertEqual(json.loads((ROOT / "site/app/components/game-profiles.json").read_text()), expected)

    def test_pages_have_reachable_real_targets(self):
        home = Page((ROOT / 'site/out/index.html').read_text())
        for route in ROUTES:
            with self.subTest(route=route):
                target = ROOT / f'site/out/{route}.html'
                self.assertTrue(target.is_file(), f'{route} export missing')
                self.assertTrue(any(a.get('href', '').rstrip('/') == f'/{route}' for a in home.links))
                self.assertEqual(Page(target.read_text()).h1s, 1)

if __name__ == '__main__':
    unittest.main()
