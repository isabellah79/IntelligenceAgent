"""Cited population-design options, distinct from individual treatment selection.

Criteria are protocol drafts with explicit provenance. A source cohort is not
automatically evidence of a predictive interaction or of an optimal population.
"""
from copy import deepcopy

from .evidence import AS_OF, OPTIONS, SOURCES
from .endpoint_comparison import ENDPOINTS

VERSION = "population-design-1.0"
SCOPE = "HR+/HER2− metastatic breast cancer after progression on endocrine therapy plus a CDK4/6 inhibitor"
POPULATION_SOURCES = deepcopy(SOURCES)
POPULATION_SOURCES["DB06-TTP"]=dict(id="DB06-TTP",title="DESTINY-Breast06 · prior endocrine/CDK4/6 duration analysis",
    url="https://pubmed.ncbi.nlm.nih.gov/41780642/",scope="Post hoc subgroups by prior first-line ET + CDK4/6 time to progression; benefit across duration groups, not a confirmed predictive interaction.",
    kind="Exploratory trial publication",checked_on=AS_OF)
for key,title,slug,scope in [
    ("FDA-PS","FDA · eligibility and performance status","performance-status","Performance-status eligibility should be scientifically justified rather than copied automatically."),
    ("FDA-CNS","FDA · eligibility and brain metastases","brain-metastases","Consider inclusion of appropriately selected patients with brain metastases; avoid an unjustified blanket exclusion."),
    ("FDA-LABS","FDA · eligibility and laboratory values","laboratory-values","Laboratory thresholds require drug- and protocol-specific justification."),
    ("FDA-WASHOUT","FDA · washout periods and concomitant medications","washout-periods-and-concomitant-medications","Washout and medication restrictions require scientific justification."),
]:
    POPULATION_SOURCES[key]=dict(id=key,title=title,url="https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cancer-clinical-trial-eligibility-criteria-"+slug,
                                scope=scope,kind="Regulatory guidance",checked_on=AS_OF)


def statement(text, refs):
    return dict(text=text,source_ids=list(refs))


def criterion(key,text,purpose,reason,refs,status="evidence_supported"):
    return dict(key=key,text=text,purpose=purpose,reason=reason,source_ids=list(refs),status=status)


def cohort(key,title,biomarker,refs,*,kind="reference",axis="Biomarker selection",extra=None,
           effect=None,transfer="direct",benefit=None,pros=None,cons=None,scope_note=None):
    return dict(key=key,title=title,biomarker=biomarker,source_ids=list(refs),kind=kind,axis=axis,
                extra=extra or [],effect=effect,transfer="unestablished" if effect is None and transfer=="direct" else transfer,
                benefit=benefit,pros=pros or [],cons=cons or [],scope_note=scope_note)


def source_effect(oid,**changes):
    return {**deepcopy(ENDPOINTS[oid]),**changes}


LONG_RESPONSE = criterion("prior_duration","Require at least 12 months on the preceding endocrine + CDK4/6 regimen.","efficacy",
    "An enrichment hypothesis based on prior endocrine sensitivity; duration is not itself a validated predictive biomarker.",["PDQ"],"design_assumption")
INCLUSIVE_PS = criterion("performance_status","Allow selected ECOG 2 participants after drug-specific medical review; define a separate stratum.","generalizability",
    "Tests broader participation. Guidance supports considering broader eligibility, not equivalent efficacy or safety in every subgroup.",["FDA-PS"],"design_assumption")


