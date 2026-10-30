"""LLM judge for the defense rubric, and its calibration against hand grades.

The plan asks for a rubric graded by an LLM judge, with 30 hand-graded option
sets used to calibrate it. ``rubric.py`` supplies matching check definitions; this
module grades each population separately using a model, and
``calibrate`` reports how far it drifts from a person's grades.

Calibration is the point. An uncalibrated judge is a number with no error bar,
and the plan says explicitly that automatic scores are checked by people before
they are trusted. So a judge run reports:

* exact agreement per rule and overall,
* Cohen's kappa on the binary pass/fail per rule,
* the rules where the judge and the person disagree, which require investigation of both the judge and the annotation rules.

Usage::

    python3 -m benchmark.judge --option-set runs/elacestrant.json     # grade one
    python3 -m benchmark.judge --calibrate hand_grades.json           # compare

The hand-grade file is a list of ``{"file": path, "grades": {rule: true|false}}``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from . import rubric
from .schema import normalise_option_set

JUDGE_SYSTEM = """You grade clinical-trial population options against a fixed rubric.
Grade ONLY the rules supplied. Judge the supplied text; do not use outside knowledge.
Return ONLY JSON: {"grades": {"<rule id>": {"pass": true|false, "why": "one sentence"}}}
Pass means the rule's requirement is met by the text. Quote nothing; be terse."""

RULE_DESCRIPTIONS = {
    "distinct_options": "3-4 options are proposed and no two options share nearly all of their defining criteria.",
    "named_axes": "every option names the axis it varies on, and at least two distinct axes appear.",
    "pros_present": "every option lists at least two specific benefits.",
    "cons_present": "every option lists at least two specific downsides.",
    "cons_substantive": "the cons name real risk classes (safety, accrual, generalisation, regulatory, evidence uncertainty), not restatements.",
    "no_overclaiming": "no claim says a subgroup benefit is proven or a predictive interaction is established without hedging.",
    "uses_guidance": "each option cites eligibility guidance (FDA/ASCO-Friends/NCI) where the criteria involve performance status, CNS disease or laboratory thresholds.",
    "cns_not_blanket": "no option excludes all CNS/brain-metastasis patients without a reasoned alternative such as stable treated disease.",
    "ps_justified": "any performance-status limit is accompanied by a reason or a route for selected ECOG 2 patients.",
    "safety_exclusion": "each option has a safety exclusion specific to the regimen and cites the label or safety source.",
    "scope_respected": "every option stays within HR+/HER2- metastatic breast cancer.",
    "criteria_complete": "each option has at least three substantive criteria beyond restating the parent population.",
    "estimates_ranged": "eligible-pool estimates are sourced valid ranges or explicitly unavailable; endpoint forecasts are separate and not represented as eligibility percentages.",
    "recommendation_defended": "one existing option has at least one cited defense; assess comparisons separately from statement count.",
    "citation_coverage": "every claim (criterion, pro, con, estimate, defence) carries at least one source id.",
    "criteria_reasoned": "every non-scope criterion has an explicit rationale explaining its purpose.",
    "uncertainty_explicit": "the population defense names an evidence limitation, unconfirmed hypothesis, or unresolved protocol issue.",
    "population_defended": "the population has its own substantial cited defense, whether or not it was recommended.",
}


def rule_sheet() -> list[dict]:
    # Some public rule IDs differ from their Python function names.
    names = {r["rule"] for r in rubric._aggregate([fn(dict(options=[], recommendation={})) for fn in rubric.COMMON_RULES])["results"]}
    return [dict(id=name, requirement=text) for name, text in RULE_DESCRIPTIONS.items() if name in names]


def _prompt(option_set: dict) -> str:
    return json.dumps(dict(rules=rule_sheet(), option_set=option_set), ensure_ascii=False)


