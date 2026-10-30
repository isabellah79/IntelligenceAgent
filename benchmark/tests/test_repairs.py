"""Regression tests for misleading scores, clinical field mixups and trial joins."""
import contextlib
import csv
import io
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from benchmark import amendment, baselines, dataset, judge, outcome_alignment, reference_accuracy, rubric, run
from benchmark.normalize import best_match, clause_delta, numbers
from benchmark.schema import normalise_option_set
from benchmark.sources import SourceCatalog
from benchmark.trial_audit import match_trial, audit


class ReferenceRegressionTests(unittest.TestCase):
    def grade(self, claim, evidence, source="S"):
        catalog = SourceCatalog({"S":dict(title="", scope=evidence, url="https://example.org")})
        output = normalise_option_set(dict(options=[dict(inclusion=[dict(text=claim, source_ids=[source])])]))
        return reference_accuracy.score_reference_accuracy(output, catalog)

    def test_opposite_statement_is_not_supported(self):
        result = self.grade("ESR1 mutation predicts benefit from endocrine therapy.",
                            "ESR1 mutation does not predict benefit from endocrine therapy.")
        self.assertEqual(result["counts"], {"conflict_flag":1})
        self.assertEqual(result["screen_score"], 0)

    def test_bad_claims_cannot_disappear_from_denominator(self):
        result = self.grade("An unrelated recruitment claim is asserted without evidence.",
                            "ESR1 mutation was measured before endocrine therapy.")
        self.assertEqual(result["support_denominator"], 1)
        self.assertIsNone(result["verified_support_score"])

    def test_bibliography_only_fabrication_is_detected(self):
        output = normalise_option_set(dict(options=[dict(references=[dict(source_id="INVENTED")])]))
        self.assertEqual(reference_accuracy.score_reference_accuracy(output, SourceCatalog({}))["fabricated_ids"], ["INVENTED"])

    def test_uncited_estimate_is_not_omitted(self):
        output = normalise_option_set(dict(options=[dict(estimates=dict(eligible_share=dict(low=.2, high=.3))) ]))
        result = reference_accuracy.score_reference_accuracy(output, SourceCatalog({}))
        self.assertEqual(result["counts"]["uncited"], 1)

    def test_biomarker_identifiers_are_not_numeric_thresholds(self):
        self.assertEqual(numbers("ESR1 HER2 CDK4/6 ECOG <=2"), {2.0})

    def test_reversed_operator_is_a_different_criterion(self):
        self.assertFalse(best_match("ECOG <=2", ["ECOG >=2"])["matched"])

    def test_reversed_polarity_does_not_match(self):
        self.assertFalse(best_match("Include patients with ESR1 mutations", ["Exclude patients with ESR1 mutations"])["matched"])

    def test_selected_and_unselected_biomarker_populations_differ(self):
        self.assertFalse(best_match("Require a qualifying ESR1 mutation", ["Allow ESR1-mutated and non-mutated disease"])["matched"])

    def test_duration_restriction_is_not_equivalent_to_no_duration_limit(self):
        self.assertFalse(best_match("Require >=12 months prior endocrine therapy", ["Require prior endocrine therapy"])["matched"])


