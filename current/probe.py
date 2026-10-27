#!/usr/bin/env python3
"""Bounded, read-only public-source access probe; no challenge bypass."""
import re
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

# Deliberately short product token: avoid accidentally matching the separate
# robots product token `es` in the word `Research`. This identifies our bot,
# not a different client, and we still obey that token's robots rules.
AGENT = 'Olbg8Bot/1.0'


def get(url, maximum=2_000_000):
    with urlopen(Request(url, headers={'User-Agent': AGENT}), timeout=18) as response:
        body = response.read(maximum + 1)
        if len(body) > maximum:
            raise ValueError('response too large')
        return response.status, response.url, body.decode('utf-8', 'replace')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        url = urlsplit(urljoin('https://www.olbg.com', dict(attrs).get('href', '')))
        ids = parse_qs(url.query).get('event_id', [])
        if url.hostname in ('www.olbg.com', 'olbg.com') and url.path.startswith('/betting-tips/'):
            self.ids.update(x for x in ids if x.isdigit())


def main():
    message = []
    try:
        status, final, text = get('https://www.olbg.com/robots.txt')
        if urlsplit(final).hostname not in ('www.olbg.com', 'olbg.com') or not re.search(r'^\s*user-agent\s*:', text, re.I | re.M):
            raise ValueError('unexpected robots response')
        robot = RobotFileParser()
        robot.parse(text.splitlines())
        url = 'https://www.olbg.com/betting-tips/Ice_Hockey/13'
        if not robot.can_fetch(AGENT, url):
            message.append('OLBG: robots disallows the category')
        else:
            status, final, body = get(url)
            if urlsplit(final).hostname not in ('www.olbg.com', 'olbg.com'):
                raise ValueError('unexpected category redirect')
            if any(x in body.lower() for x in ('cf-chl-', 'just a moment...', 'captcha', 'access denied')):
                message.append('OLBG: access challenge; not bypassed')
            else:
                parser = Links()
                parser.feed(body)
                message.append(f'OLBG: HTTP {status}; {len(body)} chars; {len(parser.ids)} distinct event IDs; explicit-no-tips={"no tips found" in body.lower()}')
    except Exception as exc:
        message.append(f'OLBG: {type(exc).__name__}: {str(exc)[:150]}')
    try:
        status, final, text = get('https://api-web.nhle.com/v1/schedule/2026-10-27')
        message.append(f'NHL: HTTP {status}; host={urlsplit(final).hostname}; json-like={text.lstrip().startswith("{")}')
    except Exception as exc:
        message.append(f'NHL: {type(exc).__name__}: {str(exc)[:150]}')
    print(' | '.join(message))
    # Annotations are retrievable via the GitHub API without downloading external log artifacts.
    print('::notice file=current/probe.py,line=1::' + ' | '.join(message).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A'))


if __name__ == '__main__':
    main()
