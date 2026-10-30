"""Population-defense benchmark. Offline by default; live calls require --baselines.

Examples:
  python3 -m benchmark.run --treatments all --out benchmark/reports/repaired.json
  python3 -m benchmark.run --option-set saved-output.json
  python3 -m benchmark.run --run-id ID --db milestone1/.local/demo.sqlite3
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from . import accrual, amendment, baselines, dataset, outcome_alignment, reference_accuracy, rubric
from .sources import SourceCatalog
from .trial_audit import match_trial
from . import scientific

OUT = Path(__file__).with_name("reports")
DEFAULT_CATALOG = Path(__file__).with_name("data") / "sources.json"


def load_catalog(fetch=False):
    try:
        return SourceCatalog.from_demo(fetch=fetch)
    except ImportError:
        if DEFAULT_CATALOG.exists():
            return SourceCatalog.from_json(str(DEFAULT_CATALOG), fetch=fetch)
        raise


def enforce_reference_gate(report):
    if report['evaluation_gate']['status']!='blocked':
        return
    for p in report['defense_rubric']['populations']:
        p['diagnostic_defense_score']=p['score']
        p['diagnostic_scientific_score']=p['scientific_score']
        p.update(score=None,scientific_score=None,gate_status='blocked')
    report['defense_rubric'].update(score=None,scientific_coverage=dict(scored=0,total=len(report['defense_rubric']['populations'])))


def score_one(option_set, catalog, gold=None, weights=None, science_bank=None, science_config=None):
    refs = reference_accuracy.score_reference_accuracy(option_set, catalog)
    safety = rubric.safety_gate(option_set)
    blockers = []
    if refs["fabricated_ids"]:
        blockers.append("Unknown reference IDs")
    if "missing" in refs["existence_problems"]:
        blockers.append("A cited source could not be found online")
    # Heuristics flag a review; they cannot certify clinical safety/entailment.
    gate = dict(status="blocked" if blockers else "review_required", blockers=blockers,
                automated_safety_flags=safety["violations"],
                reason="Clinical criterion safety and claim support require human adjudication before a training reward is usable.")
    checklist = rubric.score_defense_rubric(option_set, weights)
    bank = science_bank or scientific.load_bank()
    defense = scientific.apply_scientific_grading(checklist, option_set, bank, science_config)
    report = dict(option_set=option_set.get("provenance", {}).get("agent"),
                  provenance=option_set.get("provenance", {}), trial=option_set.get("trial", {}),
                  reference_accuracy=refs, defense_rubric=defense,
                  safety_gate=safety, evaluation_gate=gate)
    if gold:
        report["amendment_retrodiction"] = amendment.score_retrodiction(option_set, gold)
    enforce_reference_gate(report)
    return report


def summarise(reports):
    def avg(values):
        values = [v for v in values if v is not None]
        return round(mean(values), 4) if values else None
    scored = [r for r in reports if "error" not in r]
    amendments = [r["amendment_retrodiction"]["score"] for r in scored if "amendment_retrodiction" in r]
    return dict(cases=len(scored), errors=len(reports) - len(scored),
        scientific_judge_errors=sum('science_judge_error' in r for r in scored),
        populations=sum(len(r["defense_rubric"]["populations"]) for r in scored),
        population_defense=avg([r["defense_rubric"]["score"] for r in scored]),
        scientifically_assessed=sum(r["defense_rubric"]["scientific_coverage"]["scored"] for r in scored),
        scientific_strength=avg([p["scientific_score"] for r in scored for p in r["defense_rubric"]["populations"]]),
        checklist_completeness=avg([p["checklist_score"] for r in scored for p in r["defense_rubric"]["populations"]]),
        reference_screen=avg([r["reference_accuracy"]["screen_score"] for r in scored]),
        verified_reference_support=None,
        amendment_retrodiction=avg(amendments), amendment_cases_scored=sum(v is not None for v in amendments),
        amendment_exact_identity_matches=sum(r.get("historical_match", {}).get("status") == "exact_id_match" for r in scored),
        blocked_cases=sum(r["evaluation_gate"]["status"] == "blocked" for r in scored),
        review_required_cases=sum(r["evaluation_gate"]["status"] == "review_required" for r in scored),
        fabricated_sources=sorted({s for r in scored for s in r["reference_accuracy"]["fabricated_ids"]}))


def _saved_run(db_path, run_id):
    # Read-only SQLite URI: inspecting a saved review never creates or updates a DB.
    with sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute("SELECT result FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        raise ValueError("Saved run ID not found")
    return json.loads(row[0])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--baselines", action="store_true", help="Paid calls through the demo's configured provider, including Vertex Gemini")
    parser.add_argument("--treatments", default="elacestrant,capivasertib,tdxd")
    parser.add_argument("--gold")
    parser.add_argument("--option-set", action="append", default=[], help="Normalized option set or saved population-design JSON; repeatable")
    parser.add_argument("--run-id", help="Evaluate an existing saved demo/Gemini run without another model request")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parents[1] / "milestone1/.local/demo.sqlite3"))
    parser.add_argument("--out")
    parser.add_argument("--markdown-out")
    parser.add_argument("--weights", help="JSON rule-weight overrides, fixed before a held-out evaluation")
    parser.add_argument("--review-template", help="Write blank per-population hand-grading entries; null grades must be filled by reviewers")
    parser.add_argument("--science-evidence", help="Independent scientific evidence bank; defaults to the reviewed development snapshot")
    parser.add_argument("--science-weights", help="Four scientific dimension weights and scientific/completeness blend")
    parser.add_argument("--science-judge", action="store_true", help="Paid model scientific judgment using the configured Vertex/provider and independent source facts")
    args = parser.parse_args(argv)
    catalog = load_catalog(args.fetch)
    science_bank = scientific.load_bank(args.science_evidence)
    science_config = scientific.validate_config(json.loads(Path(args.science_weights).read_text()) if args.science_weights else None)
    scientific.enrich_catalog(catalog, science_bank)
    gold_pack = dataset.load_gold(args.gold) if args.gold else None
    weights = rubric.validate_weights(json.loads(Path(args.weights).read_text()) if args.weights else {})
    sets = []
    if args.run_id:
        sets.append(baselines.from_result(_saved_run(args.db, args.run_id)))
    for path in args.option_set:
        sets.append(baselines.from_result(json.loads(Path(path).read_text())))
    if not sets:
        treatments = [c["case_id"] for c in dataset.demo_equivalents()] if args.treatments == "all" else args.treatments.split(",")
        sets = [baselines.from_demo(t.strip(), catalog) for t in treatments if t.strip()]
    reports = []
    path = Path(args.out) if args.out else OUT / f"defense-v3-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.json"
    frozen_dir = path.parent / (path.stem + "-inputs")

    def evaluate(option_set):
        ids = [o["option_id"] for o in option_set["options"]]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("An option set needs nonempty populations with unique option IDs")
        identity = match_trial(option_set, gold_pack)
        row = score_one(option_set, catalog, identity.get("pair"), weights, science_bank, science_config)
        if args.science_judge:
            from .scientific_judge import judge
            try:
                assessments=judge(option_set,science_bank,science_config)
                row['defense_rubric']=scientific.apply_scientific_grading(
                    rubric.score_defense_rubric(option_set,weights),option_set,science_bank,science_config,assessments)
            except Exception as exc:
                row['science_judge_error']=f'{type(exc).__name__}: {exc}'
                for population in row['defense_rubric']['populations']:
                    population.update(score=None,scientific_score=None)
                    population['scientific_assessment'].update(status='judge_failed',score=None,dimensions=[],reason='Requested model judgment failed; no silent rule-score fallback.')
                row['defense_rubric']['score']=None
                row['defense_rubric']['scientific_coverage']['scored']=0
        enforce_reference_gate(row)
        row["historical_match"] = {k:v for k,v in identity.items() if k != "pair"}
        row["frozen_input"] = str(dataset.freeze_option_set(option_set, frozen_dir).resolve())
        nct = option_set.get("trial", {}).get("nct_id")
        for key, function, output_key in (("accrual", accrual.score_accrual_postmortem, "accrual_postmortem"),
                                         ("outcomes", outcome_alignment.score_outcome_alignment, "outcome_alignment")):
            matches = [g for g in (gold_pack or {}).get(key, []) if nct and g.get("nct_id") == nct]
            if len(matches) == 1:
                row[output_key] = function(option_set, matches[0]) if matches[0].get("review_status") == "approved" else dict(score=None, status="gold_needs_review")
        reports.append(row)

    for option_set in sets:
        evaluate(option_set)
        if args.baselines:
            context = option_set["trial"]
            producers = (("general_llm", lambda: baselines.general_llm(context, catalog)),
                         ("single_pass", lambda: baselines.single_pass(context, catalog)),
                         ("one_option", lambda: baselines.one_option(context, catalog, option_set)),
                         ("autotrial_style_prompt", lambda: baselines.autotrial_style(context, catalog)))
            for name, producer in producers:
                try:
                    evaluate(producer())
                except Exception as exc:
                    reports.append(dict(option_set=name, trial=context, error=f"{type(exc).__name__}: {exc}"))
            identity = match_trial(option_set, gold_pack)
            if identity.get("pair"):
                evaluate(baselines.original_criteria(identity["pair_id"], identity["pair"]))
    producers = sorted({r.get("option_set") or "unknown" for r in reports})
    actually_scored = lambda key: any(r.get(key, {}).get("score") is not None for r in reports)
    report = dict(benchmark="scientific-population-defense", schema_version="3.0", created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        scientific_config=science_config, scientific_anchors=scientific.ANCHORS,
        scientific_evidence=dict(sha256=science_bank['sha256'],evidence_as_of=science_bank['evidence_as_of'],
                                 review_status=science_bank['review_status'],cases=science_bank['cases'],sources=science_bank['sources']),
        mode="llm_scientific" if args.science_judge else "evidence_rules",
        reference_mode="fetch" if args.fetch else "offline", sources=catalog.records,
        summary=summarise(reports), by_producer={p:summarise([r for r in reports if (r.get("option_set") or "unknown") == p]) for p in producers},
        cases=reports,
        not_run=[name for name in ("amendment_retrodiction", "accrual_postmortem", "outcome_alignment") if not actually_scored(name)] + ["blinded_expert_review"],
        notes=["Defense grades emphasize scientific strength using a separately curated evidence bank; numerical anchors and weights remain provisional. Endpoint forecasts remain separate.",
               "General-model comparisons need matched inputs, held-out cases and calibrated human grades. These demo cases are not an independent clinical test set.",
               "Known source IDs and lexical overlap do not establish factual support. No automatic training reward is emitted."])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    if args.review_template:
        entries = [dict(file=row["frozen_input"], option_id=p["option_id"],
                        grades={r["rule"]:None for r in p["results"]},
                        scientific_grades={k:None for k in scientific.DIMENSIONS},
                        reviewer=None, notes="", scientific_scale="Ordinal 0-4, using the v3 anchored rubric")
                   for row in reports if "error" not in row for p in row["defense_rubric"]["populations"]]
        Path(args.review_template).parent.mkdir(parents=True, exist_ok=True)
        Path(args.review_template).write_text(json.dumps(entries, ensure_ascii=False, indent=1))
    if args.markdown_out:
        from .report import render_markdown
        Path(args.markdown_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown_out).write_text(render_markdown(report))
    print(f"wrote {path}")
    print(json.dumps(report["summary"], indent=1))
    return 1 if any("error" in r or 'science_judge_error' in r for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
