"""Arithmetic utilities, NOT an event prediction engine. No default probabilities."""
import math
from datetime import datetime, timezone

def probability(value):
    if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0 < value < 1:
        raise ValueError('Probability must be finite and strictly between zero and one')
    return value

def decimal_from_american(a):
    if not isinstance(a,(int,float)) or not math.isfinite(a) or abs(a)<100:
        raise ValueError('Invalid American odds')
    return 1+a/100 if a>0 else 1+100/abs(a)

def fair_decimal(win, push=0):
    probability(win)
    if not math.isfinite(push) or not 0 <= push < 1-win:
        raise ValueError('Invalid push probability')
    return (1-push)/win

def expected_value(win, offered, push=0):
    fair_decimal(win,push)
    if not math.isfinite(offered) or offered<=1:raise ValueError('Invalid decimal odds')
    return win*(offered-1)-(1-win-push)

def eligible(record, now=None):
    """Fail closed. This guard does not itself establish source truth."""
    required=('start_utc','official_source','source','selection','prediction','current_form_sources','statistics_sources','availability_sources','calibration_report','price_observed_at','probability')
    if not all(record.get(k) for k in required):return False
    try:
        now=now or datetime.now(timezone.utc)
        start=datetime.fromisoformat(record['start_utc'].replace('Z','+00:00'))
        price_time=datetime.fromisoformat(record['price_observed_at'].replace('Z','+00:00'))
        p=probability(record['probability']);a=record['american_odds']
        if not (-250<=a<=-100 or 100<=a<=10000):return False
        return (start>now and 0<=(now-price_time).total_seconds()<=3600
                and len(record['prediction'].split())>=30
                and not {'model','verified'} & set(record['prediction'].lower().split())
                and expected_value(p,decimal_from_american(a),record.get('push_probability',0))>0)
    except (ValueError,KeyError,TypeError,OverflowError):return False
