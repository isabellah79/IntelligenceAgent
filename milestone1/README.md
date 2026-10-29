# Milestone 1 Population design lab

For each treatment in **HR+/HER2− metastatic breast cancer after progression on
endocrine therapy plus a CDK4/6 inhibitor**, propose and defend candidate patient
subgroups and translate them into trial inclusion and exclusion criteria.

The unit of analysis is **treatment × population × comparator × endpoint**.
This workflow designs research populations; it does not select a treatment for
an individual patient. Its proposals are protocol drafts with scientific and
clinical review still required.

## Run

```sh
python3 -m milestone1.server
```

Open http://127.0.0.1:8765. Python 3.10+ and the standard library are sufficient
for curated proposals. The existing Vertex Gemini setup remains configured.

## Review the updated demo

1. Select a treatment and study emphasis. The parent post-CDK4/6 population is
   fixed; there is no fictional individual patient to match.
2. Compare **three candidate populations per treatment**, across 13 treatment
   strategies. The overview lists all 39 candidates. Gedatolisib is explicitly
   the triplet; capecitabine is the specified chemotherapy example.
3. Inspect each candidate's cohort-defining inclusion/exclusion draft, the
   purpose and reason for each criterion, supporting references, pros/cons and
   unresolved protocol details. Evidence-supported, exploratory and hypothetical
   restrictions are distinguished. Candidates can overlap.
4. Click **Review populations with Gemini** for a real model review of the
   selected treatment's three drafts. Gemini compares the populations, defends a
   starting draft and may propose criterion revisions or evidence-weight changes.
5. Select, propose an edit to, or reject a population. Model criterion revisions
   can be copied into a researcher-reviewed draft amendment. These records retain
   the original criteria and reasons; a proposed amendment does not inherit an HR.
6. Apply reviewed numerical weights explicitly to recalculate with Python.
   This operation does not make another model request. Criterion revisions remain
   review records rather than automatically validated protocol changes.
7. Export JSON or use **Reopen saved review** to restore the exact original
   evidence, candidate populations, assumptions, model response and feedback.

## Conditional endpoint scenarios

The original `forecast/forecast.py` engine is reused. Method A adjusts prior odds
with analyst-assigned evidence multipliers, damped by `factor ** evidence_strength`.
Method B uses a hypothetical true HR, event count and z threshold in the original
1:1 proportional-hazards normal approximation. The final score is
`blend_a*A + (1-blend_a)*B`. With no prior, only B is calculated.

Defaults remain 200 events, z=1.96, neutral analyst prior 0.50, evidence strength
0.5 and A/B blend 0.5/0.5. These choices and multipliers are provisional, not
numerical estimates established by the cited studies.

An effect is attached to a **specific candidate population and comparator**:

- EMERALD ESR1-mutated HR 0.55, exploratory duration-defined HR 0.41 and overall
  HR 0.70 remain separate records. The overall result does not prove benefit in
  ESR1-wild-type disease. A subgroup result is not a confirmed predictive rule.
- Published HRs from mixed prior-CDK4/6 or indirect settings do not automatically
  transfer to the exclusively post-CDK4/6 target. An explicit extrapolation switch
  or a population-specific analyst assumption is required.
- Hypothetical restrictions do not inherit another candidate's efficacy estimate.
  Missing comparative effects remain unestimated. An analyst can supply a
  hypothetical HR **and comparator** to investigate that particular design.
- Medians are not converted into HRs. HER2-low results are not assigned to
  HER2-ultralow. The DB06 early-progression post hoc comparison retains its own
  population and reported medians without an invented HR.
- The historical VIKTORIA-1 and Bria-ABC examples remain available in a separate
  expandable section. Their target and original caveats are preserved.

Scores do not establish the optimal cohort, head-to-head treatment superiority,
an individual benefit probability, or prospectively validated trial success.

## Gemini on Vertex AI

`vertex_settings.json` configures `gemini-3.8-flash`, project
`rag-project-494802`, global endpoint. The server uses the existing gcloud ADC
sign-in. For a new machine:

```sh
gcloud auth application-default login
gcloud auth application-default set-quota-project rag-project-494802
```

Public environment overrides are documented in `.env.example`. Never store
credentials in the repo or browser. TLS verification remains enabled.

Opening/reopening the workspace and curated calculations make no model request.
An explicit Gemini review sends the selected treatment, three population drafts,
their canonical claims and design assumptions. This is review of supplied curated
evidence, not a live literature search or a fine-tuned model.

The server validates recommendation IDs, cited claim IDs, existing criterion IDs,
same-population proposal references and bounded factors. It rejects changes to
the fixed parent-population scope. **These checks do not establish clinical
entailment or validate a proposed restriction.** Errors are shown without a
simulated model response or silent provider substitution. Model/project/location,
usage metadata and an input hash are saved without access tokens.

## Local records and compatibility

SQLite data remain in `.local/demo.sqlite3` (gitignored), configurable with
`DEMO_DB_PATH`. New results have `task=population_design`. Population feedback has
its own table keyed to the saved run, treatment and population. New APIs are
`POST /api/populations`, `POST /api/population-feedback`, and
`GET /api/runs/<run_id>`. Same-origin writes and loopback binding remain enforced.

Earlier individual-case records keep their original meaning. Opening an older
saved link offers the archived `/legacy.html` view. Its APIs, data and forecasting
checks remain compatible; [legacy documentation](LEGACY_TREATMENT_DEMO.md) describes
that former workflow. They are not reinterpreted as population-design results.

## Checks and pending evaluation

```sh
python3 -m unittest discover -s milestone1/tests -v
```

Regression checks cover distinct population records, scoped criteria and sources,
safe effect transfer, original forecast arithmetic, validated model proposals,
reviewed weight application and saved-feedback recovery. They are engineering
checks, **not a clinical benchmark or evidence of superiority over a general LLM**.
The existing evaluation/benchmark scripts are left for the user's review.

## Files

- `population_library.py`: cited candidate cohorts, criterion purposes and safety/protocol review items.
- `populations.py`: task schema, conditional forecasts and Gemini population-design review.
- `server.py`: APIs, storage and archived-demo compatibility.
- `static/index.html`, `population-app.js`, `population.css`: current workspace.
- `tests/test_populations.py`: population-design regression checks.
- `agent.py`, `scoring.py`, `endpoint_comparison.py`, `static/legacy.html`: earlier individual-case demo.
