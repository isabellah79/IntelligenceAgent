"""Offline checks: never request an access token or call a paid model."""
from copy import deepcopy
import http.client
import json
import ssl
import subprocess
import sqlite3
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

from milestone1 import llm
from milestone1.agent import compare, synthesize, validate_weight_proposals
from milestone1.evidence import DEFAULT_CASE
from milestone1.server import apply_judgment_provenance,init_db,load_run


CONFIG=dict(provider='vertex',project='rag-project-494802',location='global',model='gemini-3.8-flash')
METADATA={**CONFIG,'reported_model':'gemini-3.8-flash','usage':{'totalTokenCount':123}}


class VertexAdapterTest(unittest.TestCase):
    def test_global_endpoint_and_regional_endpoint(self):
        self.assertEqual(llm.vertex_url(CONFIG),'https://aiplatform.googleapis.com/v1/projects/rag-project-494802/locations/global/publishers/google/models/gemini-3.8-flash:generateContent')
        self.assertTrue(llm.vertex_url({**CONFIG,'location':'us-central1'}).startswith('https://us-central1-aiplatform.googleapis.com/'))

    def test_settings_cannot_inject_a_host_or_path(self):
        for field,value in [('project','../outside'),('location','global/evil'),('model','gemini-3:other'),('model','https://example.com')]:
            with self.assertRaises(ValueError):llm.vertex_url({**CONFIG,field:value})

    @patch('milestone1.llm.adc_path')
    @patch('milestone1.llm.shutil.which',return_value='/sdk/bin/gcloud')
    @patch('milestone1.llm.settings',return_value=CONFIG)
    def test_status_is_local_configuration_not_a_live_health_check(self,config,which,adc):
        adc.return_value.is_file.return_value=True
        with patch('milestone1.llm.adc_access_token') as token:
            status=llm.model_status()
        self.assertTrue(status['configured'])
        self.assertIn('checked when a request is made',status['detail'])
        token.assert_not_called()

    @patch('milestone1.llm.shutil.which',return_value='/sdk/bin/gcloud')
    @patch('milestone1.llm.subprocess.run')
    def test_adc_token_is_captured_and_never_in_an_error(self,run,which):
        run.return_value=Mock(returncode=0,stdout='private-test-token\n',stderr='')
        self.assertEqual(llm.adc_access_token(),'private-test-token')
        args=run.call_args
        self.assertEqual(args.args[0],['/sdk/bin/gcloud','auth','application-default','print-access-token'])
        self.assertTrue(args.kwargs['capture_output'])
        run.return_value=Mock(returncode=1,stdout='private-test-token',stderr='private-test-error')
        with self.assertRaises(llm.ModelServiceError) as error:llm.adc_access_token()
        self.assertNotIn('private-test',str(error.exception))

    @patch('milestone1.llm.shutil.which',return_value='/sdk/bin/gcloud')
    @patch('milestone1.llm.subprocess.run',side_effect=subprocess.TimeoutExpired('gcloud',40))
    def test_adc_timeout_is_actionable_without_raw_process_output(self,run,which):
        with self.assertRaisesRegex(llm.ModelServiceError,'Could not obtain'):llm.adc_access_token()

    def test_tls_verification_is_enabled(self):
        context=llm.ssl_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)

    @patch('milestone1.llm.urllib.request.urlopen')
    def test_http_error_redacts_body_headers_and_token(self,urlopen):
        urlopen.side_effect=urllib.error.HTTPError('https://example.com',403,'secret-body',{'Authorization':'secret-token'},None)
        with self.assertRaises(llm.ModelServiceError) as error:
            llm._post(urllib.request.Request('https://example.com'))
        self.assertIn('HTTP 403',str(error.exception))
        self.assertIn('Vertex AI User',str(error.exception))
        self.assertNotIn('secret',str(error.exception))

    @patch('milestone1.llm.urllib.request.urlopen',side_effect=http.client.RemoteDisconnected('private-upstream-message'))
    def test_closed_connection_is_a_safe_transport_error(self,urlopen):
        with self.assertRaisesRegex(llm.ModelServiceError,'could not be reached') as error:
            llm._post(urllib.request.Request('https://example.com'))
        self.assertNotIn('private',str(error.exception))

    def generate(self,payload):
        with patch('milestone1.llm.settings',return_value=CONFIG),patch('milestone1.llm.adc_access_token',return_value='test-token'),patch('milestone1.llm._post',return_value=payload) as post:
            response=llm.generate('system instructions','case and claims')
        return response,post.call_args.args[0]

    def test_gemini_request_and_response_metadata(self):
        (response,metadata),request=self.generate({'candidates':[{'finishReason':'STOP','content':{'parts':[{'thought':True,'text':'private thinking'},{'text':'{"synthesis": []}'}]}}], 'modelVersion':'gemini-3.8-flash','usageMetadata':{'totalTokenCount':123}})
        body=json.loads(request.data)
        self.assertEqual(body['generationConfig']['responseMimeType'],'application/json')
        self.assertEqual(body['generationConfig']['thinkingConfig'],{'thinkingLevel':'LOW'})
        self.assertEqual(body['systemInstruction']['parts'][0]['text'],'system instructions')
        self.assertEqual(response,'{"synthesis": []}')
        self.assertNotIn('private thinking',response)
        self.assertEqual(metadata['reported_model'],'gemini-3.8-flash')
        self.assertEqual(metadata['project'],CONFIG['project'])
        self.assertEqual(metadata['usage']['totalTokenCount'],123)
        self.assertNotIn('token',metadata)

    def test_gemini_blocked_or_truncated_response_is_not_success(self):
        for payload in [{'candidates':[]},{'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'incomplete'}]}}]}]:
            with self.assertRaises(llm.ModelServiceError):self.generate(payload)


class ModelJudgmentTest(unittest.TestCase):
    def setUp(self):
        self.result=compare(deepcopy(DEFAULT_CASE))
        self.proposal=dict(option_id='elacestrant',factor_id='direct_post_cdk',proposed_factor=1.05,
                           reason='The supplied evidence supports a cautious analyst adjustment, pending review.',
                           claim_ids=['elacestrant.adjustment.direct_post_cdk'])

    def test_proposal_is_cited_and_not_applied(self):
        before=deepcopy(self.result)
        row=validate_weight_proposals([self.proposal],self.result)[0]
        self.assertEqual(row['previous_factor'],1.2)
        self.assertEqual(row['proposed_factor'],1.05)
        self.assertIn('EMERALD',row['source_ids'])
        self.assertIn('not applied',row['status'])
        self.assertEqual(self.result,before)

    def test_invalid_factor_bounds_types_and_duplicates(self):
        for factor in [True,float('nan'),float('inf'),.49,2.01,'1.2']:
            with self.assertRaises(ValueError):validate_weight_proposals([{**self.proposal,'proposed_factor':factor}],self.result)
        with self.assertRaises(ValueError):validate_weight_proposals([self.proposal,self.proposal],self.result)

    def test_unknown_factor_treatment_and_foreign_citations(self):
        for changes in [{'option_id':'invented'},{'factor_id':'invented'},{'claim_ids':['capivasertib.pros.1']},{'claim_ids':[]},{'reason':'See https://example.com'}]:
            with self.assertRaises(ValueError):validate_weight_proposals([{**self.proposal,**changes}],self.result)

    def test_inapplicable_treatment_cannot_receive_a_weight_proposal(self):
        row={**self.proposal,'option_id':'olaparib','factor_id':'indirect_sequence','claim_ids':['olaparib.adjustment.indirect_sequence']}
        with self.assertRaises(ValueError):validate_weight_proposals([row],self.result)

    def test_zero_proposals_is_valid_and_over_eight_is_invalid(self):
        self.assertEqual(validate_weight_proposals([],self.result),[])
        with self.assertRaises(ValueError):validate_weight_proposals([self.proposal]*9,self.result)

    def model_review(self):
        payload=dict(synthesis=[dict(text='Conditional, cited interpretation.',claim_ids=['elacestrant.pros.1'])],weight_proposals=[self.proposal])
        with patch('milestone1.agent.model_configured',return_value=True),patch('milestone1.agent.generate',return_value=(json.dumps(payload),deepcopy(METADATA))):
            return synthesize(deepcopy(self.result))

    def test_synthesis_preserves_python_scores_and_records_provenance(self):
        result=self.model_review()
        self.assertEqual(result['options'],self.result['options'])
        self.assertEqual(result['mode'],'model_synthesis')
        self.assertEqual(result['model_metadata'],METADATA)
        self.assertTrue(result['model_judgments'][0]['source_ids'])

    def test_changed_weights_recalculate_scores_and_preserve_parent_review(self):
        parent=self.model_review()
        design=deepcopy(parent['endpoint_design'])
        design['factor_overrides']={'elacestrant':{'direct_post_cdk':1.05}}
        result=compare(DEFAULT_CASE,endpoint_design=design)
        apply_judgment_provenance(result,parent,'parent-test-run')
        self.assertEqual(result['parent_model_judgment_run_id'],'parent-test-run')
        self.assertEqual(result['parent_model_synthesis'],parent['synthesis'])
        self.assertEqual(len(result['applied_model_judgments']),1)
        self.assertLess(result['options'][0]['endpoint_comparison']['score'],parent['options'][0]['endpoint_comparison']['score'])

    def test_changed_case_or_design_rejects_old_judgments(self):
        parent=self.model_review()
        changed=deepcopy(DEFAULT_CASE);changed['age']+=1
        for result in [compare(changed),compare(DEFAULT_CASE,endpoint_design={**deepcopy(parent['endpoint_design']),'events':300})]:
            with self.assertRaises(ValueError):apply_judgment_provenance(result,parent,'old-run')

    def test_unapplied_or_nonmodel_parent_cannot_be_marked_as_applied(self):
        with self.assertRaises(ValueError):apply_judgment_provenance(deepcopy(self.result),self.model_review(),'parent')
        with self.assertRaises(ValueError):apply_judgment_provenance(deepcopy(self.result),self.result,'parent')

    def test_scope_guard_prevents_a_model_call(self):
        with patch('milestone1.agent.model_configured',return_value=True),patch('milestone1.agent.generate') as generate:
            for changes in [{'her2':'unknown'},{'visceral_crisis':True},{'er_positive':False}]:
                with self.assertRaises(ValueError):synthesize(compare({**DEFAULT_CASE,**changes}))
        generate.assert_not_called()

    def test_saved_review_reloads_with_feedback_without_calling_a_model(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.sqlite3';init_db(path)
            run_id='12345678-1234-4234-8234-123456789012'
            result=self.model_review();result['run_id']=run_id
            with sqlite3.connect(path) as db:
                db.execute('INSERT INTO runs VALUES (?,?,?)',(run_id,'today',json.dumps(result)))
                db.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?)',('review-id',run_id,'today','select','elacestrant','Review comment'))
            with patch('milestone1.llm.generate') as generate:
                loaded=load_run(path,run_id)
            self.assertEqual(loaded['model_metadata'],METADATA)
            self.assertEqual(loaded['saved_reviews'][0]['comment'],'Review comment')
            self.assertIsNone(load_run(path,'not-a-uuid'))
            self.assertIsNone(load_run(path,'00000000-0000-4000-8000-000000000000'))
            generate.assert_not_called()


if __name__=='__main__':unittest.main()
