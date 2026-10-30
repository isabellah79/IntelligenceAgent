"""Provisional per-population defense checklist and separate set differentiation.

The 15 common checks use shared weights for all producers. They are engineering
diagnostics, not validated clinical quality or a ground truth for the LLM judge.
Oncologist grades are the calibration reference. Endpoint forecasts never enter
this score. Weights can be overridden explicitly and are recorded in the report.
"""
from __future__ import annotations

import re
import math

from .lexicon import SUBSTANTIVE_TAGS
from .normalize import concepts, option_text
from .schema import citation_pairs

# Absolute claims that are wrong without hedging. Checked against the
# surrounding text so an explicit "does not establish" is not flagged.
OVERCLAIM_PATTERNS = (
    r"\bproven\b", r"\bguarantee[sd]?\b", r"confirmed predictive",
    r"\bwill (benefit|cure|be effective)\b", r"\bsuperior to\b", r"\bdefinitely\b",
    r"\bestablish(es|ed)? (that )?(it|this) (is|has) (superior|better)",
)
NEGATIONS = ("not", "no", "cannot", "does not", "do not", "never", "without", "fails to", "unproven",
             # A claim that something is *absent* or *unconfirmed* is the
             # opposite of overclaiming it.
             "absence", "lack of", "no evidence", "not established", "unconfirmed",
             "is not", "are not", "was not", "were not")
SAFETY_SOURCE_HINTS = ("FDA", "LABEL", "SAFETY")
GUIDANCE_HINTS = ("FDA-", "GUID", "NCI", "ASCO", "FRIENDS")
RISK_WORDS = {
    "safety": ("safety", "toxicity", "adverse", "risk", "tolerab"),
    "enrollment": ("enroll", "accrual", "recruit", "slow"),
    "generalization": ("generaliz", "general", "real-world", "applicab"),
    "regulatory": ("regulat", "label", "approval", "guidance", "indication"),
    "evidence": ("evidence", "unproven", "uncertain", "exploratory", "hypothesis", "post hoc", "not establish", "unknown", "unconfirmed"),
}


def _rule(name: str, weight: float, passed: bool, detail: str) -> dict:
    return dict(rule=name, weight=weight, pass_=bool(passed), detail=detail)


def _all_text(option: dict) -> str:
    return " ".join(option_text(option))


def _cite_ids(option: dict) -> set[str]:
    ids = {sid for r in (option.get("inclusion") or []) + (option.get("exclusion") or [])
           + (option.get("pros") or []) + (option.get("cons") or [])
           + (option.get("protocol_pending") or []) for sid in r["source_ids"]}
    for value in (option.get("estimates") or {}).values():
        if isinstance(value, dict):
            ids |= set(value.get("source_ids") or [])
    return ids


def _overclaims(text: str) -> list[str]:
    low = text.lower()
    hits = []
    for pattern in OVERCLAIM_PATTERNS:
        for match in re.finditer(pattern, low):
            window = low[max(0, match.start() - 90):match.end() + 30]
            if not any(n in window for n in NEGATIONS):
                hits.append(match.group(0))
    return hits


def _blanket_cns_exclusion(option: dict) -> bool:
    for row in option.get("exclusion") or []:
        text = row["text"].lower()
        if "cns_brain_mets" in concepts(text) and any(w in text for w in ("exclude", "excluded", "no history", "any brain")):
            if not any(w in text for w in ("stable", "treated", "selected", "asymptomatic", "unless")):
                return True
    return False


def _performance_status_rule(option: dict) -> tuple[bool, str]:
    text = _all_text(option)
    if "performance_status" not in concepts(text):
        return True, "no performance-status restriction, so nothing to justify"
    rows = [r for r in option["inclusion"] + option["exclusion"] if "performance_status" in concepts(r["text"])]
    justified = all(r.get("reason") and r.get("source_ids") for r in rows)
    return justified, "performance-status limit carries a reason or an ECOG-2 route" if justified \
        else "performance status is restricted without a stated reason"


# -- rules -----------------------------------------------------------------

