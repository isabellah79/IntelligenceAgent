"""Scientific grading regressions: evidence must outweigh presentation and forecasts."""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmark import baselines,rubric,scientific,scientific_judge,run


class ScientificGradeTests(unittest.TestCase):
    def setUp(self):
        self.bank=scientific.load_bank()
        self.options=baselines.from_demo('elacestrant')

    def assess(self,index=0,output=None):
        output=output or self.options
        return scientific.assess_population(output['options'][index],output['trial']['case_id'],self.bank,trial=output['trial'])

    def dimension(self,result,name):
        return next(r['grade'] for r in result['dimensions'] if r['dimension']==name)

    def test_primary_and_posthoc_evidence_are_distinguished(self):
        self.assertEqual(self.dimension(self.assess(0),'evidence_strength'),4)
        self.assertEqual(self.dimension(self.assess(1),'evidence_strength'),2)
        self.assertLess(self.assess(1)['score'],self.assess(0)['score'])

    def test_self_declared_reference_status_cannot_upgrade_exploratory_evidence(self):
        before=self.assess(1)
        self.options['options'][1]['evidence_context']=dict(status='reference',transfer='direct')
        self.options['options'][1]['option_id']='preferred_reference_winner'
        self.assertEqual(self.assess(1)['score'],before['score'])

    def test_science_has_eighty_percent_of_final_grade(self):
        result=scientific.apply_scientific_grading(rubric.score_defense_rubric(self.options),self.options,self.bank)
        p=result['populations'][0]
        self.assertAlmostEqual(p['score'],round(.8*p['scientific_score']+.2*p['checklist_score'],4))

    def test_forecast_values_and_provenance_do_not_change_scientific_grade(self):
        before=self.assess(0)['score']
        self.options['options'][0]['estimates']['endpoint_forecast'].update(score=1,assumed_hr=.1)
        self.options['provenance'].update(agent='fine_tuned',model='preferred-model')
        self.assertEqual(self.assess(0)['score'],before)

    def test_new_duration_does_not_inherit_published_duration_effect(self):
        for row in self.options['options'][1]['inclusion']:
            row['text']=row['text'].replace('12 months','18 months')
        grade=self.assess(1)
        self.assertEqual(self.dimension(grade,'evidence_strength'),1)
        self.assertIn('duration_min',grade['additional_untested_selection'])

    def test_duration_hypothesis_does_not_transfer_to_other_drug(self):
        grade=self.assess(1,baselines.from_demo('vepdegestrant'))
        self.assertEqual(self.dimension(grade,'evidence_strength'),1)

    def test_mixed_prior_cdk_setting_is_discounted(self):
        grade=self.assess(0,baselines.from_demo('capivasertib'))
        self.assertEqual(self.dimension(grade,'population_applicability'),3)
        self.assertEqual(self.dimension(self.assess(0),'population_applicability'),4)

    def test_extra_pik3ca_restriction_needs_specific_evidence(self):
        grade=self.assess(1,baselines.from_demo('capivasertib'))
        self.assertLess(self.dimension(grade,'selection_justification'),4)
        self.assertLess(self.dimension(grade,'evidence_strength'),4)

    def test_label_inclusion_does_not_make_ultralow_analysis_confirmatory(self):
        output=baselines.from_demo('tdxd')
        self.assertEqual(self.dimension(self.assess(0,output),'evidence_strength'),4)
        self.assertEqual(self.dimension(self.assess(1,output),'evidence_strength'),2)

    def test_by_lieve_is_noncomparative_and_ecog2_is_not_automatically_outside_evidence(self):
        output=baselines.from_demo('alpelisib')
        for index in (1,2):
            output['options'][index]['defense'][0]['source_ids'].append('BYLIEVE-2024')
            grade=self.assess(index,output)
            self.assertEqual(self.dimension(grade,'evidence_strength'),2)
            self.assertEqual(self.dimension(grade,'population_applicability'),4)

    def test_unknown_case_has_no_science_or_completeness_fallback(self):
        self.options['trial']['case_id']='unknown'
        result=scientific.apply_scientific_grading(rubric.score_defense_rubric(self.options),self.options,self.bank)
        self.assertIsNone(result['score'])
        self.assertTrue(all(p['score'] is None for p in result['populations']))

    def test_new_biomarker_cannot_silently_inherit_parent_effect(self):
        self.options['options'][0]['inclusion'].append(dict(id='new',text='Require ESR1 mutation and TP53 mutation',purpose='efficacy',reason='test',source_ids=['EMERALD']))
        self.assertIsNone(self.assess(0)['score'])

    def test_arbitrary_percent_cutoff_requires_scientific_mapping(self):
        self.options['options'][0]['inclusion'].append(dict(id='new',text='Require ESR1 allele frequency >=50%',purpose='efficacy',reason='test',source_ids=['EMERALD']))
        self.assertIsNone(self.assess(0)['score'])

    def test_os_cannot_be_graded_with_pfs_evidence(self):
        self.options['trial']['primary_endpoint']='OS'
        self.assertIsNone(self.assess(0)['score'])

    def test_out_of_scope_disease_cannot_retain_primary_evidence_credit(self):
        for row in self.options['options'][0]['inclusion']:
            row['text']=row['text'].replace('HER2-negative','HER2-positive')
        self.assertIsNone(self.assess(0)['score'])

    def test_different_comparator_requires_own_evidence(self):
        self.options['trial']['comparator']='A different active regimen'
        self.assertIsNone(self.assess(0)['score'])

    def test_historical_cutoff_cannot_use_current_evidence_bank(self):
        self.options['provenance']['evidence_cutoff']='2020-01-01'
        result=scientific.apply_scientific_grading(rubric.score_defense_rubric(self.options),self.options,self.bank)
        self.assertIsNone(result['score'])
        with patch('milestone1.llm.generate') as generate:
            scientific_judge.judge(self.options,self.bank)
        generate.assert_not_called()

    def test_empty_cons_receive_no_tradeoff_credit(self):
        self.options['options'][0]['cons']=[]
        self.assertEqual(self.dimension(self.assess(0),'tradeoffs'),0)

    def test_missing_citation_cannot_earn_primary_evidence_grade(self):
        for section in ('inclusion','exclusion','pros','cons','defense'):
            for row in self.options['options'][0][section]:
                row['source_ids']=[]
        self.assertEqual(self.dimension(self.assess(0),'evidence_strength'),1)

    def test_unsupported_absolute_selection_claim_is_penalized(self):
        self.options['options'][1]['defense']=[dict(text='This subgroup is proven to benefit more.',source_ids=['EMERALD-DURATION'])]
        self.assertEqual(self.dimension(self.assess(1),'selection_justification'),0)

    def test_invalid_scientific_weights_are_rejected(self):
        for value in (False,.2,float('nan')):
            config=deepcopy(scientific.DEFAULT_CONFIG);config['scientific_share']=value
            with self.assertRaises(ValueError): scientific.validate_config(config)
        config=deepcopy(scientific.DEFAULT_CONFIG);config['dimension_weights']['tradeoffs']=.9
        with self.assertRaises(ValueError): scientific.validate_config(config)

    def test_all_development_populations_have_explicit_scientific_assessments(self):
        from benchmark.dataset import demo_equivalents
        total=0
        for case in demo_equivalents():
            output=baselines.from_demo(case['case_id'])
            result=scientific.apply_scientific_grading(rubric.score_defense_rubric(output),output,self.bank)
            self.assertEqual(result['scientific_coverage']['scored'],3,case['case_id'])
            total+=3
        self.assertEqual(total,39)

    def test_fabrication_blocks_final_grade_instead_of_being_averaged_away(self):
        from benchmark.sources import SourceCatalog
        self.options['options'][0]['pros'].append(dict(text='A made-up study supports benefit.',source_ids=['FAKE']))
        result=run.score_one(self.options,SourceCatalog.from_demo())
        self.assertEqual(result['evaluation_gate']['status'],'blocked')
        self.assertIsNone(result['defense_rubric']['score'])


