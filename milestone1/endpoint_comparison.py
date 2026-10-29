"""Endpoint table: observed results and explicitly conditional trial scenarios.

No preference/rubric points enter this table. Reported hazard ratios describe
their original populations and comparators. Using them as hypothetical true
effects is a retrospective power scenario, not a validated prospective forecast.
"""
from copy import deepcopy
import math

from forecast.forecast import forecast_case, method_b

DEFAULT_DESIGN = dict(events=200, z_threshold=1.96, prior=.5, use_reference_effect=True,
                      evidence_strength=.5, blend_a=.5, factor_overrides={})
FACTOR_IDS = {"direct_post_cdk", "mixed_prior_cdk", "exploratory_subgroup", "long_prior_response", "posthoc_caution", "exposure_risk", "indirect_sequence"}


def evidence_ledger(o, c, design):
    rows=[]
    def add(id, factor, finding, rationale, refs):
        chosen=design["factor_overrides"].get(o["id"],{}).get(id,factor)
        rows.append(dict(id=id, factor=chosen, default_factor=factor,
                         effective_factor=chosen**design["evidence_strength"],
                         finding=finding, rationale=rationale, source_ids=refs,
                         weight_provenance="Analyst-assigned provisional multiplier; not estimated by the cited study"))
    if o["id"] in {"elacestrant","vepdegestrant","postmonarch"}:
        add("direct_post_cdk",1.2,"The source trial required prior CDK4/6 treatment.","Proposed positive modifier for setting applicability, not a second efficacy effect.",o["pros"][0]["source_ids"])
    if o["id"] in {"imlunestrant","imlunestrant_abemaciclib","capivasertib"}:
        add("mixed_prior_cdk",.9,"The reported source population includes patients with and without prior CDK4/6 exposure.","Proposed negative modifier for transfer to an exclusively post-CDK4/6 trial.",["EMBER3-UPDATE" if o["id"].startswith("imlunestrant") else "CAPITELLO"])
    if o["id"]=="imlunestrant_abemaciclib":
        add("exploratory_subgroup",.85,"The ESR1-mutated combination estimate used in this row is exploratory.","Proposed discount for subgroup uncertainty; no overall/subgroup results are pooled.",["EMBER3"])
    if o["id"]=="elacestrant" and c["endocrine_months"] is not None and c["endocrine_months"]>=12:
        add("long_prior_response",1.1,"An EMERALD analysis of ESR1-mutated patients with ≥12 months of prior ET+CDK4/6 reported HR 0.41; this case's reported duration meets that subgroup definition.","Small proposed positive modifier for contextual support; the primary HR 0.55 is retained in method B.",["EMERALD-DURATION"])
        add("posthoc_caution",.9,"The duration analysis is exploratory/post hoc and does not establish an independent predictive treatment effect.","Countervailing discount; do not treat subgroup findings as confirmed or independent replication.",["EMERALD-DURATION"])
    if o["id"]=="capivasertib":
        add("exposure_risk",.9,"CAPItello-291 reported treatment discontinuation due to adverse events in 13.0% vs 2.3%; a dedicated safety analysis describes early rash, diarrhea and hyperglycemia.","Hypothesized trial-delivery/exposure risk. Its actual relationship to endpoint success is not quantified.",["CAPITELLO","CAPI-SAFETY"])
    if o["id"]=="datodxd":
        add("exposure_risk",.95,"TROPION-Breast01 documents stomatitis, ocular toxicity and dose modifications, alongside favorable comparative severe-toxicity and patient-reported findings.","Modest proposed exposure-risk discount, not a claim of worse overall tolerability than chemotherapy.",["DATO-PRIMARY","DATO-SAFETY"])
    if o["id"]=="olaparib":
        add("indirect_sequence",.8,"OlympiAD is not a dedicated trial of the modern post-CDK4/6 treatment sequence.","Proposed discount for sequence extrapolation.",["OLYMPIAD"])
    return rows


def endpoint(trial, population, comparator, medians, hr, refs, note="", name="PFS"):
    return dict(trial=trial, population=population, comparator=comparator,
                median_pfs_months=medians, hazard_ratio=hr, source_ids=refs,
                note=note, primary_endpoint=name)