def definitions():
    """Three explicit alternatives per regimen; unknown effects remain unknown."""
    return {
        "elacestrant":[
            cohort("esr1","ESR1-mutated reference population","Require a qualifying ESR1 mutation confirmed by a specified assay.",["EMERALD","ELAC-FDA"],
                   effect=source_effect("elacestrant"),
                   extra=[criterion("prior_lines","Specify 1–2 prior endocrine lines and no more than one prior chemotherapy regimen, following EMERALD's reported history.","evidence_alignment","Keeps the proposed treatment history close to the published population.",["EMERALD"])],
                   benefit="Randomized PFS benefit versus standard endocrine monotherapy was demonstrated in the ESR1-mutated population; this does not establish superiority over other active regimens."),
            cohort("long_response","ESR1-mutated + longer prior endocrine benefit","Require a qualifying ESR1 mutation.",["EMERALD-DURATION"],kind="exploratory",axis="Prior endocrine duration",
                   extra=[{**LONG_RESPONSE,"status":"exploratory","source_ids":["EMERALD-DURATION"],"reason":"This threshold defines the published post hoc subgroup; it is not a confirmed requirement for benefit."}],
                   effect=source_effect("elacestrant",trial="EMERALD · post hoc duration subgroup",population="ESR1-mutated, prior ET + CDK4/6 ≥12 months",median_pfs_months=[8.6,1.9],hazard_ratio=.41,source_ids=["EMERALD-DURATION"]),
                   benefit="A larger observed relative effect was reported in this post hoc subgroup. No multiplicity adjustment or proven predictive duration interaction is supplied.",
                   cons=[statement("A mandatory duration threshold may exclude patients who could benefit; the subgroup estimate must not be treated as a confirmed improvement over the broader cohort.",["EMERALD-DURATION"])]),
            cohort("unselected","ESR1-unselected research population","Allow ESR1-mutated and non-mutated disease; record status and prespecify strata.",["EMERALD","ELAC-FDA"],kind="broader",axis="Broader biomarker eligibility",
                   effect=source_effect("elacestrant",population="EMERALD overall population; ESR1 unselected",median_pfs_months=None,hazard_ratio=.70,source_ids=["EMERALD"]),
                   benefit="The trial reported an overall-population PFS result. It does not establish benefit specifically in ESR1-wild-type disease.",
                   scope_note="A research alternative beyond the cited ESR1-mutated indication; requires separate scientific and regulatory justification."),
        ],
        "capivasertib":[
            cohort("pathway","PIK3CA / AKT1 / PTEN-altered population","Require at least one qualifying PIK3CA, AKT1 or PTEN alteration.",["CAPITELLO","CAPI-LABEL"],effect=source_effect("capivasertib"),transfer="mixed_prior_cdk",
                   extra=[criterion("prior_partner","Document progression on an aromatase-inhibitor-based regimen and the CDK4/6 partner.","evidence_alignment","The proposed all-post-CDK4/6 setting is narrower than the published mixed-exposure population.",["CAPITELLO"])],
                   benefit="Randomized PFS benefit was demonstrated in the pathway-altered population. Its aggregate HR is not an exclusively post-CDK4/6 estimate."),
            cohort("pik3ca","PIK3CA-mutated enrichment hypothesis","Restrict to qualifying PIK3CA mutations; characterize AKT1/PTEN and co-alterations.",["CAPITELLO","CAPI-LABEL"],kind="hypothesis",axis="One molecular subgroup",
                   benefit="PIK3CA is part of the studied altered population; greater benefit from restricting to this component is not established by the supplied aggregate result."),
            cohort("unselected","Pathway-unselected research population","Allow altered and non-altered tumors; require testing and prespecified biomarker strata.",["CAPITELLO","CAPI-LABEL"],kind="broader",axis="Broader biomarker eligibility",transfer="mixed_prior_cdk",
                   effect=source_effect("capivasertib",population="CAPItello-291 overall population; mixed prior CDK4/6",median_pfs_months=[7.2,3.6],hazard_ratio=.60),
                   benefit="The overall trial result includes altered and non-altered tumors and does not prove benefit in the non-altered subgroup alone.",scope_note="Beyond the cited biomarker-selected indication; a trial hypothesis, not an established treatment population."),
        ],
        "tdxd":[
            cohort("her2low","HER2-low, no prior metastatic chemotherapy","Require HER2 IHC 1+ or IHC 2+/ISH-negative disease.",["DB06","TDXD-FDA"],effect=source_effect("tdxd"),transfer="mixed_prior_cdk",
                   extra=[criterion("prior_chemo","Exclude prior chemotherapy for metastatic disease for this DB06-aligned cohort.","evidence_alignment","Defines the source-trial setting rather than a universal safety restriction.",["DB06"])],
                   benefit="Primary-population PFS benefit versus investigator-choice chemotherapy was demonstrated. HER2-low is not proven to benefit more than ultralow by comparing separate subgroup estimates."),
            cohort("ultralow","HER2-ultralow exploratory population","Require IHC 0 with membrane staining; exclude IHC 0 without membrane staining.",["DB06","TDXD-FDA"],kind="exploratory",axis="HER2 expression",
                   extra=[criterion("prior_chemo","Exclude prior metastatic chemotherapy for source-setting alignment.","evidence_alignment","Keeps the setting aligned with DB06.",["DB06"])],
                   benefit="DB06 included an exploratory ultralow cohort. The HER2-low primary HR is not assigned to this population."),
            cohort("rapid_progression","HER2-low / ultralow + early endocrine progression","Require HER2-low or ultralow disease and progression within 6 months of first-line ET + CDK4/6.",["DB06-TTP","DB06"],kind="exploratory",axis="Prior endocrine duration",
                   extra=[criterion("prior_chemo","Exclude prior metastatic chemotherapy for source-setting alignment.","evidence_alignment","Maintains the DB06 chemotherapy-naive setting.",["DB06"])],
                   effect=source_effect("tdxd",trial="DESTINY-Breast06 · post hoc TTP <6 months",population="HER2-low/ultralow; first-line ET + CDK4/6 TTP <6 months",median_pfs_months=[14.0,6.5],hazard_ratio=None,source_ids=["DB06-TTP"]),
                   benefit="A post hoc analysis reported benefit in early progression and the other duration groups. It did not establish early progression as a predictive selection rule.",scope_note="The comparison is exploratory. Its median PFS is shown, but no HR is inferred from the medians."),
        ],
        "gedatolisib":[
            cohort("triplet","No PIK3CA mutation detected · triplet","Require no PIK3CA mutation detected using the specified assay.",["GEDA-FDA","GEDA-LABEL"],effect=source_effect("gedatolisib"),
                   benefit="The source comparison is gedatolisib + fulvestrant + palbociclib versus fulvestrant. It does not establish a predictive comparison against PIK3CA-mutated patients."),
            cohort("long_response","No PIK3CA mutation detected + longer prior endocrine benefit","Require no PIK3CA mutation detected.",["GEDA-FDA","GEDA-LABEL","PDQ"],kind="hypothesis",axis="Prior endocrine duration",extra=[LONG_RESPONSE],
                   benefit="Tests a prior-duration enrichment hypothesis for the triplet. No duration-specific comparative HR is supplied; the aggregate triplet effect is not inherited."),
            cohort("inclusive","No PIK3CA mutation detected · broader functional status","Require no PIK3CA mutation detected.",["GEDA-LABEL","FDA-PS"],kind="hypothesis",axis="Broader functional status",extra=[INCLUSIVE_PS],
                   benefit="A broader-eligibility hypothesis with unquantified efficacy and safety in the expanded population."),
        ],
    }


