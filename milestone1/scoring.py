"""Explicit prototype policy for prioritizing a clinician's discussion.

The numeric rubric/weights below are product assumptions, not clinical facts or
validated recommendations. References support underlying criteria, NOT points.
No trial-success probability or cross-trial effect size enters the score.
"""
from copy import deepcopy
import math

VERSION = "discussion-priority-0.1"
DIMENSIONS = {
    "match": "Biomarker / treatment-context match",
    "evidence": "Evidence applicability after CDK4/6",
    "readiness": "Known review flags",
    "preference": "Delivery preference fit",
}
WEIGHT_PRESETS = {
    "fewer_visits": dict(match=30, evidence=25, readiness=20, preference=25),
    "disease_control": dict(match=30, evidence=40, readiness=20, preference=10),
    "balanced": dict(match=30, evidence=30, readiness=25, preference=15),
}
# 0–5 evidence scores reflect study-to-case applicability, not effect size.
EVIDENCE = {
    "elacestrant": (5, "Prior CDK4/6 treatment required in EMERALD.", ["EMERALD"]),
    "imlunestrant": (3, "EMBER-3 mixes CDK4/6-pretreated and naive patients.", ["IMLU-FDA"]),
    "imlunestrant_abemaciclib": (3, "Mixed prior CDK4/6 exposure and exploratory ESR1-mutated combination subgroup.", ["EMBER3"]),
    "vepdegestrant": (5, "Prior CDK4/6 treatment required in VERITAC-2.", ["VERITAC2"]),
    "capivasertib": (4, "CAPItello-291 included substantial prior CDK4/6 exposure, but not all participants were pretreated.", ["CAPITELLO"]),
    "alpelisib": (2, "SOLAR-1 is not a dedicated post-CDK4/6 randomized comparison.", ["ALPEL-LABEL"]),
    "gedatolisib": (4, "VIKTORIA-1 supports the mutation-not-detected pathway; review the precise trial cohort.", ["GEDA-LABEL"]),
    "tdxd": (4, "DB06 supports an endocrine-pretreated population without prior metastatic chemotherapy.", ["DB06"]),
    "datodxd": (4, "Randomized evidence after endocrine treatment and advanced-disease chemotherapy.", ["DATO-FDA"]),
    "sacituzumab": (3, "TROPiCS-02 involved heavily pretreated patients; counts alone do not reproduce that population.", ["TROPICS2"]),
    "chemotherapy": (2, "A broad strategy rather than one specified regimen or one comparable trial population.", ["PDQ"]),
    "olaparib": (2, "Germline BRCA-selected evidence is not a dedicated post-CDK4/6 comparison.", ["OLYMPIAD"]),
    "postmonarch": (5, "postMONARCH specifically studied treatment after CDK4/6 progression.", ["POSTMONARCH"]),
}


def validate_weights(weights):
    if not isinstance(weights, dict) or set(weights) != set(DIMENSIONS):
        raise ValueError("Weights must specify match, evidence, readiness and preference")
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 100 for v in weights.values()):
        raise ValueError("Weights must be finite numbers from 0 to 100")
    if not math.isclose(sum(weights.values()), 100, rel_tol=0, abs_tol=0.001):
        raise ValueError("Priority weights must sum to 100")
    return deepcopy(weights)


def paused_reasons(result):
    c = result["case"]
    reasons = []
    if not result["options"]:
        reasons.append("Disease is outside the demo scope.")
    if c["visceral_crisis"]:
        reasons.append("Reported visceral crisis requires urgent clinical assessment.")
    if c["her2"] == "unknown":
        reasons.append("Confirm HER2-negative disease before prioritizing treatments.")
    if c["organ_function"] != "adequate" or c["ecog"] is None or c["ecog"] > 1:
        reasons.append("Organ function or performance status needs clinical review.")
    if c["esr1"] == "unknown" or c["pik3ca"] == "unknown" or c["gbrca"] == "unknown":
        reasons.append("Resolve ESR1, PIK3CA and germline BRCA testing before prioritizing across the competing branches.")
    if c["prior_metastatic_chemo"] is None or c["additional_metastatic_lines"] is None:
        reasons.append("Confirm prior treatment counts before prioritizing across line-dependent options.")
    return reasons


