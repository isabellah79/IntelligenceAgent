"""Build amendment gold pairs from two registry snapshots.

    python3 -m benchmark.extract_gold \
        --older "/path/breast_cancer_trials_full_2026-04-14.csv" \
        --newer "/path/breast_cancer/trials.csv" \
        --out benchmark/data/gold/breast_snapshot.json

Writes a gold pack in the format ``amendment.score_retrodiction`` expects. The
pairs are *candidates*: the diff is mechanical, but whether a change is a real
eligibility amendment or a wording edit needs a look, so every pair carries its
diff size and the report is meant to be reviewed before use.

The plan asks for 200 pairs at 120/40/40. Two local snapshots yield far fewer
substantive breast pairs, so this script prints the shortfall rather than
padding the set with trivial edits.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import hashlib

from .dataset import build_amendment_pairs, split_by_start_date

TARGET = dict(train=120, validation=40, test=40)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--older", required=True)
    parser.add_argument("--newer", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--older-date", default="2026-04-14",
                        help="date the older snapshot was pulled; becomes each pair's cutoff_date")
    parser.add_argument("--newer-date", default="", help="date the newer snapshot was pulled")
    parser.add_argument("--condition", default="breast")
    parser.add_argument("--min-change", type=int, default=0,
                        help="drop pairs whose diff touches fewer clauses than this")
    parser.add_argument("--min-similarity", type=float, default=0.0,
                        help="drop pairs whose criteria texts are more similar than this "
                             "(0.99 removes whitespace and single-word edits)")
    args = parser.parse_args(argv)

    pairs = build_amendment_pairs(Path(args.older), Path(args.newer), condition=args.condition,
                                  min_similarity=args.min_similarity,
                                  older_snapshot_date=args.older_date,
                                  newer_snapshot_date=args.newer_date)
    pairs = [p for p in pairs if len(p["change"]["clauses"]) >= args.min_change]
    splits = split_by_start_date(pairs)
    pack = dict(
        notes=dict(
            older=str(args.older), newer=str(args.newer),
            produced_by="benchmark.extract_gold",
            caveat="Registry snapshot diff: shows what changed, not why. Review before use as gold.",
            target=TARGET, produced=len(pairs),
            shortfall={name: TARGET[name] - len(rows) for name, rows in splits.items()},
            source_sha256={"older":hashlib.sha256(Path(args.older).read_bytes()).hexdigest(),
                           "newer":hashlib.sha256(Path(args.newer).read_bytes()).hexdigest()},
            temporal_caveat="Start-date splits are draft partitions, not proof of temporal isolation.",
        ),
        pairs=pairs,
        splits={name:[p["pair_id"] for p in rows] for name,rows in splits.items()},
        accrual=[])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1))
    print(f"{len(pairs)} pairs -> {out}")
    for name, rows in splits.items():
        print(f"  {name}: {len(rows)} (target {TARGET[name]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
