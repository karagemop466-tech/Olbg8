# Current OLBG research dashboard

This is the separate, source-first dashboard at `/current/`; it does not edit or validate the concurrently maintained root picks desk. Open the overview, a sport page, **Research briefs**, or **Flagged for review**. Browsing requires JavaScript; `live.json` is the underlying dated capture.

The collector observes the first public OLBG page in each of 16 hubs covering 15 requested sports (including Gaelic Football and Hurling) and samples at most two event-detail pages per sport. It respects robots.txt and does not bypass blocks. The schedule is intended to refresh hourly through `.github/workflows/current-refresh.yml`; GitHub scheduling, access or deployment can fail. The committed `live.json` is a dated fallback, not live odds. The interface flags a snapshot over three hours old, upstream failures, unmatched events and timing conflicts. An error or a page with no tips is not a fixture census.

Official schedule crosswalks are limited to uniquely matched NHL/MLB events and dated manually checked links. General official directories on other rows are clearly labeled as directories, not fixture confirmations. Prices are OLBG observations, not established bookmaker offers. NHL Poisson and MLB Pythagorean/log5 prices are uncalibrated, omit important factors and are review-only. Four individually sourced briefs are low-confidence research notes, not cleared recommendations. The target of at least five high-confidence picks per sport per day, exhaustive event/market coverage, complete injury information and independently priced lines are **not met**.

## Offline checks

```sh
python3 -m unittest discover -s current/tests -v
python3 current/build_pages.py
node --check current/app.js
```

For a public-source refresh on a network that can reach the sources, run `python3 current/collect.py`; it writes a new `current/live.json`. No credentials or private API access are needed.
