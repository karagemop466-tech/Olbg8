#!/usr/bin/env python3
"""Turn the harvested ESPN scoreboards into per-sport facts.

ESPN is a publisher, not a governing body, so everything produced here is
labelled `publisher: ESPN` and the site keeps it visually separate from
league-published data. Nothing is inferred: a value that ESPN does not carry
stays absent and the writer's clause for it returns an empty string.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

STOPWORDS = {
    "fc", "cf", "sc", "ac", "bc", "hc", "if", "bk", "sk", "ff", "ffr", "rfc", "as", "us",
    "the", "club", "de", "of", "and", "team", "volley", "volleyball", "handball", "basket",
    "basketball", "hockey", "rugby", "union", "league", "women", "womens", "men", "mens",
    "w", "m", "ii", "iii", "u21", "u20", "u19", "u18", "u23",
}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def tokens(name: str) -> list[str]:
    return [t for t in fold(name).split() if t and t not in STOPWORDS]


def similarity(a: str, b: str) -> float:
    """Token containment score in [0, 1]: 1.0 means one name covers the other."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    sa, sb = set(ta), set(tb)
    inter = len(sa & sb)
    if not inter:
        # allow a shared distinctive token of 4+ characters (e.g. "Olympiacos")
        return 0.0
    contain = inter / min(len(sa), len(sb))
    jac = inter / len(sa | sb)
    last = 1.0 if ta[-1] == tb[-1] else 0.0
    return max(contain, jac, 0.7 * last + 0.3 * contain)


def load(name: str):
    p = OUT / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iso(date: str | None) -> str:
    if not date:
        return ""
    return date.replace("Z", "+00:00")


def _score(sides: list[dict]) -> tuple:
    home = next((s for s in sides if s.get("home_away") == "home"), None)
    away = next((s for s in sides if s.get("home_away") == "away"), None)
    if not home or not away:
        home, away = (sides + [None, None])[:2]
    return home, away


def record_of(side: dict) -> dict:
    """Pull a W-L record out of ESPN's record summaries."""
    out = {}
    for rec in side.get("records") or []:
        s = (rec.get("summary") or "").strip()
        m = re.match(r"^(\d+)-(\d+)(?:-(\d+))?$", s)
        if not m:
            continue
        w, l, otl = int(m.group(1)), int(m.group(2)), m.group(3)
        kind = (rec.get("type") or "").lower()
        row = {"wins": w, "losses": l}
        if otl:
            row["ot_losses"] = int(otl)
        if "total" in kind or not out:
            out.update(row)
            if otl:
                out["ot_losses"] = int(otl)
        if "home" in kind:
            out["home"] = {"w": w, "l": l}
        if "road" in kind or "away" in kind:
            out["away"] = {"w": w, "l": l}
    if out.get("wins") is not None and out.get("losses") is not None:
        gp = out["wins"] + out["losses"] + out.get("ot_losses", 0)
        if gp:
            out["pct"] = out["wins"] / gp
    return out


def build() -> dict:
    raw = load("espn_raw.json") or {}
    inj = load("espn_injuries.json") or {}
    facts: dict[str, dict] = {}

    def bucket(sport: str) -> dict:
        return facts.setdefault(sport, {"fixtures": [], "results": [], "table": {},
                                        "form": {}, "injuries": {}, "publisher": "ESPN",
                                        "sources": []})

    for key, league in (raw.get("leagues") or {}).items():
        sport = league.get("sport")
        if not sport:
            continue
        b = bucket(sport)
        b["sources"].append({"label": f"ESPN {league.get('label')} scoreboard",
                             "url": "https://www.espn.com/",
                             "league": league.get("label")})
        for ev in league.get("events") or []:
            home, away = _score(ev.get("sides") or [])
            if not home or not away:
                continue
            url = ev.get("link") or ""
            row = {
                "sport": sport,
                "competition": league.get("label"),
                "game_id": ev.get("id"),
                "start_utc": _iso(ev.get("date")),
                "status": ev.get("detail") or ev.get("state"),
                "completed": bool(ev.get("completed")),
                "home": home.get("name"), "away": away.get("name"),
                "home_score": home.get("score"), "away_score": away.get("score"),
                "venue": ev.get("venue"),
                "note": ev.get("note"),
                "source": f"ESPN ({league.get('label')})",
                "source_url": url,
                "publisher": "ESPN",
            }
            if ev.get("completed"):
                b["results"].append(row)
            else:
                b["fixtures"].append(row)
            for side in (home, away):
                name = side.get("name")
                if not name:
                    continue
                rec = record_of(side)
                if rec:
                    b["table"].setdefault(name, {"name": name, **rec})
                else:
                    b["table"].setdefault(name, {"name": name})

    # form: last five completed results for every team seen in a league
    for sport, b in facts.items():
        by_team: dict[str, list] = {}
        for r in sorted(b["results"], key=lambda r: r.get("start_utc") or ""):
            for side, opp, opp_score in (("home", r["away"], r.get("away_score")),
                                         ("away", r["home"], r.get("home_score"))):
                team = r[side]
                mine = r.get(f"{side}_score")
                if not team or mine in (None, ""):
                    continue
                try:
                    won = float(mine) > float(opp_score)
                    tied = float(mine) == float(opp_score)
                except Exception:
                    continue
                by_team.setdefault(team, []).append({
                    "date": (r.get("start_utc") or "")[:10],
                    "opponent": opp,
                    "result": "D" if tied else ("W" if won else "L"),
                    "score": f"{mine}-{opp_score}",
                    "venue": "home" if side == "home" else "away",
                    "source_url": r.get("source_url"),
                })
        b["form"] = {t: rows[-5:] for t, rows in by_team.items() if rows}

    for key, league in (inj.get("leagues") or {}).items():
        sport = league.get("sport")
        if not sport:
            continue
        b = bucket(sport)
        for r in league.get("rows") or []:
            team = r.get("team")
            if not team:
                continue
            b["injuries"].setdefault(team, []).append({
                "player": r.get("player"), "status": r.get("status"),
                "detail": r.get("detail"), "date": r.get("date"),
                "source": "ESPN injuries", "source_url": "https://www.espn.com/",
            })
    return facts


def lookup(table: dict, name: str, threshold: float = 0.75):
    """Best fuzzy key for `name` in `table`, or None."""
    best, best_score = None, 0.0
    for key in table:
        s = similarity(name, key)
        if s > best_score:
            best, best_score = key, s
    return best if best_score >= threshold else None


if __name__ == "__main__":
    f = build()
    for sport, b in f.items():
        print(f"{sport:<14} fixtures={len(b['fixtures']):>3} results={len(b['results']):>3} "
              f"table={len(b['table']):>3} form={len(b['form']):>3} injuries={len(b['injuries']):>3}")
