"""The option-set schema the benchmark grades, and a normaliser for agent output.

The benchmark must judge the demo, a baseline and a future agent the same way,
so all of them are reduced to one shape here. The shape mirrors the plan's
"What each option contains" table: population, criteria, pros, cons, estimates,
references.

An option set is::

    {
      "trial": {"nct_id": str, "condition": str, "phase": str,
                "drug": str, "primary_endpoint": str, "line_of_therapy": str},
      "options": [
        {"option_id": str,
         "population": str,                 # the one-line description
         "axes": [str],                     # named axes the option varies on
         "inclusion": [{"text": str, "purpose": str, "source_ids": [str]}],
         "exclusion": [...same...],
         "pros": [{"text": str, "source_ids": [str]}],
         "cons": [{"text": str, "source_ids": [str]}],
         "estimates": {"eligible_share": {"low": float, "high": float, "source_ids": [str]},
                       "effect_direction": {"text": str, "source_ids": [str]}},
         "references": [{"source_id": str, "supports": str}]}
      ],
      "recommendation": {"option_id": str, "defense": [{"text": str, "source_ids": [str]}]},
      "provenance": {"agent": str, "model": str, "created": str, "tools": [str]}
    }

``purpose`` is one of ``scope`` (restates the parent population), ``efficacy``,
``evidence_alignment``, ``safety``, ``generalizability`` or ``design``.
"""
from __future__ import annotations

from copy import deepcopy

PURPOSES = {"scope", "efficacy", "evidence_alignment", "safety", "generalizability", "design"}


def _rows(value) -> list[dict]:
    """Coerce a list of strings or dicts into ``{"text", "purpose", "source_ids"}`` rows."""
    rows = []
    for item in value or []:
        if isinstance(item, str):
            rows.append(dict(text=item.strip(), purpose=None, source_ids=[]))
        elif isinstance(item, dict):
            if not isinstance(item.get("source_ids") or [], list):
                raise ValueError("source_ids must be a list of source IDs")
            row = deepcopy(item)
            row.update(text=(item.get("text") or "").strip(), purpose=item.get("purpose"),
                       source_ids=[s for s in (item.get("source_ids") or []) if isinstance(s, str)])
            rows.append(row)
    return [r for r in rows if r["text"]]


def normalise_option(raw: dict, index: int = 0) -> dict:
    return dict(
        option_id=str(raw.get("option_id") or raw.get("id") or f"option_{index + 1}"),
        population=(raw.get("population") or raw.get("title") or "").strip(),
        axes=[a for a in (raw.get("axes") or []) if isinstance(a, str)],
        inclusion=_rows(raw.get("inclusion")),
        exclusion=_rows(raw.get("exclusion")),
        pros=_rows(raw.get("pros")),
        cons=_rows(raw.get("cons")),
        defense=_rows(raw.get("defense")),
        protocol_pending=_rows(raw.get("protocol_pending")),
        unclassified_criteria=_rows(raw.get("unclassified_criteria")),
        evidence_context=deepcopy(raw.get("evidence_context") or {}),
        estimates=deepcopy(raw.get("estimates") or {}),
        references=[dict(source_id=r.get("source_id"), supports=r.get("supports", ""))
                    for r in (raw.get("references") or []) if isinstance(r, dict)],
    )


def normalise_option_set(raw: dict) -> dict:
    """Coerce any producer's output into the graded shape."""
    out = dict(trial=deepcopy(raw.get("trial") or {}),
               options=[normalise_option(o, i) for i, o in enumerate(raw.get("options") or [])],
               provenance=deepcopy(raw.get("provenance") or {}))
    rec = raw.get("recommendation") or {}
    defence = rec.get("defense") or rec.get("reason") or rec.get("defence") or []
    if isinstance(defence, str):
        defence = [{"text": defence, "source_ids": rec.get("source_ids") or []}]
    out["recommendation"] = dict(option_id=rec.get("option_id") or rec.get("population_id"),
                                 defense=_rows(defence))
    return out


def citation_pairs(option_set: dict) -> list[dict]:
    """Every (claim, cited source ids) pair in an option set.

    Each pair is one unit of the reference-accuracy check: the claim text and
    the sources attached to it.
    """
    pairs = []
    for option in option_set.get("options") or []:
        oid = option["option_id"]
        for section in ("inclusion", "exclusion", "pros", "cons", "defense", "protocol_pending", "unclassified_criteria"):
            for row in option.get(section) or []:
                pairs.append(dict(option_id=oid, section=section, claim=row["text"],
                                  source_ids=row["source_ids"]))
        for name, value in (option.get("estimates") or {}).items():
            if isinstance(value, dict) and value.get("status") != "unavailable" and value:
                # Numbers are not checkable text. Use the estimate's own wording
                # when it has some, otherwise its label, so the support check
                # compares words rather than a range format.
                text = value.get("text") or value.get("note") or name.replace("_", " ")
                pairs.append(dict(option_id=oid, section="estimates", claim=text,
                                  source_ids=list(value.get("source_ids") or []),
                                  kind="estimate"))
        for reference in option.get("references") or []:
            # A bibliography-only invented ID must not escape the reference gate.
            sid = reference.get("source_id")
            if sid and sid not in {s for p in pairs if p["option_id"] == oid for s in p["source_ids"]}:
                pairs.append(dict(option_id=oid, section="bibliography", claim=str(reference.get("supports") or "Reference listed without an attached claim"), source_ids=[sid]))
    rec = option_set.get("recommendation") or {}
    for row in rec.get("defense") or []:
        pairs.append(dict(option_id=rec.get("option_id"), section="recommendation",
                          claim=row["text"], source_ids=row["source_ids"]))
    return pairs


def _estimate_text(name: str, value: dict) -> str:
    if "low" in value or "high" in value:
        return f"{name}: {value.get('low')}-{value.get('high')}"
    return f"{name}: {value}"


def cited_source_ids(option_set: dict) -> set[str]:
    return {sid for pair in citation_pairs(option_set) for sid in pair["source_ids"]}
