#!/usr/bin/env python3
"""Conservative, optional publication gate for sourced sports predictions.

This validates a *recorded evidence workflow*, not the truth of a claim. A human
or a trusted source adapter must check each cited excerpt before setting
reviewed=True. Missing, stale or contradictory evidence results in WITHHOLD.
The module is independent of the existing site generators.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import math
import re
from urllib.parse import urlsplit

# These are source authorities, not a claim that every page on the host supports
# the corresponding assertion. Do not automatically elevate a domain link into
# an event, form, injury, price or calibration verification.
OFFICIAL_HOSTS = {
    "golf": ("pgatour.com", "lpga.com", "europeantour.com", "owgr.com"),
    "volleyball": ("cev.eu", "volleyballworld.com", "legavolleyfemminile.it", "volleyball-bundesliga.de", "tvf.org.tr"),
    "rugby_union": ("world.rugby", "lnr.fr", "unitedrugby.com", "premiershiprugby.com", "epcrugby.com"),
    "cricket": ("icc-cricket.com", "cricket.com.au", "cricketireland.ie", "nzc.nz", "bcci.tv", "ecb.co.uk"),
    "snooker": ("wst.tv", "wpbsa.com"),
    "darts": ("pdc.tv", "dartswdf.com"),
    "baseball": ("mlb.com", "npb.jp"),
    "gaelic_sports": ("gaa.ie", "ladiesgaelic.ie"),
    "greyhounds": ("gbgb.org.uk",),
    "tennis": ("atptour.com", "wtatennis.com", "itftennis.com"),
    "motor_racing": ("formula1.com", "fia.com", "motogp.com", "nascar.com", "indycar.com"),
    "handball": ("eurohandball.com", "ihf.info"),
    "ice_hockey": ("nhl.com", "nhle.com", "iihf.com", "shl.se"),
    "basketball": ("nba.com", "wnba.com", "euroleaguebasketball.net", "fiba.basketball"),
    "rugby_league": ("nrl.com", "rugby-league.com", "superleague.co.uk"),
}
NEEDED_CLAIMS = ("event", "form", "match_history", "statistic", "availability")
BANNED = re.compile(r"\b(?:model|verified)\b", re.IGNORECASE)


def parse_utc(value):
    """Parse an explicitly zoned instant; a naive timestamp is not UTC proof."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            return None
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def valid_url(url, hosts=None):
    """Only absolute HTTPS URLs, optionally on an allowed host/subdomain."""
    if not isinstance(url, str):
        return False
    try:
        u = urlsplit(url)
        if u.scheme.lower() != "https" or not u.hostname or u.username or u.password:
            return False
        if u.port not in (None, 443):
            return False
        host = u.hostname.lower().rstrip(".")
        return not hosts or any(host == h or host.endswith("." + h) for h in hosts)
    except ValueError:
        return False


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_american(value):
    return isinstance(value, int) and not isinstance(value, bool) and (value <= -100 or value >= 100)


def american_to_decimal(value):
    if not valid_american(value):
        raise ValueError("American odds must be an integer <= -100 or >= +100")
    return 1.0 + (value / 100.0 if value > 0 else 100.0 / abs(value))


def fair_decimal(win_probability, push_probability=0.0):
    """Fair decimal odds for win/loss, or win/push/loss (stake refunded on push)."""
    if not number(win_probability) or not number(push_probability):
        raise ValueError("probabilities must be finite numbers")
    if not 0 < win_probability < 1 or not 0 <= push_probability < 1:
        raise ValueError("invalid win or push probability")
    if win_probability + push_probability >= 1:
        raise ValueError("a positive loss probability is required")
    return (1.0 - push_probability) / win_probability


def expected_net(win_probability, push_probability, decimal):
    """Expected profit on one unit; returned stake on a push has zero profit."""
    fair_decimal(win_probability, push_probability)
    if not number(decimal) or decimal <= 1:
        raise ValueError("decimal odds must exceed 1")
    return win_probability * (decimal - 1.0) - (1.0 - win_probability - push_probability)


