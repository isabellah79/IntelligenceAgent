# Scientific population-defense benchmark, version 3

## Distributable oncology review form

Open `reports/oncology-review.html` in a modern browser, or send that single file
to the reviewer. All scripts, styles and nine population drafts are embedded;
the form needs no server, login, API access or companion files. Reference links
open the source websites when clicked.

The reviewer enters four 0–4 ratings, comments, suggested criteria changes and
an optional treatment-specific population preference. AI grades and endpoint
forecasts start hidden. Revealing AI records exposure, preserving completed
pre-AI ratings separately from later assisted edits.

- **Save review HTML** downloads a self-contained filled copy to return.
- **Export review JSON** preserves the entire review for import/resumption.
- **Export independent ratings** produces calibration-compatible entries only
  for complete numerical ratings saved before AI exposure. Unassessable or
  assisted-only ratings stay in the full review, not the calibration export.
- Browser autosave is best-effort; download a copy before closing. The form
  does not upload reviewer details or feedback.

The distributable contains portable input hashes instead of local filesystem
paths or cloud-project configuration. `scientific_calibration.py` matches these
full SHA-256 identities to the original frozen inputs on the researcher's machine.

The checked-in review example includes its three frozen inputs, referenced
relative to the scorecard, so it can be regenerated in another checkout. Other
local run outputs and caches are ignored. To review the HTML from GitHub,
download `reports/oncology-review.html` and open it in a modern browser; GitHub's
source-file view does not execute the form.

Regenerate the page after updating its source report:

```sh
python3 -m benchmark.review_html \
  --report benchmark/reports/scientific-defense-v3-gemini.json \
  --out benchmark/reports/oncology-review.html
```

Test the portable state and independent-rating logic with
`node --test benchmark/review_page/state.test.js`. Node is needed only for those
developer tests, not for reviewers opening the HTML file.

The primary unit is one scientifically defended population within a treatment
strategy. The v3 defense grade is **80% scientific assessment + 20% completeness**.
The conditional primary-endpoint forecast remains separate and contributes no
weight. A stronger defense is not an individual benefit probability.

The benchmark now prioritizes the defense rubric from the proposal's Evaluation
design. Historical amendments, accrual and outcomes remain secondary, optional
checks; they are never treated as clinical gold merely because a file exists.

## Run locally

From `demo-source`:

```sh
python3 -m benchmark.run --treatments all \
  --gold benchmark/data/gold/breast_snapshot.json \
  --science-weights benchmark/data/scientific_weights_v3.json \
  --out benchmark/reports/scientific-defense-v3.json \
  --markdown-out benchmark/reports/scientific-defense-v3.md \
  --review-template benchmark/reports/scientific-hand-grades-v3-blank.json
python3 -m unittest discover -s benchmark/tests -t . -v
```

These commands make no model or network requests. Inputs are frozen beside the
report with SHA-256-derived filenames. The Markdown report shows per-population
scores, failed checks, endpoint forecasts, operational differences and references.

Evaluate a normalized option set or an existing saved demo/Gemini output:

```sh
python3 -m benchmark.run --option-set saved-population-output.json --out benchmark/reports/saved.json
python3 -m benchmark.run --run-id YOUR_RUN_ID --out benchmark/reports/saved-gemini.json
```

The saved-Gemini adapter evaluates its actual recommendation and the supplied
population drafts. Suggested criterion edits are not silently applied; this is
not a claim that Gemini generated a new population library.

## Scientific grading: the primary measurement

| Dimension | Weight within scientific assessment | What is evaluated |
|---|---:|---|
| Evidence strength | 35% | Primary/co-primary randomized results versus exploratory subgroups, noncomparative cohorts, or unsupported extrapolation. |
| Population applicability | 25% | Match to the source cohort, prior CDK4/6 exposure, added restrictions, treatment line, comparator and PFS endpoint. |
| Selection justification | 25% | Scientific basis for each selection rule; trial-defined selection versus an unvalidated enrichment or access hypothesis. |
| Tradeoffs | 15% | Criterion-specific advantages, exclusions, uncertainty, recruitment/generalizability costs and mitigations. |

