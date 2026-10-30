"""Evidence-backed scientific grading, separate from checklist and endpoint forecast.

Policy judgments are explicit ordinal anchors, not learned clinical probabilities.
Evidence facts live outside the evaluated answer. IDs, agent labels, self-declared
'reference' status, and numeric endpoint forecasts cannot earn scientific credit.
Unknown cases/constraints remain unassessed rather than falling back to completeness.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from pathlib import Path

from .normalize import concepts, selection_states

DATA = Path(__file__).with_name('data')
DIMENSIONS = ('evidence_strength', 'population_applicability', 'selection_justification', 'tradeoffs')
LABELS = dict(zip(DIMENSIONS, ('Evidence strength', 'Population applicability', 'Selection justification', 'Tradeoffs')))
DEFAULT_CONFIG = dict(version='scientific-v3', scientific_share=.8,
                      dimension_weights=dict(evidence_strength=.35, population_applicability=.25,
                                             selection_justification=.25, tradeoffs=.15))
ANCHORS = {
 'evidence_strength': ['Contradicted or fabricated support', 'Indirect rationale; no candidate-specific comparative estimate',
                       'Exploratory randomized subgroup or noncomparative clinical cohort', 'Prespecified randomized subgroup',
                       'Randomized primary/co-primary population evidence'],
 'population_applicability': ['Outside the defined disease or regimen', 'Major line, exposure or cohort mismatch',
                             'Important extrapolation or additional untested selection', 'Substantial overlap with a mixed source population',
                             'Candidate setting directly represented in the source'],
 'selection_justification': ['No operative selection rule or a contradicted superiority claim', 'Added restriction/expansion without supporting selection evidence',
                            'Plausible, explicitly exploratory selection or generalizability hypothesis',
                            'Studied cohort rationale with a material unresolved selection limitation',
                            'Trial-defined selection with direct clinical/regulatory justification; predictive superiority still requires interaction evidence'],
 'tradeoffs': ['No downside or unsupported quantitative tradeoff', 'Generic caveats only',
               'Population-specific downside linked to a criterion', 'Both sides of selection/expansion addressed with uncertainty and a mitigation/alternative',
               'Documented quantitative tradeoff and justified design choice, with independently reviewed numerical support'],
}


def validate_config(config=None):
    out = deepcopy(DEFAULT_CONFIG if config is None else config)
    if not isinstance(out, dict) or set(out) != set(DEFAULT_CONFIG):
        raise ValueError('Scientific config needs version, scientific_share and dimension_weights')
    share = out['scientific_share']
    if type(share) not in (int,float) or not math.isfinite(share) or not .5 < share <= 1:
        raise ValueError('Scientific grading must have more than half of the final weight')
    weights = out['dimension_weights']
    if not isinstance(weights, dict) or set(weights) != set(DIMENSIONS):
        raise ValueError('Scientific config must name exactly the four scientific dimensions')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v <= 0 for v in weights.values()) or not math.isclose(sum(weights.values()),1):
        raise ValueError('Scientific dimension weights must be positive and sum to 1')
    return out


def load_bank(path=None):
    bank = json.loads(Path(path or DATA/'scientific_evidence_v3.json').read_text())
    if bank.get('schema_version') != '1.0' or not isinstance(bank.get('cases'),dict):
        raise ValueError('Invalid scientific evidence bank')
    for case in bank['cases'].values():
        ids=[r['id'] for r in case['analyses']]
        if len(ids)!=len(set(ids)):
            raise ValueError('Duplicate scientific evidence profile IDs')
        for record in case['analyses']:
            if any(s not in bank.get('sources',{}) for s in record['source_ids']):
                raise ValueError('Scientific evidence profile cites an unknown source')
    raw = json.dumps(bank, sort_keys=True, ensure_ascii=False).encode()
    bank['sha256'] = hashlib.sha256(raw).hexdigest()
    return bank


def enrich_catalog(catalog, bank):
    """Expose factual evidence to every producer, never grading anchors or scores."""
    for sid, source in bank.get('sources',{}).items():
        if sid not in catalog.records:
            catalog.records[sid] = dict(id=sid, title=source['title'], url=source['url'],
                                       kind=source.get('kind','Trial publication'), scope=source['finding'])
        catalog.records[sid]['scientific_facts'] = source['finding']
        catalog.records[sid]['scientific_facts_url'] = source['url']
    return catalog


def _selection(option):
    rows = [r for r in option.get('inclusion',[]) if r.get('purpose') not in ('scope','safety','design')]
    # Full sentences are retained in the audit; generic consent/safety text never
    # becomes evidence of antitumor enrichment.
    text = ' '.join(r['text'] for r in rows).lower().replace('−','-')
    operative = ' '.join(r['text'].split(';')[0] for r in rows).lower()
    states = selection_states(operative)
    if 'esr1' in states:
        biomarker = 'esr1_'+states['esr1']
    elif 'brca' in states:
        biomarker = 'gbrca' if 'germline' in operative else 'brca_unspecified'
    elif re.search(r'no pik3ca mutation|pik3ca.{0,12}(wild.type|not detected)',operative):
        biomarker = 'pik3ca_not_detected'
    elif re.search(r'allow altered and non.altered|pathway.unselected',operative):
        biomarker = 'pathway_unselected'
    elif {'pik3ca','akt1','pten'} <= concepts(operative):
        biomarker = 'pathway_altered'
    elif 'pik3ca' in states:
        biomarker = 'pik3ca_altered' if states['pik3ca']=='altered' else 'pik3ca_'+states['pik3ca']
    elif 'her2_ultralow' in concepts(text) or 'ultralow' in text:
        biomarker = 'her2_both' if re.search(r'her2.low or ultralow|low / ultralow',text) else 'her2_ultralow'
    elif 'her2_low' in concepts(text):
        biomarker = 'her2_low'
    else:
        biomarker = None
    duration = re.search(r'(?:at least|>=|≥)\s*(\d+)\s*months',text)
    rapid = re.search(r'(?:within|<|less than)\s*(\d+)\s*months',text)
    ecog = re.search(r'(?:allow|include|selected).{0,25}ecog\s*2',text)
    prior_adc = re.search(r'(?:allow|include).{0,35}prior adc',text)
    earlier = re.search(r'before the source|earlier.{0,15}(line|sequence)|before.{0,30}required prior',text)
    no_chemo = bool(re.search(r'no prior (?:metastatic )?chemotherapy|exclude prior (?:metastatic )?chemotherapy|exclude prior chemotherapy for metastatic',text))
    immediate_ai = bool(re.search(r'ai\s*\+\s*cdk4/6 as the immediately preceding|immediate.{0,35}(aromatase|ai\b)',text))
    profile = dict(biomarker=biomarker, duration_min=int(duration[1]) if duration else None,
                   rapid_months=int(rapid[1]) if rapid else None, ecog2=bool(ecog),
                   prior_adc=bool(prior_adc), earlier_line=bool(earlier), no_chemo=no_chemo,
                   immediate_ai=immediate_ai)
    return profile, rows


def _profile(case, selection):
    """Match fact profiles on operative selectors, not option IDs or self-labels."""
    matches = []
    for record in case['analyses']:
        selector = record.get('selector',{})
        if all(selection.get(k)==v for k,v in selector.items()):
            matches.append(record)
    if not matches:
        return None
    specificity = max(len(r.get('selector',{})) for r in matches)
    best = [r for r in matches if len(r.get('selector',{}))==specificity]
    if len(best)!=1:
        return None
    return best[0]


def _citations(option):
    return {sid for section in ('inclusion','exclusion','pros','cons','defense')
            for row in option.get(section,[]) for sid in row.get('source_ids',[])}


def _row(dimension, grade, reason, source_ids, criterion_ids=(), limitations=()):
    return dict(dimension=dimension, label=LABELS[dimension], grade=grade, max_grade=4,
                reason=reason, source_ids=sorted(set(source_ids)), criterion_ids=list(criterion_ids),
                limitations=list(limitations), origin='Explicit provisional grading policy applied to independently stored source facts')


def _tradeoffs(option, selection, source_ids):
    pros = ' '.join(r['text'] for r in option.get('pros',[])).lower()
    cons = ' '.join(r['text'] for r in option.get('cons',[])).lower()
    defense = ' '.join(r['text'] for r in option.get('defense',[])).lower()
    selected_concepts = set().union(*(concepts(r['text']) for r in option.get('inclusion',[]) if r.get('purpose')=='efficacy'))
    population_specific = bool(selected_concepts & concepts(cons)) or any(w in cons for w in
        ('threshold','restriction','restricting','expanded','narrower','earlier','non-altered','wild-type','excluded','exclude','ecog 2','duration','subgroup-specific','adc-to-adc'))
    uncertainty = bool(re.search(r'unproven|not establish|unconfirmed|unknown|needs?.{0,15}validat|exploratory|hypothesis',cons+' '+defense))
    mitigation = bool(re.search(r'stratif|strata|alternative|without imposing|may exclude|excludes patients|separate.{0,20}(analysis|justif|cohort)',pros+' '+cons+' '+defense))
    if not cons:
        grade,reason=0,'No downside is supplied.'
    elif not population_specific:
        grade,reason=1,'Caveats are generic; the loss or risk caused by this selection rule is not made explicit.'
    elif pros and uncertainty and mitigation:
        grade,reason=3,'A population-specific downside, an explicit uncertainty and an alternative/mitigation are discussed alongside the proposed benefit.'
    else:
        grade,reason=2,'A criterion-specific downside is discussed, but the decision between enrichment, access and recruitment is not fully defended.'
    # Numeric prevalence or benefit assertions are never validated by a regex.
    # The rule-based grader cannot grant level 4 without adjudicated quantities.
    return _row('tradeoffs',grade,reason,source_ids,limitations=['Qualitative text screen; level 4 requires independently reviewed numerical tradeoff evidence.'])


def assess_population(option, case_id, bank, config=None, trial=None):
    config=validate_config(config)
    case=bank['cases'].get(case_id)
    selection,criteria=_selection(option)
    base=dict(option_id=option['option_id'], method='evidence_rules_v3', provisional=True,
              calibrated=False, extracted_selection=selection, evidence_bank_sha256=bank['sha256'])
    if trial and trial.get('primary_endpoint') not in (None,'','PFS'):
        return dict(**base,status='unassessed',score=None,dimensions=[],reason='The source bank covers PFS; it cannot grade a different target endpoint by transferring PFS evidence.')
    if case is None:
        return dict(**base,status='unassessed',score=None,dimensions=[],reason='No independently curated evidence case matches this treatment context.')
    from .rubric import _scope_respected
    if not _scope_respected(dict(options=[option]))['pass_']:
        return dict(**base,status='unassessed',score=None,dimensions=[],reason='The inclusion criteria do not preserve the fixed HR+/HER2-negative metastatic post-CDK4/6 population. The source effect cannot be transferred.')
    record=_profile(case,selection)
    if record is None:
        return dict(**base,status='unassessed',score=None,dimensions=[],reason='Selection does not match one unambiguous evidence profile; clinical mapping is required.')
    if trial and trial.get('comparator') and trial['comparator'].strip().lower()!=str(record.get('comparator','')).strip().lower():
        return dict(**base,status='unassessed',score=None,dimensions=[],reason='The requested comparator is not the reviewed source comparison. Cross-trial efficacy transfer is not graded.')
    citations=_citations(option)
    source_ids=record['source_ids']
    cited=bool(citations & set(source_ids))
    extra=[]
    selector=record.get('selector',{})
    for key in ('duration_min','rapid_months','ecog2','prior_adc','earlier_line','no_chemo','immediate_ai'):
        if selection[key] and key not in selector and key not in case.get('source_constraints',[]):
            extra.append(key)
    # A new operative efficacy clause the parser cannot interpret prevents a
    # confident source match. Do not award the parent study's grade by default.
    known_tokens={'esr1','pik3ca','akt1','pten','brca','her2_low','her2_ultralow','prior_cdk','prior_endocrine',
                  'prior_chemo','prior_adc','prior_lines','performance_status'}
    def mapped(row):
        text=row['text'].lower()
        if concepts(text) & known_tokens:
            return True
        return bool(re.search(r'allow altered and non.altered|before the source|earlier.{0,15}(line|sequence)|specify capecitabine',text))
    unmapped=[r for r in criteria if r.get('purpose')=='efficacy' and not mapped(r)]
    known_markers={'ESR1','HER2','BRCA1','BRCA2','BRCA1/2','PIK3CA','AKT1','CDK4','CDK6','CDK4/6','IHC0','IHC1','IHC2'}
    for row in criteria:
        if row.get('purpose')!='efficacy':
            continue
        markers=set(re.findall(r'\b[A-Z][A-Za-z]*\d+(?:/\d+)?\b',row['text']))
        if markers-known_markers or re.search(r'\d+\s*%',row['text']):
            unmapped.append(row)
    if unmapped:
        return dict(**base,status='unassessed',score=None,dimensions=[],reason='An efficacy-selection clause has no supported mapping in the evidence bank.',unmapped_criteria=[r['text'] for r in unmapped])
    level={'randomized_primary':4,'randomized_prespecified_subgroup':3,'randomized_exploratory':2,
           'single_arm':2,'indirect_guidance':1,'unreported_subgroup':1}[record['analysis_type']]
    evidence_reason=record['finding']
    limits=list(record.get('limitations',[]))
    if extra:
        level=min(level,1)
        evidence_reason+=' Additional selection is not evaluated by that analysis: '+', '.join(extra)+'. The parent effect is not inherited.'
    if not cited:
        level=min(level,1)
        evidence_reason+=' The answer does not cite the evidence supporting this population-specific profile.'
        limits.append('Relevant evidence may exist in the bank but is not cited by the submitted defense.')
    applicability={'required':4,'mixed':3,'indirect':2,'unknown':None}[record['prior_cdk']]
    if applicability is None:
        return dict(**base,status='unassessed',score=None,dimensions=[],reason='Prior-CDK4/6 applicability is unresolved in the reviewed source.')
    applicability_reason='Source prior-CDK4/6 setting: '+record['prior_cdk']+'. '+record.get('setting_note','')
    if extra:
        applicability=min(applicability,1 if any(k in extra for k in ('earlier_line','prior_adc','no_chemo')) else 2)
        applicability_reason+=' The additional selection/expansion needs its own population evidence.'
    justification={'trial_defined':4,'studied_broadening':3,'exploratory_only':2,'unsupported_restriction':1,
                   'indirect_rationale':2}[record['selection_support']]
    selection_reason=record['selection_reason']
    if extra:
        # Caution improves honest reasoning but does not turn a new threshold into
        # validated selection. A new population can be scientifically worth testing.
        text=' '.join(r['text']+' '+str(r.get('reason','')) for r in criteria+option.get('defense',[])+option.get('cons',[])).lower()
        honest=bool(re.search(r'hypothes|unproven|not.{0,20}(establish|validated|confirmed)|unknown|unquantified|needs?.{0,15}validat',text))
        justification=min(justification,2 if honest else 1)
        selection_reason+=' The added rule is a research hypothesis, not demonstrated enrichment.'
    from .rubric import _overclaims
    overclaims=[r['text'] for section in ('defense','pros') for r in option.get(section,[]) if _overclaims(r['text'])]
    if overclaims and (record.get('interaction_supported') is not True or extra):
        justification=0
        selection_reason+=' An unsupported superiority/predictive claim overstates the available evidence.'
        limits.append('Unsupported absolute claim: '+overclaims[0])
    rationale_ids=[r.get('id',str(i)) for i,r in enumerate(criteria)]
    rows=[_row('evidence_strength',level,evidence_reason,source_ids,rationale_ids,limits),
          _row('population_applicability',applicability,applicability_reason,source_ids,rationale_ids),
          _row('selection_justification',justification,selection_reason,source_ids,rationale_ids,
               ['Trial inclusion and observed subgroup benefit do not establish a predictive interaction.']),
          _tradeoffs(option,selection,source_ids)]
    if not any(r.get('reason') for r in criteria) or not option.get('defense'):
        rows[2]['grade']=min(rows[2]['grade'],1)
        rows[2]['reason']+=' The answer omits criterion rationales or a population-specific defense.'
    if selection['earlier_line'] and re.search(r'specify the exact line',' '.join(r['text'].lower() for r in criteria)):
        rows[2]['grade']=0
        rows[2]['reason']+=' The proposed earlier line remains unspecified, so this is not yet an operative eligibility rule.'
    score=sum(config['dimension_weights'][r['dimension']]*r['grade']/4 for r in rows)
    return dict(**base,status='provisional_scored',score=round(score,4),dimensions=rows,
                evidence_profile=record['id'],additional_untested_selection=extra,
                source_facts=dict(finding=record['finding'],analysis_type=record['analysis_type'],source_ids=source_ids,
                                  comparator=record.get('comparator'),endpoint='PFS'),
                limitations=['The target comparator is unspecified; grading refers to the source comparison, not superiority over other active treatments.'] if not (trial or {}).get('comparator') else [],
                interpretation='Scientific defensibility under the evidence-supported trial-design objective; not an individual benefit estimate or a cross-treatment efficacy ranking.')


def apply_scientific_grading(checklist, option_set, bank, config=None, assessments=None):
    config=validate_config(config)
    out=deepcopy(checklist)
    options={o['option_id']:o for o in option_set['options']}
    case_id=option_set.get('trial',{}).get('case_id')
    for p in out['populations']:
        p['checklist_score']=p['score']
        p['scientific_assessment']=(assessments[p['option_id']] if assessments is not None else
                                    assess_population(options[p['option_id']],case_id,bank,config,option_set.get('trial')))
        cutoff=option_set.get('provenance',{}).get('evidence_cutoff')
        if cutoff and bank.get('evidence_as_of','')>cutoff:
            p['scientific_assessment'].update(status='unassessed',score=None,dimensions=[],reason='The scientific evidence bank postdates this historical evidence cutoff.')
        science=p['scientific_assessment']['score']
        p['scientific_score']=science
        p['score']=round(config['scientific_share']*science+(1-config['scientific_share'])*p['checklist_score'],4) if science is not None else None
    valid=[p['score'] for p in out['populations'] if p['score'] is not None]
    out.update(benchmark='scientific_defense_v3',version='3.0',config=config,
               score=round(sum(valid)/len(valid),4) if valid else None,
               scientific_coverage=dict(scored=len(valid),total=len(out['populations'])),
               interpretation='80% scientific assessment and 20% completeness by default. Missing scientific assessment yields no final score, not a checklist fallback. No subgroup ranking is forced.')
    return out