def decimal_to_american(decimal):
    if not number(decimal) or decimal <= 1:
        raise ValueError("decimal odds must exceed 1")
    raw = 100.0 * (decimal - 1.0) if decimal >= 2 else -100.0 / (decimal - 1.0)
    return int(round(raw))


def _reviewed_source(source, event_id, role, sport, as_of):
    if not isinstance(source, dict) or source.get("reviewed") is not True:
        return False
    if source.get("scope") != role or str(source.get("event_id", "")) != event_id:
        return False
    if not str(source.get("excerpt", "")).strip():
        return False
    fetched = parse_utc(source.get("observed_utc"))
    if fetched is None or fetched > as_of:
        return False
    hosts = ("olbg.com",) if role == "market" else OFFICIAL_HOSTS.get(sport, ())
    return bool(hosts) and valid_url(source.get("url"), hosts)


def assess(candidate, as_of, max_quote_age=timedelta(hours=4)):
    """Return an ordered list of reasons to withhold a candidate.

    `as_of` must be an aware datetime supplied by the caller. These checks
    neither fetch URLs nor inspect whether an excerpt faithfully represents a
    source. Passing is necessary, not sufficient, for editorial publication.
    """
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be an explicitly zoned datetime")
    if not isinstance(max_quote_age, timedelta) or max_quote_age <= timedelta(0):
        raise ValueError("max_quote_age must be positive")
    as_of = as_of.astimezone(timezone.utc)
    if not isinstance(candidate, dict):
        return ["candidate_not_object"]
    issues = []
    sport = str(candidate.get("sport", "")).lower().replace("-", "_")
    event = candidate.get("event") if isinstance(candidate.get("event"), dict) else {}
    market = candidate.get("market") if isinstance(candidate.get("market"), dict) else {}
    pricing = candidate.get("pricing") if isinstance(candidate.get("pricing"), dict) else {}
    sources = candidate.get("sources") if isinstance(candidate.get("sources"), list) else []
    eid = str(event.get("id", "")).strip()
    if not candidate.get("id"):
        issues.append("missing_id")
    if sport not in OFFICIAL_HOSTS:
        issues.append("unknown_sport")
    if not eid or not str(event.get("name", "")).strip():
        issues.append("missing_event_identity")
    starts = parse_utc(event.get("start_utc"))
    if starts is None:
        issues.append("missing_or_unzoned_start")
    elif starts <= as_of:
        issues.append("event_started_or_expired")

    refs = {}
    duplicate_ids = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid.strip():
            continue
        if sid in refs:
            duplicate_ids.add(sid)
        refs[sid] = source
    if duplicate_ids:
        issues.append("duplicate_source_id")
    def lookup(key):
        return refs.get(key) if isinstance(key, str) else None

    claim_refs = candidate.get("claim_sources") if isinstance(candidate.get("claim_sources"), dict) else {}
    for role in NEEDED_CLAIMS:
        source = lookup(claim_refs.get(role))
        if not eid or not _reviewed_source(source, eid, role, sport, as_of):
            issues.append("missing_" + role + "_evidence")
    if candidate.get("material_availability_reviewed") is not True:
        issues.append("availability_not_assessed")

    if not str(market.get("name", "")).strip() or not str(market.get("selection", "")).strip():
        issues.append("missing_market_or_selection")
    if market.get("status") != "offered":
        issues.append("offer_not_confirmed")
    market_src = lookup(market.get("source_id"))
    if not eid or not _reviewed_source(market_src, eid, "market", sport, as_of):
        issues.append("missing_olbg_market_evidence")
    elif any(market_src.get(key) != market.get(key) for key in ("name", "selection", "status", "offered_american", "observed_utc")):
        issues.append("market_capture_mismatch")
    quote_time = parse_utc(market.get("observed_utc"))
    if quote_time is None or quote_time > as_of:
        issues.append("invalid_quote_time")
    elif as_of - quote_time > max_quote_age:
        issues.append("stale_quote")
    if quote_time is not None and starts is not None and quote_time >= starts:
        issues.append("quote_not_pregame")
    odds = market.get("offered_american")
    if not valid_american(odds):
        issues.append("missing_or_invalid_offered_odds")
    elif not -250 <= odds <= 10000:
        issues.append("offered_odds_outside_window")

    if market.get("settlement") not in ("win_loss", "win_push_loss"):
        issues.append("unknown_settlement")
    if market.get("period") not in ("regulation", "including_extra_time", "full_event", "other_explicit"):
        issues.append("unknown_period")
    if not str(market.get("rules_note", "")).strip():
        issues.append("missing_settlement_rules")
    pwin, ppush = pricing.get("win_probability"), pricing.get("push_probability")
    try:
        decimal = fair_decimal(pwin, ppush)
        if market.get("settlement") == "win_loss" and ppush != 0:
            issues.append("push_in_win_loss_market")
        if not valid_american(pricing.get("fair_american")) or abs(decimal_to_american(decimal) - pricing["fair_american"]) > 1:
            issues.append("fair_price_mismatch")
    except ValueError:
        issues.append("invalid_probability_or_push")

    cal = pricing.get("calibration") if isinstance(pricing.get("calibration"), dict) else {}
    if pricing.get("independent_from_tip_shares") is not True:
        issues.append("independent_pricing_not_recorded")
    if not str(pricing.get("method", "")).strip():
        issues.append("missing_pricing_method")
    if not isinstance(pricing.get("input_source_ids"), list) or not pricing["input_source_ids"]:
        issues.append("missing_pricing_inputs")
    else:
        for sid in pricing["input_source_ids"]:
            source = lookup(sid)
            if not isinstance(source, dict) or source.get("scope") not in NEEDED_CLAIMS or not _reviewed_source(source, eid, source.get("scope"), sport, as_of):
                issues.append("unreviewed_pricing_input")
                break
    train = parse_utc(cal.get("train_end_utc"))
    first = parse_utc(cal.get("holdout_start_utc"))
    last = parse_utc(cal.get("holdout_end_utc"))
    count, brier = cal.get("sample_size"), cal.get("brier_score")
    if (cal.get("reviewed") is not True or not valid_url(cal.get("artifact_url"))
        or not isinstance(count, int) or isinstance(count, bool) or count < 1
        or not number(brier) or not 0 <= brier <= 1
        or not train or not first or not last or not train < first <= last <= as_of
        or (starts is not None and last >= starts)):
        issues.append("missing_out_of_sample_calibration")
    if pricing.get("confidence") not in ("low", "medium", "high"):
        issues.append("missing_confidence")
    if not str(pricing.get("confidence_basis", "")).strip():
        issues.append("missing_confidence_basis")

    text = candidate.get("analysis") if isinstance(candidate.get("analysis"), str) else ""
    if len(re.findall(r"\b[\w’'-]+\b", text)) < 30:
        issues.append("short_analysis")
    if BANNED.search(text):
        issues.append("banned_word_in_analysis")
    selection = market.get("selection")
    if not isinstance(selection, str) or not selection.strip() or selection.casefold() not in text.casefold():
        issues.append("selection_not_explicit_in_analysis")
    return list(dict.fromkeys(issues))


def assess_all(candidates, as_of, max_quote_age=timedelta(hours=4)):
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    texts = [re.sub(r"\s+", " ", str(c.get("analysis", "")).strip()).casefold() if isinstance(c, dict) else "" for c in candidates]
    counts = Counter(t for t in texts if t)
    results = []
    for candidate, text in zip(candidates, texts):
        reasons = assess(candidate, as_of, max_quote_age)
        if text and counts[text] > 1:
            reasons.append("duplicate_analysis")
        results.append({"id": candidate.get("id") if isinstance(candidate, dict) else None,
                        "status": "withhold" if reasons else "reviewed_schema_only",
                        "reasons": reasons})
    return results