Each uses an anchored ordinal grade from 0 to 4. All anchors are stored in the
report and documented in [SCIENTIFIC_GRADING.md](SCIENTIFIC_GRADING.md). Weights
and scores are provisional judgments; they are not learned efficacy probabilities.
`--science-weights` accepts the versioned blend and four dimension weights.

`scientific.py` applies an explicit evidence policy to separately stored source
facts in `data/scientific_evidence_v3.json`. The fact bank contains study design,
analysis status, source setting and supported selection scope, **not per-option
scores**. Matching uses operative criteria rather than option IDs, agent/model
identity, or self-declared reference/hypothesis labels. Extra unsupported
restrictions cannot inherit the parent study's evidence grade. Unknown mappings
are unassessed and yield no final score. An evidence bank newer than a historical
cutoff is not used.

The literature snapshot was checked against primary publications and official
assessments on October 30, 2026. Its clinical interpretation still needs oncology
review; it is not a complete systematic review. Missing evidence in this bank does
not mean no evidence exists anywhere.

A second assessment mode uses the configured provider, including Vertex Gemini:

```sh
python3 -m benchmark.run --treatments elacestrant,capivasertib,tdxd \
  --science-judge --out benchmark/reports/scientific-gemini.json \
  --markdown-out benchmark/reports/scientific-gemini.md
```

This explicitly makes paid calls: one scientific-review request per treatment.
The judge receives the four anchored dimensions, source facts and submitted
criteria/reasons/pros/cons. Producer identity, self-labeled evidence status and
numeric endpoint forecasts are withheld. It returns criterion-linked explanations
and source IDs. Raw grades, evidence ceilings, model metadata and input hash are
recorded; invented sources, missing dimensions and wrong-candidate criteria are
rejected. Evidence ceilings prevent exploratory analyses from being upgraded by
confident model prose. A requested judge failure is reported without a silent
rule-score fallback. Agreement with clinicians has not been established.

The original 15 completeness checks remain in `rubric.py`, now contributing 20%
of the default final score. `--weights` controls those checklist weights only.
The report keeps scientific, completeness and final grades visible separately.
Changing a subgroup's endpoint forecast does not change any scientific grade.

Multi-option design remains separate: pairwise operative criteria, named axes and
recommendation defense. Single-option baselines share the same population-quality
scale. Equal scientific assessments may tie. All comparisons refer to research
population defenses, not cross-treatment efficacy rankings.

Unknown prevalence is acceptable when explicitly marked unavailable. Conditional
endpoint forecasts keep their assumed HR, comparator and unavailable reason.

## Reference screening and the gate

- All claims stay in the screening denominator, including uncited and low-overlap
  claims. Low overlap no longer proves a claim is merely methodological context.
- Shared wording is called `text_match`, not verified support. Negation, numeric,
  comparison-direction and biomarker-state conflicts are flagged for review.
- `reference_screen` is lexical screening. `verified_reference_support` remains
  null until actual source adjudication is implemented. It is not medical accuracy.
- `--fetch` checks URLs and uses PubMed abstracts where available; other sources
  may still use catalog descriptions. Network failures are not proof of fabrication.
- A nonexistent catalog ID, including an ID only in the bibliography, blocks the
  evaluation gate. Otherwise the gate remains `review_required`: automatic checks
  do not certify source entailment or clinical safety. No training reward is emitted.

Older v1/v2 scorecards use different rules/denominators and cannot be compared with v3.

## Trial origins and matching

See [TRIAL_PROVENANCE.md](TRIAL_PROVENANCE.md) for exact source paths, examples
and why the existing 20 candidates are not a post-CDK4/6 validation dataset.

