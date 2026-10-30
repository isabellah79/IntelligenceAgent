# Where the historical trial candidates came from

The previous benchmark extracted candidates from two CSV files already stored
in the project's RAG work. It did not retrieve a new, task-specific trial dataset.
Paths below are relative to `demo-source`:

- Older: `../RAG Project_副本/app_rag_approach/backend/data/breast_cancer_trials_full_2026-04-14.csv`
- Newer: `../RAG Project_副本/app_rag_approach/backend/data/breast_cancer/trials.csv`

The older file contains 16,248 records; the newer file contains 16,414. Their
SHA-256 hashes and full paths are recorded by `python3 -m benchmark.trial_audit`.
These are ClinicalTrials.gov exports from the previous project work, not patient
records. The older filename records April 14, 2026. The previous README describes
the newer snapshot as May 26; its exact pull date has not been independently
verified. Those dates are six weeks apart, not sixteen. A record's last-update
date cannot itself establish when the CSV was downloaded.

## Three different matching questions

1. **Is this the same registered trial in both exports?** Join by exact `nctId`.
   Duplicate IDs are rejected. Drug-name overlap and acronyms are insufficient.
2. **Is it relevant to our HR+/HER2− metastatic post-CDK4/6 question?** Review
   disease setting, intervention, treatment history, comparator, endpoint and
   cohort. The audit's keyword flags only prioritize this review.
3. **Did it have a real, relevant eligibility amendment?** Compare criteria,
   inspect the changed clauses, establish dates and direction, and obtain human
   confirmation. Formatting or template changes are not validated gold.

The original extraction filtered condition text containing breast, phase text
containing PHASE2 or PHASE3 (including combined phase1/2), and detected criteria
changes. It did not enforce the current population or treatment scope. This
produced 20 candidates, including early-stage, triple-negative, prevention and
imaging studies. All remain unreviewed candidates; none is silently promoted to gold.

One title explicitly mentions our setting:
[NCT07258108](https://clinicaltrials.gov/study/NCT07258108), Sac-TMT plus KL-A167
in PD-L1+, HR+/HER2− metastatic breast cancer after CDK4/6 inhibitors. It studies
a different regimen from the current demo. Its presence does not establish a
usable benchmark example, a verified amendment, or evidence for our treatments.

## Source trials used by the demo

Identity was cross-checked against the local registry title/intervention fields:

| Demo evidence source | Registry ID | Present among the original 20 amendment candidates? |
|---|---|---|
| EMERALD, elacestrant | [NCT03778931](https://clinicaltrials.gov/study/NCT03778931) | No |
| CAPItello-291, capivasertib + fulvestrant | [NCT04305496](https://clinicaltrials.gov/study/NCT04305496) | No |
| DESTINY-Breast06 / DB-06, T-DXd | [NCT04494425](https://clinicaltrials.gov/study/NCT04494425) | No |

These are evidence-source identities, not assignments of an NCT ID to a newly
proposed population. The CSV also contains an unrelated EMERALD radiotherapy
study and an EXoPERT EMERALD study, illustrating why acronym matching is unsafe.
The three source links are an explicit, locally checked audit map rather than
an automatic acronym-to-NCT resolver or independent online verification.

## What the repaired runner does

For historical evaluation it requires an explicit target `trial.nct_id` in the
submitted option set and matches it exactly to a supplied pack. Multiple
amendments require a `pair_id`. Human-approved gold and separate model knowledge
and evidence cutoffs are additional prerequisites. A generation timestamp does
not satisfy them, and a trial start-date split does not prevent all leakage.

The current demo is a prospective population-design exercise with no historical
target NCT ID. Therefore its amendment evaluation is correctly reported as not
run, even when this candidate pack is loaded. The primary development evaluation
is per-population defense and between-population differentiation.
