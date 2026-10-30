"""Benchmark datasets: load, split, and freeze option sets.

The plan asks for 200 phase 2/3 trials with an eligibility amendment, split by
start date into 120 train / 40 validation / 40 test. This module builds that
table where the data allows and is explicit where it does not.

Two inputs are supported:

* Registry snapshots — two CSVs of ClinicalTrials.gov records taken at different
  dates. Diffing them finds trials whose criteria text changed. Checked in:
  ``benchmark/data/snapshots.json`` names the files.
* Gold packs — hand-built JSON files under ``benchmark/data/gold/`` for the
  news-based and accrual pairs, which need reading rather than diffing.

Nothing here downloads anything. ``scripts/extract_gold.py`` produces snapshot
gold; the news packs are written by a person and carry their source URLs.
"""
from __future__ import annotations

import csv
import json
import re
import hashlib
from pathlib import Path

from .normalize import clause_delta

DATA = Path(__file__).with_name("data")


def resolve_frozen_input(report_path: str | Path, reference: str | Path) -> Path:
    """Resolve portable fixture paths against their report, not the shell cwd."""
    reference = Path(reference)
    return reference if reference.is_absolute() else Path(report_path).resolve().parent / reference


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        rows = list(csv.DictReader(handle))
    ids = [r.get("nctId") for r in rows if r.get("nctId")]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate NCT IDs prevent an unambiguous snapshot join")
    return rows


def build_amendment_pairs(older: Path, newer: Path, *, phases: tuple[str, ...] = ("PHASE2", "PHASE3"),
                          condition: str = "breast", min_similarity: float = 0.0,
                          older_snapshot_date: str = "", newer_snapshot_date: str = "") -> list[dict]:
    """Trials whose criteria text changed between two registry snapshots.

    ``min_similarity`` filters near-identical edits (typos); 0 keeps everything
    the whitespace-folded comparison finds different.

    ``older_snapshot_date`` becomes the pair's ``cutoff_date``: the last date on
    which the original criteria were the whole public record. An agent whose
    knowledge or browsing reaches past it could have copied the amendment rather
    than reasoned to it, which ``amendment.score_retrodiction`` reports as a leak.
    """
    before = {r.get("nctId"): r for r in _read_csv(older) if r.get("nctId")}
    after = {r.get("nctId"): r for r in _read_csv(newer) if r.get("nctId")}
    pairs = []
    for nct, row in after.items():
        old = before.get(nct)
        if not old:
            continue
        old_text = (old.get("includeCriteria") or "") + "\n" + (old.get("excludeCriteria") or "")
        new_text = (row.get("includeCriteria") or "") + "\n" + (row.get("excludeCriteria") or "")
        if not norm_text(old_text) or not norm_text(new_text):
            continue
        if norm_text(old_text) == norm_text(new_text):
            continue
        phase = (row.get("phases") or "").upper().replace(" ", "")
        if phases and not any(p in phase for p in phases):
            continue
        if condition and condition.lower() not in (row.get("conditions") or "").lower():
            continue
        delta = clause_delta(old_text, new_text)
        if not delta["added"] and not delta["removed"]:
            continue
        if min_similarity and _similarity(old_text, new_text) > min_similarity:
            continue
        pairs.append(dict(
            pair_id=f"{nct}-snapshot",
            nct_id=nct,
            kind="snapshot",
            title=row.get("bTitle") or row.get("oTitle") or "",
            phase=phase,
            start_date=row.get("startDate") or "",
            original_criteria=old_text.strip(),
            amended_criteria=new_text.strip(),
            original_inclusion=old.get("includeCriteria") or "",
            original_exclusion=old.get("excludeCriteria") or "",
            amended_inclusion=row.get("includeCriteria") or "",
            amended_exclusion=row.get("excludeCriteria") or "",
            change=dict(summary="registry snapshot diff",
                        direction="unreviewed",  # Inclusion and exclusion additions have different meanings.
                        clauses=delta["added"] + delta["removed"],
                        # Kept separately so a reviewer can see which side of the
                        # amendment each clause came from, and so the retrodiction
                        # scorer can tell a widening from a new restriction.
                        added=delta["added"], removed=delta["removed"],
                        axis=""),
            evidence=dict(source="ClinicalTrials.gov snapshots", url=f"https://clinicaltrials.gov/study/{nct}",
                          date=row.get("lastUpdateDate") or ""),
            # The last date on which the original criteria were the whole public
            # record. An agent with knowledge past this could have seen the change.
            cutoff_date=older_snapshot_date or None,
            review_status="unreviewed_candidate",
            snapshot_dates=dict(older=older_snapshot_date or None, newer=newer_snapshot_date or None),
            source_files=dict(older=str(older), newer=str(newer)),
        ))
    return pairs


def _similarity(a: str, b: str) -> float:
    import difflib
    return difflib.SequenceMatcher(None, norm_text(a), norm_text(b)).ratio()


def split_by_start_date(pairs: list[dict], fractions=(0.6, 0.2, 0.2)) -> dict[str, list[dict]]:
    """Train/validation/test by start date, as the plan specifies.

    This is only a draft partition. Trial start date alone cannot prevent
    amendment/publication leakage; evidence dates and model knowledge need review.
    """
    ordered = sorted(pairs, key=lambda p: (p.get("start_date") or "9999", p["pair_id"]))
    n = len(ordered)
    n_train = int(n * fractions[0])
    n_val = int(n * fractions[1])
    return dict(train=ordered[:n_train],
                validation=ordered[n_train:n_train + n_val],
                test=ordered[n_train + n_val:])


def load_gold(path: str | Path) -> dict:
    """A gold pack: ``{"pairs": [...], "accrual": [...], "notes": {}}``."""
    payload = json.loads(Path(path).read_text())
    payload.setdefault("pairs", [])
    payload.setdefault("accrual", [])
    payload.setdefault("notes", {})
    return payload


def freeze_option_set(option_set: dict, out_dir: Path) -> Path:
    """Write a produced option set to disk with a content hash.

    Freezing matters for a benchmark: scoring must be reproducible against the
    exact bytes the agent produced, not a re-run that may differ.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(option_set, ensure_ascii=False, sort_keys=True, indent=1)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
    name = f"{option_set.get('trial', {}).get('nct_id') or 'trial'}-{digest}.json"
    path = out_dir / name
    path.write_text(raw)
    return path


def demo_equivalents() -> list[dict]:
    """Gold-shaped records derived from the demo's own worked scenario.

    The demo designs populations for one treatment at a time inside a fixed
    parent population. This turns each of its treatments into a benchmark case
    so the harness can be scored today, before the 200-trial set exists.
    """
    from milestone1.populations import propose

    result = propose()
    cases = []
    for treatment in result["treatments"]:
        cases.append(dict(
            case_id=treatment["id"],
            title=treatment["title"],
            condition="HR+/HER2- metastatic breast cancer after endocrine + CDK4/6",
            phase="Phase 3 (post-CDK4/6 setting)",
            drug=treatment["title"],
            primary_endpoint="PFS",
            line_of_therapy="post-CDK4/6",
            populations=len(treatment["populations"]),
            source_ids=treatment["source_ids"],
        ))
    return cases
