"""Benchmark 3: amendment retrodiction.

The question: given a trial's *original* criteria and public information from
before its amendment, does one of the agent's options contain the change the
sponsor later made?

Gold pairs come in two flavours and the report keeps them apart, because the
evidence behind each differs:

* ``snapshot`` — two registry snapshots of the same trial taken months apart
    diffed locally. This yields amendment candidates until human review confirms
    a substantive change, its direction and relevance.
* ``news`` — the change is recorded in a press release, conference abstract or
  published report (the most current source, as the plan notes). Weaker at the
    clause level. News evidence needs human-normalized target clauses; a URL or
    a shared topic alone cannot establish the direction of an amendment.

Ground truth format (one JSON object per pair)::

    {"pair_id": str, "nct_id": str, "kind": "snapshot"|"news",
     "original_criteria": str, "amended_criteria": str | null,
     "change": {"summary": str,
                "direction": "added"|"removed"|"loosened"|"tightened",
                "clauses": [str],            # the changed criteria, verbatim
                "axis": str},                 # e.g. "brain metastases"
     "evidence": {"source": str, "url": str, "date": str},
     "cutoff_date": str}                      # what the agent was allowed to see
"""
from __future__ import annotations
from datetime import date

from .normalize import best_match, clause_delta, distinguishing_clauses, split_clauses


def derive_change(original: str, amended: str) -> dict:
    """Gold change record from two snapshots of the same trial."""
    delta = clause_delta(original, amended)
    return dict(clauses=delta["added"] + delta["removed"], direction="unreviewed",
                added=delta["added"], removed=delta["removed"], summary="registry snapshot diff")


def score_retrodiction(option_set: dict, gold: dict, agent_cutoff: str | None = None) -> dict:
    """Did any option contain the sponsor's later change?

    Also reports whether the agent *cited* the trial's own original criteria as
    the starting point, since an option that merely restates the original text
    should not earn credit for the change.
    """
    base = dict(benchmark="amendment_retrodiction", pair_id=gold.get("pair_id"), nct_id=gold.get("nct_id"))
    if gold.get("review_status") != "approved":
        return dict(**base, score=None, status="gold_needs_review", detail="A snapshot difference is an unreviewed candidate, not validated gold.")
    cutoff = agent_cutoff or option_set.get("provenance", {}).get("model_knowledge_cutoff")
    evidence_cutoff = option_set.get("provenance", {}).get("evidence_cutoff")
    allowed = gold.get("cutoff_date")
    if not cutoff or not evidence_cutoff or not allowed:
        return dict(**base, score=None, status="temporal_controls_unverified", detail="Supply model_knowledge_cutoff and evidence_cutoff separately from response creation time.")
    try:
        for value in (cutoff, evidence_cutoff, allowed):
            date.fromisoformat(value)
    except (ValueError, TypeError):
        return dict(**base, score=None, status="temporal_controls_unverified", detail="Historical boundaries must be explicit ISO calendar dates.")
    if cutoff > allowed or evidence_cutoff > allowed:
        return dict(**base, score=None, status="potential_temporal_leakage", provenance_leak=True,
                    detail="Knowledge/evidence may postdate the permitted historical boundary. This flags risk, not proof the model saw the amendment.")
    change = gold["change"]
    target_clauses = [c for c in change.get("clauses") or [] if c.strip()]
    original_clauses = split_clauses(gold.get("original_criteria") or "")
    target_clauses = [c for c in target_clauses if not best_match(c, original_clauses)["matched"]]
    if not target_clauses:
        return dict(**base, score=None, status="removal_only_or_rewording_needs_review",
                    detail="No new operative target clause is supplied; absence of old text alone does not prove the agent proposed the intended relaxation.")
    options = option_set["options"]
    per_option = []
    for option in options:
        candidates = distinguishing_clauses(option)
        best = None
        all_targets_matched = True
        for target in target_clauses:
            match = best_match(target, candidates)
            all_targets_matched = all_targets_matched and match["matched"]
            if best is None or match["score"] > best["score"]:
                best = dict(target=target, **match)
        # An option that only re-states the original protocol cannot have
        # anticipated the amendment: it contains nothing the sponsor did not
        # already say. Any clause it carries that the original did not have
        # counts as its own content.
        novel = [c for c in candidates if not best_match(c, original_clauses)["matched"]]
        per_option.append(dict(option_id=option["option_id"],
                               matched=bool(best and all_targets_matched),
                               score=best["score"] if best else 0.0,
                               basis=best["basis"] if best else "none",
                               target=best["target"][:200] if best else "",
                               novel_clauses=len(novel),
                               copy_of_original=bool(candidates) and not novel))

    # Credit requires a real match that is not a transcription of the original.
    genuine = [row for row in per_option if row["matched"] and not row["copy_of_original"]]
    return dict(benchmark="amendment_retrodiction",
                pair_id=gold.get("pair_id"), nct_id=gold.get("nct_id"), kind=gold.get("kind"),
                direction=change.get("direction"),
                score=1.0 if genuine else 0.0,
                status="exploratory_scored",
                matched_options=[row["option_id"] for row in genuine],
                copies_of_original=[row["option_id"] for row in per_option if row["copy_of_original"]],
                best_score=round(max((r["score"] for r in per_option), default=0.0), 4),
                provenance_leak=False,
                cutoff_date=gold.get("cutoff_date"),
                per_option=per_option)
