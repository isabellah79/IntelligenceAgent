# Scientific population defense benchmark — provisional

The defense grade emphasizes evidence strength, population applicability, selection justification and tradeoffs. Endpoint forecasts use separate clinical/design assumptions. Neither establishes which subgroup benefits more.

The rubric is not yet calibrated against oncologist grades. Equal-quality defenses can tie; the evaluator does not force a ranking.

## Scientific grading

Final defense = 80% scientific assessment + 20% completeness. Endpoint forecasts contribute zero weight.

| Scientific dimension | Weight within scientific assessment |
|---|---:|
| Evidence strength | 35% |
| Population applicability | 25% |
| Selection justification | 25% |
| Tradeoffs | 15% |

Each dimension uses an anchored 0–4 grade with cited reasons. The evidence bank was checked against primary/official sources; clinician adjudication is pending.

Missing scientific mappings produce **Unassessed**, never a completeness-only final score. Different ordinal profiles can produce equal totals.

## Current rule weights

| Check | Weight |
|---|---:|
| pros_present | 1.0 |
| cons_present | 1.0 |
| cons_substantive | 1.0 |
| no_overclaiming | 2.0 |
| uses_guidance | 1.0 |
| cns_not_blanket | 1.5 |
| ps_justified | 1.0 |
| safety_exclusion | 1.5 |
| scope_respected | 1.5 |
| criteria_complete | 1.0 |
| estimates_ranged | 1.0 |
| citation_coverage | 1.5 |
| criteria_reasoned | 1.5 |
| uncertainty_explicit | 1.5 |
| population_defended | 2.0 |

These are provisional analyst weights and must be fixed before held-out evaluation.

## Elacestrant · demo

| Population | Defense /100 | Scientific /100 | Completeness /100 | Conditional endpoint forecast | References |
|---|---:|---:|---:|---|---|
| ESR1-mutated reference population | 95.5 | 96.2 | 92.5 | 0.756 · Provisional A/B endpoint score | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications) |
| ESR1-mutated + longer prior endocrine benefit | 71.5 | 66.2 | 92.5 | 0.751 · Provisional A/B endpoint score | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/), [EMERALD-DURATION](https://pubmed.ncbi.nlm.nih.gov/39087959/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications) |
| ESR1-unselected research population | 90.5 | 90.0 | 92.5 | 0.604 · Provisional A/B endpoint score | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications) |

**Scientific reasons for each population:**