```sh
python3 -m benchmark.trial_audit \
  --gold benchmark/data/gold/breast_snapshot.json \
  --out benchmark/reports/trial-audit.json
```

The audit records file hashes, record counts, exact NCT joins, agreement of saved
criteria with CSV text, and keyword triage for scope. Triage is not clinical review.
Historical scoring requires an explicit target NCT ID, one unambiguous amendment,
reviewed gold, and separate model-knowledge/evidence cutoffs. Response creation
time is not a knowledge cutoff. Missing temporal controls mean no score; a later
cutoff flags leakage risk rather than proving the model memorized the answer.

The demo designs prospective cohorts. An evidence trial is not automatically its
historical target. Neither a drug name nor an acronym assigns an NCT ID. A supplied
pack with no matching evaluated case remains listed as `not_run`.

`extract_gold.py` now preserves inclusion/exclusion sections, file hashes and
draft split membership; `--min-change` is applied. Additions alone do not establish
whether eligibility tightened or loosened. Extraction yields unreviewed candidates.
Start-date splits alone do not establish temporal isolation. The existing 20-pair
file is retained as the original artifact, interpreted as unreviewed by default.

## General-model comparisons and clinician calibration

```sh
python3 -m benchmark.run --baselines --treatments elacestrant
```

This explicitly makes paid calls through the demo's configured provider, including
Vertex Gemini. The general-model baseline gets the same context, source-catalog
excerpts, requested output fields and three-option task. Its provenance records
the provider and model actually called. Other ablations are single pass, selection
of one existing option, and an imitation-style prompt. The last is not the actual
AutoTrial system. The original-protocol adapter runs only with an exact historical
case match and preserves unclassified criteria when section identity is unavailable.
One baseline failure is reported independently and does not suppress later ones.

`judge.py` can grade the common rules per population using the configured provider.
It grades supplied text, not independently fetched clinical evidence. The blank
hand-grading file contains Boolean completeness grades and separate 0–4 scientific
grades. Oncologists must replace nulls before the corresponding calibration. Multi-population files require an explicit `option_id` per grade row.

```sh
python3 -m benchmark.judge --calibrate completed-hand-grades.json --out calibration.json
```

Agreement and Cohen's kappa measure judge/human consistency, not clinical validity.
Low agreement can reflect judge errors, annotation differences, unclear rules or
label prevalence. A second judge and blinded expert comparisons remain necessary
before a superiority claim. Keep related trial/subgroup examples together in the
same data split and reserve independent test cases before tuning prompts or weights.

The four scientific dimensions have their own **ordinal** calibration:

```sh
python3 -m benchmark.scientific_calibration \
  --human-grades completed-scientific-grades.json \
  --report benchmark/reports/scientific-gemini.json \
  --out benchmark/reports/scientific-calibration.json
```

This makes no model requests. It reports per-dimension mean absolute error, exact
agreement, agreement within one grade, and quadratic weighted kappa. Exact frozen
input path plus option ID links human and predicted grades. Human grades are the
reference; matching the rule-based policy is not proof of scientific quality.

The current 13 treatment cases/39 populations are development examples, not a
held-out test set. No fine-tuning or improved-over-general-LLM result is implied.

## Secondary evaluations

- Amendment scoring is exploratory and requires reviewed, date-controlled cases.
  It requires the new operative targets to match, not an arbitrary old clause.
  Removal-only/rewording cases need further structured review.
- Accrual scoring needs reviewed restrictive-criterion annotations and an exact
  target-trial match. A stop reason alone does not establish which criterion caused it.
- Outcome alignment needs reviewed subgroup data. Point estimates without a
  matched interaction signal return inconclusive, rather than a benefit ranking.
  Even an interaction signal is exploratory; multiplicity and subgroup mapping
  require expert review.
- Blinded oncologist preference and clinical validity are not yet measured.
