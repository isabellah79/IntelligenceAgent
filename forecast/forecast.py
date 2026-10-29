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
from datetime import date


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


def _number(value, name, lower, upper):
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{name} must be a finite number between {lower} and {upper}")


def validate_case(case):
    """Validate analyst assumptions before calling the original two methods."""
    if not isinstance(case, dict):
        raise ValueError("forecast_case must be an object")
    # Reject non-JSON values/nonfinite metadata as well as invalid model inputs.
    try:
        json.dumps(case, allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("Forecast assumptions must contain valid, finite JSON values") from None
    if not isinstance(case.get("trial"), str) or not 1 <= len(case["trial"].strip()) <= 1000:
        raise ValueError("A trial/comparator/endpoint description is required")
    try:
        date.fromisoformat(case["as_of"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("as_of must be a calendar date: YYYY-MM-DD") from None
    a, b = case.get("method_a"), case.get("method_b")
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise ValueError("Both method_a and method_b are required")
    _number(a.get("prior"), "prior", 0.000001, 0.999999)
    factors = a.get("factors")
    if not isinstance(factors, list) or len(factors) > 20:
        raise ValueError("factors must be a list of at most 20 adjustments")
    for f in factors:
        if not isinstance(f, dict) or not isinstance(f.get("name"), str) or not 1 <= len(f["name"]) <= 200:
            raise ValueError("Each adjustment needs a name (1–200 characters)")
        _number(f.get("factor"), "odds adjustment", 0.01, 100)
    events = b.get("events")
    if type(events) is not int or not 1 <= events <= 1000000:
        raise ValueError("events must be an integer between 1 and 1000000")
    for key in ("scenarios", "bars"):
        rows = b.get(key)
        if not isinstance(rows, list) or not 1 <= len(rows) <= 20:
            raise ValueError(f"{key} needs 1–20 rows")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Each {key} entry must be an object")
            _number(row.get("weight"), f"{key} weight", 0, 1)
            if key == "scenarios":
                if not isinstance(row.get("name"), str) or not 1 <= len(row["name"]) <= 200:
                    raise ValueError("Each effect scenario needs a name")
                _number(row.get("hr"), "scenario HR", 0.05, 5)
            else:
                _number(row.get("z"), "statistical threshold z", 0, 10)
        if not math.isclose(sum(row["weight"] for row in rows), 1, rel_tol=0, abs_tol=1e-6):
            raise ValueError(f"{key} weights must sum to 1")
    return case


def forecast_case(case):
    """Reusable API for the existing CLI; no changes to its model equations.

    Assumptions are judgment calls, not learned or calibrated parameters. The
    target is a trial statistical endpoint, never individual treatment response.
    """
    validate_case(case)
    p_a, rows_a = method_a(case["method_a"]["prior"], case["method_a"]["factors"])
    b = case["method_b"]
    p_b, rows_b = method_b(b["events"], b["scenarios"], b["bars"])
    return {
        "method_a": p_a, "method_b": p_b, "combined": (p_a + p_b) / 2,
        "method_disagreement": abs(p_a - p_b),
        "method_a_steps": [dict(name=n, factor=f, odds=o, probability=p) for n, f, o, p in rows_a],
        "method_b_scenarios": [dict(z_threshold=z, name=n, hr=hr, expected_z=ez, probability=p)
                               for z, n, hr, ez, p in rows_b],
        "target": "Trial meets the specified statistical endpoint versus its comparator",
        "calibration": "Experimental; hand-set assumptions; not a patient benefit probability",
    }


def main(path):
    with open(path) as fh:
        case = json.load(fh)
    validate_case(case)

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