### ESR1-mutated reference population

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 4 | The ESR1-mutated subgroup was a randomized co-primary endpoint population in EMERALD, with efficacy verified in the FDA label assessment. | [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |
| Population applicability | 4 | Candidate setting of post-CDK4/6 HR+/HER2- metastatic breast cancer matches EMERALD eligibility and FDA labeling directly. | [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |
| Selection justification | 4 | Direct regulatory and trial-defined selection based on co-primary efficacy outcomes, acknowledging that predictive superiority over other active regimens still requires prospective interaction evidence. | [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |
| Tradeoffs | 3 | Identifies both sides of restricting to ESR1 mutations, recognizing potential exclusion of responders and lack of duration filtering, while citing relevant criteria. | [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: safety_exclusion.

### ESR1-mutated + longer prior endocrine benefit

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 2 | The >=12 months prior duration threshold is derived strictly from post hoc, exploratory subgroup analysis without multiplicity adjustment. | [EMERALD-DURATION](https://pubmed.ncbi.nlm.nih.gov/39087959/) |
| Population applicability | 4 | Directly matches the post-CDK4/6 metastatic HR+/HER2- setting evaluated in the EMERALD duration subgroup analysis. | [EMERALD-DURATION](https://pubmed.ncbi.nlm.nih.gov/39087959/) |
| Selection justification | 2 | The additional >=12-month restriction represents a plausible hypothesis-generating post hoc enrichment without confirmed predictive interaction evidence. | [EMERALD-DURATION](https://pubmed.ncbi.nlm.nih.gov/39087959/) |
| Tradeoffs | 3 | Articulates the tension between enriched effect signals and patient exclusion or recruitment slowdowns without relying on unsupported quantitative estimates. | [EMERALD-DURATION](https://pubmed.ncbi.nlm.nih.gov/39087959/) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: safety_exclusion.

### ESR1-unselected research population

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 4 | EMERALD evaluated all-patient (unselected) PFS as a randomized co-primary endpoint. | [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |
| Population applicability | 4 | Directly reflects the broad post-CDK4/6 trial population enrolled in EMERALD. | [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |
| Selection justification | 3 | Rationale rests on the studied overall trial cohort, but carries a major unresolved selection limitation given FDA restriction to ESR1-mutated tumors and lack of proven wild-type benefit. | [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |
| Tradeoffs | 3 | Balances broader recruitment and generalizability against the downside of including ESR1-wild-type patients where benefit is unestablished by label review. | [ELAC-FDA](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf), [EMERALD](https://pubmed.ncbi.nlm.nih.gov/35584336/) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: safety_exclusion.


**Differences between populations:**

- elacestrant__esr1 versus elacestrant__long_response: elacestrant__long_response: Require at least 12 months on the preceding endocrine + CDK4/6 regimen.
- elacestrant__esr1 versus elacestrant__unselected: elacestrant__esr1: Require a qualifying ESR1 mutation confirmed by a specified assay.; elacestrant__unselected: Allow ESR1-mutated and non-mutated disease; record status and prespecify strata.
- elacestrant__long_response versus elacestrant__unselected: elacestrant__long_response: Require a qualifying ESR1 mutation.; elacestrant__long_response: Require at least 12 months on the preceding endocrine + CDK4/6 regimen.; elacestrant__unselected: Allow ESR1-mutated and non-mutated disease; record status and prespecify strata.

**Forecast assumptions:**

- elacestrant__esr1: assumed HR 0.55; comparator Fulvestrant or aromatase inhibitor. A trial-statistic illustration, not a patient-benefit probability or ranking of optimal populations.
- elacestrant__long_response: assumed HR 0.41; comparator Fulvestrant or aromatase inhibitor. A trial-statistic illustration, not a patient-benefit probability or ranking of optimal populations.
- elacestrant__unselected: assumed HR 0.7; comparator Fulvestrant or aromatase inhibitor. A trial-statistic illustration, not a patient-benefit probability or ranking of optimal populations.

Historical match: not_requested. No historical gold pack supplied.

Review status: review_required. Human source and clinical safety review remain pending.

## Capivasertib + fulvestrant · demo

| Population | Defense /100 | Scientific /100 | Completeness /100 | Conditional endpoint forecast | References |
|---|---:|---:|---:|---|---|
| PIK3CA / AKT1 / PTEN-altered population | 92.0 | 90.0 | 100.0 | Unavailable | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications) |
| PIK3CA-mutated enrichment hypothesis | 56.0 | 45.0 | 100.0 | Unavailable | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications) |
| Pathway-unselected research population | 87.0 | 83.8 | 100.0 | Unavailable | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications) |

**Scientific reasons for each population:**

### PIK3CA / AKT1 / PTEN-altered population

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 4 | Dual primary PFS endpoint evaluation was prespecified in the randomized phase 3 CAPItello-291 trial in the PIK3CA/AKT1/PTEN-altered population. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Population applicability | 3 | Substantial overlap exists as CAPItello-291 enrolled 69.1% prior CDK4/6 inhibitor recipients, but the candidate restricts exclusively to an all-post-CDK4/6 setting. | [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Selection justification | 4 | The composite PIK3CA/AKT1/PTEN alteration requirement directly matches the trial-defined co-primary population and regulatory indication, though predictive superiority over alternatives requires interaction evidence. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Tradeoffs | 3 | Candidate explicitly addresses both sides of cohort selection, noting that aggregate pathway benefit does not resolve individual alteration heterogeneity or guarantee predictive superiority in an exclusively post-CDK4/6 setting. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: No completeness failures detected.

### PIK3CA-mutated enrichment hypothesis

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 1 | Restricting solely to PIK3CA mutations lacks a candidate-specific comparative estimate, relying on indirect rationale from the composite pathway-altered trial population. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Population applicability | 3 | Represents an extrapolation and additional restriction compared to the broader mixed-exposure studied trial population. | [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Selection justification | 1 | Added restriction excluding AKT1 and PTEN alterations without supporting selection evidence showing greater benefit compared to the established multi-gene rule. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Tradeoffs | 3 | Addresses downside risks of exclusion, recognizing that narrowing to PIK3CA alone excludes patients who may benefit and could impair recruitment without proven enhanced efficacy. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: No completeness failures detected.

### Pathway-unselected research population

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 4 | CAPItello-291 tested overall population PFS as a co-primary randomized endpoint, although the aggregate positive result cannot establish efficacy within the non-altered stratum alone. | [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Population applicability | 3 | Substantial overlap with the CAPItello-291 mixed prior-therapy cohort, with target-to-source mismatch regarding universal prior CDK4/6 exposure. | [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Selection justification | 3 | Provides a plausible exploratory research rationale to capture both biomarker strata, but carries an unresolved selection limitation since capivasertib indication is restricted to pathway-altered tumors. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |
| Tradeoffs | 3 | Articulates both trade-offs of broadening the cohort, balancing expanded recruitment and generalizability against testing outside the established altered indication without demonstrated isolated benefit in non-altered cases. | [CAPI-LABEL](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf), [CAPITELLO](https://pubmed.ncbi.nlm.nih.gov/37256976/) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: No completeness failures detected.


**Differences between populations:**

- capivasertib__pathway versus capivasertib__pik3ca: capivasertib__pathway: Document progression on an aromatase-inhibitor-based regimen and the CDK4/6 partner.
- capivasertib__pathway versus capivasertib__unselected: capivasertib__pathway: Require at least one qualifying PIK3CA, AKT1 or PTEN alteration.; capivasertib__pathway: Document progression on an aromatase-inhibitor-based regimen and the CDK4/6 partner.; capivasertib__unselected: Allow altered and non-altered tumors; require testing and prespecified biomarker strata.
- capivasertib__pik3ca versus capivasertib__unselected: capivasertib__pik3ca: Restrict to qualifying PIK3CA mutations; characterize AKT1/PTEN and co-alterations.; capivasertib__unselected: Allow altered and non-altered tumors; require testing and prespecified biomarker strata.

**Forecast assumptions:**

- capivasertib__pathway: The reference includes a different treatment-history population. Explicitly allow source-to-target extrapolation or enter a justified hypothetical effect.
- capivasertib__pik3ca: No comparative HR for this candidate is supplied. Specify an explicit hypothetical HR and comparator to explore a scenario.
- capivasertib__unselected: The reference includes a different treatment-history population. Explicitly allow source-to-target extrapolation or enter a justified hypothetical effect.

Historical match: not_requested. No historical gold pack supplied.

Review status: review_required. Human source and clinical safety review remain pending.

## Trastuzumab deruxtecan (T-DXd) · demo

| Population | Defense /100 | Scientific /100 | Completeness /100 | Conditional endpoint forecast | References |
|---|---:|---:|---:|---|---|
| HER2-low, no prior metastatic chemotherapy | 92.0 | 90.0 | 100.0 | Unavailable | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |
| HER2-ultralow exploratory population | 73.0 | 66.2 | 100.0 | Unavailable | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |
| HER2-low / ultralow + early endocrine progression | 68.0 | 60.0 | 100.0 | Unavailable | [ABC](https://doi.org/10.1016/j.breast.2024.103756), [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [DB06-TTP](https://pubmed.ncbi.nlm.nih.gov/41780642/), [FDA-CNS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-brain-metastases), [FDA-LABS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-laboratory-values), [FDA-PS](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-performance-status), [FDA-WASHOUT](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-washout-periods-and-concomitant-medications), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |

**Scientific reasons for each population:**

### HER2-low, no prior metastatic chemotherapy

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 4 | DESTINY-Breast06 demonstrated randomized phase 3 primary-population PFS benefit specifically in the HER2-low, chemotherapy-naive setting. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/) |
| Population applicability | 3 | The source trial population was not exclusively post-CDK4/6, creating substantial overlap with a mixed prior-therapy source population. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |
| Selection justification | 4 | Selection aligns with the trial-defined primary population and FDA-indicated phenotype, though predictive superiority over ultralow is not established. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |
| Tradeoffs | 3 | Addresses population-specific tradeoffs and safety considerations (such as ILD screening), noting the limitation of excluding ultralow disease. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: No completeness failures detected.

### HER2-ultralow exploratory population

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 2 | The HER2-ultralow cohort was explicitly evaluated as an exploratory randomized subgroup in DESTINY-Breast06 without primary confirmatory status. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |
| Population applicability | 3 | Source population DB06 included mixed prior therapy rather than exclusively post-CDK4/6 progression, though it directly tested ultralow disease. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |
| Selection justification | 3 | Studied cohort rationale is based on a trial-defined subgroup with regulatory inclusion, but remains limited by its exploratory nature. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |
| Tradeoffs | 3 | Acknowledges recruitment hurdles, lack of separate predictive interaction, and safety adjudications like ILD monitoring. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: No completeness failures detected.

### HER2-low / ultralow + early endocrine progression

Assessment method: llm_scientific_v3; calibration pending.

| Dimension | Grade /4 | Reason | Evidence |
|---|---:|---|---|
| Evidence strength | 2 | Evidence relies on a post hoc subgroup analysis of progression time on prior ET plus CDK4/6 from DESTINY-Breast06. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [DB06-TTP](https://pubmed.ncbi.nlm.nih.gov/41780642/) |
| Population applicability | 3 | Although evaluating post-CDK4/6 timing, the underlying DB06 source trial was broader and not restricted strictly to early progressors. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [DB06-TTP](https://pubmed.ncbi.nlm.nih.gov/41780642/) |
| Selection justification | 2 | Restricting to progression within 6 months is an added exploratory restriction lacking predictive interaction evidence, as benefit was observed across duration groups. | [DB06-TTP](https://pubmed.ncbi.nlm.nih.gov/41780642/) |
| Tradeoffs | 3 | Explicitly notes the risk of unnecessarily narrowing the eligible population given benefit across duration groups, balanced with safety mitigation. | [DB06](https://pubmed.ncbi.nlm.nih.gov/39282896/), [DB06-TTP](https://pubmed.ncbi.nlm.nih.gov/41780642/), [TDXD-FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2) |

Source-to-target limit: The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.

Completeness checks: No completeness failures detected.


**Differences between populations:**

- tdxd__her2low versus tdxd__ultralow: tdxd__her2low: Require HER2 IHC 1+ or IHC 2+/ISH-negative disease.; tdxd__ultralow: Require IHC 0 with membrane staining; exclude IHC 0 without membrane staining.
- tdxd__her2low versus tdxd__rapid_progression: tdxd__her2low: Require HER2 IHC 1+ or IHC 2+/ISH-negative disease.; tdxd__rapid_progression: Require HER2-low or ultralow disease and progression within 6 months of first-line ET + CDK4/6.
- tdxd__ultralow versus tdxd__rapid_progression: tdxd__ultralow: Require IHC 0 with membrane staining; exclude IHC 0 without membrane staining.; tdxd__rapid_progression: Require HER2-low or ultralow disease and progression within 6 months of first-line ET + CDK4/6.

**Forecast assumptions:**

- tdxd__her2low: The reference includes a different treatment-history population. Explicitly allow source-to-target extrapolation or enter a justified hypothetical effect.
- tdxd__ultralow: No comparative HR for this candidate is supplied. Specify an explicit hypothetical HR and comparator to explore a scenario.
- tdxd__rapid_progression: No comparative HR for this candidate is supplied. Specify an explicit hypothetical HR and comparator to explore a scenario.

Historical match: not_requested. No historical gold pack supplied.

Review status: review_required. Human source and clinical safety review remain pending.

## Evaluation coverage

Not evaluated: amendment_retrodiction, accrual_postmortem, outcome_alignment, blinded_expert_review.

Older scorecards use a different rubric and denominator and should not be compared numerically with this version.
