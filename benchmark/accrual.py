"""Benchmark 4: accrual post-mortem.

For trials that stopped or stalled for slow accrual, does the agent list the
restrictive criterion as a con? The plan calls for reviewing every flagged case,
so this scorer is precise about *which* criterion it expected the agent to name.

Ground truth (one JSON object per trial)::

    {"trial_id": str, "nct_id": str, "phase": str,
     "restrictive_criteria": [str],        # from the trial's own criteria text
     "stop_reason": str,                   # verbatim, e.g. whyStopped
     "stop_reason_source": str,            # "whyStopped" | "publication" | "news"
     "evidence": {"source": str, "url": str, "date": str}}

A con earns credit when it mentions the criterion's concept *and* uses accrual
language ("slow enrolment", "narrow population", "may limit accrual"). Naming a
restriction without connecting it to accrual is a near miss and is recorded
separately, because the plan's question is specifically about the post-mortem.
"""
from __future__ import annotations

from .lexicon import CONCEPTS
from .normalize import concepts

ACCRUAL_WORDS = ("accrual", "enrol", "recruit", "pool", "narrow", "few patients",
                 "restrictive", "slow", "generaliz", "eligible patients")


def _accrual_language(text: str) -> bool:
    return any(word in text.lower() for word in ACCRUAL_WORDS)


def score_accrual_postmortem(option_set: dict, gold: dict) -> dict:
    targets = gold.get("restrictive_criteria") or []
    cons = [(o["option_id"], r["text"]) for o in option_set["options"]
            for r in (o.get("cons") or [])]
    rows = []
    for target in targets:
        target_concepts = concepts(target)
        mentions = [(oid, text) for oid, text in cons
                    if target_concepts & concepts(text)]
        with_accrual = [(oid, text) for oid, text in mentions if _accrual_language(text)]
        rows.append(dict(
            criterion=target[:200],
            matched=bool(with_accrual),
            # A con that names the restriction but not the accrual consequence.
            near_miss=bool(mentions) and not with_accrual,
            options=[oid for oid, _ in mentions],
            best_quote=(with_accrual or mentions or [(None, "")])[0][1][:200],
        ))
    hits = sum(1 for r in rows if r["matched"])
    total = len(rows) or 1
    return dict(benchmark="accrual_postmortem",
                trial_id=gold.get("trial_id"), nct_id=gold.get("nct_id"),
                score=round(hits / total, 4),
                hits=hits, targets=len(rows),
                # The plan says review all flagged cases; these are the near misses.
                flag_for_review=[r for r in rows if r["near_miss"]],
                rows=rows,
                stop_reason=gold.get("stop_reason", ""))


def known_concepts() -> list[str]:
    """Concept names the accrual matcher can see; useful when writing gold data."""
    return sorted(CONCEPTS)