class ScientificCalibrationTests(unittest.TestCase):
    def test_ordinal_agreement_reports_errors_and_kappa(self):
        from benchmark.scientific_calibration import calibrate
        grades={d:3 for d in scientific.DIMENSIONS}
        report=dict(cases=[dict(frozen_input='/private/tmp/frozen.json',defense_rubric=dict(populations=[dict(option_id='p',score=.75,
                    scientific_assessment=dict(score=.75,dimensions=[dict(dimension=d,grade=2) for d in scientific.DIMENSIONS]))]))])
        result=calibrate([dict(file='/private/tmp/frozen.json',option_id='p',scientific_grades=grades)],[report])
        self.assertEqual(result['dimensions']['evidence_strength']['mean_absolute_error'],1)
        self.assertEqual(result['dimensions']['tradeoffs']['within_one_grade'],1)

    def test_null_scientific_human_grades_are_rejected(self):
        from benchmark.scientific_calibration import calibrate
        with self.assertRaises(ValueError):
            calibrate([dict(scientific_grades={d:None for d in scientific.DIMENSIONS})],[])

    def test_ordinal_kappa_is_undefined_without_variation(self):
        from benchmark.scientific_calibration import quadratic_kappa
        self.assertIsNone(quadratic_kappa([3,3],[3,3]))
        self.assertEqual(quadratic_kappa([0,4],[0,4]),1)


