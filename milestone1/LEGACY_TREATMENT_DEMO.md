# Milestone 1 · Treatment strategy comparison

A local research demo for **ER+/HER2− metastatic breast cancer after progression
on endocrine therapy plus a CDK4/6 inhibitor**, inspired by the IQVIA scenario.
Uses Python 3.10+ and its standard library. No installation, cloud storage,
embedding service, API key or trial CSV is needed for curated mode.

## Current default: cited endpoint-comparison table

The main view now shows **next treatments after CDK4/6 progression**, rather than
automatically adding a CDK4/6 inhibitor to every treatment. Its columns are:
treatment with immediate reference links, case fit, published primary-endpoint
evidence, provisional PFS forecast score, pros, and cons/limitations.

The earlier hand-set discussion-priority scores are retained in the exported
data/code for traceability, but are **not the score displayed in the table**.

`endpoint_comparison.py` provides the provisional endpoint framework. Default
assumptions are a neutral analyst prior 0.50, 200 PFS events, 1:1 allocation,
z=1.96, evidence strength 0.5, and A/B blend 0.5/0.5. Literature findings have
source links; numerical odds multipliers are editable analyst assumptions,
not estimates made by those studies. Each row's ledger separates the finding,
modeling rationale, chosen multiplier, damped multiplier and score change.
The event/design settings are under “Edit the case and PFS forecast assumptions.”
Weight edits mark results stale; use the visible recalculate button above the
table to apply them. All inputs and outputs are persisted/exported with the run.

Method A uses `prior odds × product(factor ** evidence_strength)`. Method B uses
the source HR as a hypothetical true effect: it is a retrospective source-effect
power illustration, not a validated prospective forecast. The final score is
`blend_a*A + (1-blend_a)*B`. Clear the prior to see B alone; set evidence strength
to zero to neutralize modifiers. Different source comparators/populations still
prevent a head-to-head treatment ranking. No estimates are invented for absent
or inapplicable comparative evidence. See [literature ledger](LITERATURE_REVIEW.md)
for additional primary-source reading and the reasons for proposed +/− modifiers.

## Run

From the repository root:

```sh
python3 -m milestone1.server
```

Open **http://127.0.0.1:8765**. Use `--port 8766` if needed.

The default fictional case is the reviewed example: age 62, postmenopausal,
ER+/HER2-low, ESR1 and PIK3CA detected, progression after 22 months on an
aromatase inhibitor + ribociclib, no metastatic chemotherapy or ADC, ECOG 1,
preserved organ function and no visceral crisis. Metastatic disease and actual
progression on endocrine + CDK4/6 are prerequisites of this focused workflow;
it does not cover switching before progression or first-line treatment.

## Walk through the demo

1. Review the automatically loaded default table. Each row shows its reference
   links, applicability reason, endpoint evidence/score, benefits and limitations.
2. Change ESR1 to “not detected.” ESR1-selected branches become not matched.
3. Change PIK3CA to “unknown.” Alpelisib and gedatolisib need more information;
   unknown is never treated as mutation-negative. AKT1/PTEN can still independently
   support the capivasertib branch.
4. Change HER2 to IHC 0 without membrane staining. The cited T-DXd indication
   is not matched; this is different from HER2-ultralow.
5. Add a prior metastatic chemotherapy regimen and update additional regimens.
   Dato-DXd changes to relevant for discussion. Sacituzumab requires at least
   two additional metastatic systemic regimens. “Regimens” count sequential
   treatment regimens, not the individual drugs within the initial combination.
6. Toggle visceral crisis. Routine sequencing synthesis pauses for urgent
   clinical review, while cards remain available as evidence context.
7. Expand a row's “Literature + / − evidence weights” ledger. Change a multiplier
   and use “Recalculate with current evidence weights” above the table. Adjust
   global endpoint assumptions in the case editor. The equation remains provisional.
8. Select for discussion, propose an edit, or reject a card. Export the run,
   scoring policy, recommendation and reviewer feedback as JSON.
9. Open the experimental forecast section. Load the original VIKTORIA-1 or
   Bria-ABC example and inspect both methods, every odds adjustment and the
   assumed HR scenarios. Edit assumptions and recalculate; edited examples are
   explicitly hypothetical and do not inherit an observed outcome.

Inputs changed after a run mark results stale and disable review/export until
the case is rerun. Numeric fields may be cleared to explicitly mean unknown.

## Legacy discussion-priority rubric (not the table's endpoint score)

The new `scoring.py` implements an explicit, **unvalidated discussion policy**.
It helps structure a fictional clinician review; it does not select treatment
for a real patient or estimate individual response/survival.

