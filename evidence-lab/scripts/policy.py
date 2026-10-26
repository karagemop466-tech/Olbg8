"""Fail-closed publication policy. Source links alone are not verification."""
import re
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse

def instant(s):
    value=datetime.fromisoformat(s.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('timezone required')
    return value

def publication_errors(pick,now=None):
    now=now or datetime.now(timezone.utc)
    errors=[]
    from scripts.pricing import eligible_odds, expected_return
    for name in ['selection','market','event_id','sport','olbg_url','official_url','start_utc','odds_observed_at','market_american','probability','confidence','prediction','price_artifact','calibration_artifact','evidence']:
        if pick.get(name) is None or pick.get(name)=='': errors.append('Missing '+name)
    try:
        if instant(pick['start_utc'])<=now: errors.append('Event already started')
        age=now-instant(pick['odds_observed_at'])
        if age<timedelta(0) or age>timedelta(minutes=30): errors.append('Stale or future odds timestamp')
        if not eligible_odds(pick['market_american']): errors.append('Outside -250 to +10000 odds range')
        if expected_return(pick['probability'],pick.get('push_probability',0),pick['market_american'])<=0: errors.append('No positive expected return')
    except (KeyError,ValueError,TypeError): errors.append('Invalid time, odds or probability')
    text=pick.get('prediction') or ''
    if len(text.split())<30: errors.append('Prediction shorter than 30 words')
    if re.search(r'\b(model|verified)\b',text,re.I): errors.append('Prohibited editorial word')
    if pick.get('confidence') not in ['low','medium','high']: errors.append('Invalid confidence label')
    # Every claim needs content evidence, not a homepage or a Boolean flag.
    evidence=pick.get('evidence') or []
    for field in ['fixture','form','recent_match','statistic','availability','market_rules']:
        claims=[c for c in evidence if c.get('field')==field]
        if not claims or any(not all(c.get(k) for k in ['url','excerpt','retrieved_at','official_host']) or urlparse(c.get('url','')).hostname!=c.get('official_host') for c in claims):
            errors.append('Missing official content evidence: '+field)
    # Prototypes have not been calibrated. Never promote by changing a Boolean.
    errors.append('Production pricing and calibration adapters not implemented')
    return errors
