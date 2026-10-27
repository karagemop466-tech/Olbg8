from __future__ import annotations
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collect

# Synthetic markup: no real events or prices are asserted by these fixtures.
CARD = '''<div class="grd tip content-visibility-auto">
  <div class="rw ev" itemscope><a itemprop="url" href="https://www.olbg.com/betting-tips/Ice_Hockey/Other/NHL/Alpha_@_Beta/13?event_id=123"><h5 itemprop="name">AAA Alpha @ BBB Beta</h5></a><p class="text-sm truncate"><i></i>NHL</p><div><time itemprop="startDate" datetime="2031-01-02T01:07:00.000Z">today</time></div></div>
  <div class="rw sel"><a href="/x"><h4>AAA Alpha</h4></a><p>Money Line</p><div><div>nested</div></div></div>
  <div class="rw odds"><span class="ui-odds" data-decimal="1.77" data-american="-130"></span></div>
</div>'''
DETAILS = '''<ul><li class="group/market"><div><button id="market_id_100"><h4>Money Line</h4></button>
<div id="200" class="block grd"><div class="rw slct"><h4>Alpha</h4></div><div><span class="ui-odds" data-decimal="1.77" data-american="-130"></span></div></div>
<div id="201" class="block grd"><div class="rw slct"><h4>Beta</h4></div><div><span class="ui-odds" data-decimal="2.10" data-american="110"></span></div></div>
</div></li><li><button id="market_id_101"><h4>Points Total</h4></button><div id="202" class="grd"><div><h4>Over 5.5</h4></div></div></li></ul>'''

class ParserTests(unittest.TestCase):
    def test_category_card(self):
        p = collect.CategoryParser(); p.feed(CARD)
        self.assertEqual(len(p.rows), 1)
        r = p.rows[0]
        self.assertEqual(r['event'], 'AAA Alpha @ BBB Beta')
        self.assertEqual(r['competition'], 'NHL')
        self.assertEqual(r['start'], '2031-01-02T01:07:00Z')
        self.assertEqual(r['selection'], 'AAA Alpha')
        self.assertEqual(r['market'], 'Money Line')
        self.assertEqual(r['odds'], {'american':-130, 'decimal':1.77})

    def test_market_details_and_missing_odds(self):
        p = collect.MarketParser(); p.feed(DETAILS)
        self.assertEqual([m['name'] for m in p.markets], ['Money Line','Points Total'])
        self.assertEqual([s['selection'] for s in p.markets[0]['selections']], ['Alpha','Beta'])
        self.assertEqual(p.markets[0]['selections'][1]['odds']['american'], 110)
        self.assertIsNone(p.markets[1]['selections'][0]['odds'])

    def test_odds_fail_closed(self):
        self.assertIsNone(collect.odds_from({'data-decimal':'2.00','data-american':'-130'}))
        self.assertIsNone(collect.odds_from({'data-decimal':'0','data-american':'0'}))
        self.assertIsNone(collect.odds_from({}))

    def test_legitimate_captcha_reference_is_not_challenge(self):
        self.assertFalse(collect.is_challenge('<title>Sports tips</title><script src="captcha.js"></script>'))
        self.assertTrue(collect.is_challenge('<title>Just a moment...</title>'))
        self.assertTrue(collect.is_challenge('<title>X</title><div class="cf-chl-test">'))

    def test_only_public_event_urls(self):
        self.assertTrue(collect.valid_olbg_url('https://www.olbg.com/betting-tips/A/1?event_id=12'))
        self.assertFalse(collect.valid_olbg_url('https://evil.invalid/betting-tips/A/1?event_id=12'))
        self.assertFalse(collect.valid_olbg_url('https://www.olbg.com/api/A?event_id=12'))

class CrosswalkTests(unittest.TestCase):
    def setUp(self):
        p = collect.CategoryParser(); p.feed(CARD)
        self.r = p.rows[0]; self.r['sport'] = 'ice-hockey'
        self.f = {'league':'NHL','away':'Alpha','home':'Beta','start':'2031-01-02T01:00:00Z','url':'https://api-web.nhle.com/v1/gamecenter/1/landing'}

    def test_exact_team_and_time(self):
        m = collect.dynamic_crosswalk(self.r, [self.f], '2031-01-01T00:00:00Z')
        self.assertEqual(m['timeDifferenceMinutes'], 7)
        self.assertEqual(m['start'], self.f['start'])
        self.assertIsNone(collect.dynamic_crosswalk(self.r, [self.f, self.f], '2031-01-01T00:00:00Z'))
        self.assertIsNone(collect.dynamic_crosswalk(self.r, [{**self.f,'home':'Gamma'}], '2031-01-01T00:00:00Z'))
        self.assertIsNone(collect.dynamic_crosswalk({**self.r,'competition':None}, [self.f], '2031-01-01T00:00:00Z'))

    def test_manual_requires_id_name_and_date(self):
        c = [{'sport':'ice-hockey','id':'123','name':self.r['event'],'date':'2031-01-02','officialUrl':'https://example.org','note':'test'}]
        self.assertIsNotNone(collect.manual_crosswalk(self.r, c))
        self.assertIsNone(collect.manual_crosswalk({**self.r,'event':'Something else'}, c))
        self.assertIsNone(collect.manual_crosswalk({**self.r,'start':'2031-01-03T01:00:00Z'}, c))

    def test_nhl_mlb_parsing_and_status(self):
        nhl = {'gameWeek':[{'games':[{'id':12,'gameState':'FUT','startTimeUTC':'2031-01-02T01:00:00Z',
              'awayTeam':{'commonName':{'default':'Alpha'}},'homeTeam':{'commonName':{'default':'Beta'}}},
              {'id':13,'gameState':'FINAL'}]}]}
        self.assertEqual(len(collect.nhl_fixtures(nhl)), 1)
        mlb = {'dates':[{'games':[{'gamePk':8,'gameDate':'2031-01-02T01:00:00Z','status':{'abstractGameState':'Preview'},
                'teams':{'away':{'team':{'teamName':'Alpha'}},'home':{'team':{'teamName':'Beta'}}}}]}]}
        self.assertEqual(len(collect.mlb_fixtures(mlb)), 1)

    def test_nhl_line_requires_matching_season_and_inputs(self):
        official={'kind':'schedule-api','gameType':2,'season':20302031,'homeAbbrev':'BBB','awayAbbrev':'AAA'}
        team={'seasonId':20302031,'gamesPlayed':10,'goalFor':30,'goalAgainst':30}
        line=collect.nhl_line(official,{'BBB':team,'AAA':team})
        self.assertIsNotNone(line)
        self.assertAlmostEqual(line['homeProbability'],.5,places=8)
        self.assertIsNone(collect.nhl_line({**official,'gameType':3},{'BBB':team,'AAA':team}))
        self.assertIsNone(collect.nhl_line({**official,'season':20402041},{'BBB':team,'AAA':team}))

    def test_failure_is_not_no_events(self):
        class Failed:
            def get(self, url): raise OSError('offline')
        out = collect.build_snapshot(Failed(), datetime(2031,1,1,tzinfo=timezone.utc), 0)
        self.assertEqual(out['events'], [])
        self.assertTrue(all(h['status'] == 'error' for h in out['hubs']))
        self.assertEqual(out['publishedPicks'], [])

if __name__ == '__main__': unittest.main()