def remaining_definitions():
    rows={}
    for oid,ref in [("imlunestrant","IMLU-FDA"),("imlunestrant_abemaciclib","EMBER3"),("vepdegestrant","VERITAC2")]:
        rows[oid]=[
            cohort("esr1","ESR1-mutated post-CDK4/6 population","Require a qualifying ESR1 mutation; document prior endocrine and CDK4/6 agents.",[ref],effect=source_effect(oid),
                   transfer="direct" if oid=="vepdegestrant" else "mixed_prior_cdk",
                   kind="exploratory" if oid=="imlunestrant_abemaciclib" else "reference",
                   benefit="The source supports the specified ESR1-mutated comparison. Confirmatory versus exploratory analysis and prior-CDK4/6 exposure remain explicit in the evidence record."),
            cohort("long_response","ESR1-mutated + longer prior endocrine benefit","Require a qualifying ESR1 mutation.",[ref,"PDQ"],kind="hypothesis",axis="Prior endocrine duration",extra=[LONG_RESPONSE],
                   benefit="Tests prior endocrine sensitivity as an enrichment hypothesis. The elacestrant duration result is not transferred to this drug."),
            cohort("inclusive","ESR1-mutated + broader functional status","Require a qualifying ESR1 mutation.",[ref,"FDA-PS"],kind="hypothesis",axis="Broader functional status",extra=[INCLUSIVE_PS],
                   benefit="Tests generalizability; broader eligibility is not evidence of equivalent drug benefit in ECOG 2."),
        ]
    rows["alpelisib"]=[
        cohort("pik3ca","PIK3CA-mutated post-CDK4/6 population","Require a qualifying PIK3CA mutation.",["ALPEL-LABEL"],effect=source_effect("alpelisib"),transfer="indirect",
               benefit="Biomarker-selected rationale is supported, but the supplied pivotal evidence is not a dedicated comparative post-CDK4/6 estimate."),
        cohort("ai_sequence","PIK3CA-mutated immediately after AI + CDK4/6","Require a qualifying PIK3CA mutation and AI + CDK4/6 as the immediately preceding regimen.",["ALPEL-LABEL","PDQ"],kind="hypothesis",axis="Immediate prior treatment",
               benefit="A precise sequencing proposal. No comparative effect for this narrowed post-CDK4/6 cohort is supplied in this snapshot."),
        cohort("inclusive","PIK3CA-mutated + broader functional status","Require a qualifying PIK3CA mutation.",["ALPEL-LABEL","FDA-PS"],kind="hypothesis",axis="Broader functional status",extra=[INCLUSIVE_PS],
               benefit="Requires drug-specific glucose and tolerability assessment; expanding eligibility does not establish greater efficacy."),
    ]
    for oid,ref,min_lines in [("datodxd","DATO-FDA",1),("sacituzumab","TROPICS2",2)]:
        history=("Require prior endocrine therapy and at least one chemotherapy regimen for advanced disease." if oid=="datodxd" else
                 "Require prior endocrine therapy plus at least two additional metastatic systemic therapies; document chemotherapy-heavy source-population alignment.")
        rows[oid]=[
            cohort("pretreated","Previously treated reference population",history,[ref],effect=source_effect(oid),transfer="mixed_prior_cdk" if oid=="datodxd" else "direct",
                   benefit="The randomized comparison supports the specified pretreated source population, not every earlier or ADC-exposed subgroup."),
            cohort("earlier","Earlier treatment-line hypothesis","Study the regimen before the source population's required prior-treatment burden; specify the exact line.",[ref,"PDQ"],kind="hypothesis",axis="Earlier treatment line",
                   benefit="Greater benefit earlier in the sequence is unproven by the supplied later-line result.",scope_note="This research cohort differs from the cited indication; source HR is not transferred."),
            cohort("prior_adc","Prior ADC-exposed sequencing hypothesis",history+" Allow and stratify prior ADC exposure.",[ref],kind="hypothesis",axis="ADC sequence",
                   benefit="No comparative estimate for the proposed ADC-to-ADC sequence is supplied; target/payload and prior resistance must be specified."),
        ]
    rows["olaparib"]=[
        cohort("gbrca","Germline BRCA1/2-mutated population","Require a pathogenic germline BRCA1/2 alteration and document prior chemotherapy/endocrine context.",["OLYMPIAD","OLAP-NCI"],effect=source_effect("olaparib"),transfer="indirect",
               benefit="Randomized evidence supports germline BRCA-selected disease, but is not specific to this modern post-CDK4/6 sequence."),
        cohort("no_chemo","Germline BRCA-mutated, chemotherapy-naive research cohort","Require a qualifying germline BRCA1/2 alteration and no prior chemotherapy.",["OLAP-NCI","OLYMPIAD"],kind="hypothesis",axis="Prior chemotherapy",
               benefit="A sequencing hypothesis beyond the supplied prior-chemotherapy context; no effect is inherited from OlympiAD.",scope_note="Requires separate regulatory and scientific justification."),
        cohort("inclusive","Germline BRCA-mutated + broader functional status","Require a qualifying germline BRCA1/2 alteration.",["OLAP-NCI","FDA-PS"],kind="hypothesis",axis="Broader functional status",extra=[INCLUSIVE_PS],
               benefit="An expanded-eligibility hypothesis with no supplied subgroup-specific comparative estimate."),
    ]
    rows["postmonarch"]=[
        cohort("post_ai","After CDK4/6 + aromatase inhibitor","Require progression on prior CDK4/6 + aromatase inhibitor; specify treatment history against the source protocol.",["POSTMONARCH"],effect=source_effect("postmonarch"),
               benefit="Investigator-assessed primary PFS supports this comparison; the BICR result is not substituted into the forecast."),
        cohort("long_response","Longer prior endocrine benefit hypothesis","Require prior CDK4/6 + aromatase inhibitor.",["POSTMONARCH","PDQ"],kind="hypothesis",axis="Prior endocrine duration",extra=[LONG_RESPONSE],
               benefit="A candidate enrichment rule, not a validated duration-dependent benefit for this regimen."),
        cohort("inclusive","Post-CDK4/6 + broader functional status","Require prior CDK4/6 + aromatase inhibitor.",["POSTMONARCH","FDA-PS"],kind="hypothesis",axis="Broader functional status",extra=[INCLUSIVE_PS],
               benefit="Tests broader trial participation; benefit magnitude in the expanded population is unknown."),
    ]
    rows["chemotherapy"]=[
        cohort("capecitabine","Capecitabine after endocrine options become unsuitable","Specify capecitabine as the chemotherapy regimen and document endocrine resistance or unsuitability.",["CAPE","PDQ"],
               benefit="A regimen-specific research population. No single comparative post-CDK4/6 HR or unique predictive biomarker is supplied."),
        cohort("chemo_naive","Capecitabine as first metastatic chemotherapy","Specify capecitabine; require no prior metastatic chemotherapy and document prior endocrine + CDK4/6 progression.",["CAPE","PDQ"],kind="hypothesis",axis="Chemotherapy line",
               benefit="A sequencing hypothesis. An earlier line does not by itself prove a larger incremental treatment effect."),
        cohort("inclusive","Capecitabine + broader functional status","Specify capecitabine and prior endocrine + CDK4/6 progression.",["CAPE","FDA-PS"],kind="hypothesis",axis="Broader functional status",extra=[INCLUSIVE_PS],
               benefit="Tests participation beyond a narrowly fit population, subject to regimen-specific safety review."),
    ]
    return rows


