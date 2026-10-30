"""Citation identity and lexical screening, not an entailment evaluator.

All claims stay in the screening denominator. Low overlap is unresolved support,
not automatically a background citation. Conflict heuristics require review.
`support_score` is a compatibility alias for `screen_score`; verified clinical
support remains unavailable pending source adjudication.
"""
from __future__ import annotations

from collections import Counter
from statistics import mean

from .schema import citation_pairs
from .sources import SourceCatalog, sentence_support

SUPPORT_THRESHOLD = 0.18
CONTEXT_THRESHOLD = 0.10
SUPPORT_WEIGHTS = dict(text_match=1.0, weak_text_match=0.5, unsupported=0.0,
                      context_only=0.0, uncited=0.0, fabricated=0.0, conflict_flag=0.0)


def _support_verdict(claim: str, catalog: SourceCatalog, source_ids: list[str]) -> dict:
    supports = []
    for sid in source_ids:
        evidence = catalog.evidence_text(sid)
        supports.append(dict(source_id=sid, **sentence_support(claim, evidence["text"]),
                             evidence_basis=evidence["basis"]))
    if not supports:
        return dict(verdict="uncited", detail="no source attached", support=[])
    best = max(supports, key=lambda s: s["score"])
    clean = [s for s in supports if not any(s.get(k) for k in ("polarity_conflict", "numeric_conflict", "comparison_conflict", "categorical_conflict"))]
    if clean:
        best = max(clean, key=lambda s: s["score"])
    if not clean:
        verdict, detail = "conflict_flag", "Possible negation or numeric conflict; human source review required."
    elif best["score"] >= SUPPORT_THRESHOLD:
        verdict = "text_match" if best["score"] >= 2 * SUPPORT_THRESHOLD else "weak_text_match"
        detail = f"best evidence overlap {best['score']:.2f}"
        if not best["shared_concepts"]:
            detail += " (wording only, no shared concept)"
    elif best["score"] < CONTEXT_THRESHOLD and not best["shared_concepts"]:
        verdict = "context_only"
        detail = "Low overlap: support is undetermined. This is not proof that the citation is merely background."
    else:
        verdict = "unsupported"
        detail = f"the source does not carry this claim (best overlap {best['score']:.2f})"
    return dict(verdict=verdict, detail=detail, support=supports,
                evidence_basis=best["evidence_basis"])


def score_reference_accuracy(option_set: dict, catalog: SourceCatalog) -> dict:
    scored = []
    for pair in citation_pairs(option_set):
        ids = [s for s in pair["source_ids"] if isinstance(s, str) and s]
        unknown = [s for s in ids if not catalog.known(s)]
        row = {**pair, **_support_verdict(pair["claim"], catalog, [s for s in ids if s not in unknown])}
        if unknown:
            row["verdict"] = "fabricated"
            row["detail"] = f"source id(s) not in catalog: {', '.join(unknown)}"
        row["unknown_source_ids"] = unknown
        row["existence"] = _existence(ids, catalog)
        scored.append(row)

    counts = Counter(row["verdict"] for row in scored)
    checkable = scored  # Do not inflate the score by dropping low-overlap or uncited claims.
    support_rate = (round(mean(SUPPORT_WEIGHTS[r["verdict"]] for r in checkable), 4)
                    if checkable else None)
    fabricated_ids = sorted({sid for row in scored for sid in row["unknown_source_ids"]})
    existence_checked = [r for r in scored if r["existence"] not in ("not_rechecked", "none")]
    unresolvable = sorted({row["existence"] for row in existence_checked
                           if row["existence"] in ("missing", "inaccessible")})

    return dict(
        benchmark="reference_accuracy",
        citations=len(scored),
        # Grounding over the claims that assert something about a source.
        support_score=support_rate,
        screen_score=support_rate,
        verified_support_score=None,
        interpretation="Text-alignment screening, not verified claim support. All claims stay in the denominator; human entailment review is pending.",
        support_denominator=len(checkable),
        fabricated_ids=fabricated_ids,
        fabrication_rate=round(len([r for r in scored if r["unknown_source_ids"]]) / len(scored), 4) if scored else None,
        existence_checked=bool(existence_checked),
        existence_problems=unresolvable,
        counts=dict(counts),
        context_only_share=round(counts.get("context_only", 0) / len(scored), 4) if scored else None,
        by_section=_by_section(scored),
        # The plan's human check: 50 references per version, worst first.
        review_sample=sorted([r for r in scored if r["verdict"] != "text_match"],
                             key=lambda r: r["verdict"] == "context_only")[:50],
        pairs=scored,
    )


def _existence(ids: list[str], catalog: SourceCatalog) -> str:
    """Worst existence status across a claim's citations."""
    if not ids:
        return "none"
    statuses = []
    for sid in ids:
        resolved = catalog.resolve(sid)
        if resolved["status"] == "unverified":
            return "not_rechecked"
        statuses.append(resolved["status"])
    if "missing" in statuses:
        return "missing"
    if "inaccessible" in statuses:
        return "inaccessible"
    return "ok"


def _by_section(scored: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for row in scored:
        grouped.setdefault(row["section"], []).append(row)
    out = {}
    for section, rows in sorted(grouped.items()):
        checkable = rows
        out[section] = dict(count=len(rows),
                            support_score=(round(mean(SUPPORT_WEIGHTS[r["verdict"]] for r in checkable), 4)
                                           if checkable else None),
                            fabrications=sum(1 for r in rows if r["verdict"] == "fabricated"))
    return out
