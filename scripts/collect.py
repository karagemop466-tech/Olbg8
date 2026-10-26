"""Best-effort discovery of PUBLIC OLBG event links. Never emits recommendations.
Conservative robots handling: unknown/failed robots -> no collection, no bypass.
No undocumented endpoint calls, cookies, login, proxy rotation or anti-bot evasion.
"""
import hashlib
import json
import re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib import request,robotparser
from urllib.parse import urljoin,urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[1]
AGENT='Olbg8Research/1.0'
MAX_BYTES=2_000_000
class EventLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.active=None;self.text=[];self.events={}
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            url=urljoin('https://www.olbg.com',dict(attrs).get('href',''))
            u=urlparse(url); eid=parse_qs(u.query).get('event_id',[''])[0]
            if u.hostname in ['olbg.com','www.olbg.com'] and u.path.startswith('/betting-tips/') and eid.isdigit():
                self.active=(eid,url);self.text=[]
    def handle_data(self,data):
        if self.active:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.active:
            eid,url=self.active;label=' '.join(' '.join(self.text).split())
            if label and eid not in self.events:self.events[eid]={'id':eid,'label':label,'url':url}
            self.active=None

def get(url):
    req=request.Request(url,headers={'User-Agent':AGENT})
    with request.urlopen(req,timeout=20) as response:
        if urlparse(response.url).hostname not in ['olbg.com','www.olbg.com']: raise ValueError('Unexpected redirect host')
        body=response.read(MAX_BYTES+1)
        if len(body)>MAX_BYTES:raise ValueError('Response exceeds size cap')
        return body.decode('utf-8','replace')

def main():
    now=datetime.now(timezone.utc).isoformat()
    result={'attempted_at':now,'coverage':'partial; first public category response only, no pagination guarantee','pages':[]}
    archive=ROOT/'data'/'collection';archive.mkdir(parents=True,exist_ok=True)
    try:
        robots=get('https://www.olbg.com/robots.txt')
        if '<html' in robots.lower() or not re.search(r'^\s*user-agent\s*:',robots,re.I|re.M):raise ValueError('Invalid robots.txt response')
        rp=robotparser.RobotFileParser();rp.parse(robots.splitlines())
        delay=rp.crawl_delay(AGENT) or rp.crawl_delay('*') or 1
        if delay>30:raise ValueError('Crawl delay exceeds collector budget')
    except Exception as exc:
        result['status']='blocked';result['error']=f'Cannot establish robots permission: {type(exc).__name__}: {exc}'
        (ROOT/'data'/'collection-status.json').write_text(json.dumps(result,indent=2)+'\n');return
    import time
    for sport in json.loads((ROOT/'data'/'sports.json').read_text()):
        for url in sport['olbg_urls']:
            item={'sport':sport['slug'],'url':url,'events':[],'retrieved_at':None}
            try:
                if not rp.can_fetch(AGENT,url): raise ValueError('robots.txt disallows collection')
                time.sleep(delay)
                body=get(url)
                if any(token in body.lower() for token in ['just a moment...','cf-chl-','captcha','access denied']): raise ValueError('Access challenge; no bypass attempted')
                parser=EventLinks();parser.feed(body)
                if not parser.events and 'no tips found' not in body.lower():raise ValueError('No recognized events or explicit no-tips state; markup requires review')
                digest=hashlib.sha256(body.encode()).hexdigest()
                snapshot=archive/(digest+'.html');snapshot.write_text(body)
                item.update(status='observed',retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=digest,snapshot='data/collection/'+snapshot.name,events=list(parser.events.values()))
            except Exception as exc:item.update(status='blocked',error=f'{type(exc).__name__}: {exc}')
            result['pages'].append(item)
    result['status']='partial' if any(p['status']=='observed' for p in result['pages']) else 'blocked'
    (ROOT/'data'/'collection-status.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
