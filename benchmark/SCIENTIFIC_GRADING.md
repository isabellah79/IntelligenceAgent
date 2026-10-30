# Scientific grading policy v3

The research objective is to defend a treatment-specific population within
HR+/HER2-negative advanced/metastatic breast cancer after endocrine plus CDK4/6
progression. The grade measures the defensibility of that proposal. It is not a
patient-benefit probability, a validated trial-success prediction, or a comparison
of drug efficacy across unrelated trials.

Final defense = 0.80 × scientific grade + 0.20 × completeness grade.
Scientific grade = 0.35 × evidence + 0.25 × applicability + 0.25 × selection
justification + 0.15 × tradeoffs. Each scientific dimension is divided by 4
before averaging; reports display the result on a 0–100 scale.

These weights express a provisional research preference. They must be fixed
before held-out evaluation and calibrated against oncology review. Do not tune
them to force a particular population to win. Different dimension profiles can tie.

## Ordinal anchors

| Grade | Evidence strength | Population applicability | Selection justification | Tradeoffs |
|---:|---|---|---|---|
| 0 | Contradicted/fabricated support | Outside target disease/regimen | No operative rule or unsupported predictive/superiority claim | No downside or an unsupported quantitative tradeoff |
| 1 | Indirect rationale or no candidate-specific comparative estimate in the bank | Major treatment-line/exposure mismatch | Added rule with no selection evidence | Generic caveats |
| 2 | Exploratory randomized subgroup or noncomparative clinical cohort | Important extrapolation or added untested selection | Plausible explicitly exploratory/access hypothesis | Criterion-specific downside |
| 3 | Prespecified randomized subgroup | Substantial overlap with a mixed source cohort | Studied cohort with a material unresolved selection limitation | Balanced advantages/risks, uncertainty and mitigation/alternative |
| 4 | Randomized primary/co-primary efficacy population | Direct representation of the candidate setting | Trial-defined clinical/regulatory selection rationale | Independently supported quantitative tradeoff and justified design choice |

A 4 for biomarker selection does not imply a proven treatment-effect interaction.
Regulatory inclusion is evidence for the selection rationale, not proof that an
exploratory efficacy analysis was confirmatory. Single-arm data may directly
match a sequence while still scoring below randomized evidence on evidence strength.

The current automated modes cap tradeoffs at 3 because independently adjudicated
quantitative recruitment/benefit tradeoffs have not been supplied. They do not
reward invented precision. Oncologists can use the full 0–4 scale when actual
supporting evidence is available.

## Evidence-backed distinctions in the worked cases

- EMERALD: ESR1-mutated PFS was a primary randomized efficacy analysis. Its
  >=12-month prior endocrine/CDK4/6 analysis was post hoc, exploratory and not
  multiplicity-adjusted. These receive different evidence anchors even if both
  defenses have the same number of citations. [Primary](https://pubmed.ncbi.nlm.nih.gov/35584336/),
  [duration analysis](https://pubmed.ncbi.nlm.nih.gov/39087959/).
- CAPItello-291: pathway-altered and overall PFS were dual primary analyses;
  prior CDK4/6 exposure was mixed. A PIK3CA-only restriction needs justification
  beyond the aggregate PIK3CA/AKT1/PTEN result. The bank does not claim that no
  component-level analysis exists elsewhere. [Primary](https://pubmed.ncbi.nlm.nih.gov/37256976/).
- DESTINY-Breast06: HER2-low PFS was primary; ultralow efficacy was exploratory.
  Label inclusion of ultralow does not change its original analysis status.
  Early-progression subgroup analyses were post hoc and showed benefit across
  duration groups, rather than validating an early-progression exclusion rule.
  [Primary](https://pubmed.ncbi.nlm.nih.gov/39282896/),
  [duration analysis](https://pubmed.ncbi.nlm.nih.gov/41780642/).
- BYLieve: immediate prior AI+CDK4/6 and ECOG <=2 were represented in cohort A,
  but the study was noncomparative. Its eligibility evidence cannot become a
  randomized HR or an ECOG-2-specific effect estimate. A defense that omits this
  relevant study is told which support is missing, rather than silently receiving
  citation credit. [2024 report](https://pubmed.ncbi.nlm.nih.gov/39637900/).

Facts are stored independently in `data/scientific_evidence_v3.json`, with URLs,
review dates, analysis status and limitations. They were checked by the assistant
against primary/official sources; no oncologist approval is implied. This is a
bounded literature snapshot, not a systematic review or a finished gold standard.

## What prevents superficial score inflation

- Renaming an option or labeling it reference/evidence-supported does not change
  the evidence match. Source analysis type and operative selection criteria matter.
- More citations or confident prose cannot turn an unstudied 18-month cutoff
  into the published 12-month population or transfer a result to another drug.
- New ECOG, ADC-sequencing or treatment-line extensions do not inherit the parent
  population's comparative effect. Eligibility evidence and efficacy are separate.
- A mismatched comparator or endpoint and unmapped efficacy markers/cutoffs are
  unassessed. They are not filled in with the old checklist score.
- The score never uses forecast probability, assumed HR magnitude, model identity
  or the agent's self-declared evidence category as a grading target.
- Unknown/broken reference identities block the final grade. A diagnostic score
  may be retained for debugging, with the block visible.

## Two assessment methods

`evidence_rules_v3` is a reproducible provisional policy over the evidence bank.
Its selection extraction and qualitative tradeoff checks are limited text rules.
It is suitable for debugging and recording explicit assumptions, not a clinical
reference standard. A target comparator not specified by the case remains a
source-to-target limitation: the assessment refers to the source's comparison.

`llm_scientific_v3` uses the configured Gemini/provider to assess the substance
of the defense against the same four anchors and the supplied evidence. It uses
opaque candidate/criterion aliases and omits producer identity and forecasts.
Factual evidence ceilings, validated source/criterion IDs and complete output
schema constrain the response. Raw grades and caps are preserved. This still
cannot guarantee clinical entailment or remove same-model judge bias.

Grades from these methods are labeled separately. Human review is needed to
resolve disagreements. The human template records four 0–4 grades, a reviewer and
notes per frozen population. `scientific_calibration.py` compares these with saved
predictions without calling a model. Keep complete source trials/treatment
families together when splitting data, and reserve independent test cases before
optimizing prompts, weights or a future fine-tuned model.