SAFETY = {
    "capivasertib":("Resolve uncontrolled glucose abnormalities and clinically important rash/diarrhea risk before enrollment; define drug-specific thresholds.","CAPI-LABEL"),
    "alpelisib":("Resolve uncontrolled glucose abnormalities and assess severe rash/diarrhea risk before enrollment; define fasting glucose/HbA1c criteria.","ALPEL-LABEL"),
    "gedatolisib":("Assess stomatitis, skin toxicity and glucose risk; define management and recovery requirements.","GEDA-LABEL"),
    "tdxd":("Exclude active or suspected ILD/pneumonitis pending pulmonary assessment; adjudicate prior ILD and define cardiac monitoring.","TDXD-FDA"),
    "datodxd":("Assess active ILD/pneumonitis, ocular disease and stomatitis; define pulmonary, ophthalmic and recovery criteria.","DATO-FDA"),
    "sacituzumab":("Resolve clinically important neutropenia, infection and diarrhea risk; define marrow and recovery thresholds.","TROPICS2"),
    "vepdegestrant":("Assess QTc prolongation and interacting medicines; specify ECG and medication rules.","VERITAC2"),
    "imlunestrant_abemaciclib":("Assess cytopenias, diarrhea, hepatic injury, ILD and thromboembolic risk; define recovery and monitoring rules.","EMBER3"),
    "postmonarch":("Assess abemaciclib-related cytopenia, diarrhea, hepatic, pulmonary and thromboembolic risks; define monitoring rules.","EMBER3"),
    "olaparib":("Assess hematologic and organ-function risks, prior therapies and interacting medicines against the full protocol and label.","OLAP-NCI"),
    "chemotherapy":("Assess capecitabine-specific contraindications, DPD/DPYD context, renal function and gastrointestinal toxicity; define protocol-specific thresholds.","CAPE"),
}


