"""Audit historical candidates without inventing a match to a prospective design.

Registry identity: exact NCT ID. Source-trial identity, target-population relevance,
and a verified substantive amendment are separate questions. No name/drug fuzzy
match authorizes historical scoring.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from .dataset import norm_text

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TRIALS = {
    "elacestrant": ("EMERALD", "NCT03778931", "elacestrant"),
    "capivasertib": ("CAPItello-291", "NCT04305496", "capivasertib"),
    "tdxd": ("DESTINY-Breast06 / DB-06", "NCT04494425", "deruxtecan"),
}


def match_trial(option_set: dict, gold_pack: dict | None) -> dict:
    if not gold_pack:
        return dict(status="not_requested", reason="No historical gold pack supplied.")
    nct = option_set.get("trial", {}).get("nct_id")
    if not nct:
        return dict(status="unmatched", reason="This is a prospective population-design case, with no historical target NCT ID. Source-trial names do not substitute for a target trial.")
    if not re.fullmatch(r"NCT\d{8}", nct):
        return dict(status="invalid_id", reason="Target NCT ID must use the registry identifier format.")
    pairs = [p for p in gold_pack.get("pairs", []) if p.get("nct_id") == nct]
    if not pairs:
        return dict(status="unmatched", nct_id=nct, reason="No exact NCT ID match in the supplied amendment pack.")
    if len(pairs) > 1:
        requested = option_set.get("trial", {}).get("pair_id")
        pairs = [p for p in pairs if p.get("pair_id") == requested]
    if len(pairs) != 1:
        return dict(status="ambiguous", nct_id=nct, reason="Multiple amendments exist; supply an explicit pair_id.")
    return dict(status="exact_id_match", nct_id=nct, pair_id=pairs[0]["pair_id"], pair=pairs[0],
                reason="Exact target NCT ID only. Relevance, amendment review, and temporal controls still require separate checks.")


def _read(path: Path) -> tuple[dict, dict]:
    raw = path.read_bytes()
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [r.get("nctId") for r in rows if r.get("nctId")]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate NCT IDs in {path.name}; identity join is ambiguous")
    return dict(file=str(path), sha256=hashlib.sha256(raw).hexdigest(), rows=len(rows),
                latest_record_update=max((r.get("lastUpdateDate", "") for r in rows), default=""),
                pull_date_verified=False), {r["nctId"]: r for r in rows if r.get("nctId")}


def _text(row: dict) -> str:
    return (row.get("includeCriteria") or "") + "\n" + (row.get("excludeCriteria") or "")


def scope_screen(row: dict) -> dict:
    title = row.get("bTitle", "")
    text = (title + " " + _text(row)).lower().replace("−", "-")
    hr = bool(re.search(r"(?:hr|er)\s*\+|(?:hormone|estrogen) receptor[- ]positive", text))
    her2 = bool(re.search(r"her[- ]?2\s*[-/]|her[- ]?2[- ]negative", text))
    metastatic = bool(re.search(r"metastatic|advanced", text))
    explicit_post = bool(re.search(r"after.{0,50}cdk|post[- ]cdk|progress.{0,80}cdk", text))
    return dict(hr_positive_mentioned=hr, her2_negative_mentioned=her2,
                advanced_disease_mentioned=metastatic, post_cdk_wording=explicit_post,
                status="scope_review_candidate" if all((hr, her2, metastatic, explicit_post)) else "scope_not_confirmed",
                interpretation="Keyword triage only; trial-wide mixed cohorts and the actual prior-treatment rules need oncology review.")


def audit(pack: dict, older: Path, newer: Path) -> dict:
    old_manifest, before = _read(older)
    new_manifest, after = _read(newer)
    rows = []
    for pair in pack.get("pairs", []):
        nct = pair["nct_id"]
        old, new = before.get(nct), after.get(nct)
        rows.append(dict(nct_id=nct, registry_url=f"https://clinicaltrials.gov/study/{nct}",
            title=pair.get("title", ""), present_in_both=old is not None and new is not None,
            original_text_matches_export=bool(old and norm_text(_text(old)) == norm_text(pair.get("original_criteria", ""))),
            amended_text_matches_export=bool(new and norm_text(_text(new)) == norm_text(pair.get("amended_criteria", ""))),
            scope=scope_screen(new or {}), review_status=pair.get("review_status", "unreviewed_candidate"),
            changes_human_verified=bool(pair.get("review_status") == "approved"),
            local_change_count=len(pair.get("change", {}).get("clauses", []))))
    sources = []
    for treatment, (name, nct, drug) in SOURCE_TRIALS.items():
        row = after.get(nct) or {}
        identity = drug in (row.get("interventionName", "") + " " + row.get("bTitle", "")).lower()
        sources.append(dict(treatment_id=treatment, source_trial_name=name, nct_id=nct,
            registry_url=f"https://clinicaltrials.gov/study/{nct}", title=row.get("bTitle"),
            local_identity_check=identity, in_amendment_candidates=any(p["nct_id"] == nct for p in rows),
            role="Evidence source only; never assigned as the prospective target trial."))
    return dict(identity_join="Exact nctId equality between the two local CSV exports.",
        original_selection="Breast condition text, phase containing PHASE2/PHASE3, and detected eligibility-text changes. This did not restrict to HR+/HER2- post-CDK4/6.",
        source_manifests=dict(older=old_manifest, newer=new_manifest),
        date_note="April 14 is recorded in the older filename. May 26 is reported by the previous README; a latest record-update date is not proof of CSV pull date.",
        candidates=rows, source_trial_links=sources,
        summary=dict(candidates=len(rows), present_in_both=sum(r["present_in_both"] for r in rows),
                     scope_review_candidates=sum(r["scope"]["status"] == "scope_review_candidate" for r in rows),
                     approved=sum(r["changes_human_verified"] for r in rows)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--older")
    parser.add_argument("--newer")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    pack = json.loads(Path(args.gold).read_text())
    older = Path(args.older or pack["notes"]["older"])
    newer = Path(args.newer or pack["notes"]["newer"])
    result = audit(pack, older.resolve(), newer.resolve())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps(result["summary"], indent=1))


if __name__ == "__main__":
    main()
