# Independent source review (pinned snapshot)

This **additive** review does not own or rewrite the root desk. It examines the 53 rows in `data/picks.json` at commit [`43c3c96d52b0f80bfc8c7e7eba114406805d9d57`](https://github.com/karagemop466-tech/Olbg8/blob/43c3c96d52b0f80bfc8c7e7eba114406805d9d57/data/picks.json), from an OLBG capture timestamped **2026-10-27 05:26 UTC**. Source review was completed **2026-10-27 06:34:45 UTC**. Both are historical; neither the review page nor the compact snapshot refreshes automatically. The current root may have changed.

Open [`index.html`](index.html) for the source-linked **Flagged for review** findings and a filterable 53-row historical ledger. [`method.html`](method.html) explains the gate and its limits. A linked official fixture confirms only the specified event identity or assertion—not all prose, an injury-free roster, an available bet or a calibrated probability. Where an exact fixture was not checked, an official directory is labelled **reference only**.

## Findings and sources

- Ireland–Namibia: [Cricket Ireland](https://cricketireland.ie/news/series-leveller) says Namibia's second-ODI win levelled a five-match series 1–1, contrary to the archived claim that Ireland had already won or could sweep it.
- Lilli Tagger: [WTA's player biography](https://www.wtatennis.com/players/332150/lilli-tagger) gives 17 February 2008 as her birth date, so she was 18, not 22, on the snapshot date.
- Boston–Carolina: the [NHL official feed](https://api-web.nhle.com/v1/score/2026-10-27) assigns the quoted −192/−196 prices to Carolina, not Boston.
- India–New Zealand: the [Cricket Australia match centre](https://www.cricket.com.au/matches/CA:41097/new-zealand-men-india-men-new-zealand-v-india-t20is-2026-men) marked both teams to be announced at review; the archived XI assertion was not established by that page.
- A price-window mismatch, uncalibrated tip-share-derived probabilities, opposing same-market selections and a start-date discrepancy are detailed, with primary sources and pinned code/data links, on the review page.
- A separate inspection of [PR #37 at `19b53ff`](https://github.com/karagemop466-tech/Olbg8/blob/19b53ff54743e03f8eaf25a299ab1bd162a4cefe/data/desk-20261027.json), reviewed at 06:42 UTC, found that several advertised edges against a de-vigged benchmark are negative at the displayed odds, podium Yes outcomes are normalized as though mutually exclusive, and volleyball set scores are described as player props. These findings are pinned to that revision, not a claim about later fixes. They were communicated in [PR #37](https://github.com/karagemop466-tech/Olbg8/pull/37#issuecomment-6435555346).

Source pages, odds and lineups are time-sensitive. `findings.json` and `catalog.json` are the auditable data behind the report; `snapshot.json` is a compact copy of the exact fields needed from the pinned payload, with an SHA-256 of the source bytes. The review does **not** claim every row's factual claims were manually checked. The baseline's cross-session errors were communicated to the root owner in [PR #31 comments](https://github.com/karagemop466-tech/Olbg8/pull/31#issuecomment-6435324505).

## Optional future publication gate

`gate.py` is a conservative, dependency-free Python module. `assess(candidate, as_of)` returns reasons to withhold. `assess_all` adds exact normalized-duplicate detection. It expects explicitly recorded evidence; it does not fetch URLs or validate excerpts against them. `reviewed_schema_only` means the structured checks passed, **not** that a real match, source, offer, injury or probability has been verified.

The strict candidate structure includes:

- `event`: an ID, name and explicitly zoned future `start_utc`;
- `market`: exact name and selection, `status: offered`, time-stamped `offered_american`, referenced OLBG evidence, settlement, period and rules note;
- `sources`: per-claim records with ID, scope, source URL, review flag, event ID, observed UTC time and an excerpt; `claim_sources` maps `event`, `form`, `match_history`, `statistic`, and `availability` to those IDs. Each official role is checked against a sport-specific host allowlist, but being on an official host does not prove the excerpt;
- `material_availability_reviewed: true` only when the actual evidence has been examined for material absences;
- `pricing`: independent win/push probabilities, consistent fair American odds, method and source IDs, confidence with a basis, and a reviewed chronological out-of-sample calibration artifact (training end, holdout dates, sample size and Brier score);
- `analysis`: unique, explicit selection and at least 30 words, with the two prohibited terms excluded.

The default quote-age threshold is **four hours** and may be supplied to `assess` as a `timedelta`. It is an operational safety setting, not a guarantee that a four-hour-old quote exists. The gate rejects started events, naive times, future or stale quotes, unsupported/mismatched source references, invalid/out-of-window offered prices, unspecified settlement, missing push mass for push markets, and unrecorded calibration. It correctly computes fair decimal odds as `(1 - p_push) / p_win`. It never turns a tip percentage into a winning probability.

The adapter in `build_report.py` reads only fields present in the historical payload. Manually checked event crosswalks appear separately in the ledger at identity scope; the adapter does not invent per-source observation timestamps, offer timestamps, lineups, claim excerpts, push probabilities or a calibration history. Thus all 53 rows are **withheld by this optional gate**; this is a finding about the available evidence and schema, not a claim that all 53 underlying opinions are false.

## Reproduce

```sh
python3 -m unittest discover -s audit-1c2e36bf -p 'test_*.py' -v
python3 audit-1c2e36bf/build_report.py --check
node --check audit-1c2e36bf/filter.js
```

To regenerate the pinned `snapshot.json`, copy the historical `data/picks.json` from the specified commit and run:

```sh
python3 audit-1c2e36bf/extract.py --input path/to/pinned-picks.json
python3 audit-1c2e36bf/build_report.py
```

Extraction refuses mismatched SHA-256 input. Tests are offline; external HTTP status and the continuing accuracy of live sources are not implied. The gate is not wired into the parallel root site's CI or refresh workflow: integrating it is a separate coordination request, and it cannot replace current collection, human editorial review, settlement verification or calibration.
