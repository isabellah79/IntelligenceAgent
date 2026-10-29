# Literature ledger for population design and endpoint scenarios

The current task is proposing populations and criteria **for each treatment**.
`population_library.py` separates reference cohorts, exploratory subgroups and
untested restrictions. Each candidate has its own comparator/effect record; an
effect is not automatically transferred across a new criterion or sequence.

New population-design sources include FDA guidance on
[performance status](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status),
[brain metastases](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases),
[laboratory values](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values),
and [washout/medication restrictions](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications).
Guidance informs scientifically justified eligibility; it does not establish
drug benefit or safety equivalence for every expanded subgroup.

The [2026 DB06 prior-duration analysis](https://pubmed.ncbi.nlm.nih.gov/41780642/)
defines subgroups post hoc and reports benefit across prior ET+CDK4/6 duration
groups. The early-progression candidate is explicitly exploratory, not a proven
reason to exclude slower-progressing patients. Its reported PFS medians are
retained without deriving an HR from them.

The historical ledger below describes the earlier individual-case endpoint
table, retained in `/legacy.html`. In the new workflow the EMERALD primary,
duration subgroup and overall results are separate population records; the
duration HR is not substituted into the broader population. New source-to-target
extrapolation is opt-in. Numerical factors remain provisional analyst choices.

Reviewed 2026-10-29. This is a focused primary-source review, not a systematic
review. Studies support the findings below. **They do not estimate the odds
multipliers in the demo.** Those remain editable analyst assumptions, pending
clinical calibration. Related publications from one trial are not independent
replications. Source-cohort outcomes and different controls cannot establish a
head-to-head treatment ordering.

| Source | Finding and implication | Treatment in the framework |
| --- | --- | --- |
| [EMERALD primary report](https://pubmed.ncbi.nlm.nih.gov/35584336/) and [FDA benefit assessment](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf) | Prior CDK4/6 was required; use the ESR1-mutated primary-population result, not an all-comer indication. | Primary HR 0.55 retained. Proposed applicability multiplier 1.20. |
| [EMERALD duration analysis](https://pubmed.ncbi.nlm.nih.gov/39087959/) | ESR1-mutated patients with ≥12 months prior ET+CDK4/6 had PFS 8.6 vs 1.9 months, HR 0.41. This exploratory result is not an independently confirmed selection rule. | For a matching duration, proposed +1.10 and countervailing post-hoc caution ×0.90. Do not replace primary HR 0.55 with 0.41. |
| [EMBER-3 updated efficacy](https://pubmed.ncbi.nlm.nih.gov/41391667/) | Monotherapy ESR1-mutated and overall-population combination analyses answer different questions. Prior CDK4/6 exposure is mixed. | Proposed applicability ×0.90. Table retains the specifically named cohort and data cut; no pooling of updated overall and subgroup results. |
| [FDA ESR1-mutated combination assessment](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-imlunestrant-combination-abemaciclib-er-positive-her2-negative-esr1-mutated-advanced-or) | ESR1-mutated combination analysis is exploratory. | Additional proposed ×0.85 subgroup-uncertainty factor. |
| [CAPItello-291](https://pubmed.ncbi.nlm.nih.gov/37256976/) and [safety analysis](https://pubmed.ncbi.nlm.nih.gov/39241495/) | Prior CDK4/6 exposure was mixed; adverse-event discontinuation and early diarrhea/rash/hyperglycemia matter to delivery and exposure. | Proposed ×0.90 applicability and ×0.90 exposure-risk factors. The studies do not quantify how these change trial success odds. |
| [VERITAC-2 FDA assessment](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-vepdegestrant-er-positive-her2-negative-esr1-mutated-advanced-or-metastatic-breast) and [original publication](https://www.nejm.org/doi/abs/10.1056/NEJMoa2505725) | Prior CDK4/6 required. FDA HR 0.57 differs slightly from original publication HR 0.58. | Table explicitly uses FDA 0.57; no averaging. Proposed applicability ×1.20. |
| [DESTINY-Breast06](https://pubmed.ncbi.nlm.nih.gov/39282896/) | HER2-low primary population, no prior metastatic chemotherapy; HER2-ultralow exploratory. | Do not transfer HER2-low HR to ultralow or a chemotherapy-pretreated case. No fabricated quantitative literature bonus. |
| [TROPION-Breast01 primary report](https://pubmed.ncbi.nlm.nih.gov/39265124/) and [safety/PRO report](https://pubmed.ncbi.nlm.nih.gov/42497483/) | PFS benefit; lower grade ≥3 treatment-related toxicity than chemotherapy in the primary report, alongside stomatitis/ocular events and dose modifications. | Show both pros and cons. Proposed modest ×0.95 exposure-risk factor. Absence of demonstrated OS improvement is **not** subtracted from a PFS endpoint score. |
| [TROPiCS-02 FDA assessment](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-sacituzumab-govitecan-hziy-hr-positive-breast-cancer) | PFS 5.5 vs 4.0 months and OS 14.4 vs 11.2 months are different outcomes in heavily pretreated patients. | Use PFS HR 0.661 for the PFS calculation, not OS HR. Apply line-of-therapy gates. |
| [postMONARCH](https://pubmed.ncbi.nlm.nih.gov/39693591/) | Direct post-CDK4/6 randomized study; primary investigator-assessed HR 0.73 differs from BICR HR 0.55. | Use primary HR 0.73 and proposed applicability ×1.20, not the more favorable secondary assessment. |

## Provisional equation

Method A reuses `forecast.py`: prior odds multiplied by evidence modifiers.
Each multiplier is damped as `factor ** evidence_strength` (default strength 0.5).
Default prior is 0.50, explicitly a neutral analyst choice rather than a validated
reference-class rate. Method B reuses the original 1:1 proportional-hazards
normal approximation at 200 assumed events and z=1.96. Its default hypothetical
true HR is the published source HR, so this is a **retrospective source-effect
illustration**, not an independently validated prospective forecast.

The default final score is `0.5*A + 0.5*B`; the A weight, prior, event count,
threshold, adjustment strength and individual evidence factors are editable and
saved in the run. Set evidence strength to zero to remove all evidence modifiers.
Related evidence may still be double-counted by this provisional blend; sensitivity
analysis and calibration on time-separated data remain needed. Scores do not
estimate a patient's response probability or automatically determine therapy.