def build_library():
    definitions_by_id={**definitions(),**remaining_definitions()}
    treatments=[]
    for template in OPTIONS:
        oid=template["id"];t={k:deepcopy(template[k]) for k in ("id","title","family","route","pros","cons","evidence")}
        if oid=="gedatolisib":t.update(title="Gedatolisib + fulvestrant + palbociclib",route="IV infusions + IM injections + oral drug")
        if oid=="chemotherapy":t.update(title="Capecitabine (chemotherapy example)",route="Oral chemotherapy")
        t["populations"]=[]
        for definition in definitions_by_id[oid]:
            p=deepcopy(definition);p["id"]=oid+"__"+p.pop("key");p["treatment_id"]=oid
            refs=p["source_ids"]
            p["inclusion"]=[
                criterion("disease","HR-positive, HER2-negative metastatic breast cancer.","scope","The user-defined parent population; biomarker refinements appear below.",refs),
                criterion("post_cdk","Document progression on endocrine therapy plus a CDK4/6 inhibitor in the advanced-disease setting.","scope","Required project scope. Some reference trials contain broader prior-treatment populations.",refs,"design_assumption"),
                criterion("selection",p.pop("biomarker"),"efficacy","Defines this candidate population; evidence strength is recorded separately.",refs,"design_assumption" if p["kind"]=="hypothesis" else "evidence_supported"),
                *p.pop("extra"),
                criterion("consent","Adults able to provide informed consent; document menopausal/ovarian-suppression and reproductive requirements for the selected regimen.","design","Operational protocol proposal; age, sex and endocrine requirements need regimen-specific confirmation.",refs,"design_assumption"),
            ]
            if oid=="elacestrant" and not any(c["key"]=="prior_lines" for c in p["inclusion"]):
                p["inclusion"].insert(3,criterion("prior_lines","Specify 1–2 prior endocrine lines and no more than one prior chemotherapy regimen, following EMERALD's reported history.","evidence_alignment","Retains the source treatment-history limits while varying the stated population axis.",["EMERALD"]))
            p["exclusion"]=[
                criterion("outside_scope","Exclude disease outside the defined HR+/HER2− metastatic setting.","scope","Keeps the candidate inside the parent research question.",refs),
                criterion("urgent_instability","Exclude urgent organ compromise that makes the protocol's treatment or assessment schedule inappropriate; liver metastases alone are not visceral crisis.","safety","Requires clinical adjudication rather than an anatomical blanket exclusion.",["ABC"],"safety_review"),
                criterion("unresolved_safety",SAFETY.get(oid,("Resolve clinically important regimen-specific contraindications and interacting medicines before enrollment.",refs[0]))[0],"safety","Safety screening is not evidence that the excluded subgroup has less antitumor benefit.",[SAFETY.get(oid,(None,refs[0]))[1]],"safety_review"),
            ]
            p["protocol_pending"]=[
                statement("Finalize assay/variant definitions, prior-agent/line limits and disease-assessment rules against the source protocol.",refs),
                statement("Specify justified laboratory thresholds, recovery and washout periods, concomitant medicines and reproductive precautions.",["FDA-LABS","FDA-WASHOUT"]),
                statement("Set a reasoned performance-status policy and CNS criteria; do not automatically exclude all stable brain metastases.",["FDA-PS","FDA-CNS"]),
            ]
            p["pros"]=[statement("An explicit cohort definition permits a prespecified analysis for this treatment and comparator.",refs),*p["pros"]]
            specific={
                "elacestrant__esr1":("Retains the studied ESR1-selected population without imposing an unconfirmed prior-duration threshold.","The biomarker alone does not identify every patient who will benefit; prior endocrine sensitivity and early progression still need characterization."),
                "elacestrant__long_response":("Has a published duration-defined subgroup signal to motivate a prospective enrichment test.","The ≥12-month rule can exclude shorter-duration patients despite the absence of a confirmed predictive duration interaction."),
                "elacestrant__unselected":("Allows recruitment across ESR1 strata and tests generalizability using a prespecified biomarker analysis.","The overall-population result cannot establish benefit specifically in ESR1-wild-type tumors; the cited indication is ESR1-selected."),
                "capivasertib__pathway":("Retains all three qualifying pathway-alteration groups studied in the biomarker-selected comparison.","Different pathway alterations may remain heterogeneous; the aggregate estimate does not resolve each alteration in an exclusively post-CDK4/6 cohort."),
                "capivasertib__pik3ca":("Makes a single molecular component of the pathway-selected population independently testable.","Excludes patients with AKT1/PTEN alterations alone who are part of the broader selected population; stronger benefit from the restriction is unproven."),
                "capivasertib__unselected":("Can study both biomarker strata and broaden recruitment while retaining alteration testing.","A positive overall result cannot be assigned to the non-altered stratum alone; this cohort goes beyond the cited biomarker-selected indication."),
                "tdxd__her2low":("Uses the HER2-low primary-analysis phenotype and a chemotherapy-naive source setting.","The source population is not exclusively post-CDK4/6; HER2-low versus ultralow benefit differences are not established by separate estimates."),
                "tdxd__ultralow":("Separately evaluates a source-trial subgroup that would be missed by restricting to HER2-low alone.","The ultralow analysis is exploratory; the HER2-low primary HR is not a quantitative effect for this cohort."),
                "tdxd__rapid_progression":("Makes a reported early-endocrine-progression subgroup prospectively testable.","The analysis reported benefit across duration groups, so excluding slower-progressing patients needs an additional scientific rationale."),
            }.get(p["id"])
            if specific:p["pros"].append(statement(specific[0],refs))
            if p["kind"] in {"reference","alternative"}:
                p["pros"].append(statement("Provides a starting population for evidence review, subject to the documented source-to-target differences.",refs))
            elif p["kind"]=="broader":
                p["pros"].append(statement("Can broaden recruitment and applicability; actual eligible-pool size has not been estimated.",refs))
            else:
                p["pros"].append(statement("Makes an enrichment or generalizability hypothesis explicit and testable; a stronger treatment effect is not assumed.",refs))
            p["cons"]=[statement("Subgroup benefit does not establish a predictive interaction, the optimal cohort, or superiority over other active treatments.",refs),*p["cons"]]
            if specific:p["cons"].append(statement(specific[1],refs))
            if p["kind"] in {"hypothesis","exploratory"}:
                p["cons"].append(statement("A narrower rule may slow recruitment and reduce generalizability; subgroup-specific benefit needs validation.",refs))
            p["benefit_statement"]=statement(p.pop("benefit"),refs)
            p["regimen"]=t["title"] if oid!="chemotherapy" else "Capecitabine (chemotherapy example)"
            if p["id"]=="gedatolisib__triplet":p["regimen"]="Gedatolisib + fulvestrant + palbociclib"
            for section in ("inclusion","exclusion","pros","cons","protocol_pending"):
                for i,row in enumerate(p[section]):row["id"]=p["id"]+"."+section+"."+str(row.pop("key",i+1))
            p["benefit_statement"]["id"]=p["id"]+".benefit"
            t["populations"].append(p)
        t["starting_population_id"]=t["populations"][0]["id"]
        t["source_ids"]=sorted({r for p in t["populations"] for r in p["source_ids"]})
        treatments.append(t)
    return treatments