class ScientificJudgeTests(unittest.TestCase):
    def setUp(self):
        self.bank=scientific.load_bank()
        self.options=baselines.from_demo('elacestrant')
        self.prompt,self.mapping,self.assessments=scientific_judge.prepare(self.options,self.bank)

    def payload(self):
        return dict(populations=[dict(candidate_id=alias,dimensions={d:dict(grade=2,reason='A population-specific reason supported by the supplied evidence.',source_ids=['EMERALD'],criterion_ids=[next(iter(item['criteria']))]) for d in scientific.DIMENSIONS}) for alias,item in self.mapping.items()])

    def validate(self,payload):
        return scientific_judge.validate_response(payload,self.mapping,self.assessments,self.bank,dict(model='test'),'hash')

    def test_judge_prompt_hides_endpoint_scores_and_producer_identity(self):
        text=json.dumps(self.prompt)
        self.assertNotIn('endpoint_forecast',text)
        self.assertNotIn('provenance',text)
        self.assertNotIn('option_id',text)
        self.assertNotIn('evidence_context',text)

    def test_judge_cannot_invent_a_candidate(self):
        payload=self.payload();payload['populations'][0]['candidate_id']='invented'
        with self.assertRaises(ValueError): self.validate(payload)

    def test_judge_cannot_invent_a_source(self):
        payload=self.payload();payload['populations'][0]['dimensions']['evidence_strength']['source_ids']=['fake']
        with self.assertRaises(ValueError): self.validate(payload)

    def test_judge_cannot_use_another_candidates_criterion(self):
        payload=self.payload();payload['populations'][0]['dimensions']['tradeoffs']['criterion_ids']=['p2.c1']
        with self.assertRaises(ValueError): self.validate(payload)

    def test_judge_cannot_use_boolean_instead_of_ordinal_grade(self):
        payload=self.payload();payload['populations'][0]['dimensions']['tradeoffs']['grade']=True
        with self.assertRaises(ValueError): self.validate(payload)

    def test_exploratory_evidence_ceiling_is_applied_and_logged(self):
        payload=self.payload();payload['populations'][1]['dimensions']['evidence_strength']['grade']=4
        grade=self.validate(payload)['elacestrant__long_response']['dimensions'][0]
        self.assertEqual(grade['grade'],2)
        self.assertEqual(grade['raw_model_grade'],4)
        self.assertTrue(grade['ceiling_applied'])

    def test_judge_failure_does_not_silently_become_rule_based_success(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            target=Path(folder)/'report.json'
            with patch('benchmark.scientific_judge.judge',side_effect=ValueError('bad response')):
                code=run.main(['--treatments','elacestrant','--science-judge','--out',str(target)])
            result=json.loads(target.read_text())
        self.assertEqual(code,1)
        self.assertIsNone(result['cases'][0]['defense_rubric']['score'])
        self.assertIn('science_judge_error',result['cases'][0])


if __name__=='__main__': unittest.main()