def _distinct_options(option_set: dict) -> dict:
    """Options must vary on *different* axes, not add one clause to the same one."""
    options = option_set["options"]
    if len(options) < 3:
        return _rule("distinct_options", 1.5, False, f"{len(options)} options; the plan asks for 3-4")
    pairs = differentiation(option_set)
    passed = bool(pairs) and all(p["differentiated"] for p in pairs)
    return _rule("distinct_options", 1.5, passed, f"{sum(p['differentiated'] for p in pairs)}/{len(pairs)} pairs have different operational criteria; overlap between cohorts is allowed")


def _named_axes(option_set: dict) -> dict:
    options = option_set["options"]
    named = sum(1 for o in options if o["axes"])
    axes = {a.strip().lower() for o in options for a in o["axes"]}
    return _rule("named_axes", 1.0, named == len(options) and len(axes) >= 2,
                 f"{named}/{len(options)} options name axes; {len(axes)} distinct axes")


def _pros_present(option_set: dict) -> dict:
    short = [o["option_id"] for o in option_set["options"] if len(o["pros"]) < 2]
    return _rule("pros_present", 1.0, not short, f"options with fewer than 2 pros: {short or 'none'}")


def _cons_present(option_set: dict) -> dict:
    short = [o["option_id"] for o in option_set["options"] if len(o["cons"]) < 2]
    return _rule("cons_present", 1.0, not short, f"options with fewer than 2 cons: {short or 'none'}")


def _cons_substantive(option_set: dict) -> dict:
    """Cons must name a real downside class, not restate the population."""
    weak = []
    for option in option_set["options"]:
        text = " ".join(r["text"].lower() for r in option["cons"])
        if not any(any(w in text for w in words) for words in RISK_WORDS.values()):
            weak.append(option["option_id"])
    return _rule("cons_substantive", 1.0, not weak, f"cons that name no risk class: {weak or 'none'}")


def _no_overclaiming(option_set: dict) -> dict:
    hits = []
    for option in option_set["options"]:
        for text in option_text(option) + [r["text"] for r in option["pros"] + option["cons"] + option.get("defense", [])]:
            found = _overclaims(text)
            if found:
                hits.append(dict(option_id=option["option_id"], claim=text[:120], terms=found))
    return _rule("no_overclaiming", 2.0, not hits, f"{len(hits)} absolute claims without hedging")


def _uses_guidance(option_set: dict) -> dict:
    missing = []
    for option in option_set["options"]:
        ids = _cite_ids(option)
        if not any(any(h in sid for h in GUIDANCE_HINTS) for sid in ids):
            missing.append(option["option_id"])
    return _rule("uses_guidance", 1.0, not missing, f"options citing no eligibility guidance: {missing or 'none'}")


def _cns_not_blanket(option_set: dict) -> dict:
    bad = [o["option_id"] for o in option_set["options"] if _blanket_cns_exclusion(o)]
    return _rule("cns_not_blanket", 1.5, not bad, f"unjustified blanket CNS exclusion: {bad or 'none'}")


def _ps_justified(option_set: dict) -> dict:
    fails = [o["option_id"] for o in option_set["options"] if not _performance_status_rule(o)[0]]
    return _rule("ps_justified", 1.0, not fails, f"unjustified performance-status limits: {fails or 'none'}")


def _safety_exclusion(option_set: dict) -> dict:
    missing = []
    for option in option_set["options"]:
        tagged = [r for r in option["exclusion"] if r.get("purpose") == "safety"]
        cited = [r for r in tagged if any(any(h in sid for h in SAFETY_SOURCE_HINTS) for sid in r["source_ids"])]
        if not tagged or not cited:
            missing.append(option["option_id"])
    return _rule("safety_exclusion", 1.5, not missing, f"options lacking a cited regimen safety screen: {missing or 'none'}")


def _scope_respected(option_set: dict) -> dict:
    """Every option must stay inside HR+/HER2- metastatic disease."""
    bad = []
    for option in option_set["options"]:
        text = " ".join(r["text"] for r in option["inclusion"]).lower().replace("−", "-")
        cs = concepts(text)
        her2_negative = bool(re.search(r"\bher2(?:[\s-]*negative\b|\s*-(?=\s|[,;./)]|$))", text)) or bool(cs & {"her2_low", "her2_ultralow"})
        contradictory = any('her2_positive' in concepts(r['text']) and not
                            re.search(r'\bexclude|\bnot\b|\bnegative\b|\bwithout\b',r['text'],re.I)
                            for r in option['inclusion'])
        if not ("hr_positive" in cs and her2_negative and
                any(w in text for w in ("metastatic", "advanced")) and "prior_cdk" in cs and not contradictory):
            bad.append(option["option_id"])
    return _rule("scope_respected", 1.5, not bad, f"options not anchored to HR+/HER2- disease: {bad or 'none'}")