def judge(option_set: dict, model: str | None = None) -> dict:
    """Judge one population at a time through the configured demo provider.

    This grades the defense text only. It does not independently read sources
    or certify entailment, clinical safety, or treatment-effect differences.
    """
    from .baselines import _ask
    from milestone1.llm import settings
    if model and model != settings()["model"]:
        raise ValueError("Configure the judge provider/model explicitly through the demo settings before calling")
    option_set = normalise_option_set(option_set)
    populations = []
    for option in option_set["options"]:
        single = dict(trial=option_set["trial"], options=[option], recommendation={})
        payload = _ask(JUDGE_SYSTEM, _prompt(single), max_tokens=4000)
        grades = payload["grades"]
        weights = {r["rule"]:r["weight"] for r in rubric.score_defense_rubric(single)["results"]}
        rows = []
        for name in weights:
            grade = grades.get(name, {})
            if type(grade.get("pass")) is not bool:
                raise ValueError(f"Judge omitted a Boolean grade for {name}")
            rows.append(dict(rule=name, pass_=grade["pass"], why=grade.get("why", ""), weight=weights[name]))
        populations.append(dict(option_id=option["option_id"], **rubric._aggregate(rows), provenance=payload.get("provenance")))
    return dict(benchmark="population_defense_judge_v2", populations=populations,
                score=round(mean(p["score"] for p in populations), 4) if populations else None,
                results=populations[0]["results"] if len(populations) == 1 else [],
                calibrated=False, interpretation="LLM text judgment; requires comparison with human grades before use.")


def cohens_kappa(a: list[bool], b: list[bool]) -> float | None:
    """Agreement corrected for chance, on two binary graders."""
    if not a or len(a) != len(b):
        return None
    n = len(a)
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected == 1.0:
        return None  # No label variation: chance-corrected agreement is undefined.
    return round((observed - expected) / (1 - expected), 4)


def calibrate(hand_grades: list[dict], judge_fn=judge) -> dict:
    """Compare judge grades with hand grades, per rule and overall.

    ``hand_grades`` entries: ``{"file": path, "grades": {rule: bool}}``.
    """
    per_rule: dict[str, dict] = {r["id"]: dict(judge=[], hand=[]) for r in rule_sheet()}
    disagreements = []
    for case in hand_grades:
        if not case.get("grades") or any(type(v) is not bool for v in case["grades"].values()):
            raise ValueError("Fill blank hand grades with Boolean values before calling a paid judge")
        if set(case["grades"]) - set(per_rule):
            raise ValueError("Hand grades contain unknown rule IDs")
    for case in hand_grades:
        option_set = json.loads(Path(case["file"]).read_text())
        option_set = normalise_option_set(option_set)
        if len(option_set["options"]) > 1:
            selected = [o for o in option_set["options"] if o["option_id"] == case.get("option_id")]
            if len(selected) != 1:
                raise ValueError("Hand grades for a multi-population file must specify option_id")
            option_set["options"] = selected
        judged = judge_fn(option_set)
        by_rule = {r["rule"]: r["pass_"] for r in judged["results"]}
        for name, human in case["grades"].items():
            if name not in by_rule:
                raise ValueError(f"Missing or unknown calibrated rule: {name}")
            if type(human) is not bool:
                raise ValueError("Human grades must be Boolean, not strings")
            per_rule[name]["judge"].append(by_rule[name])
            per_rule[name]["hand"].append(bool(human))
            if by_rule[name] != bool(human):
                disagreements.append(dict(file=case["file"], rule=name,
                                          judge=by_rule[name], hand=bool(human)))
    report, all_judge, all_hand = {}, [], []
    for name, rows in per_rule.items():
        if not rows["judge"]:
            continue
        agree = sum(1 for j, h in zip(rows["judge"], rows["hand"]) if j == h) / len(rows["judge"])
        report[name] = dict(agreement=round(agree, 4),
                            kappa=cohens_kappa(rows["judge"], rows["hand"]),
                            cases=len(rows["judge"]))
        all_judge += rows["judge"]
        all_hand += rows["hand"]
    overall = dict(agreement=round(mean(1.0 if j == h else 0.0 for j, h in zip(all_judge, all_hand)), 4)
                   if all_hand else None,
                   kappa=cohens_kappa(all_judge, all_hand),
                   cases=len(hand_grades))
    return dict(benchmark="judge_calibration", overall=overall, by_rule=report,
                # These are the rules to rewrite before the judge is trusted.
                weakest_rules=sorted(report, key=lambda k: report[k]["agreement"])[:5],
                disagreements=disagreements,
                note="Low agreement can reflect judge errors, ambiguous rules, annotation differences, or label prevalence. Investigate disagreements; do not assume the rubric alone is at fault.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--option-set")
    parser.add_argument("--calibrate")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    if args.calibrate:
        result = calibrate(json.loads(Path(args.calibrate).read_text()))
    elif args.option_set:
        result = judge(json.loads(Path(args.option_set).read_text()))
    else:
        parser.error("give --option-set or --calibrate")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
