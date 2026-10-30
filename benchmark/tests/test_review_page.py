import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from benchmark.review_html import prepare_data,build,script_json
from benchmark.scientific_calibration import calibrate
from benchmark.scientific import DIMENSIONS
from benchmark.dataset import resolve_frozen_input

REPORT=Path(__file__).resolve().parents[1]/'reports/scientific-defense-v3-gemini.json'


class ReviewHTMLTests(unittest.TestCase):
    def test_payload_has_nine_proposals_and_no_private_runtime_paths(self):
        data=prepare_data(REPORT)
        self.assertEqual(len(data['cases']),3)
        self.assertEqual(sum(len(c['populations']) for c in data['cases']),9)
        raw=json.dumps(data)
        for forbidden in ('/Users/','"project":','application_default_credentials','frozen_input','promptTokenCount'):
            self.assertNotIn(forbidden,raw)
        self.assertTrue(all(len(c['input_sha256'])==64 for c in data['cases']))

    def test_complete_proposal_text_and_citations_are_preserved(self):
        data=prepare_data(REPORT)
        source=json.loads(REPORT.read_text())
        frozen=json.loads(resolve_frozen_input(REPORT,source['cases'][0]['frozen_input']).read_text())
        self.assertEqual(data['cases'][0]['populations'][0]['inclusion'],frozen['options'][0]['inclusion'])
        self.assertTrue(data['cases'][0]['populations'][0]['protocol_pending'])

    def test_html_is_a_single_file_without_external_runtime_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'review.html';build(REPORT,out);html=out.read_text()
        self.assertTrue(html.lower().startswith('<!doctype html>'))
        self.assertNotRegex(html,r'<script[^>]+src=')
        self.assertNotRegex(html,r'<link[^>]+stylesheet')
        self.assertNotIn('fetch(',html)
        self.assertIn('id="review-data"',html)
        self.assertIn('id="review-state" type="application/json">null</script>',html)
        self.assertNotIn('/Users/',html)
        data=json.loads(re.search(r'<script id="review-data" type="application/json">(.*?)</script>',html,re.S)[1])
        self.assertEqual(len(data['dataset_id']),64)

    def test_script_json_preserves_text_without_allowing_script_breakout(self):
        payload={'text':'</script><script>alert(1)</script>&'}
        text=script_json(payload)
        self.assertNotIn('</script>',text)
        self.assertEqual(json.loads(text),payload)

    def test_report_and_frozen_inputs_can_move_to_another_checkout(self):
        source=json.loads(REPORT.read_text())
        with tempfile.TemporaryDirectory() as folder:
            target_report=Path(folder)/REPORT.name
            target_report.write_text(json.dumps(source))
            for case in source['cases']:
                self.assertFalse(Path(case['frozen_input']).is_absolute())
                target=resolve_frozen_input(target_report,case['frozen_input'])
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(resolve_frozen_input(REPORT,case['frozen_input']),target)
            generated=prepare_data(target_report)
        self.assertEqual(generated['dataset_id'],prepare_data(REPORT)['dataset_id'])

    def test_portable_ratings_match_full_frozen_input_hash(self):
        source=json.loads(REPORT.read_text());case=source['cases'][0];population=case['defense_rubric']['populations'][0]
        digest=hashlib.sha256(resolve_frozen_input(REPORT,case['frozen_input']).read_bytes()).hexdigest()
        grades={d:2 for d in DIMENSIONS}
        result=calibrate([dict(file=Path(case['frozen_input']).name,input_sha256=digest,option_id=population['option_id'],scientific_grades=grades)],[source])
        self.assertEqual(result['populations'],1)
        with self.assertRaises(ValueError):
            calibrate([dict(file=case['frozen_input'],input_sha256='0'*64,option_id=population['option_id'],scientific_grades=grades)],[source])


if __name__=='__main__':unittest.main()
