#!/usr/bin/env python3
"""Offline integrity checks for the pinned review report and source ledger."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import unittest

import build_report
import extract
from gate import OFFICIAL_HOSTS, valid_url

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.table = None
        self.in_body = False
        self.row = None
        self.rows = {}
        self.links = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if attr.get("id"):
            self.anchors.add(attr["id"])
        if tag == "table":
            self.table = attr.get("id")
        if tag == "tbody" and self.table:
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.row = []
        if tag == "a" and attr.get("href"):
            self.links.append(attr["href"])
            if self.row is not None:
                self.row.append(attr["href"])
        if tag in ("script", "link"):
            href = attr.get("src") or attr.get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            self.rows.setdefault(self.table, []).append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_body = False
        if tag == "table":
            self.table = None


def parse_html(path):
    parser = TableReader()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot, cls.catalog, cls.findings, cls.results = build_report.document()
        cls.index = parse_html(HERE / "index.html")

    def test_pinned_snapshot_and_identifiers(self):
        self.assertEqual(self.snapshot["baseline_commit"], extract.BASELINE)
        self.assertEqual(self.snapshot["source_picks_sha256"], extract.PICKS_SHA256)
        rows = self.snapshot["picks"]
        self.assertEqual(len(rows), 53)
        self.assertEqual(len({row["pick_id"] for row in rows}), 53)
        self.assertEqual(len({(row["sport_key"], row["event_id"]) for row in rows}), 46)
        self.assertEqual(len(self.catalog["directories"]), 15)
        self.assertEqual(len(self.findings["items"]), 18)

    def test_official_crosswalks_are_explicit_and_in_scope(self):
        for key, item in self.catalog["event_sources"].items():
            sport, event_id = key.split(":", 1)
            self.assertIn(sport, OFFICIAL_HOSTS, key)
            self.assertTrue(event_id, key)
            self.assertTrue(valid_url(item["url"], OFFICIAL_HOSTS[sport]), key)
            self.assertGreater(len(item["supports"]), 15, key)
        for sport, entry in self.catalog["directories"].items():
            self.assertIn(sport, OFFICIAL_HOSTS)
            self.assertTrue(valid_url(entry[1], OFFICIAL_HOSTS[sport]), sport)

    def test_gate_is_fail_closed_for_the_legacy_payload(self):
        self.assertEqual(Counter(result["status"] for result in self.results), {"withhold": 53})
        for result in self.results:
            self.assertIn("offer_not_confirmed", result["reasons"], result["id"])
            self.assertIn("missing_out_of_sample_calibration", result["reasons"], result["id"])
            self.assertIn("independent_pricing_not_recorded", result["reasons"], result["id"])
        self.assertEqual(sum(f'{p["sport_key"]}:{p["event_id"]}' in self.catalog["event_sources"] for p in self.snapshot["picks"]), 34)
        self.assertTrue(all("missing_event_evidence" in r["reasons"] for r in self.results))

    def test_report_rows_have_listing_and_official_links(self):
        rows = self.index.rows.get("ledger-table", [])
        self.assertEqual(len(rows), 53)
        all_official = tuple({h for hosts in OFFICIAL_HOSTS.values() for h in hosts} | {"liiga.fi"})
        for links in rows:
            self.assertTrue(any(valid_url(u, ("olbg.com",)) for u in links), links)
            self.assertTrue(any(valid_url(u, all_official) for u in links), links)
        findings = self.index.rows.get("findings-table", [])
        self.assertEqual(len(findings), 18)
        for links in findings:
            self.assertTrue(any(valid_url(u, all_official + ("olbg.com",)) for u in links), links)

    def test_local_links_assets_and_fragments(self):
        for filename in ("index.html", "method.html"):
            page = HERE / filename
            parser = parse_html(page)
            for href in parser.links:
                u = urlsplit(href)
                if u.scheme or href.startswith("mailto:"):
                    continue
                target = (page.parent / unquote(u.path)).resolve() if u.path else page
                self.assertTrue(target.exists(), f"{filename}: missing {href}")
                if u.fragment and target.suffix == ".html":
                    self.assertIn(unquote(u.fragment), parse_html(target).anchors,
                                  f"{filename}: missing fragment {href}")

    def test_generated_output_is_deterministic(self):
        self.assertEqual((HERE / "index.html").read_text(encoding="utf-8"), build_report.render())
        self.assertNotIn("__LEDGER_ROWS__", build_report.render())
        self.assertNotIn("__BASE_SHORT__", build_report.render())

    def test_window_discrepancy_is_reproducible(self):
        rows = {r["pick_id"]: r for r in self.snapshot["picks"]}
        out = {pid for pid, r in rows.items() if r.get("in_window") and isinstance(r.get("our_american"), (int, float))
               and not -250 <= r["our_american"] <= 10000}
        self.assertEqual(out, {"P008", "P015", "P051"})
        self.assertEqual([rows[pid]["our_american"] for pid in sorted(out)], [-259, -269, -291])

    def test_excerpt_source_does_not_promote_unrelated_claims(self):
        record = next(x for x in self.snapshot["picks"] if x["pick_id"] == "P010")
        adapted = build_report.adapt_legacy(record, self.catalog)
        self.assertIn("cricket:188852", self.catalog["event_sources"])
        self.assertEqual(adapted["sources"], [])
        self.assertNotIn("event", adapted["claim_sources"])
        self.assertNotIn("form", adapted["claim_sources"])
        self.assertIsNone(adapted["market"].get("offered_american"))
        self.assertIsNone(adapted["event"].get("start_utc"))
        self.assertFalse(adapted["pricing"]["independent_from_tip_shares"])


if __name__ == "__main__":
    unittest.main()
