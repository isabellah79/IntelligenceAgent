from copy import deepcopy
import math
import unittest

from forecast.forecast import forecast_case, method_a, method_b
from milestone1.agent import compare
from milestone1.evidence import DEFAULT_CASE, SOURCES
from milestone1.forecasting import examples, evaluate_forecast
from milestone1.scoring import WEIGHT_PRESETS


class DiscussionScoreTest(unittest.TestCase):
    def case(self, **updates):
        return {**deepcopy(DEFAULT_CASE), **updates}

    def test_score_is_the_sum_of_visible_contributions(self):
        r=compare(self.case())
        for o in r['options']:
            s=o['priority_score']
            if s['value'] is not None:
                self.assertAlmostEqual(s['value'],sum(x['contribution'] for x in s['components']))
                self.assertGreaterEqual(s['value'],0);self.assertLessEqual(s['value'],100)
                self.assertTrue(set(s['source_ids'])<=SOURCES.keys())
        self.assertEqual(r['priority_policy']['forecast_weight'],0)

    def test_default_gives_clear_conditional_shortlist_without_fake_tiebreak(self):
        r=compare(self.case())
        self.assertEqual(r['recommendation']['status'],'shortlist')
        self.assertEqual(set(r['recommendation']['option_ids']),{'elacestrant','vepdegestrant'})
        self.assertIn('unique winner',r['recommendation']['text'])
        self.assertTrue(r['recommendation']['comparison'])
        self.assertEqual(r['recommendation']['score'],92)

    def test_later_line_and_unmatched_options_get_no_score_not_zero(self):
        for o in compare(self.case())['options']:
            if o['status']!='discuss':
                self.assertIsNone(o['priority_score']['value'])
                self.assertFalse(o['priority_score']['eligible_for_priority'])
        g=next(o for o in compare(self.case())['options'] if o['id']=='gedatolisib')
        self.assertIsNotNone(g['trial_forecast'])
        self.assertIsNone(g['priority_score']['value'])

    def test_safety_flag_holds_the_option_out_of_recommendation(self):
        r=compare(self.case(diabetes='uncontrolled',ild_history='yes'))
        for o in r['options']:
            if o['id'] in {'alpelisib','capivasertib','tdxd'}:
                self.assertIsNone(o['priority_score']['value'])
                self.assertTrue(o['priority_score']['blocked_reasons'])

    def test_global_review_holds_remove_all_priority_scores(self):
        for change in [dict(visceral_crisis=True),dict(her2='unknown'),dict(organ_function='impaired'),
                       dict(ecog=None),dict(esr1='unknown'),dict(prior_metastatic_chemo=None)]:
            r=compare(self.case(**change))
            self.assertEqual(r['ranking'],[])
            self.assertEqual(r['recommendation']['status'],'paused')
            self.assertTrue(all(o['priority_score']['value'] is None for o in r['options']))

    def test_weight_changes_are_recorded_and_change_contributions(self):
        weights=dict(match=20,evidence=50,readiness=20,preference=10)
        r=compare(self.case(),weights)
        self.assertEqual(r['priority_policy']['weights'],weights)
        capi=next(o for o in r['options'] if o['id']=='capivasertib')
        self.assertEqual(capi['priority_score']['components'][1]['contribution'],40)
        self.assertTrue(r['priority_policy']['sensitivity'])

    def test_invalid_weights_fail_rather_than_silently_normalize(self):
        for weights in [dict(match=100,evidence=100,readiness=0,preference=0),
                        dict(match=math.nan,evidence=50,readiness=25,preference=25),
                        dict(match=True,evidence=49,readiness=25,preference=25),{}]:
            with self.assertRaises(ValueError):compare(self.case(),weights)

    def test_preference_weight_presets_have_no_hidden_forecast_term(self):
        for preference,weights in WEIGHT_PRESETS.items():
            r=compare(self.case(preference=preference))
            self.assertEqual(r['priority_policy']['weights'],weights)
            self.assertEqual(sum(weights.values()),100)
            self.assertEqual(r['priority_policy']['forecast_weight'],0)


class ForecastTest(unittest.TestCase):
    def example(self):
        return deepcopy(examples()['viktoria1_wt']['case'])

    def test_both_original_examples_reproduce_original_equations(self):
        for item in examples().values():
            c=item['case'];actual=forecast_case(c)
            a,_=method_a(c['method_a']['prior'],c['method_a']['factors'])
            b=c['method_b'];p_b,_=method_b(b['events'],b['scenarios'],b['bars'])
            self.assertEqual(actual['method_a'],a);self.assertEqual(actual['method_b'],p_b)
            self.assertEqual(actual['combined'],(a+p_b)/2)

    def test_null_effect_has_only_type_one_error_at_the_bar(self):
        c=self.example();c['method_b']={'events':200,'scenarios':[{'name':'null','hr':1,'weight':1}], 'bars':[{'z':1.96,'weight':1}]}
        self.assertAlmostEqual(forecast_case(c)['method_b'],0.025,places=3)

    def test_better_assumed_effect_increases_conditional_power(self):
        c=self.example();c['method_b']['scenarios']=[{'name':'effect','hr':0.8,'weight':1}]
        before=forecast_case(c)['method_b'];c['method_b']['scenarios'][0]['hr']=0.6
        self.assertGreater(forecast_case(c)['method_b'],before)

    def test_invalid_model_inputs_do_not_produce_percentages(self):
        cases=[]
        for prior in [0,1,True,math.nan]:
            c=self.example();c['method_a']['prior']=prior;cases.append(c)
        c=self.example();c['method_b']['events']=0;cases.append(c)
        c=self.example();c['method_b']['scenarios'][0]['hr']=0;cases.append(c)
        c=self.example();c['method_b']['scenarios'][0]['weight']=0.9;cases.append(c)
        c=self.example();c['method_b']['bars'][0]['weight']=-1;cases.append(c)
        c=self.example();c['as_of']='not a date';cases.append(c)
        for c in cases:
            with self.assertRaises(ValueError):forecast_case(c)

    def test_historical_example_is_not_predictive_validation(self):
        r=evaluate_forecast(self.example(),'gedatolisib')
        self.assertEqual(r['historical_outcome'],1)
        self.assertIn('leakage',r['interpretation'])
        self.assertFalse(r['included_in_treatment_score'])

    def test_forecast_cannot_transfer_to_another_drug(self):
        r=evaluate_forecast(self.example(),'elacestrant')
        self.assertIn('cannot be transferred',r['interpretation'])

    def test_edited_example_does_not_inherit_observed_outcome(self):
        c=self.example();c['method_b']['events']=250
        r=evaluate_forecast(c,'gedatolisib')
        self.assertEqual(r['provenance'],'User-edited analyst assumptions')
        self.assertNotIn('historical_outcome',r)
        self.assertIsNone(r['example_id'])


if __name__=='__main__':unittest.main()
