"""Single-trial outcome forecast: two methods, averaged.

Method A (reference class + adjustments):
    odds_final = odds_prior * f1 * f2 * ... ; p = odds / (1 + odds)

Method B (effect-size model):
    For each scenario of the true hazard ratio, the expected z statistic at
    d events (1:1 randomisation) is  -ln(HR) * sqrt(d) / 2.
    P(cross) = P(Z > z_bar - expected_z). Scenarios are weighted, and when the
    statistical bar is unknown, several bars are weighted too.

Usage:
    python forecast.py cases/bria_abc.json
    python forecast.py cases/viktoria1_wt.json
"""

import json
import math
import sys


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def method_a(prior, factors):
    odds = prior / (1 - prior)
    rows = [("prior", None, odds, prior)]
    for f in factors:
        odds *= f["factor"]
        rows.append((f["name"], f["factor"], odds, odds / (1 + odds)))
    return odds / (1 + odds), rows


def method_b(events, scenarios, bars):
    scale = math.sqrt(events) / 2
    total = 0.0
    rows = []
    for bar in bars:
        p_bar = 0.0
        for s in scenarios:
            expected_z = -math.log(s["hr"]) * scale
            p_cross = 1 - norm_cdf(bar["z"] - expected_z)
            p_bar += s["weight"] * p_cross
            rows.append((bar["z"], s["name"], s["hr"], expected_z, p_cross))
        total += bar["weight"] * p_bar
    return total, rows


def brier(p, outcome):
    return (p - outcome) ** 2


def main(path):
    with open(path) as fh:
        case = json.load(fh)

    print(f"# {case['trial']}  (as of {case['as_of']})\n")

    p_a, rows_a = method_a(case["method_a"]["prior"], case["method_a"]["factors"])
    print("Method A: reference class + adjustments")
    for name, factor, odds, p in rows_a:
        f = "" if factor is None else f"x{factor:<4}"
        print(f"  {name:<32} {f:<6} odds {odds:5.2f}  p {p:6.1%}")
    print(f"  => {p_a:.1%}\n")

    mb = case["method_b"]
    p_b, rows_b = method_b(mb["events"], mb["scenarios"], mb["bars"])
    print(f"Method B: effect-size model ({mb['events']} events)")
    for z_bar, name, hr, ez, pc in rows_b:
        print(f"  bar z={z_bar:<5} {name:<28} HR {hr:<5} E[z] {ez:5.2f}  P(cross) {pc:6.1%}")
    print(f"  => {p_b:.1%}\n")

    p = (p_a + p_b) / 2
    print(f"Forecast (average of A and B): {p:.1%}")

    outcome = case.get("outcome")
    if outcome is not None:
        print(f"\nOutcome: {'YES' if outcome else 'NO'}")
        print(f"  Brier, this forecast:        {brier(p, outcome):.3f}")
        for name, q in case.get("benchmarks", {}).items():
            print(f"  Brier, {name + ':':<22}{brier(q, outcome):.3f}")


if __name__ == "__main__":
    main(sys.argv[1])