ENDPOINTS = {
    "elacestrant": endpoint("EMERALD", "ESR1-mutated; prior CDK4/6 required", "Fulvestrant or aromatase inhibitor", [3.8, 1.9], .55, ["EMERALD", "ELAC-FDA"]),
    "imlunestrant": endpoint("EMBER-3", "ESR1-mutated; mixed prior CDK4/6 exposure", "Fulvestrant or exemestane", [5.5, 3.8], .62, ["IMLU-FDA"], "The reported ESR1-mutated estimate is not exclusively a post-CDK4/6 result."),
    "imlunestrant_abemaciclib": endpoint("EMBER-3", "ESR1-mutated subgroup; mixed prior CDK4/6 exposure", "Imlunestrant alone", [11.1, 5.5], .53, ["EMBER3"], "This ESR1-mutated combination analysis is exploratory, not the overall-population primary estimate."),
    "vepdegestrant": endpoint("VERITAC-2", "ESR1-mutated; prior CDK4/6 required", "Fulvestrant", [5.0, 2.1], .57, ["VERITAC2"], "This row uses the FDA-assessed HR 0.57. The original journal report gives HR 0.58; the estimates are not merged."),
    "capivasertib": endpoint("CAPItello-291", "PIK3CA/AKT1/PTEN-altered; mixed prior CDK4/6 exposure", "Placebo + fulvestrant", [7.3, 3.1], .50, ["CAPITELLO", "CAPI-LABEL"]),
    "alpelisib": endpoint("PIQRAY / SOLAR-1 evidence context", "PIK3CA-mutated; pivotal study not a dedicated post-CDK4/6 comparison", "No post-CDK4/6 comparative estimate supplied", None, None, ["ALPEL-LABEL"], "No source-backed comparative post-CDK4/6 HR is supplied in this library. No endpoint forecast is invented."),
    "gedatolisib": endpoint("VIKTORIA-1 · triplet comparison", "No PIK3CA mutation detected", "Fulvestrant", [9.3, 2.0], .24, ["GEDA-FDA", "GEDA-LABEL"], "Result shown is gedatolisib + fulvestrant + palbociclib; the doublet has a separate result. The original 64.7% forecast remains a historical example in the lab."),
    "tdxd": endpoint("DESTINY-Breast06", "HER2-low primary population; no prior metastatic chemotherapy", "Investigator-choice chemotherapy", [13.2, 8.1], .62, ["DB06", "TDXD-FDA"], "HER2-ultralow was exploratory; do not use the HER2-low estimate as its effect assumption."),
    "datodxd": endpoint("TROPION-Breast01", "After endocrine therapy and chemotherapy for advanced disease", "Investigator-choice chemotherapy", [6.9, 4.9], .63, ["DATO-FDA"]),
    "sacituzumab": endpoint("TROPiCS-02", "Heavily pretreated, including prior metastatic chemotherapy", "Single-agent chemotherapy", [5.5, 4.0], .661, ["TROPICS2"], "PFS is shown here. The 14.4 vs 11.2 month OS result is a separate endpoint, not the PFS score."),
    "chemotherapy": endpoint("Regimen-specific trial needed", "Depends on selected drug and treatment history", "Specify a comparator", None, None, ["PDQ", "CAPE"], "Chemotherapy is a strategy, not one regimen. Specify a drug, population and comparator before calculating a trial-endpoint score."),
    "olaparib": endpoint("OlympiAD", "Germline BRCA-mutated HER2-negative disease", "Investigator-choice chemotherapy", [7.0, 4.2], .58, ["OLYMPIAD", "OLAP-NCI"], "Not a dedicated post-CDK4/6 population; prior-treatment requirements need review."),
    "postmonarch": endpoint("postMONARCH", "After prior CDK4/6 + endocrine therapy", "Placebo + fulvestrant", [6.0, 5.3], .73, ["POSTMONARCH"], "Investigator-assessed primary PFS; the BICR estimate is different. Do not substitute it into this primary-endpoint row."),
}