def _criteria_complete(option_set: dict) -> dict:
    thin = [o["option_id"] for o in option_set["options"]
            if sum(1 for r in o["inclusion"] + o["exclusion"]
                   if r.get("purpose") in SUBSTANTIVE_TAGS or r.get("purpose") == "scope") < 3]
    return _rule("criteria_complete", 1.0, not thin, f"options with fewer than 3 substantive criteria: {thin or 'none'}")


def _estimates_ranged(option_set: dict) -> dict:
    """Unknown is acceptable; a forecast must never be passed off as prevalence."""
    weak = []
    for option in option_set["options"]:
        est = option.get("estimates") or {}
        share = est.get("eligible_share") if isinstance(est.get("eligible_share"), dict) else {}
        unknown = share.get("status") == "unavailable" and bool(share.get("reason"))
        low, high = share.get("low"), share.get("high")
        ranged = all(type(v) in (int, float) and math.isfinite(v) for v in (low, high))
        valid = bool(ranged and 0 <= low <= high <= 1 and share.get("source_ids") and
                     "endpoint" not in str(share.get("note", "")).lower())
        if not (unknown or valid):
            weak.append(option["option_id"])
    return _rule("estimates_ranged", 1.0, not weak, f"options without a sourced range estimate: {weak or 'none'}")


def _recommendation_defended(option_set: dict) -> dict:
    rec = option_set.get("recommendation") or {}
    ids = {o["option_id"] for o in option_set["options"]}
    if rec.get("option_id") not in ids:
        return _rule("recommendation_defended", 2.0, False, "no recommended option among the proposed options")
    defense = rec.get("defense") or []
    cited = [r for r in defense if r["source_ids"]]
    compares = any(len(o["population"].split()) and any(a in r["text"].lower() for r in defense
                                                         for a in ("than", "over", "compared", "instead", "rather"))
                   for o in option_set["options"])
    ok = bool(defense) and bool(cited)
    return _rule("recommendation_defended", 2.0, ok,
                 f"{len(defense)} defense statements, {len(cited)} cited, comparison language={compares}")


def _citation_coverage(option_set: dict) -> dict:
    pairs = citation_pairs(option_set)
    uncited = [p for p in pairs if not p["source_ids"]]
    return _rule("citation_coverage", 1.5, not uncited,
                 f"{len(uncited)}/{len(pairs)} claims carry no source")


RULES = (_distinct_options, _named_axes, _pros_present, _cons_present, _cons_substantive,
         _no_overclaiming, _uses_guidance, _cns_not_blanket, _ps_justified, _safety_exclusion,
         _scope_respected, _criteria_complete, _estimates_ranged, _recommendation_defended,
         _citation_coverage)


def _criteria_reasoned(option_set: dict) -> dict:
    rows = [r for o in option_set["options"] for r in o["inclusion"] + o["exclusion"] if r.get("purpose") != "scope"]
    justified = sum(bool(r.get("reason")) for r in rows)
    return _rule("criteria_reasoned", 1.5, bool(rows) and justified == len(rows), f"{justified}/{len(rows)} non-scope criteria have an explicit rationale")


def _uncertainty_explicit(option_set: dict) -> dict:
    text = " ".join(r["text"] for o in option_set["options"] for k in ("cons", "defense", "protocol_pending") for r in o.get(k, []))
    return _rule("uncertainty_explicit", 1.5, bool(re.search(r"uncertain|unproven|unknown|exploratory|hypothes|not establish|needs? validation|not.*predictive|pending|finaliz", text, re.I)), "Checks whether the defense states a limitation; not whether that limitation is clinically correct")


def _population_defended(option_set: dict) -> dict:
    rows = [r for o in option_set["options"] for r in o.get("defense", [])]
    return _rule("population_defended", 2.0, any(r.get("source_ids") and len(r["text"].split()) >= 8 for r in rows), "Population needs its own cited defense, independently of which option is recommended")


