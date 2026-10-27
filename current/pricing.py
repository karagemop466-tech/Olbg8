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
