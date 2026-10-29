from copy import deepcopy
import unittest

from forecast.forecast import method_b
from milestone1.agent import compare
from milestone1.endpoint_comparison import DEFAULT_DESIGN, ENDPOINTS
from milestone1.evidence import DEFAULT_CASE, SOURCES


class EndpointTableTest(unittest.TestCase):
    def result(self, design=None, **case):
        return compare({**DEFAULT_CASE,**case},endpoint_design=design)

    def endpoint(self,r,id='elacestrant'):
        return next(o['endpoint_comparison'] for o in r['options'] if o['id']==id)

    def test_primary_pfs_results_are_not_preference_points(self):
        a=self.endpoint(self.result());b=self.endpoint(self.result(preference='disease_control'))
        self.assertEqual(a['hazard_ratio'],.55)
        self.assertEqual(a['median_pfs_months'],[3.8,1.9])
        self.assertEqual(a['score'],b['score'])

    def test_forecast_uses_original_methods_and_records_literature_delta(self):
        e=self.endpoint(self.result())
        b,_=method_b(200,[dict(name='source',hr=.55,weight=1)],[dict(z=1.96,weight=1)])
        self.assertAlmostEqual(e['method_b'],b)
        self.assertAlmostEqual(e['score'],.5*e['method_a']+.5*b)
        self.assertAlmostEqual(e['evidence_delta'],e['score']-e['unadjusted_score'])

    def test_neutral_evidence_strength_removes_adjustment(self):
        d={**deepcopy(DEFAULT_DESIGN),'evidence_strength':0}
        e=self.endpoint(self.result(d))
        self.assertAlmostEqual(e['method_a'],.5)
        self.assertAlmostEqual(e['evidence_delta'],0)
        self.assertTrue(all(x['effective_factor']==1 for x in e['evidence_adjustments']))

    def test_explicit_negative_weight_lowers_final_score(self):
        before=self.endpoint(self.result())
        d={**deepcopy(DEFAULT_DESIGN),'factor_overrides':{'elacestrant':{'direct_post_cdk':.5}}}
        after=self.endpoint(self.result(d))
        self.assertLess(after['score'],before['score'])
        self.assertEqual(after['method_b'],before['method_b'])
        self.assertEqual(after['evidence_adjustments'][0]['factor'],.5)

    def test_primary_hr_not_replaced_by_optimistic_posthoc_hr(self):
        e=self.endpoint(self.result())
        self.assertEqual(e['hazard_ratio'],.55)
        self.assertEqual({f['id'] for f in e['evidence_adjustments']}, {'direct_post_cdk','long_prior_response','posthoc_caution'})
        e=self.endpoint(self.result(endocrine_months=6))
        self.assertEqual({f['id'] for f in e['evidence_adjustments']},{'direct_post_cdk'})

    def test_no_prior_means_conditional_power_only(self):
        e=self.endpoint(self.result({**deepcopy(DEFAULT_DESIGN),'prior':None}))
        self.assertEqual(e['score'],e['method_b']);self.assertIsNone(e['method_a'])
        self.assertIsNone(e['evidence_delta'])

    def test_no_forecast_for_missing_or_inapplicable_evidence(self):
        r=self.result()
        for id in ['alpelisib','chemotherapy','gedatolisib','datodxd','sacituzumab','olaparib']:
            e=self.endpoint(r,id);self.assertIsNone(e['score']);self.assertTrue(e['unavailable_reason'])
        e=self.endpoint(self.result(her2='ultralow'),'tdxd');self.assertIsNone(e['score'])

    def test_all_treatments_have_immediate_reference_data_and_all_weights_are_cited(self):
        r=self.result()
        self.assertEqual(set(ENDPOINTS),{o['id'] for o in r['options']})
        for o in r['options']:
            e=o['endpoint_comparison'];self.assertTrue(e['source_ids']);self.assertTrue(set(e['source_ids'])<=SOURCES.keys())
            for factor in e['evidence_adjustments']:
                self.assertTrue(factor['source_ids']);self.assertTrue(set(factor['source_ids'])<=SOURCES.keys())
                self.assertIn('Analyst-assigned',factor['weight_provenance'])

    def test_os_never_substituted_for_primary_pfs(self):
        e=self.endpoint(self.result(),'sacituzumab')
        self.assertEqual(e['median_pfs_months'],[5.5,4.0]);self.assertEqual(e['primary_endpoint'],'PFS')
        e=self.endpoint(self.result(),'postmonarch');self.assertEqual(e['hazard_ratio'],.73)

    def test_invalid_designs_fail_without_silent_reweighting(self):
        for change in [{'events':True},{'events':0},{'prior':1},{'blend_a':1.5},{'evidence_strength':-1},
                       {'factor_overrides':{'elacestrant':{'direct_post_cdk':0}}},
                       {'factor_overrides':{'invented':{}}}]:
            with self.assertRaises(ValueError):self.result({**deepcopy(DEFAULT_DESIGN),**change})


if __name__=='__main__':unittest.main()
