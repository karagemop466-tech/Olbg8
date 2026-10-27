from __future__ import annotations
import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pages
import pricing

class SiteTests(unittest.TestCase):
    def test_scope_and_hurling(self):
        sports = json.loads((ROOT/'catalog.json').read_text())
        self.assertEqual(len(sports), 15)
        gaelic = next(x for x in sports if x['key']=='gaelic-sports')
        self.assertEqual([h[0] for h in gaelic['hubs']], ['Gaelic_Football','Hurling'])
        self.assertTrue(all(urlparse(s['official']).scheme=='https' for s in sports))

    def test_briefs_are_unique_sourced_and_long(self):
        briefs = json.loads((ROOT/'briefs.json').read_text())
        self.assertEqual(len({x['id'] for x in briefs}), len(briefs))
        self.assertEqual(len({x['prediction'] for x in briefs}), len(briefs))
        for b in briefs:
            self.assertGreaterEqual(len(b['prediction'].split()), 30, b['id'])
            for word in ('model', 'verified'):
                self.assertNotIn(word, b['prediction'].lower())
            self.assertEqual(b['status'], 'needs-review')
            self.assertEqual(b['confidence'], 'Low')
            self.assertTrue(b['officialSources'])
            self.assertTrue(all(urlparse(s['url']).scheme=='https' for s in b['officialSources']))
            self.assertEqual(urlparse(b['olbg']).hostname, 'www.olbg.com')
        line = next(x['researchLine'] for x in briefs if x['researchLine'])
        p = pricing.log5(pricing.pythagorean(832,618), pricing.pythagorean(736,650))
        self.assertAlmostEqual(line['probability'], p)
        self.assertEqual(line['american'], pricing.american(p))

    def test_generated_pages_and_assets(self):
        sports = json.loads((ROOT/'catalog.json').read_text())
        for sport in sports:
            file = ROOT/'sports'/f"{sport['key']}.html"
            self.assertEqual(file.read_text(), build_pages.shell(sport['name'],'sport','..',sport['key']))
        for file in list(ROOT.glob('*.html')) + list((ROOT/'sports').glob('*.html')):
            text=file.read_text()
            for link in re.findall(r'(?:href|src)="([^"]+)"',text):
                parsed=urlparse(link)
                if not parsed.scheme and not link.startswith('#'):
                    self.assertTrue((file.parent/parsed.path).exists(), (file,link))

    def test_capture_invariants_when_present(self):
        file=ROOT/'live.json'
        if not file.exists(): self.skipTest('seed capture has not yet been retrieved')
        data=json.loads(file.read_text())
        self.assertEqual(data['schema'], 'olbg-current/v1')
        self.assertEqual(len(data['sports']),15)
        self.assertEqual(len(data['hubs']),16)
        self.assertEqual(data['publishedPicks'],[])
        pairs=set()
        for e in data['events']:
            pair=(e['hub'],e['id']); self.assertNotIn(pair,pairs);pairs.add(pair)
            self.assertEqual(urlparse(e['url']).hostname,'www.olbg.com')
            if not e['event']:
                self.assertIsNone(e['official'])
            if e['official']:
                self.assertEqual(urlparse(e['official']['url']).scheme,'https')
            if e['odds']:
                self.assertGreaterEqual(abs(e['odds']['american']),100)
                self.assertGreater(e['odds']['decimal'],1)

if __name__=='__main__': unittest.main()
