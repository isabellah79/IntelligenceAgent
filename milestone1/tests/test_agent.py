import unittest
from copy import deepcopy

from milestone1.agent import compare, validate_case, validate_model_synthesis
from milestone1.evidence import DEFAULT_CASE, OPTIONS, SOURCES


class ClinicalRulesTest(unittest.TestCase):
    def case(self, **changes):
        return {**deepcopy(DEFAULT_CASE), **changes}

    def options(self, **changes):
        return {o['id']: o for o in compare(self.case(**changes))['options']}

    def test_default_is_not_an_indiscriminate_adc_recommendation(self):
        o = self.options()
        for key in ['elacestrant', 'capivasertib', 'alpelisib', 'tdxd']:
            self.assertEqual(o[key]['status'], 'discuss', key)
        for key in ['datodxd', 'sacituzumab']:
            self.assertEqual(o[key]['status'], 'later_line', key)
        self.assertEqual(o['gedatolisib']['status'], 'not_matched')

    def test_unknown_is_not_negative(self):
        o = self.options(pik3ca='unknown', esr1='unknown')
        for key in ['elacestrant','capivasertib','alpelisib','gedatolisib']:
            self.assertEqual(o[key]['status'], 'needs_information', key)

    def test_akt1_or_pten_is_enough_for_pathway_branch(self):
        for field in ['akt1','pten']:
            o=self.options(pik3ca='not_detected', **{field:'detected'})
            self.assertEqual(o['capivasertib']['status'], 'discuss')
            self.assertEqual(o['alpelisib']['status'], 'not_matched')

    def test_zero_is_different_from_ultralow(self):
        self.assertEqual(self.options(her2='zero')['tdxd']['status'], 'not_matched')
        self.assertEqual(self.options(her2='ultralow')['tdxd']['status'], 'discuss')
        self.assertEqual(self.options(her2='unknown')['tdxd']['status'], 'needs_information')

    def test_sequence_requirements_and_population_caveat(self):
        o=self.options(prior_metastatic_chemo=1, additional_metastatic_lines=1)
        self.assertEqual(o['datodxd']['status'], 'discuss')
        self.assertEqual(o['sacituzumab']['status'], 'later_line')
        self.assertTrue(any('DB06' in s['source_ids'] for s in o['tdxd']['case_concerns']))
        self.assertEqual(self.options(prior_metastatic_chemo=2,additional_metastatic_lines=2)['sacituzumab']['status'], 'discuss')

    def test_unknown_counts_do_not_satisfy_prior_treatment(self):
        o=self.options(prior_metastatic_chemo=None,additional_metastatic_lines=None)
        self.assertEqual(o['datodxd']['status'], 'needs_information')
        self.assertEqual(o['sacituzumab']['status'], 'needs_information')

    def test_crisis_pauses_sequencing(self):
        result=compare(self.case(visceral_crisis=True))
        self.assertIn('Clinical review',result['synthesis'][0]['text'])
        self.assertTrue(any('urgent' in s['text'] for s in result['alerts']))

    def test_outside_scope_produces_no_options(self):
        self.assertEqual(compare(self.case(er_positive=False))['options'], [])
        self.assertEqual(compare(self.case(her2='positive'))['options'], [])

    def test_case_specific_safety_flags(self):
        o=self.options(diabetes='uncontrolled',ild_history='yes',prior_adc=True)
        self.assertTrue(o['alpelisib']['case_concerns'])
        self.assertGreaterEqual(len(o['tdxd']['case_concerns']),2)

    def test_menopausal_context_is_not_silently_ignored(self):
        self.assertEqual(self.options(menopausal='premenopausal')['elacestrant']['status'],'needs_information')

    def test_strict_schema_does_not_invent_missing_case_facts(self):
        for changes in [{'er_positive':'false'}, {'age':True}, {'ecog':8}, {'pik3ca':[]},
                        {'prior_metastatic_chemo':2,'additional_metastatic_lines':0}]:
            with self.assertRaises(ValueError):validate_case(self.case(**changes))
        with self.assertRaises(ValueError):validate_case({})

    def test_citations_resolve_for_all_claims_fit_rules_and_flags(self):
        self.assertEqual(len({o['id'] for o in OPTIONS}),len(OPTIONS))
        ids=[]
        for o in OPTIONS:
            for key in ['pros','cons','evidence']:
                for s in o[key]:
                    ids.append(s['id']);self.assertTrue(s['source_ids'])
                    self.assertTrue(set(s['source_ids'])<=SOURCES.keys())
        self.assertEqual(len(set(ids)),len(ids))
        for changes in [{},{'diabetes':'unknown','ild_history':'yes','prior_adc':True},
                        {'visceral_crisis':True},{'her2':'unknown'}]:
            r=compare(self.case(**changes))
            for s in r['alerts']+r['synthesis']:
                self.assertTrue(set(s['source_ids'])<=SOURCES.keys())
            for o in r['options']:
                self.assertTrue(set(o['fit_source_ids'])<=SOURCES.keys())

    def test_repeated_runs_do_not_mutate_evidence(self):
        before=deepcopy(OPTIONS)
        compare(self.case(diabetes='uncontrolled'));compare(self.case())
        self.assertEqual(before,OPTIONS)

    def test_model_cannot_invent_source_ids(self):
        r=compare(self.case())
        with self.assertRaises(ValueError):
            validate_model_synthesis({'synthesis':[{'text':'Claim','claim_ids':['invented']}]},r)
        with self.assertRaises(ValueError):
            validate_model_synthesis({'synthesis':[{'text':'Claim','claim_ids':[]}]},r)
        out=validate_model_synthesis({'synthesis':[{'text':'Conditional discussion','claim_ids':['elacestrant.pros.1']}]},r)
        self.assertIn('EMERALD',out[0]['source_ids'])
        self.assertIn('not independently verified',out[0]['kind'])


if __name__ == '__main__':unittest.main()
