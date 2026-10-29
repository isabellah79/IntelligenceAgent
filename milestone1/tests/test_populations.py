"""Population-design regression checks; these are not a clinical benchmark."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from forecast.forecast import method_b
from milestone1.population_library import POPULATION_SOURCES, SCOPE, build_library
from milestone1.populations import (DEFAULT_CONTEXT, DEFAULT_DESIGN, all_populations, propose,
    validate_review, review_populations, attach_population_judgment, focused_treatment)
from milestone1.server import init_db, load_run


class PopulationDesignTest(unittest.TestCase):
    def setUp(self):self.result=propose()
    def population(self,pid,result=None):return all_populations((result or self.result)['treatments'])[pid]

    def test_task_has_no_individual_patient_or_treatment_winner(self):
        self.assertEqual(self.result['task'],'population_design')
        self.assertNotIn('case',self.result);self.assertNotIn('ranking',self.result)
        self.assertEqual(self.result['context']['parent_population'],SCOPE)

    def test_all_thirteen_treatments_have_three_distinct_populations(self):
        self.assertEqual(len(self.result['treatments']),13)
        ids=[]
        for t in self.result['treatments']:
            self.assertEqual(len(t['populations']),3)
            self.assertEqual(len({p['title'] for p in t['populations']}),3)
            self.assertIn(t['starting_population_id'],{p['id'] for p in t['populations']})
            ids.extend(p['id'] for p in t['populations'])
        self.assertEqual(len(set(ids)),39)

    def test_criteria_preserve_parent_scope_and_separate_safety_from_efficacy(self):
        for p in all_populations(self.result['treatments']).values():
            self.assertTrue(any(c['id'].endswith('.post_cdk') for c in p['inclusion']))
            self.assertTrue(any(c['purpose']=='efficacy' for c in p['inclusion']))
            self.assertTrue(any(c['purpose']=='safety' for c in p['exclusion']))
            self.assertTrue(p['protocol_pending'])
            for c in p['inclusion']+p['exclusion']:
                self.assertTrue(c['reason']);self.assertIn(c['status'],{'evidence_supported','design_assumption','exploratory','safety_review'})

    def test_all_criteria_claims_and_weights_have_resolving_sources_and_unique_ids(self):
        ids=[]
        for p in all_populations(self.result['treatments']).values():
            rows=[p['benefit_statement'],*p['forecast']['factors']]
            for section in ('inclusion','exclusion','pros','cons','protocol_pending'):rows.extend(p[section])
            for row in rows:
                ids.append(row['id']);self.assertTrue(row['source_ids'])
                self.assertTrue(set(row['source_ids'])<=POPULATION_SOURCES.keys())
        self.assertEqual(len(ids),len(set(ids)))

    def test_no_blanket_brain_metastasis_exclusion(self):
        for p in all_populations(self.result['treatments']).values():
            self.assertTrue(any('FDA-CNS' in row['source_ids'] for row in p['protocol_pending']))
            self.assertFalse(any('brain metastases' in row['text'].lower() for row in p['exclusion']))

    def test_evidence_belongs_to_each_population_not_just_the_drug(self):
        self.assertEqual(self.population('elacestrant__esr1')['effect']['hazard_ratio'],.55)
        p=self.population('elacestrant__long_response')
        self.assertEqual(p['effect']['hazard_ratio'],.41);self.assertEqual(p['kind'],'exploratory')
        self.assertEqual(self.population('elacestrant__unselected')['effect']['hazard_ratio'],.70)
        self.assertNotEqual(self.population('elacestrant__esr1')['forecast']['score'],p['forecast']['score'])

    def test_source_mixed_cdk_effect_does_not_automatically_transfer(self):
        for pid in ('capivasertib__pathway','imlunestrant__esr1','tdxd__her2low','datodxd__pretreated'):
            p=self.population(pid);self.assertEqual(p['transfer'],'mixed_prior_cdk');self.assertIsNone(p['forecast']['score'])
        design={**deepcopy(DEFAULT_DESIGN),'allow_extrapolation':True}
        p=self.population('capivasertib__pathway',propose(design=design))
        self.assertEqual(p['forecast']['assumed_hr'],.5)
        self.assertIn('extrapolation',p['forecast']['effect_origin'])

    def test_unknown_hypothesis_effect_is_never_copied_from_reference(self):
        for p in all_populations(self.result['treatments']).values():
            if p['kind']=='hypothesis':
                self.assertIsNone(p['effect']);self.assertIsNone(p['forecast']['score'])
                self.assertEqual(p['transfer'],'unestablished')
        self.assertIsNone(self.population('tdxd__ultralow')['forecast']['score'])

    def test_no_hr_is_inferred_from_medians(self):
        p=self.population('tdxd__rapid_progression')
        self.assertEqual(p['effect']['median_pfs_months'],[14.0,6.5])
        self.assertIsNone(p['effect']['hazard_ratio']);self.assertIsNone(p['forecast']['score'])

    def test_gedatolisib_enrichment_does_not_inherit_aggregate_triplet_effect(self):
        a=self.population('gedatolisib__triplet');b=self.population('gedatolisib__long_response')
        self.assertEqual(a['effect']['hazard_ratio'],.24)
        self.assertIsNone(b['effect']);self.assertIsNone(b['forecast']['score'])
        self.assertEqual(a['regimen'],b['regimen']);self.assertNotIn('±',a['regimen'])

    def test_explicit_effect_and_comparator_apply_to_one_population_only(self):
        d={**deepcopy(DEFAULT_DESIGN),'effect_overrides':{'capivasertib__pik3ca':dict(hr=.65,comparator='Fulvestrant')}}
        result=propose(design=d)
        p=self.population('capivasertib__pik3ca',result)
        self.assertEqual(p['forecast']['assumed_hr'],.65)
        self.assertEqual(p['forecast']['comparator'],'Fulvestrant')
        self.assertIn('Analyst-specified',p['forecast']['effect_origin'])
        self.assertIsNone(self.population('capivasertib__pathway',result)['forecast']['score'])

    def test_population_forecast_uses_original_engine_and_explicit_blend(self):
        p=self.population('elacestrant__esr1');f=p['forecast']
        b,_=method_b(200,[dict(name='effect',hr=.55,weight=1)],[dict(z=1.96,weight=1)])
        self.assertAlmostEqual(f['method_b'],b)
        self.assertAlmostEqual(f['score'],.5*f['method_a']+.5*f['method_b'])
        without=propose(design={**deepcopy(DEFAULT_DESIGN),'evidence_strength':0})
        self.assertAlmostEqual(self.population(p['id'],without)['forecast']['method_a'],.5)

    def test_missing_prior_gives_only_conditional_power(self):
        p=self.population('elacestrant__esr1',propose(design={**deepcopy(DEFAULT_DESIGN),'prior':None}))
        self.assertEqual(p['forecast']['score'],p['forecast']['method_b']);self.assertIsNone(p['forecast']['method_a'])

    def test_disabling_published_effects_requires_explicit_override(self):
        p=self.population('elacestrant__esr1',propose(design={**deepcopy(DEFAULT_DESIGN),'use_reference_effect':False}))
        self.assertIsNone(p['forecast']['score'])

    def test_invalid_context_or_design_is_rejected(self):
        for change in ({'objective':[]},{'primary_endpoint':'OS'},{'parent_population':'Any breast cancer'}):
            with self.assertRaises(ValueError):propose(context={**DEFAULT_CONTEXT,**change})
        for change in ({'events':True},{'prior':1},{'allow_extrapolation':'true'},
                       {'effect_overrides':{'unknown':{'hr':.5,'comparator':'Control'}}},
                       {'effect_overrides':{'elacestrant__esr1':{'hr':.5,'comparator':''}}},
                       {'factor_overrides':{'elacestrant__esr1':{'wrong':1.2}}}):
            with self.assertRaises(ValueError):propose(design={**deepcopy(DEFAULT_DESIGN),**change})

    def test_repeated_builds_do_not_mutate_evidence_or_default_design(self):
        before=deepcopy(build_library());design=deepcopy(DEFAULT_DESIGN)
        propose(design={**deepcopy(DEFAULT_DESIGN),'effect_overrides':{'elacestrant__long_response':dict(hr=.9,comparator='Control')}})
        self.assertEqual(build_library(),before);self.assertEqual(DEFAULT_DESIGN,design)


class PopulationModelReviewTest(unittest.TestCase):
    def setUp(self):
        self.result=propose();self.pid='elacestrant__esr1'
        self.payload=dict(synthesis=[dict(text='A conditional population design comparison.',claim_ids=[self.pid+'.benefit'])],
            recommendation=dict(population_id=self.pid,reason='A reference-supported starting protocol draft.',claim_ids=[self.pid+'.benefit']),
            criterion_proposals=[],weight_proposals=[])
    def weight(self):return dict(population_id=self.pid,factor_id=self.pid+'.factor.setting_alignment',proposed_factor=1.05,reason='A provisional, cautious analyst adjustment.',claim_ids=[self.pid+'.benefit'])
    def criterion(self):return dict(population_id=self.pid,criterion_id=self.pid+'.inclusion.selection',action='revise',replacement_text='Require a centrally confirmed qualifying ESR1 alteration.',reason='Make the assay definition explicit in the protocol.',claim_ids=[self.pid+'.inclusion.selection'])

    def test_review_has_a_within_treatment_recommendation_and_citations(self):
        r=validate_review(self.payload,self.result)
        self.assertEqual(r['recommendation']['population_id'],self.pid)
        self.assertTrue(r['synthesis'][0]['source_ids'])

    def test_model_cannot_recommend_another_treatment_population(self):
        payload=deepcopy(self.payload);payload['recommendation']['population_id']='capivasertib__pathway'
        with self.assertRaises(ValueError):validate_review(payload,self.result)

    def test_unknown_or_cross_population_claims_fail(self):
        for claim in ('invented','capivasertib__pathway.benefit','elacestrant__long_response.benefit'):
            payload=deepcopy(self.payload);payload['criterion_proposals']=[{**self.criterion(),'claim_ids':[claim]}]
            with self.assertRaises(ValueError):validate_review(payload,self.result)

    def test_criteria_proposals_are_bounded_drafts_not_applied(self):
        before=deepcopy(self.result);payload=deepcopy(self.payload);payload['criterion_proposals']=[self.criterion()]
        r=validate_review(payload,self.result)
        self.assertEqual(r['criterion_proposals'][0]['status'],'Proposed; requires researcher review')
        self.assertEqual(self.result,before)
        for change in ({'criterion_id':'invented'},{'action':'add'},{'replacement_text':'See https://example.com'},{'criterion_id':self.pid+'.inclusion.post_cdk'}):
            payload['criterion_proposals']=[{**self.criterion(),**change}]
            with self.assertRaises(ValueError):validate_review(payload,self.result)

    def test_weights_are_population_scoped_and_do_not_change_scores_until_applied(self):
        payload=deepcopy(self.payload);payload['weight_proposals']=[self.weight()]
        before=deepcopy(self.result);r=validate_review(payload,self.result)
        self.assertEqual(r['weight_proposals'][0]['previous_factor'],1.2)
        self.assertEqual(before,self.result)
        for factor in (True,float('nan'),.49,2.01):
            payload['weight_proposals']=[{**self.weight(),'proposed_factor':factor}]
            with self.assertRaises(ValueError):validate_review(payload,self.result)

    def test_model_cannot_adjust_an_inactive_population_forecast(self):
        result=propose(focus_treatment_id='capivasertib');payload=deepcopy(self.payload)
        pid='capivasertib__pathway';payload['synthesis']=[dict(text='Conditional review.',claim_ids=[pid+'.benefit'])]
        payload['recommendation']=dict(population_id=pid,reason='Reference cohort.',claim_ids=[pid+'.benefit'])
        payload['weight_proposals']=[dict(population_id=pid,factor_id=pid+'.factor.setting_alignment',proposed_factor=1.1,reason='Hypothesis.',claim_ids=[pid+'.benefit'])]
        with self.assertRaises(ValueError):validate_review(payload,result)

    def mock_review(self):
        payload=deepcopy(self.payload);payload['weight_proposals']=[self.weight()];payload['criterion_proposals']=[self.criterion()]
        metadata=dict(model='test-model',provider='vertex',project='test-project',location='global',usage={})
        with patch('milestone1.populations.model_status',return_value={'configured':True}),patch('milestone1.populations.generate',return_value=(json.dumps(payload),metadata)) as generate:
            result=review_populations(deepcopy(self.result))
        return result,generate.call_args

    def test_prompt_and_context_are_population_design_not_individual_treatment(self):
        r,args=self.mock_review()
        self.assertIn('population-design',args.args[0]);self.assertNotIn('case',json.loads(args.args[1]))
        self.assertEqual(r['mode'],'model_population_review')
        self.assertEqual(r['treatments'],self.result['treatments'])
        self.assertEqual(len(r['model_input_sha256']),64)

    def test_reviewed_weight_application_records_parent_and_recalculates(self):
        parent,_=self.mock_review();design=deepcopy(parent['design'])
        design['factor_overrides']={self.pid:{self.weight()['factor_id']:1.05}}
        result=propose(design=design);attach_population_judgment(result,parent,'parent-test')
        self.assertEqual(len(result['applied_model_weights']),1)
        self.assertEqual(result['model_review'],parent['model_review'])
        before=all_populations(parent['treatments'])[self.pid]['forecast']['score'];after=all_populations(result['treatments'])[self.pid]['forecast']['score']
        self.assertLess(after,before)
        changed=propose(design={**design,'events':300})
        with self.assertRaises(ValueError):attach_population_judgment(changed,parent,'parent-test')

    def test_saved_population_feedback_restores_with_original_run(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.sqlite3';init_db(path);rid='12345678-1234-4234-8234-123456789012'
            r=deepcopy(self.result);r['run_id']=rid
            with sqlite3.connect(path) as db:
                db.execute('INSERT INTO runs VALUES (?,?,?)',(rid,'today',json.dumps(r)))
                db.execute('INSERT INTO population_feedback VALUES (?,?,?,?,?,?,?)',('review',rid,'today','elacestrant',self.pid,'edit','Proposed revised criterion'))
            saved=load_run(path,rid)
            self.assertEqual(saved['task'],'population_design')
            self.assertEqual(saved['saved_reviews'][0]['population_id'],self.pid)
            self.assertEqual(saved['saved_reviews'][0]['comment'],'Proposed revised criterion')


if __name__=='__main__':unittest.main()
