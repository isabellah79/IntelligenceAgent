"""Benchmark 5: outcome alignment (marked "needs study" in the plan).

The question: does the recommended population favour subgroups where the drug
later worked, and avoid those where it did not?

This is the benchmark the plan is most cautious about, and the caution is
justified. A subgroup estimate is noisy, a forest plot invites over-reading, and
"the recommendation happened to lean toward the subgroup with the larger point
estimate" is a weak signal even when true. So this scorer is built to report
*agreement*, never causation, and every result carries its caveats.

Input is hand-extracted, one JSON object per trial::

    {"trial_id": str, "nct_id": str, "drug": str,
     "subgroups": [{"label": str, "hazard_ratio": float | null,
                    "ci_low": float | null, "ci_high": float | null,
                    "interaction_p": float | null,
                    "source": str, "source_url": str}],
     "note": str}

The scorer asks a deliberately narrow question: is the recommended option's
defined population closer to the favourable subgroup or the unfavourable one,
using the same clause matcher as everything else? A trial whose subgroups show
no interaction evidence gets ``inconclusive`` rather than a guess.
"""
from __future__ import annotations

from .normalize import concepts, distinguishing_clauses

INTERACTION_ALPHA = 0.05  # Exploratory screen, not a multiplicity-adjusted analysis.
PARENT_CONCEPTS = frozenset({"hr_positive", "her2_zero", "organ_function"})


def _favourable(subgroup: dict) -> bool | None:
    """Whether the subgroup's point estimate beats its comparator."""
    hr = subgroup.get("hazard_ratio")
    if hr is None:
        return None
    return hr < 1.0


def _relative(subgroup: dict, groups: list[dict]) -> str | None:
    """Where a subgroup sits relative to the others in its own trial.

    A trial where every subgroup has HR < 1 has no favourability contrast to
    align with: the drug worked everywhere, and "aligned" would be an artefact of
    a threshold that only ever splits at 1.0. Ranking within the trial is the
    question this benchmark can actually answer, and when the groups are too
    close it declines to answer.
    """
    hrs = [g["hazard_ratio"] for g in groups if g.get("hazard_ratio") is not None]
    if len(hrs) < 2:
        return None
    hr = subgroup.get("hazard_ratio")
    lo, hi = min(hrs), max(hrs)
    if hi - lo < 0.05:
        return "indistinct"
    if hr == lo:
        return "more_favourable"
    if hr == hi:
        return "less_favourable"
    return "middle"


def _interaction_significant(subgroup: dict) -> bool:
    p = subgroup.get("interaction_p")
    return p is not None and p < INTERACTION_ALPHA


def _specific_concepts(text: str) -> set[str]:
    """Concepts that identify a subgroup, not the shared parent population.

    Every option in this benchmark sits inside HR+/HER2- disease, so those
    concepts cannot distinguish which subgroup a recommendation leaned toward.
    """
    return concepts(text) - PARENT_CONCEPTS


def score_outcome_alignment(option_set: dict, gold: dict) -> dict:
    recommended = option_set.get("recommendation", {}).get("option_id")
    option = next((o for o in option_set["options"] if o["option_id"] == recommended), None)
    subgroups = [s for s in gold.get("subgroups") or [] if s.get("hazard_ratio") is not None]
    base = dict(benchmark="outcome_alignment", trial_id=gold.get("trial_id"),
                nct_id=gold.get("nct_id"), recommended=recommended)

    if option is None:
        return dict(**base, status="no_recommendation", score=None,
                    detail="no recommended option to align")
    if len(subgroups) < 2:
        return dict(**base, status="insufficient_subgroups", score=None,
                    detail=f"{len(subgroups)} subgroup estimate(s); alignment needs at least two")

    profile = _specific_concepts(" ".join(distinguishing_clauses(option)))
    rows = []
    for subgroup in subgroups:
        overlap = _specific_concepts(" ".join([subgroup.get("label", ""), subgroup.get("source", "")]))
        rows.append(dict(label=subgroup["label"], hazard_ratio=subgroup["hazard_ratio"],
                         favourable=_favourable(subgroup),
                         relative_to_trial=_relative(subgroup, subgroups),
                         interaction_p=subgroup.get("interaction_p"),
                         concept_overlap=sorted(profile & overlap)))

    matched = [r for r in rows if r["concept_overlap"]]
    if not matched:
        return dict(**base, status="no_population_match", score=None,
                    detail="the recommended population does not map onto any reported subgroup",
                    subgroups=rows)

    interactions = [r for r in matched if _interaction_significant(r)]
    if not interactions:
        return dict(**base, status="inconclusive_no_interaction", score=None, subgroups=rows,
                    matched_subgroups=[r["label"] for r in matched],
                    caveat="Different subgroup point estimates alone do not establish differential benefit. No matched interaction signal is supplied.")

    if all(r["relative_to_trial"] == "indistinct" for r in matched):
        return dict(**base, status="indistinct_subgroups", score=None, subgroups=rows,
                    detail="the matched subgroups have nearly identical estimates; "
                           "no favourability contrast to align with")

    more = [r for r in matched if r["relative_to_trial"] == "more_favourable"]
    less = [r for r in matched if r["relative_to_trial"] == "less_favourable"]
    if more and not less:
        score, status = 1.0, "aligned"
    elif less and not more:
        score, status = 0.0, "misaligned"
    else:
        score = len(more) / (len(more) + len(less)) if (more or less) else 0.5
        status = "mixed"

    return dict(**base, status=status, score=round(score, 4), subgroups=rows,
                matched_subgroups=[r["label"] for r in matched],
                interaction_signals=[r["label"] for r in interactions],
                # The plan's caveat, carried in the output so a reader cannot
                # take the number without it.
                caveat=("Alignment compares within-trial subgroup estimates, which are noisy; "
                        "it is agreement, not predictive validity. "
                        + ("No matched subgroup reports a significant interaction test, so a "
                           "difference between subgroups is not established."
                           if not interactions else
                           "At least one matched subgroup reports a significant interaction test; "
                           "treat it as more informative but still exploratory until replicated.")))