def score_option(o, c, weights, paused):
    block = list(paused)
    if o["status"] != "discuss":
        block.append(o["fit_reason"])
    if o["case_concerns"]:
        block.extend(s["text"] for s in o["case_concerns"])
    if block:
        return dict(value=None, label="Not scored — review required", eligible_for_priority=False,
                    blocked_reasons=block, components=[], source_ids=o["fit_source_ids"])
    is_generic = o["gate"] == "any"
    points, evidence_reason, evidence_refs = EVIDENCE[o["id"]]
    if c["prior_cdk"] == "unknown":
        points = min(points, 3)
        evidence_reason += " Prior CDK4/6 agent is unknown; applicability score is capped at 3/5."
    if o["id"] == "tdxd" and c["her2"] == "ultralow":
        points = min(points, 3)
        evidence_reason += " HER2-ultralow evidence is exploratory; score capped at 3/5."
    oral_only = o["id"] in {"elacestrant", "imlunestrant", "imlunestrant_abemaciclib", "vepdegestrant", "olaparib"}
    visits = 5 if oral_only else 3 if "IM" in o["route"] else 2
    preference_reason = "Entered priority is fewer visits: oral-only delivery receives 5/5; injection combinations 3/5; infusion or unspecified strategy 2/5. Monitoring still applies."
    if c["preference"] != "fewer_visits":
        visits = 3
        preference_reason = "No specific delivery preference: neutral 3/5. Disease-control preference increases the evidence weight; it does not infer efficacy from cross-trial medians."
    values = {
        "match": (3 if is_generic else 5, "A broad strategy rather than a biomarker-selected match." if is_generic else o["fit_reason"], o["fit_source_ids"]),
        "evidence": (points, evidence_reason, evidence_refs),
        "readiness": (3, "No encoded case-specific review flags are present. Neutral 3/5: complete drug-specific safety assessment has not been performed.", [r for s in o["cons"] for r in s["source_ids"]]),
        "preference": (visits, preference_reason, [r for s in o["pros"] + o["cons"] for r in s["source_ids"]]),
    }
    components = []
    for key, (v, reason, refs) in values.items():
        components.append(dict(key=key, label=DIMENSIONS[key], points=v, maximum=5,
                               weight=weights[key], contribution=round(v / 5 * weights[key], 2),
                               reason=reason, source_ids=sorted(set(refs))))
    return dict(value=round(sum(row["contribution"] for row in components), 1),
                label="Discussion priority / 100", eligible_for_priority=True, blocked_reasons=[],
                components=components, source_ids=sorted({r for row in components for r in row["source_ids"]}))


def rank_options(result, weights=None):
    c = result["case"]
    weights = validate_weights(weights if weights is not None else WEIGHT_PRESETS[c["preference"]])
    paused = paused_reasons(result)
    for o in result["options"]:
        o["priority_score"] = score_option(o, c, weights, paused)
    scored = sorted((o for o in result["options"] if o["priority_score"]["value"] is not None),
                    key=lambda o: -o["priority_score"]["value"])
    top = scored[0]["priority_score"]["value"] if scored else None
    shortlist = [o for o in scored if top - o["priority_score"]["value"] <= 5]
    recommendation = dict(status="paused" if not scored else "shortlist" if len(shortlist) > 1 else "priority",
                          title="Clinical review needed before prioritization" if not scored else "Suggested next clinical discussion",
                          option_ids=[o["id"] for o in shortlist], score=top,
                          text="; ".join(paused) if paused else "Resolve the flagged facts before selecting a scored option.",
                          reasons=[], comparison=[], next_checks=[])
    if shortlist:
        recommendation["text"] = ("Prioritize discussing " + " or ".join(o["title"] for o in shortlist)
            + ". " + ("These options are within 5 policy points; the rubric does not justify a unique winner." if len(shortlist)>1 else "This option scores highest under the stated discussion policy."))
        for o in shortlist:
            recommendation["reasons"].append(dict(option_id=o["id"], title=o["title"],
                text=" ".join(row["reason"] for row in o["priority_score"]["components"] if row["key"] in {"match", "evidence", "preference"}),
                source_ids=o["priority_score"]["source_ids"]))
        for o in scored:
            if o in shortlist:
                continue
            leader = shortlist[0]
            differences = []
            for a, b in zip(leader["priority_score"]["components"], o["priority_score"]["components"]):
                if a["contribution"] > b["contribution"]:
                    differences.append(dict(dimension=b["label"], policy_point_gap=round(a["contribution"]-b["contribution"],2), reason=b["reason"], source_ids=b["source_ids"]))
            recommendation["comparison"].append(dict(option_id=o["id"], title=o["title"], score=o["priority_score"]["value"], differences=differences))
        recommendation["next_checks"] = [
            "Confirm the precise prior regimens, assays/variants and current regulatory indication.",
            "Review drug interactions, organ function and each option's toxicity/monitoring requirements with the treating team.",
            "Discuss the shortlist and alternatives with the clinician; this rubric is not a validated treatment-benefit model.",
        ]
    # Simple weight sensitivity: ±10 points between preference and evidence,
    # keeping the other weights fixed and the total 100. This is policy sensitivity.
    sensitivity = []
    for delta in (-10, 10):
        alt = dict(weights, evidence=weights["evidence"]+delta, preference=weights["preference"]-delta)
        if min(alt.values()) < 0 or max(alt.values()) > 100 or not scored:
            continue
        values = [(o, score_option(o,c,alt,paused)["value"]) for o in scored]
        high = max(v for _, v in values)
        sensitivity.append(dict(weights=alt, shortlist_ids=[o["id"] for o,v in values if high-v <= 5]))
    result["priority_policy"] = dict(version=VERSION, weights=weights, dimensions=DIMENSIONS,
        formula="sum((dimension points / 5) × dimension weight); weights total 100",
        provenance="Hand-set prototype rubric, not a guideline-endorsed or learned clinical score",
        exclusions="Unmatched, later-line, unresolved case concerns and global review holds receive no score, not zero.",
        tie_margin=5, sensitivity=sensitivity,
        forecast_weight=0,
        limitations="References support clinical facts, not the numeric points or weights. No cross-trial HR/PFS ranking or patient success probability is calculated.")
    result["ranking"] = [dict(option_id=o["id"], title=o["title"], score=o["priority_score"]["value"]) for o in scored]
    result["recommendation"] = recommendation
    return result
