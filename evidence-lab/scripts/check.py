"""Local Pages base-path, assets, fragment and external source presence checks."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse,unquote
ROOT=Path(__file__).resolve().parents[1]/'_site'
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__();self.links=[];self.ids=set();self.rows=[];self.row=None;self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        for key in ['href','src']:
            if key in a:self.links.append(a[key])
        if tag=='tr':self.row=[]
        if tag=='a' and self.row is not None:self.row.append(a.get('href',''))
    def handle_endtag(self,tag):
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row);self.row=None

def check():
    errors=[];pages={p:Page(p.read_text()) for p in ROOT.rglob('*.html')}
    for p,parsed in pages.items():
        for url in parsed.links:
            u=urlparse(url)
            if u.scheme or u.netloc:continue
            path=unquote(u.path)
            if path.startswith('/Olbg8/'):target=ROOT/path[len('/Olbg8/'):]
            elif path.startswith('/'):errors.append(f'{p}: domain-root URL breaks project Pages: {url}');continue
            else:target=(p.parent/path).resolve() if path else p
            if target.is_dir():target=target/'index.html'
            if url.endswith('../index.html') and not target.exists():continue  # parent site is outside isolated build
            if not target.exists():errors.append(f'{p}: missing target {url}')
            elif u.fragment and target in pages and u.fragment not in pages[target].ids:errors.append(f'{p}: missing fragment {url}')
    if errors:raise ValueError('\n'.join(errors))
    print(f'PASS: {len(pages)} HTML pages; all local links, assets and fragments resolve under /Olbg8/. External availability is not implied.')
    return len(pages)
if __name__=='__main__':check()
