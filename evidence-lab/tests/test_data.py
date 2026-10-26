import json
import unittest
from datetime import datetime,timezone
from urllib.parse import urlparse,parse_qs
from scripts.build import ROOT,SPORTS,EVENTS,PICKS,main
from scripts.check import check,Page
from scripts.policy import publication_errors,instant
from scripts.collect import EventLinks
class DataTests(unittest.TestCase):
    def test_sport_scope(self):
        self.assertEqual(len(SPORTS),15)
        self.assertEqual(len({s['slug'] for s in SPORTS}),15)
        self.assertEqual(sum(len(s['olbg_urls']) for s in SPORTS),16)
    def test_unique_ids(self):self.assertEqual(len(EVENTS),len({(x['sport'],x['id']) for x in EVENTS}))
    def test_source_urls(self):
        for x in EVENTS:
            self.assertEqual(urlparse(x['olbg_url']).hostname,'www.olbg.com')
            self.assertEqual(parse_qs(urlparse(x['olbg_url']).query)['event_id'],[x['id']])
            self.assertTrue(x['flags'])
    def test_no_unsubstantiated_fields(self):
        self.assertEqual(PICKS,[])
        for x in EVENTS:
            for k in ['start_utc','selection','confidence','probability','fair_american','prediction']:self.assertIsNone(x[k])
    def test_official_confirmation_is_scoped(self):
        for x in EVENTS:
            self.assertEqual(bool(x['official_fact']),bool(x['official_url']))
            self.assertNotEqual(x['status'],'verified')
            if x['official_start_utc']:self.assertTrue(x['official_fact'])
    def test_no_automatic_promotions(self):self.assertTrue(publication_errors({}))
    def test_editorial_banned_word(self):
        errs=publication_errors({'prediction':'This verified model is a pick.'})
        self.assertIn('Prohibited editorial word',errs)
    def test_timezone_required(self):
        with self.assertRaises(ValueError):instant('2026-10-27T01:00:00')
    def test_early_start_rejected(self):
        errs=publication_errors({'start_utc':'2026-10-25T23:00:00Z'},datetime(2026,10,26,tzinfo=timezone.utc))
        self.assertIn('Event already started',errs)
    def test_production_disabled(self):
        self.assertIn('Production pricing and calibration adapters not implemented',publication_errors({}))
    def test_public_link_parser(self):
        p=EventLinks();p.feed('<a href="/betting-tips/Tennis/X/3?event_id=123"><b>A vs B</b></a><a href="/betting-tips/Tennis/X/3?event_id=123">A</a><a href="https://evil.example/?event_id=4">Fake</a>')
        self.assertEqual(list(p.events),['123']);self.assertEqual(p.events['123']['label'],'A vs B')
    def test_build_and_local_links(self):main();self.assertEqual(check(),21)
    def test_rows_have_official_review_link(self):
        # All data rows, not header rows. Every official-directory-only link stays labelled as such.
        allowed={urlparse(s['official_url']).hostname for s in SPORTS}|{'www.lpga.com'}
        main()
        for path in (ROOT/'_site').rglob('*.html'):
            page=Page(path.read_text())
            for row in page.rows:
                if row:self.assertTrue(any(urlparse(u).hostname in allowed for u in row),f'{path}: missing official source')
    def test_no_placeholder_fixture_dates(self):
        self.assertEqual(next(x for x in EVENTS if x['id']=='160795')['official_start_utc'],'2026-10-28T00:00:00Z')
    def test_all_sports_have_research(self):
        for s in SPORTS:
            for field in ['source_scope','pricing_method','required_inputs','markets']:self.assertTrue(s[field])