COMMON_RULES = tuple(fn for fn in RULES if fn not in (_distinct_options, _named_axes, _recommendation_defended)) + (_criteria_reasoned, _uncertainty_explicit, _population_defended)


def _aggregate(results: list[dict]) -> dict:
    total = sum(r["weight"] for r in results) or 1.0
    earned = sum(r["weight"] for r in results if r["pass_"])
    return dict(score=round(earned / total, 4),
                rules=len(results),
                passed=sum(1 for r in results if r["pass_"]),
                failures=[r for r in results if not r["pass_"]],
                results=results)


def differentiation(option_set: dict) -> list[dict]:
    """Pairwise operational differences; different axis names alone earn no credit."""
    from .normalize import best_match
    options = option_set["options"]
    rows = []
    for i, left in enumerate(options):
        for right in options[i + 1:]:
            differences = {}
            for a, b in ((left, right), (right, left)):
                unique = []
                for section in ("inclusion", "exclusion"):
                    candidates = [r["text"] for r in b[section] if r.get("purpose") not in ("scope", "design")]
                    for row in a[section]:
                        if row.get("purpose") in ("scope", "design"):
                            continue
                        if not best_match(row["text"], candidates)["matched"]:
                            unique.append(dict(section=section, text=row["text"], source_ids=row["source_ids"]))
                differences[a["option_id"]] = unique
            rows.append(dict(left=left["option_id"], right=right["option_id"],
                             differentiated=any(differences.values()), differences=differences,
                             interpretation="Text-based operational differences; neither disjointness nor differential treatment benefit is established."))
    return rows


def validate_weights(weights):
    weights = {} if weights is None else weights
    known = {fn(dict(options=[], recommendation={}))["rule"] for fn in COMMON_RULES}
    if not isinstance(weights, dict) or set(weights) - known:
        raise ValueError("Unknown population-defense rule in weights")
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 10 for v in weights.values()):
        raise ValueError("Rule weights must be finite numbers from 0 to 10")
    defaults = {r["rule"]:r["weight"] for r in (fn(dict(options=[], recommendation={})) for fn in COMMON_RULES)}
    if sum({**defaults, **weights}.values()) <= 0:
        raise ValueError("At least one rule must have a positive weight")
    return weights


def score_defense_rubric(option_set: dict, weights=None) -> dict:
    weights = validate_weights(weights)
    populations = []
    for option in option_set["options"]:
        single = dict(options=[option], recommendation=option_set.get("recommendation", {}))
        rows = [fn(single) for fn in COMMON_RULES]
        for row in rows:
            row["weight"] = weights.get(row["rule"], row["weight"])
        grade = _aggregate(rows)
        populations.append(dict(option_id=option["option_id"], population=option["population"],
                                **grade, endpoint_forecast=option["estimates"].get("endpoint_forecast"),
                                provisional=True))
    set_results = [fn(option_set) for fn in (_distinct_options, _named_axes, _recommendation_defended)]
    pairs = differentiation(option_set)
    return dict(benchmark="population_defense_v2", version="2.0",
                weight_overrides=weights,
                score=round(sum(p["score"] for p in populations) / len(populations), 4) if populations else None,
                populations=populations, rules=len(COMMON_RULES),
                passed=sum(p["passed"] for p in populations),
                failures=[dict(option_id=p["option_id"], **r) for p in populations for r in p["failures"]],
                results=[r for p in populations for r in p["results"]],
                set_design=dict(**_aggregate(set_results), differentiation=pairs),
                interpretation="Mean of per-population defense checklist scores. Multi-option design is reported separately, so single-option baselines share the same quality scale. Uncalibrated; not a clinical-benefit ranking.")


def safety_gate(option_set: dict) -> dict:
    """The plan's milestone 2 gate: no unsafe criterion, no fabricated reference.

    Fabrication is checked in ``reference_accuracy``; this reports criterion-safety
    violations a rubric pass must not hide.
    """
    violations = []
    for option in option_set["options"]:
        if _blanket_cns_exclusion(option):
            violations.append(dict(option_id=option["option_id"], kind="blanket_cns_exclusion",
                                   detail="excludes all CNS disease without a reasoned alternative"))
        for text in option_text(option):
            if _overclaims(text):
                violations.append(dict(option_id=option["option_id"], kind="unsafe_claim",
                                       detail=text[:160]))
    return dict(passed=not violations, violations=violations)
