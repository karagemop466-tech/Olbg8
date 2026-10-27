#!/usr/bin/env python3
"""Reproducible, deliberately uncalibrated baseball reference calculation."""

def pythagorean(runs_for: int, runs_against: int) -> float:
    if runs_for <= 0 or runs_against <= 0:
        raise ValueError('run totals must be positive')
    return runs_for**2 / (runs_for**2 + runs_against**2)


def log5(a: float, b: float) -> float:
    if not (0 < a < 1 and 0 < b < 1):
        raise ValueError('team strengths must lie strictly between 0 and 1')
    return a * (1 - b) / (a * (1 - b) + (1 - a) * b)


def american(p: float) -> int:
    if not 0 < p < 1:
        raise ValueError('probability must lie strictly between 0 and 1')
    return round(-100 * p / (1-p)) if p >= .5 else round(100 * (1-p) / p)


if __name__ == '__main__':
    mil, tb = pythagorean(832, 618), pythagorean(736, 650)
    p = log5(mil, tb)
    print(f'MIL {p:.6f} / {american(p):+d}; TB {1-p:.6f} / {american(1-p):+d}')


def nhl_reference(home: dict, away: dict) -> dict:
    """A toy independent-Poisson winner reference, not a calibrated prediction.

    Standing goals can include overtime/shootout effects; splitting equal scores
    evenly is an explicit assumption, not a claim about actual OT strength.
    """
    import math
    for t in (home, away):
        if (not all(isinstance(t.get(k), int) for k in ('gamesPlayed','goalFor','goalAgainst'))
                or t['gamesPlayed'] < 5 or min(t['goalFor'], t['goalAgainst']) <= 0):
            raise ValueError('incomplete or insufficient official standings')
    hg = (home['goalFor']/home['gamesPlayed'] + away['goalAgainst']/away['gamesPlayed']) / 2
    ag = (away['goalFor']/away['gamesPlayed'] + home['goalAgainst']/home['gamesPlayed']) / 2
    if not (0 < hg < 10 and 0 < ag < 10):
        raise ValueError('unsupported scoring rate')
    def mass(rate):
        xs = [math.exp(-rate)]
        for n in range(1, 41): xs.append(xs[-1]*rate/n)
        if abs(1-sum(xs)) > 1e-8: raise ValueError('truncation error')
        return xs
    hm, am = mass(hg), mass(ag)
    p_home = sum(hm[h]*am[a] for h in range(len(hm)) for a in range(len(am)) if h>a)
    p_tie = sum(a*b for a,b in zip(hm,am))
    p_home += p_tie/2
    return {'homeProbability':p_home,'awayProbability':1-p_home,
            'homeAmerican':american(p_home),'awayAmerican':american(1-p_home),
            'expectedHomeGoals':hg,'expectedAwayGoals':ag,'tiedScoreMass':p_tie}