def validate_design(value):
    if value is None:
        return deepcopy(DEFAULT_DESIGN)
    if not isinstance(value, dict) or set(value) != set(DEFAULT_DESIGN):
        raise ValueError("Endpoint design requires events, z_threshold, prior and use_reference_effect")
    if type(value["events"]) is not int or not 1 <= value["events"] <= 1000000:
        raise ValueError("Endpoint events must be an integer between 1 and 1000000")
    z = value["z_threshold"]
    if type(z) not in (int, float) or not math.isfinite(z) or not 0 < z <= 10:
        raise ValueError("Endpoint z threshold must be a finite number above 0 and at most 10")
    prior = value["prior"]
    if prior is not None and (type(prior) not in (int, float) or not math.isfinite(prior) or not .000001 <= prior <= .999999):
        raise ValueError("Reference-class prior must be between 0 and 1, or null if not supplied")
    if type(value["use_reference_effect"]) is not bool:
        raise ValueError("use_reference_effect must be a boolean")
    for key in ("evidence_strength","blend_a"):
        if type(value[key]) not in (int,float) or not math.isfinite(value[key]) or not 0<=value[key]<=1:
            raise ValueError(f"{key} must be between 0 and 1")
    overrides=value["factor_overrides"]
    if not isinstance(overrides,dict) or not set(overrides)<=set(ENDPOINTS):
        raise ValueError("Unknown treatment in evidence factor overrides")
    for factors in overrides.values():
        if not isinstance(factors,dict) or not set(factors)<=FACTOR_IDS:
            raise ValueError("Unknown evidence factor")
        if any(type(v) not in (int,float) or not math.isfinite(v) or not .25<=v<=4 for v in factors.values()):
            raise ValueError("Evidence multipliers must be finite numbers from 0.25 to 4")
    return deepcopy(value)


def add_endpoint_table(result, design=None):
    design = validate_design(design)
    result["endpoint_design"] = design
    result["endpoint_score_definition"] = {
        "label": "Illustrative PFS endpoint scenario",
        "target": "Chance of crossing a trial's statistical significance threshold, conditional on the stated true-HR assumption",
        "method": "Original forecast.py methods A/B, with editable evidence multipliers and A/B blend. The 50% starting prior is a neutral analyst assumption, not a literature-derived success rate.",
        "effect_assumption": "The published source-cohort HR is treated as a hypothetical true HR. This is a retrospective power illustration, not prospective validation.",
        "limitations": "Provisional, uncalibrated framework. Sources support findings, not numerical multipliers. Related reports are not independent evidence. Different cohorts/comparators prevent a head-to-head treatment ranking; not a patient-benefit probability.",
    }
    for o in result["options"]:
        e = deepcopy(ENDPOINTS[o["id"]])
        e["score"] = None
        e["method_a"] = None
        e["method_b"] = None
        e["unadjusted_score"] = None
        e["evidence_delta"] = None
        e["evidence_adjustments"] = evidence_ledger(o,result["case"],design)
        e["source_ids"] = sorted(set(e["source_ids"]) | {r for row in e["evidence_adjustments"] for r in row["source_ids"]})
        e["score_type"] = "Conditional power" if design["prior"] is None else "Experimental A+B forecast"
        e["unavailable_reason"] = ""
        blocked = list(o["priority_score"]["blocked_reasons"])
        # Endpoint estimation does not depend on preference points; use only
        # case/applicability review holds, not their numeric contributions.
        if blocked:
            e["unavailable_reason"] = "Case applicability / review hold: " + " ".join(blocked)
        elif e["hazard_ratio"] is None:
            e["unavailable_reason"] = e["note"]
        elif o["id"] == "tdxd" and result["case"]["her2"] == "ultralow":
            e["unavailable_reason"] = "The cited effect is for HER2-low, not a HER2-ultralow-specific estimate."
        elif not design["use_reference_effect"]:
            e["unavailable_reason"] = "Choose a justified true-HR assumption in the forecast lab; source-HR illustration is disabled."
        else:
            b = dict(events=design["events"], scenarios=[dict(name="Published HR used as hypothetical true effect",hr=e["hazard_ratio"],weight=1)], bars=[dict(z=design["z_threshold"],weight=1)])
            if design["prior"] is None:
                value, _ = method_b(b["events"],b["scenarios"],b["bars"])
                e["score"] = e["method_b"] = value
            else:
                factors=[dict(name=row["id"],factor=row["effective_factor"]) for row in e["evidence_adjustments"]]
                f = forecast_case(dict(trial=e["trial"]+": hypothetical PFS illustration vs "+e["comparator"], as_of=result["evidence_as_of"], method_a=dict(prior=design["prior"],factors=factors),method_b=b))
                e["method_a"],e["method_b"] = f["method_a"],f["method_b"]
                e["score"] = design["blend_a"]*e["method_a"]+(1-design["blend_a"])*e["method_b"]
                e["unadjusted_score"] = design["blend_a"]*design["prior"]+(1-design["blend_a"])*e["method_b"]
                e["evidence_delta"] = e["score"]-e["unadjusted_score"]
                e["method_a_steps"]=f["method_a_steps"]
        o["endpoint_comparison"] = e
    return result
