"""Read-only daily discovery. Never promote observations into selections.

Fetches public pages at low frequency; records HTTP/parse failures distinctly
from empty fixture sets. No private API, credentials or access-control bypass.
"""
import json,hashlib,time
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin,urlsplit,parse_qs
class EventLinks(HTMLParser):
 def __init__(self):super().__init__();self.found={};self.current=None;self.text=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   url=dict(attrs).get('href','');u=urlsplit(urljoin('https://www.olbg.com',url));eid=parse_qs(u.query).get('event_id')
   self.current=(eid[0],u.geturl()) if u.hostname in ('www.olbg.com','olbg.com') and '/betting-tips/' in u.path and eid else None;self.text=[]
 def handle_data(self,data):
  if self.current:self.text.append(data)
 def handle_endtag(self,tag):
  if tag=='a' and self.current:
   eid,url=self.current;label=' '.join(' '.join(self.text).split())
   self.found.setdefault(eid,dict(event_id=eid,source=url,anchor_text=label));self.current=None

def run():
 d=json.loads(Path('data/research.json').read_text());results=[]
 sources=[(s['name'],s['url']) for s in d['sports']]
 for sport,url in sources:
  row=dict(sport=sport,source=url,retrieved_at=datetime.now(timezone.utc).isoformat(),complete=False,events=[],error=None)
  try:
   with urlopen(Request(url,headers={'User-Agent':'Olbg8-Research/1.0 (public-page research; low frequency)'}),timeout=25) as r:
    content=r.read(4_000_000);row['http_status']=r.status
   row['sha256']=hashlib.sha256(content).hexdigest();p=EventLinks();p.feed(content.decode('utf-8','replace'));row['events']=list(p.found.values())
   row['status']='discovered_unverified' if p.found else 'no_event_links_extracted_not_proof_of_no_events'
  except Exception as exc:row['status']='fetch_failed';row['error']=str(exc)
  results.append(row);time.sleep(1)
 Path('discovery-report.json').write_text(json.dumps(dict(generated_at=datetime.now(timezone.utc).isoformat(),note='Unverified discovery only. No prices or predictions. Pagination and JS may hide events.',sources=results),indent=2)+'\n')
 print(f'{sum(r["status"]=="fetch_failed" for r in results)}/{len(results)} sources failed; report saved; research dataset unchanged.')
if __name__=='__main__':run()