class PopulationScoreTests(unittest.TestCase):
    def setUp(self):
        self.output = baselines.from_demo("elacestrant")

    def test_endpoint_forecast_never_becomes_eligible_share(self):
        estimates = self.output["options"][0]["estimates"]
        self.assertEqual(estimates["eligible_share"]["status"], "unavailable")
        self.assertNotIn("low", estimates["eligible_share"])
        self.assertIsNotNone(estimates["endpoint_forecast"]["score"])

    def test_rationales_and_status_survive_adapter(self):
        row = self.output["options"][0]["inclusion"][0]
        self.assertTrue(row["reason"])
        self.assertEqual(row["status"], "evidence_supported")

    def test_one_option_ablation_has_identical_population_grade(self):
        original = rubric.score_defense_rubric(self.output)
        selected = baselines.one_option(self.output["trial"], SourceCatalog({}), self.output)
        self.assertEqual(len(selected["options"]), 1)
        self.assertEqual(rubric.score_defense_rubric(selected)["score"], original["populations"][0]["score"])

    def test_missing_reasons_reduce_only_affected_population_score(self):
        before = rubric.score_defense_rubric(self.output)
        for row in self.output["options"][0]["inclusion"]:
            row.pop("reason", None)
        after = rubric.score_defense_rubric(self.output)
        self.assertLess(after["populations"][0]["score"], before["populations"][0]["score"])
        self.assertEqual(after["populations"][1]["score"], before["populations"][1]["score"])

    def test_endpoint_value_does_not_change_defense_score(self):
        before = rubric.score_defense_rubric(self.output)["score"]
        self.output["options"][0]["estimates"]["endpoint_forecast"]["score"] = .01
        self.assertEqual(rubric.score_defense_rubric(self.output)["score"], before)

    def test_invalid_weights_cannot_silently_change_formula(self):
        for weights in ([], {"unknown":1}, {"pros_present":-1}, {"pros_present":float("nan")}, {"pros_present":True}):
            with self.assertRaises(ValueError):
                rubric.score_defense_rubric(self.output, weights)

    def test_distinct_axis_names_do_not_rescue_identical_criteria(self):
        for i in range(1, 3):
            self.output["options"][i]["inclusion"] = deepcopy(self.output["options"][0]["inclusion"])
            self.output["options"][i]["exclusion"] = deepcopy(self.output["options"][0]["exclusion"])
            self.output["options"][i]["axes"] = [f"invented axis {i}"]
        pairs = rubric.score_defense_rubric(self.output)["set_design"]["differentiation"]
        self.assertTrue(all(not p["differentiated"] for p in pairs))

    def test_esr1_selected_and_unselected_options_are_differentiated(self):
        pairs = rubric.differentiation(self.output)
        selected = next(p for p in pairs if p["left"] == "elacestrant__esr1" and p["right"] == "elacestrant__unselected")
        self.assertTrue(selected["differentiated"])

    def test_scope_cannot_pass_just_because_her2_positive_is_mentioned(self):
        self.output["options"][0]["inclusion"] = [dict(text="HER2-positive metastatic breast cancer after CDK4/6", purpose="scope", source_ids=[])]
        failures = rubric.score_defense_rubric(self.output)["populations"][0]["failures"]
        self.assertIn("scope_respected", [r["rule"] for r in failures])

    def test_saved_gemini_review_preserves_recommendation_without_reapplying_proposals(self):
        from milestone1.populations import propose
        saved = propose()
        saved.update(model_review=dict(treatment_id="elacestrant", recommendation=dict(population_id="elacestrant__long_response", reason="Conditional research choice", source_ids=["EMERALD-DURATION"]), criterion_proposals=[]),
                     model_metadata=dict(model="configured-gemini"), created_at="2026-10-30")
        adapted = baselines.from_result(saved)
        self.assertEqual(adapted["recommendation"]["option_id"], "elacestrant__long_response")
        self.assertEqual(adapted["provenance"]["agent"], "saved_gemini_review")