Four dimensions receive 0–5 points. The displayed score is
`sum(points / 5 * weight)`, with weights summing to 100. The sources support
underlying facts; numeric assignments and weights are hand-set product choices,
not facts endorsed by those sources.

| Dimension | Default fewer-visits weight | Assignment |
| --- | ---: | --- |
| Context match | 30 | Specific biomarker branch 5; broad strategy 3, after applicability gates |
| Post-CDK4/6 evidence applicability | 25 | Named, inspectable 2–5 rubric in `EVIDENCE`; dedicated prior-CDK trials score higher than indirect/mixed populations, without comparing effect sizes |
| Known review flags | 20 | Neutral 3 pending full drug safety assessment; unresolved case-specific concerns hold the option out of scoring |
| Delivery preference fit | 25 | For fewer visits: oral-only 5, injection combinations 3, infusion/unspecified strategy 2; neutral 3 otherwise |

The UI exposes editable weights and alternate presets. Choosing disease control
increases the evidence-applicability weight, not a predicted efficacy score.
This first policy does not quantify clinical efficacy, adverse-event utilities,
or the effect of prior response duration; these need clinical calibration.

Unmatched, later-line and unresolved options have **no score**, rather than a
misleading zero. Global review holds (crisis, unknown HER2, impaired/unknown
organ function or performance status, unresolved key biomarkers or treatment
counts) pause prioritization. A safety-review flag does not establish that a
drug is contraindicated; it means this limited prototype cannot prioritize it.

Options within 5 policy points of the highest score form a shortlist. The demo
explains each shortlisted option, why other scored options score lower, and
what remains to check. It also shifts 10 points between evidence and preference
to expose sensitivity to policy weights. Neither the 5-point margin nor the
sensitivity analysis is a statistical confidence interval.

For the default fictional case, elacestrant and vepdegestrant both score 92/100
under the fewer-visits preset. They remain tied; no head-to-head superiority is
claimed. This is not a 92% probability of treatment success.

## Original forecast.py integration

`forecast/forecast.py` now exposes `forecast_case()` while retaining its original
CLI and equations. `forecasting.py` imports that implementation directly:

- Method A multiplies prior odds by explicit analyst adjustment factors.
- Method B averages the chance of crossing statistical thresholds over assumed
  true-HR scenarios for a 1:1 proportional-hazards trial design.
- The combined forecast remains the equal-weight average of A and B.

VIKTORIA-1 reproduces approximately 69.7% (A), 59.7% (B), 64.7% combined. The
matching gedatolisib card links this original example, including its **PIK3CA
wild-type population and known-result/leakage caveat**. A matched historical
trial is not a treatment-benefit prediction. Other cards have no invented
forecast priors; users can enter custom trial assumptions in the lab. Associating
an unchanged example with another drug explicitly warns against transferring
the estimate. Bria-ABC is a separate research example, not this treatment setting.

Forecasts have **zero weight in the discussion score**. Combining a trial's
statistical power/base rate with an individual's treatment choice would change
the target of the model without validation. No observed trial HR is automatically
reused as a prospective true-effect forecast. Forecasts, assumptions and separate
IDs are saved in the local `forecast_runs` table. Current, non-stale forecast
results are included in comparison JSON exports.

## Gemini evidence judgment through Vertex AI

The configured foundation model is **`gemini-3.8-flash`**, using Vertex AI project
**`rag-project-494802`** and the **global** endpoint. Public, nonsecret settings
are in `vertex_settings.json`. Environment variables in `.env.example` override
them; `.env` files are not loaded automatically.

Install the Google Cloud CLI and sign in locally once:

```sh
gcloud auth application-default login
gcloud auth application-default set-quota-project rag-project-494802
python3 -m milestone1.server
```

The Google identity needs access to the project's enabled Vertex AI API, billing,
model and quota (typically the Vertex AI User role). The backend obtains a
short-lived ADC token via `gcloud`; credentials stay outside the project and
browser. TLS verification remains enabled, using system roots plus `certifi`
when installed or the Cloud SDK CA bundle. The adapter honors normal urllib
network/proxy settings. See Google's [model documentation](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash)
and [REST request reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference).

1. Run the default fictional case in curated mode to see the cited table.
2. Click **Run Gemini evidence review**. This sends the case, curated claims,
   applicability rules, endpoint assumptions and existing weight ledger to Google.
   Gemini reviews this supplied snapshot; it does not retrieve new literature.
3. Inspect its cited interpretation and proposed factor changes. Each suggestion
   shows the previous/new multiplier and rationale. No score changes yet.
