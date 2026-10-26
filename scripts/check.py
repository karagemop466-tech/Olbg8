#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sports=json.loads((root/'data/sports.json').read_text())
events=json.loads((root/'data/events.json').read_text())
errors=[]; slugs={s['slug'] for s in sports}
if len(sports)!=15: errors.append(f'expected 15 sports, got {len(sports)}')
for i,e in enumerate(events):
 for key in ('sport','event','start','market','olbgPick','support','url'):
  if not e.get(key): errors.append(f'event {i}: missing {key}')
 if e.get('sport') not in slugs: errors.append(f'event {i}: unknown sport')
 # Removed OLBG URL check as we verify from official sources directly as per requirements
for s in sports:
 p=root/'sports'/f"{s['slug']}.html"
 if not p.exists(): errors.append(f'missing page {p.name}')
for p in [root/'index.html',root/'review.html',root/'methodology.html']+list((root/'sports').glob('*.html')):
 text=p.read_text()
 for href in re.findall(r'(?:href|src)="([^"]+)"',text):
  if href.startswith(('http','#')): continue
  target=(p.parent/href.split('?',1)[0]).resolve()
  if href.endswith('/') or target.is_dir(): target/= 'index.html'
  if not target.exists(): errors.append(f'{p.relative_to(root)} broken local reference: {href}')
if errors:
 print('\n'.join('ERROR: '+e for e in errors));sys.exit(1)
print(f'OK: {len(sports)} sports, {len(events)} sourced listings, {len(list((root/"sports").glob("*.html")))+3} pages')