class TrialIdentityTests(unittest.TestCase):
    def setUp(self):
        self.pair = dict(pair_id="amendment-1", nct_id="NCT00000001", original_criteria="HER2-low disease", change=dict(clauses=["HER2-low or HER2-ultralow disease"]), cutoff_date="2020-01-01")
        self.pack = dict(pairs=[self.pair])

    def test_names_and_drug_overlap_do_not_create_a_trial_match(self):
        result = match_trial(dict(trial=dict(drug="elacestrant", source_trial_names=["EMERALD"])), self.pack)
        self.assertEqual(result["status"], "unmatched")

    def test_exact_id_match_does_not_imply_approved_gold(self):
        result = match_trial(dict(trial=dict(nct_id="NCT00000001")), self.pack)
        self.assertEqual(result["status"], "exact_id_match")
        self.assertIsNone(amendment.score_retrodiction(dict(options=[]), result["pair"])["score"])

    def test_ambiguous_amendment_requires_pair_id(self):
        self.pack["pairs"].append(dict(self.pair, pair_id="amendment-2"))
        self.assertEqual(match_trial(dict(trial=dict(nct_id="NCT00000001")), self.pack)["status"], "ambiguous")
        self.assertEqual(match_trial(dict(trial=dict(nct_id="NCT00000001", pair_id="amendment-2")), self.pack)["pair_id"], "amendment-2")

    def test_creation_date_is_not_used_as_knowledge_cutoff(self):
        self.pair["review_status"] = "approved"
        output = dict(options=[], provenance=dict(created="2019-01-01"))
        result = amendment.score_retrodiction(output, self.pair)
        self.assertEqual(result["status"], "temporal_controls_unverified")

    def test_unmatched_gold_remains_not_run(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            gold = Path(folder) / "gold.json"
            target = Path(folder) / "report.json"
            gold.write_text(json.dumps(self.pack))
            code = run.main(["--gold",str(gold),"--out",str(target),"--treatments","elacestrant"])
            report = json.loads(target.read_text())
        self.assertEqual(code, 0)
        self.assertIn("amendment_retrodiction", report["not_run"])
        self.assertEqual(report["summary"]["amendment_cases_scored"], 0)

    def test_threshold_edit_is_detected_even_when_concepts_are_unchanged(self):
        delta = clause_delta("ECOG <=1", "ECOG <=2")
        self.assertTrue(delta["added"] and delta["removed"])


class SnapshotExtractionTests(unittest.TestCase):
    def write_csv(self, path, records):
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    def test_snapshot_join_preserves_sections_and_requires_review(self):
        with tempfile.TemporaryDirectory() as folder:
            old, new = Path(folder)/"old.csv", Path(folder)/"new.csv"
            row = dict(nctId="NCT00000001", conditions="Breast Cancer", phases="PHASE3", bTitle="Example", startDate="2019-01-01", includeCriteria="ECOG <=1", excludeCriteria="Exclude interstitial lung disease")
            self.write_csv(old,[row])
            self.write_csv(new,[dict(row,includeCriteria="ECOG <=2")])
            pairs = dataset.build_amendment_pairs(old,new,older_snapshot_date="2020-01-01")
            self.assertEqual(len(pairs),1)
            self.assertEqual(pairs[0]["original_exclusion"],row["excludeCriteria"])
            self.assertEqual(pairs[0]["review_status"],"unreviewed_candidate")
            self.assertEqual(pairs[0]["change"]["direction"],"unreviewed")
            result = audit(dict(pairs=pairs),old,new)
            self.assertTrue(result["candidates"][0]["original_text_matches_export"])
            self.assertEqual(len(result["source_manifests"]["older"]["sha256"]),64)

    def test_duplicate_nct_ids_cannot_silently_overwrite_a_record(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"duplicate.csv"
            self.write_csv(path,[dict(nctId="NCT00000001"),dict(nctId="NCT00000001")])
            with self.assertRaises(ValueError):
                dataset.build_amendment_pairs(path,path)

    def test_min_change_and_split_membership_are_saved(self):
        from benchmark.extract_gold import main
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            old, new, output = (Path(folder)/name for name in ("old.csv","new.csv","gold.json"))
            row = dict(nctId="NCT00000001", conditions="Breast Cancer", phases="PHASE3", bTitle="Example", startDate="2019-01-01", includeCriteria="HER2-low disease", excludeCriteria="")
            self.write_csv(old,[row])
            self.write_csv(new,[dict(row,excludeCriteria="Exclude prior chemotherapy")])
            main(["--older",str(old),"--newer",str(new),"--out",str(output),"--min-change","2"])
            pack = json.loads(output.read_text())
        self.assertEqual(pack["pairs"],[])
        self.assertEqual(pack["splits"],dict(train=[],validation=[],test=[]))


class JudgeAndOutcomeTests(unittest.TestCase):
    def test_kappa_without_label_variation_is_undefined(self):
        self.assertIsNone(judge.cohens_kappa([True,True],[True,True]))
        self.assertEqual(judge.cohens_kappa([True,False],[True,False]),1.0)

    def test_general_llm_uses_configured_demo_provider(self):
        with patch("milestone1.llm.generate", return_value=(json.dumps(dict(options=[])),dict(model="test-gemini",provider="vertex"))) as generate:
            payload = baselines._ask("system", "task")
        generate.assert_called_once()
        self.assertEqual(payload["provenance"]["provider"], "vertex")

    def test_general_baseline_keeps_three_options(self):
        payload = baselines.from_demo()
        with patch("benchmark.baselines._ask", return_value=deepcopy(payload)):
            output = baselines.general_llm(payload["trial"], SourceCatalog({}))
        self.assertEqual(len(output["options"]), 3)

    def test_judge_requires_boolean_grades(self):
        output = baselines.from_demo()
        output["options"] = output["options"][:1]
        grades = {r["id"]:dict(pass_="false") for r in judge.rule_sheet()}
        with patch("benchmark.baselines._ask", return_value=dict(grades=grades)):
            with self.assertRaises(ValueError):
                judge.judge(output)

    def test_blank_human_grades_fail_before_paid_judge_call(self):
        fake_judge = unittest.mock.Mock()
        with self.assertRaises(ValueError):
            judge.calibrate([dict(file="unused.json", grades=dict(pros_present=None))], fake_judge)
        fake_judge.assert_not_called()

    def test_no_interaction_cannot_be_called_better_subgroup(self):
        output = normalise_option_set(dict(options=[dict(option_id="a", inclusion=[dict(text="Require HER2-low disease", purpose="efficacy")])], recommendation=dict(option_id="a")))
        gold = dict(subgroups=[dict(label="HER2-low",hazard_ratio=.5),dict(label="HER2-ultralow",hazard_ratio=.8)])
        result = outcome_alignment.score_outcome_alignment(output,gold)
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "inconclusive_no_interaction")


if __name__ == "__main__":
    unittest.main()