4. Click **Apply model suggestions & recalculate with Python** to accept them.
   The original forecasting equations recompute the scores. This action makes
   no additional model call. The saved run links the prior review, metadata,
   cited reasons and exact applied factors; exports retain that provenance.

**Reopen this saved review** provides a local link that restores the original
output, assumptions and saved feedback without a new Gemini request. Save that
link to return to the same review; the records live in the local SQLite database.

Gemini may propose zero to eight changes to existing, active evidence factors,
within 0.5–2.0. The server rejects unknown factors, duplicates, inapplicable
options and references to another treatment's claims. Changed case facts or
forecast assumptions require a fresh review before applying prior suggestions.
Multipliers remain provisional judgments, not numerical estimates from trials.
The model never supplies the final numerical score.

Curated mode is deterministic and makes no model request. Loading the page does
not call Gemini. Configuration status means that settings and a local ADC file
are present; only a successful request verifies access. API/network failures are
shown as errors, without silently substituting a model result. Scope exclusions,
unknown HER2 status and visceral crisis stop a model request.

Each model statement must cite existing claim IDs; the server resolves them to
curated source links. **This checks reference IDs, not clinical entailment.**
Model text and weight magnitude still require clinical review. Recorded metadata
includes requested/reported model, project, location and token usage when supplied.
No access token or upstream response headers are saved. An optional Anthropic
adapter remains available via `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` and
`ANTHROPIC_MODEL`.

## Evidence and clinical limits

`evidence.py` is a curated, paraphrased evidence snapshot dated **2026-10-29**,
with U.S. regulatory context. Every pro, con and evidence statement has source
IDs. Sources include original trial publications, labels and official assessments.
The app does not claim to search PubMed, retrieve full articles, or verify links
live. Clinical review of the curated library is pending. Recheck current labels
before updating or reusing this snapshot; source pages can change.

Covered: elacestrant, imlunestrant, imlunestrant + abemaciclib, vepdegestrant,
capivasertib + fulvestrant, alpelisib + fulvestrant, gedatolisib combinations,
T-DXd, Dato-DXd, sacituzumab govitecan, conventional chemotherapy, and separate
olaparib and postMONARCH branches. This is a focused comparison, not an exhaustive
guideline or proof of drug eligibility. Prior variants, assays, doses, prior
fulvestrant/PI3K/AKT exposure, concomitant drugs and other label details need review.

The demo makes no cross-trial efficacy ranking, individual survival forecast,
automatic prescribing decision, or unsupported estimate of population size. PFS/OS values
retain their population/comparator context. Relevant-for-discussion means a
branch matches the entered filters, not that all clinical requirements are met.
Clinical trial participation and other regimens remain outside this small library.

Gedatolisib selection follows its prescribing information (no PIK3CA mutation
detected); a conflicting official summary encountered during research is not
used as the selection rule.

## Local records

Runs and researcher feedback are stored in `milestone1/.local/demo.sqlite3`
(gitignored). Set `DEMO_DB_PATH` to use another location. Each run preserves
the case, exact output, source catalog, evidence version, timestamp and mode.
Feedback refers to that run and option; an edit records a proposed change rather
than silently rewriting the curated evidence. Exported JSON includes reviews
created in the current UI session. The database retains earlier reviews.

Use fictional cases; this local prototype has no authentication or patient-data
workflow. It binds to loopback and rejects foreign browser origins. It is not
a production server. No publishing or deployment configuration is changed.

## Checks

```sh
python3 -m unittest discover -s milestone1/tests -v
```

These checks cover clinical branching, missing information, treatment sequence,
source-ID integrity, case validation, crisis handling, score arithmetic/holds,
weight sensitivity, original forecast parity, invalid forecast inputs, historical
provenance, Gemini response parsing, credential/error handling, bounded model
weight proposals and reviewed-factor application. They do not validate clinical
correctness, predictive calibration or make paid model calls.

## Files

- `evidence.py`: sources, canonical claims and option definitions.
- `agent.py`: case schema, applicability rules and validated model judgments.
- `llm.py`: server-side Vertex Gemini / optional Anthropic transport.
- `vertex_settings.json`: public model/project/location configuration.
- `endpoint_comparison.py`: visible PFS scenario scores and cited weight ledger.
- `scoring.py`: legacy discussion-priority rubric retained in JSON exports.
- `forecasting.py`: adapter to the original two-method forecasting code/examples.
- `server.py`: local HTTP API and SQLite feedback storage.
- `static/`: buildless, responsive comparison UI.
- `tests/`: offline regression checks.

The forecasting prototype is now accessible in this demo. Its hand-set trial
probabilities are not used to estimate patient benefit or rank treatments.
