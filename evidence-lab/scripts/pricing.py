"""Research kernels, NOT fitted sport forecasts. No market odds as fitting inputs.
Kernels return scenario distributions; sport-specific calibration/inputs remain missing.
"""
import math
import random
from collections import defaultdict

def number(x):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
        raise ValueError('finite number required')
    return x

def probability(p):
    number(p)
    if not 0 < p < 1: raise ValueError('probability must be strictly between zero and one')
    return p

def american_to_decimal(odds):
    number(odds)
    if abs(odds)<100: raise ValueError('American odds require magnitude >= 100')
    return 1+odds/100 if odds>0 else 1+100/abs(odds)

def fair_odds(p_win,p_push=0):
    probability(p_win); number(p_push)
    if p_push<0 or p_win+p_push>=1: raise ValueError('need positive loss probability')
    dec=(1-p_push)/p_win
    am=100*(dec-1) if dec>=2 else -100/(dec-1)
    return {'decimal':dec,'american':am}

def no_vig(odds):
    """Market benchmark only; never an independently originated probability."""
    if len(odds)<2: raise ValueError('complete mutually exclusive market required')
    implied=[1/american_to_decimal(o) for o in odds]
    return [p/sum(implied) for p in implied]

def eligible_odds(odds):
    american_to_decimal(odds)
    return -250<=odds<=10000

def expected_return(p_win,p_push,odds):
    probability(p_win); number(p_push)
    if p_push<0 or p_win+p_push>1: raise ValueError('invalid settlement probabilities')
    return p_win*(american_to_decimal(odds)-1)-(1-p_win-p_push)

def first_to(p,target):
    """IID unit-wins prototype. Snooker frames / volleyball sets / darts legs.
    Not valid for alternating throw, varying set strengths or set-based darts as-is.
    """
    probability(p)
    if isinstance(target,bool) or not isinstance(target,int) or not 1<=target<=100:
        raise ValueError('target must be an integer from 1 to 100')
    out={}
    for loss in range(target):
        combinations=math.comb(target+loss-1,loss)
        out[(target,loss)]=combinations*p**target*(1-p)**loss
        out[(loss,target)]=combinations*(1-p)**target*p**loss
    return out

def poisson_scores(home_rate,away_rate,max_score=100):
    """Independent regulation scoring prototype; NO implicit overtime or tie removal.
    Not an appropriate default for high-scoring or dependent component sports.
    """
    for rate in [home_rate,away_rate]:
        number(rate)
        if not 0<rate<=30: raise ValueError('rate must be in (0,30]')
    if not isinstance(max_score,int) or not 1<=max_score<=200: raise ValueError('invalid score bound')
    def pmf(rate):
        arr=[math.exp(-rate)]
        for k in range(1,max_score+1): arr.append(arr[-1]*rate/k)
        return arr
    h,a=pmf(home_rate),pmf(away_rate)
    retained=sum(h)*sum(a)
    if 1-retained>1e-8: raise ValueError('truncated tail too large; increase bound')
    return {(i,j):x*y for i,x in enumerate(h) for j,y in enumerate(a)}

def settle_scores(scores,market,line=0):
    """Regulation 1X2, home handicap or OVER total. Pushes stay separate.
    Scores must represent the exact settlement period and include draw outcomes.
    """
    if market not in ['regulation_1x2','handicap','total']: raise ValueError('unsupported market')
    number(line)
    if not scores or abs(sum(scores.values())-1)>1e-8: raise ValueError('probability mass must sum to 1')
    out=({'home':0.0,'draw':0.0,'away':0.0} if market=='regulation_1x2' else {'win':0.0,'push':0.0,'loss':0.0})
    for (h,a),mass in scores.items():
        number(h);number(a);number(mass)
        if min(h,a,mass)<0: raise ValueError('negative score/mass')
        margin=h+a-line if market=='total' else h-a+(line if market=='handicap' else 0)
        if market=='regulation_1x2':out['home' if margin>0 else 'away' if margin<0 else 'draw']+=mass
        else:out['win' if margin>0 else 'loss' if margin<0 else 'push']+=mass
    return out

def race_order(means,stdevs,simulations=10000,seed=0):
    """Lower-is-better independent Gaussian timing/scoring research prototype.
    Can explore full fields in golf / motor racing / greyhounds. Does not account
    for correlated weather, non-finishes, cuts, interference or dead heats.
    """
    if len(means)<2 or set(means)!=set(stdevs): raise ValueError('complete field required')
    for v in means.values(): number(v)
    for v in stdevs.values():
        number(v)
        if v<=0: raise ValueError('positive variance required')
    if not isinstance(simulations,int) or not 100<=simulations<=1000000: raise ValueError('simulation count')
    rng=random.Random(seed)
    ranks={key:[0]*len(means) for key in means}
    for _ in range(simulations):
        order=sorted(means,key=lambda key:rng.gauss(means[key],stdevs[key]))
        for rank,key in enumerate(order): ranks[key][rank]+=1
    return {key:[n/simulations for n in counts] for key,counts in ranks.items()}
