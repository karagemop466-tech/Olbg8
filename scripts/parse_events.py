#!/usr/bin/env python3
"""Extract every market and outcome (with odds) from OLBG event-page snapshots.

The event pages embed a server-side payload of the form
    event:{slug:"...",sportName:"...",tournament:"...",markets:[{name:"...",tips:[{selection:"...",odds:"2.10",...}]}]}
This module parses that JS object literal (no dependencies) into data/markets.json.
Nothing is inferred: absent fields stay None and untouched pages are reported.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "data" / "raw" / "events"


class JSParser:
    def __init__(self, text, pos=0):
        self.s = text
        self.i = pos
        self.n = len(text)

    def ws(self):
        while self.i < self.n:
            c = self.s[self.i]
            if c in " \t\r\n,":
                self.i += 1
            elif self.s.startswith("//", self.i):
                j = self.s.find("\n", self.i)
                self.i = self.n if j < 0 else j + 1
            elif self.s.startswith("/*", self.i):
                j = self.s.find("*/", self.i)
                self.i = self.n if j < 0 else j + 2
            else:
                return

    def value(self):
        self.ws()
        if self.i >= self.n:
            raise ValueError("eof")
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return self.string()
        if c == "'":
            return self.string("'")
        if self.s.startswith("true", self.i):
            self.i += 4
            return True
        if self.s.startswith("false", self.i):
            self.i += 5
            return False
        if self.s.startswith("null", self.i):
            self.i += 4
            return None
        if self.s.startswith("undefined", self.i):
            self.i += 9
            return None
        m = re.match(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", self.s[self.i:])
        if m:
            self.i += m.end()
            v = m.group(0)
            return float(v) if ("." in v or "e" in v.lower()) else int(v)
        # bare scalar (identifier) - consume until delimiter
        m = re.match(r"[A-Za-z_$][\w$]*", self.s[self.i:])
        if m:
            self.i += m.end()
            return m.group(0)
        raise ValueError(f"unexpected {c!r} at {self.i}")

    def string(self, q='"'):
        self.i += 1
        out = []
        while self.i < self.n:
            c = self.s[self.i]
            if c == "\\":
                self.i += 1
                e = self.s[self.i]
                out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "/": "/", "\\": "\\"}.get(e, e))
                self.i += 1
            elif c == q:
                self.i += 1
                return "".join(out)
            else:
                out.append(c)
                self.i += 1
        raise ValueError("unterminated string")

    def obj(self):
        self.i += 1
        d = {}
        while True:
            self.ws()
            if self.i >= self.n:
                raise ValueError("eof object")
            if self.s[self.i] == "}":
                self.i += 1
                return d
            c = self.s[self.i]
            if c in "\"'":
                k = self.string(c)
            else:
                m = re.match(r"[A-Za-z_$][\w$]*", self.s[self.i:])
                if not m:
                    raise ValueError(f"bad key at {self.i}")
                k = m.group(0)
                self.i += m.end()
            self.ws()
            if self.i < self.n and self.s[self.i] == ":":
                self.i += 1
                d[k] = self.value()
            else:
                d[k] = True  # shorthand
            self.ws()
            if self.i < self.n and self.s[self.i] == ",":
                self.i += 1

    def arr(self):
        self.i += 1
        out = []
        while True:
            self.ws()
            if self.i >= self.n:
                raise ValueError("eof array")
            if self.s[self.i] == "]":
                self.i += 1
                return out
            out.append(self.value())
            self.ws()
            if self.i < self.n and self.s[self.i] == ",":
                self.i += 1


def extract_event(html):
    m = re.search(r"event:\{slug:", html)
    if not m:
        return None
    p = JSParser(html, m.start() + len("event:"))
    return p.value()


def norm_american(a):
    if a is None:
        return None
    s = str(a).strip()
    if s in ("", "0"):
        return None
    try:
        v = int(s)
    except ValueError:
        return None
    return v


def main():
    records = []
    problems = []
    for f in sorted(EVENTS.glob("*.html")):
        if f.name.startswith("_"):
            continue
        html = f.read_text(encoding="utf-8", errors="replace")
        try:
            ev = extract_event(html)
        except Exception as e:  # noqa: BLE001
            problems.append((f.name, f"parse error: {e}"))
            continue
        if not ev:
            problems.append((f.name, "no embedded event payload"))
            continue
        markets = []
        for mk in ev.get("markets") or []:
            outs = []
            for t in mk.get("tips") or []:
                if not isinstance(t, dict):
                    continue
                dec = None
                try:
                    dec = float(t.get("odds")) if t.get("odds") not in (None, "") else None
                except (TypeError, ValueError):
                    dec = None
                outs.append({
                    "selection": t.get("selection"),
                    "decimal": dec,
                    "american": norm_american(t.get("american_odds")),
                    "fractional": t.get("fractional_odds"),
                    "win_tips": t.get("win_tips"),
                    "win_tips_count": t.get("win_tips_count"),
                    "confidence": t.get("confidence"),
                    "comments": t.get("comments_count"),
                })
            markets.append({"market_id": mk.get("id"), "name": mk.get("name"), "outcomes": outs})
        sport_file = f.stem.rsplit("_", 1)[0]
        records.append({
            "sport_file": sport_file,
            "event_id": ev.get("id"),
            "event": (ev.get("slug") or "").split("/")[-2].replace("_", " ") if ev.get("slug") else None,
            "sport_name": ev.get("sportName"),
            "tournament": ev.get("tournament"),
            "league": ev.get("leagueName"),
            "event_date": ev.get("eventDate"),
            "start_unix": ev.get("unixTimestamp"),
            "olbg_slug": ev.get("slug"),
            "markets": markets,
        })
    (ROOT / "data" / "markets.json").write_text(json.dumps(records, indent=1) + "\n")
    n_mk = sum(len(r["markets"]) for r in records)
    n_out = sum(len(m["outcomes"]) for r in records for m in r["markets"])
    print(f"events={len(records)} markets={n_mk} outcomes={n_out} problems={len(problems)}")
    for p in problems[:15]:
        print("  problem:", p)


if __name__ == "__main__":
    main()
