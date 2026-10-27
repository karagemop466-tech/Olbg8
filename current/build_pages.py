#!/usr/bin/env python3
"""Create static shells; data and navigation are rendered by current/app.js."""
from __future__ import annotations
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent


def shell(title: str, page: str, base: str = '.', sport: str = '') -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Source-first multi-sport research, OLBG observations and official-source links.">
  <title>{escape(title)} · The Research Desk</title>
  <link rel="stylesheet" href="{escape(base)}/styles.css">
  <script src="{escape(base)}/app.js" defer></script>
</head>
<body data-page="{escape(page)}" data-sport="{escape(sport)}" data-base="{escape(base)}">
  <noscript><div class="noscript">This dashboard requires JavaScript to display its source snapshot. The JSON data is available at <a href="{escape(base)}/live.json">live.json</a>.</div></noscript>
  <div class="layout"><div id="sidebar"></div><div class="main-column"><div id="topbar"></div><main id="app" class="workspace" aria-live="polite"><div class="empty">Loading the latest source snapshot…</div></main><div id="footer"></div></div></div>
</body>
</html>
'''


def build():
    pages = [('index.html','Overview','home'),('listings.html','All listings','listings'),
             ('briefs.html','Research briefs','briefs'),('review.html','Flagged for review','review'),
             ('methodology.html','Methodology','method')]
    for path,title,page in pages:
        (HERE/path).write_text(shell(title,page), encoding='utf-8')
    for sport in json.loads((HERE/'catalog.json').read_text()):
        target=HERE/'sports'/f"{sport['key']}.html"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(shell(sport['name'],'sport','..',sport['key']),encoding='utf-8')
    print(f'Built {len(pages) + len(json.loads((HERE/"catalog.json").read_text()))} current dashboard shells.')

if __name__ == '__main__': build()
