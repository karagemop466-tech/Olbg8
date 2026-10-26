import unittest,json,sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
sys.path.insert(0,str(Path(__file__).parent))
from pricing import *
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  self.links.extend(v for k,v in attrs if k in ('href','src'))
class Tests(unittest.TestCase):
 def test_links(self):
  pages=list(Path('_site').glob('*.html'));self.assertEqual(len(pages),20)
  for page in pages:
   p=Links();p.feed(page.read_text())
   for url in p.links:
    u=urlsplit(url)
    if not u.scheme and u.path:self.assertTrue((page.parent/unquote(u.path)).exists(),url)
 def test_evidence(self):
  d=json.loads(Path('data/research.json').read_text());self.assertEqual(len(d['sports']),15)
  ids=set()
  for r in d['events']:
   key=(r['sport'],r['event_id']);self.assertNotIn(key,ids);ids.add(key)
   self.assertTrue(r['source'].startswith('https://www.olbg.com/'))
   self.assertFalse(eligible(r));self.assertIsNone(r['prediction']);self.assertIsNone(r['fair_decimal'])
   self.assertTrue(r['flags'])
 def test_prices(self):
  self.assertAlmostEqual(decimal_from_american(-250),1.4)
  self.assertEqual(decimal_from_american(10000),101)
  self.assertAlmostEqual(fair_decimal(.6,.1),1.5)
  self.assertAlmostEqual(expected_value(.7,1.4),-.02)
  self.assertAlmostEqual(expected_value(.6,2,.1),.3)
  for p in (0,1,-.2,float('nan')):
   with self.assertRaises(ValueError):fair_decimal(p)
  for a in (0,50,-50,float('inf')):
   with self.assertRaises(ValueError):decimal_from_american(a)
if __name__=='__main__':unittest.main()
