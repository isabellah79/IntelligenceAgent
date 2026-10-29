"""Curated evidence snapshot. No live retrieval or automatic clinical verification.

Statements are paraphrases, not quotations. Trial estimates describe the stated
trial population and must never be used to rank treatments across trials.
"""
VERSION = "2026-10-29.2"
AS_OF = "2026-10-29"


def source(id, title, url, kind, scope):
    return dict(id=id, title=title, url=url, kind=kind, scope=scope,
                checked_on=AS_OF, verification="Curated from primary/official source; clinician review pending")


SOURCES = {s["id"]: s for s in [
    source("EMERALD-DURATION", "EMERALD · prior-duration subgroup analysis", "https://pubmed.ncbi.nlm.nih.gov/39087959/", "Exploratory trial subgroup publication", "ESR1-mutated and prior ET+CDK4/6 ≥12 months: PFS 8.6 vs 1.9 months, HR 0.41. Post hoc, no multiplicity adjustment; not the primary-population result."),
    source("EMBER3-UPDATE", "EMBER-3 · updated phase 3 efficacy", "https://pubmed.ncbi.nlm.nih.gov/41391667/", "Trial follow-up publication", "Updated ESR1-mutated monotherapy benefit; combination PFS also reported in the overall population. Do not merge subgroup and overall estimates."),
    source("CAPI-SAFETY", "CAPItello-291 · adverse-event analysis", "https://pubmed.ncbi.nlm.nih.gov/39241495/", "Trial safety analysis", "Rash, diarrhea and hyperglycemia can require supportive treatment, interruptions, reductions or discontinuation. No numerical forecast adjustment was estimated by the authors."),
    source("DATO-PRIMARY", "TROPION-Breast01 · primary phase 3 results", "https://pubmed.ncbi.nlm.nih.gov/39265124/", "Trial publication", "PFS HR 0.63; grade ≥3 treatment-related adverse events 20.8% vs 44.7% at the reported analysis. OS was immature in this publication."),
    source("DATO-SAFETY", "TROPION-Breast01 · safety and patient-reported outcomes", "https://pubmed.ncbi.nlm.nih.gov/42497483/", "Trial safety analysis", "Stomatitis, ocular events and ILD; protocol supportive care and delayed deterioration in patient-reported outcomes. No validated efficacy-odds multiplier."),
    source("GEDA-FDA", "FDA · VIKTORIA-1 PFS comparisons", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-gedatolisib-fulvestrant-or-without-palbociclib-hr-positive-her2-negative-locally", "Regulatory assessment", "Triplet and doublet have separate PFS comparisons; no PIK3CA mutation detected."),
    source("EMERALD", "EMERALD · randomized phase 3", "https://pubmed.ncbi.nlm.nih.gov/35584336/", "Trial publication", "ER+/HER2− advanced disease after endocrine therapy; prior CDK4/6 required."),
    source("ELAC-FDA", "FDA · elacestrant benefit assessment", "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2023/217639Orig1s000RiskR.pdf", "Regulatory assessment", "ESR1-mutated population; endocrine monotherapy comparator."),
    source("IMLU-FDA", "FDA · imlunestrant monotherapy", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-imlunestrant-er-positive-her2-negative-esr1-mutated-advanced-or-metastatic-breast", "Regulatory assessment", "EMBER-3 included patients with and without prior CDK4/6 treatment."),
    source("EMBER3", "FDA · imlunestrant + abemaciclib", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-imlunestrant-combination-abemaciclib-er-positive-her2-negative-esr1-mutated-advanced-or", "Regulatory assessment", "ESR1-mutated subgroup exploratory combination analysis; mixed prior CDK4/6 exposure."),
    source("VERITAC2", "FDA · vepdegestrant / VERITAC-2", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-vepdegestrant-er-positive-her2-negative-esr1-mutated-advanced-or-metastatic-breast", "Regulatory assessment", "Prior CDK4/6 required; ESR1-mutated efficacy population; OS immature at PFS analysis."),
    source("CAPITELLO", "CAPItello-291 · randomized phase 3", "https://pubmed.ncbi.nlm.nih.gov/37256976/", "Trial publication", "PIK3CA/AKT1/PTEN-altered PFS population; 69.1% of overall population previously received CDK4/6."),
    source("CAPI-LABEL", "TRUQAP · prescribing information", "https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d698c106-2322-401e-b738-cbd83c843ecf", "Prescribing information", "Qualifying PIK3CA/AKT1/PTEN alterations; fulvestrant combination; safety and monitoring."),
    source("ALPEL-LABEL", "PIQRAY · prescribing information", "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b20b4e18-7a4b-4500-a08f-06c6dab0ee5b", "Prescribing information", "PIK3CA-mutated HR+/HER2− advanced disease after endocrine therapy; SOLAR-1 is not a dedicated post-CDK4/6 randomized trial."),
    source("GEDA-LABEL", "REVTORPYK · prescribing information", "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=959d73ef-831f-4005-956c-210702270bda", "Prescribing information", "No PIK3CA mutation detected; fulvestrant with or without palbociclib. FDA approval July 2026."),
    source("DB06", "DESTINY-Breast06 · randomized phase 3", "https://pubmed.ncbi.nlm.nih.gov/39282896/", "Trial publication", "HR+/HER2-low or ultralow after endocrine therapy; no prior chemotherapy for metastatic disease. Primary PFS analysis in HER2-low."),
    source("TDXD-FDA", "FDA · T-DXd in HER2-low / ultralow disease", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-fam-trastuzumab-deruxtecan-nxki-unresectable-or-metastatic-hr-positive-her2-low-or-her2", "Regulatory assessment", "After at least one endocrine therapy in metastatic disease; HER2-low IHC 1+ or 2+/ISH−, ultralow IHC 0 with membrane staining."),
    source("DATO-FDA", "FDA approval summary · TROPION-Breast01", "https://pmc.ncbi.nlm.nih.gov/articles/PMC12393668/", "Regulatory assessment", "Prior endocrine-based treatment AND chemotherapy for unresectable/metastatic disease; PFS benefit, no demonstrated OS improvement in reported analysis."),
    source("TROPICS2", "FDA · sacituzumab govitecan / TROPiCS-02", "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-sacituzumab-govitecan-hziy-hr-positive-breast-cancer", "Regulatory assessment", "Label: endocrine therapy plus at least two additional metastatic systemic therapies. Trial: heavily pretreated, including prior chemotherapy."),
    source("ABC", "ABC 6/7 · advanced breast cancer consensus", "https://doi.org/10.1016/j.breast.2024.103756", "Consensus guideline", "Visceral crisis means serious organ compromise; liver metastases alone are not visceral crisis."),
    source("PDQ", "NCI · breast cancer treatment PDQ", "https://www.cancer.gov/types/breast/hp/breast-treatment-pdq", "Official evidence summary", "Optimal endocrine sequence remains uncertain; sequential endocrine-based approaches often precede chemotherapy without visceral crisis."),
    source("CAPE", "Capecitabine · prescribing information", "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=e28a5ef7-4731-f8ac-e053-2995a90a21bf", "Prescribing information", "Drug-specific safety; not evidence that all chemotherapy agents share a toxicity profile."),
    source("OLYMPIAD", "OlympiAD · olaparib randomized phase 3", "https://www.nejm.org/doi/full/10.1056/NEJMoa1706450", "Trial publication", "Germline BRCA-mutated HER2− metastatic disease; not a dedicated post-CDK4/6 population."),
    source("OLAP-NCI", "NCI · olaparib use in breast cancer", "https://www.cancer.gov/about-cancer/treatment/drugs/olaparib", "Official drug summary", "Germline BRCA1/2 selection; prior chemotherapy and endocrine treatment context must be checked."),
    source("POSTMONARCH", "postMONARCH · randomized phase 3", "https://pubmed.ncbi.nlm.nih.gov/39693591/", "Trial publication", "Abemaciclib + fulvestrant after prior CDK4/6 progression; investigator-assessed primary PFS."),
]}


def claim(text, *refs):
    return {"text": text, "source_ids": list(refs)}


def option(id, title, family, route, gate, pros, cons, evidence, limits):
    return dict(id=id, title=title, family=family, route=route, gate=gate,
                pros=pros, cons=cons, evidence=evidence, limits=limits)


OPTIONS = [
    option("elacestrant", "Elacestrant", "ER-directed", "Oral monotherapy", "esr1",
        [claim("An oral ESR1-directed option with randomized evidence after CDK4/6 treatment.", "EMERALD", "ELAC-FDA")],
        [claim("Nausea is common; some patients progress early despite biomarker selection.", "EMERALD")],
        [claim("ESR1-mutated population: median PFS 3.8 vs 1.9 months; HR 0.55, 95% CI 0.39–0.77, against standard endocrine monotherapy.", "ELAC-FDA")],
        "PFS is a trial population estimate, not a prediction. Postmenopausal women/adult men in the approval context."),
    option("imlunestrant", "Imlunestrant", "ER-directed", "Oral monotherapy", "esr1",
        [claim("An oral treatment option for ESR1-mutated ER+/HER2− disease after endocrine therapy.", "IMLU-FDA")],
        [claim("Trial evidence includes both CDK4/6-pretreated and CDK4/6-naive patients; applicability needs careful review.", "IMLU-FDA")],
        [claim("EMBER-3 supports the ESR1-mutated indication; do not assume efficacy in ESR1-not-detected disease.", "IMLU-FDA")],
        "Do not extrapolate a mixed-population result to every post-CDK4/6 case."),
    option("imlunestrant_abemaciclib", "Imlunestrant + abemaciclib", "ER-directed", "Oral combination", "esr1",
        [claim("Adds a CDK4/6 inhibitor to an oral ER-directed strategy; FDA-approved for ESR1-mutated disease after endocrine therapy.", "EMBER3")],
        [claim("Adds diarrhea, neutropenia, hepatotoxicity, pneumonitis and thromboembolism risks; oral administration still requires monitoring.", "EMBER3")],
        [claim("Exploratory ESR1-mutated subgroup (159 patients): PFS 11.1 vs 5.5 months; HR 0.53, 95% CI 0.35–0.80, versus imlunestrant alone.", "EMBER3")],
        "Mixed prior CDK4/6 exposure; subgroup analysis is exploratory and OS was immature at the cited analysis."),
    option("vepdegestrant", "Vepdegestrant", "ER-directed", "Oral PROTAC degrader", "esr1",
        [claim("A distinct ER-degradation mechanism, studied in a trial requiring prior CDK4/6 treatment.", "VERITAC2")],
        [claim("QTc prolongation is a precaution; OS was immature at the cited PFS analysis.", "VERITAC2")],
        [claim("ESR1-mutated population: PFS 5.0 vs 2.1 months; HR 0.57, 95% CI 0.42–0.77, versus fulvestrant.", "VERITAC2")],
        "PROTAC degrader, not a conventional SERD. No head-to-head comparison with the other options shown."),
    option("capivasertib", "Capivasertib + fulvestrant", "PI3K / AKT pathway", "Oral drug + IM injections", "pathway",
        [claim("Targets qualifying PIK3CA, AKT1 or PTEN alterations with an endocrine partner.", "CAPI-LABEL")],
        [claim("Rash, diarrhea and hyperglycemia require assessment and monitoring; fulvestrant adds injection visits.", "CAPI-LABEL", "CAPITELLO")],
        [claim("Pathway-altered population: PFS 7.3 vs 3.1 months; HR 0.50, 95% CI 0.38–0.65, versus placebo + fulvestrant.", "CAPITELLO")],
        "69.1% of the overall trial population had prior CDK4/6 therapy. Mutation detection alone is not a full suitability assessment."),
    option("alpelisib", "Alpelisib + fulvestrant", "PI3K / AKT pathway", "Oral drug + IM injections", "pik3ca",
        [claim("A PIK3CA-directed endocrine combination for qualifying mutated disease after endocrine therapy.", "ALPEL-LABEL")],
        [claim("Hyperglycemia, rash and diarrhea can limit treatment. Assess fasting glucose/HbA1c and monitoring needs.", "ALPEL-LABEL")],
        [claim("The label supports PIK3CA-selected use; its pivotal SOLAR-1 evidence is not a dedicated post-CDK4/6 randomized comparison.", "ALPEL-LABEL")],
        "No modeled individual benefit or unsupported post-CDK4/6 efficacy estimate is supplied."),
    option("gedatolisib", "Gedatolisib + fulvestrant ± palbociclib", "PI3K / AKT pathway", "IV infusions + IM injections ± oral drug", "pik3ca_absent",
        [claim("An approved pathway-directed option when no PIK3CA mutation is detected after metastatic endocrine therapy.", "GEDA-LABEL")],
        [claim("Stomatitis, skin reactions and hyperglycemia are relevant risks; repeated infusions add visit burden.", "GEDA-LABEL")],
        [claim("Patient selection requires absence of detected PIK3CA mutations; this is different from alpelisib selection.", "GEDA-LABEL")],
        "Unknown mutation status is not the same as no mutation detected. Label, rather than conflicting summary wording, governs this demo rule."),
    option("tdxd", "Trastuzumab deruxtecan (T-DXd)", "Antibody–drug conjugates", "IV infusions", "her2_low",
        [claim("An ADC option for HR+/HER2-low or ultralow disease after metastatic endocrine therapy; prior metastatic chemotherapy is not required by this indication.", "TDXD-FDA")],
        [claim("Interstitial lung disease/pneumonitis, including fatal events, and infusion/cytotoxic treatment burden are important considerations.", "DB06")],
        [claim("HER2-low primary population: PFS 13.2 vs 8.1 months; HR 0.62, 95% CI 0.52–0.75, versus chemotherapy.", "DB06")],
        "DESTINY-Breast06 excluded prior metastatic chemotherapy. HER2-ultralow analysis was exploratory; do not assign HER2-low estimates to all subgroups."),
    option("datodxd", "Datopotamab deruxtecan (Dato-DXd)", "Antibody–drug conjugates", "IV infusions", "prior_chemo",
        [claim("Offers a TROP2-directed ADC mechanism after endocrine therapy and chemotherapy for advanced disease.", "DATO-FDA")],
        [claim("Stomatitis, ocular toxicity and pneumonitis require assessment. Reported analysis did not demonstrate an OS improvement.", "DATO-FDA")],
        [claim("TROPION-Breast01: PFS 6.9 vs 4.9 months; HR 0.63, 95% CI 0.52–0.76, versus chemotherapy.", "DATO-FDA")],
        "Prior endocrine-based therapy AND chemotherapy for unresectable/metastatic disease required in the U.S. indication."),
    option("sacituzumab", "Sacituzumab govitecan", "Antibody–drug conjugates", "IV infusions", "two_additional",
        [claim("A TROP2-directed option with randomized survival evidence in heavily pretreated HR+/HER2− disease.", "TROPICS2")],
        [claim("Neutropenia, diarrhea, fatigue and repeated infusions add treatment burden.", "TROPICS2")],
        [claim("TROPiCS-02: OS 14.4 vs 11.2 months; HR 0.789, 95% CI 0.646–0.964, versus single-agent chemotherapy.", "TROPICS2")],
        "Label requires endocrine-based therapy and ≥2 additional metastatic systemic therapies; trial patients had substantial prior chemotherapy."),
    option("chemotherapy", "Conventional chemotherapy", "Chemotherapy", "Oral or IV, depending on agent", "any",
        [claim("A treatment route when endocrine approaches are unsuitable/exhausted or rapid disease control is needed; selection depends on clinical context.", "PDQ", "ABC")],
        [claim("Toxicity varies by agent. Capecitabine, for example, can cause hand–foot syndrome, diarrhea, fatigue and cytopenias.", "CAPE")],
        [claim("Without visceral crisis, sequential endocrine-based approaches are often considered before chemotherapy; the optimal sequence remains uncertain.", "PDQ")],
        "This card is a strategy, not one regimen. Do not assume oral chemotherapy has the same burden as an infusion regimen."),
    option("olaparib", "Olaparib / PARP branch", "Additional branches", "Oral treatment", "gbrca",
        [claim("Olaparib has randomized evidence in germline BRCA-mutated HER2− metastatic disease.", "OLYMPIAD")],
        [claim("Biomarker selection and prior chemotherapy/endocrine requirements must be checked; trial evidence is not specific to modern post-CDK4/6 sequencing.", "OLAP-NCI", "OLYMPIAD")],
        [claim("The breast cancer indication is germline BRCA-selected; a negative result does not support this branch.", "OLAP-NCI")],
        "This branch requires additional treatment-history and safety assessment, not mutation status alone."),
    option("postmonarch", "Abemaciclib + fulvestrant", "Additional branches", "Oral drug + IM injections", "any",
        [claim("Randomized postMONARCH evidence specifically addresses treatment after CDK4/6 progression.", "POSTMONARCH")],
        [claim("The investigator-assessed median PFS difference was modest; adding abemaciclib brings monitoring and toxicity burden.", "POSTMONARCH", "EMBER3")],
        [claim("Investigator-assessed PFS: 6.0 vs 5.3 months; HR 0.73, 95% CI 0.57–0.95, versus placebo + fulvestrant.", "POSTMONARCH")],
        "Prior CDK4/6 agent and treatment sequence matter. Do not treat all CDK4/6 continuation strategies as equivalent."),
]

# Stable claim identifiers allow references to be checked independently of prose.
for item in OPTIONS:
    for section in ("pros", "cons", "evidence"):
        for i, statement in enumerate(item[section], 1):
            statement["id"] = f"{item['id']}.{section}.{i}"

DEFAULT_CASE = dict(
    age=62, er_positive=True, her2="low", menopausal="postmenopausal",
    esr1="detected", pik3ca="detected", akt1="not_detected", pten="not_detected",
    gbrca="not_detected", prior_cdk="ribociclib", prior_endocrine="aromatase_inhibitor",
    endocrine_months=22, prior_metastatic_chemo=0, additional_metastatic_lines=0,
    prior_adc=False, visceral_crisis=False, ecog=1, organ_function="adequate",
    diabetes="no", ild_history="no", preference="fewer_visits",
)
