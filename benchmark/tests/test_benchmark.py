"""Offline tests for the benchmark scorers.

    python3 -m unittest discover -s benchmark/tests -v

These pin the arithmetic, not the clinical content. The point is that a scoring
change cannot silently move the numbers: each test states the behaviour a
reviewer expects and fails loudly when it changes.
"""
import unittest

from benchmark import accrual, amendment, outcome_alignment, reference_accuracy, rubric
from benchmark.baselines import from_demo, original_criteria
from benchmark.normalize import clause_delta, clause_similarity, concepts, split_clauses
from benchmark.schema import citation_pairs, normalise_option_set
from benchmark.sources import SourceCatalog, sentence_support


def small_catalog() -> SourceCatalog:
    return SourceCatalog({
        "TRIAL": dict(id="TRIAL", title="A phase 3 trial", scope="ESR1-mutated disease after prior endocrine therapy.",
                      url="https://pubmed.ncbi.nlm.nih.gov/35584336/"),
        "FDA-CNS": dict(id="FDA-CNS", title="FDA guidance on brain metastases",
                    scope="Consider including patients with treated stable brain metastases; avoid unjustified exclusion.",
                    url="https://example.org/cns"),
        "LABEL": dict(id="LABEL", title="Prescribing information",
                      scope="Assess interstitial lung disease and neutropenia before enrollment.",
                      url="https://example.org/label"),
    }, fetch=False)


def option(option_id, inclusion=(), exclusion=(), pros=(), cons=(), axes=(), estimates=None):
    return dict(option_id=option_id, population=f"population {option_id}", axes=list(axes),
                inclusion=list(inclusion), exclusion=list(exclusion), pros=list(pros),
                cons=list(cons), estimates=estimates or {}, references=[])


def row(text, purpose="efficacy", sources=("TRIAL",)):
    return dict(text=text, purpose=purpose, source_ids=list(sources), reason="A prespecified criterion rationale.")


class ClauseParsingTests(unittest.TestCase):
    def test_numbered_lines_become_clauses(self):
        text = "1. Age 18 or older.\n2. HER2-low disease.\n- No prior chemotherapy."
        self.assertEqual(len(split_clauses(text)), 3)

    def test_concepts_are_recognised(self):
        self.assertIn("cns_brain_mets", concepts("History of brain metastases is excluded"))
        self.assertIn("her2_low", concepts("HER2-low, IHC 1+ or 2+/ISH negative"))

    def test_threshold_conflict_lowers_the_match(self):
        same = clause_similarity("At least 2 prior lines of therapy", "at least 2 prior lines")
        clash = clause_similarity("At least 2 prior lines of therapy", "at least 4 prior lines")
        self.assertGreater(same["score"], clash["score"])
        self.assertTrue(clash["numeric_conflict"])

    def test_delta_reports_added_and_removed(self):
        delta = clause_delta("1. HER2-low disease.\n2. No prior chemotherapy.",
                             "1. HER2-low disease.\n2. Prior endocrine therapy required.")
        self.assertEqual(len(delta["added"]), 1)
        self.assertEqual(len(delta["removed"]), 1)


class ReferenceAccuracyTests(unittest.TestCase):
    def test_unknown_source_is_fabrication(self):
        catalog = small_catalog()
        option_set = normalise_option_set({"options": [option("a", pros=[row("A real claim.", sources=["NOPE"])])]})
        result = reference_accuracy.score_reference_accuracy(option_set, catalog)
        self.assertEqual(result["fabricated_ids"], ["NOPE"])
        self.assertEqual(result["counts"]["fabricated"], 1)

    def test_low_overlap_claim_stays_in_screen_denominator(self):
        catalog = small_catalog()
        option_set = normalise_option_set({"options": [option("a", cons=[
            row("Subgroup benefit does not establish a predictive interaction for this cohort.")])]})
        result = reference_accuracy.score_reference_accuracy(option_set, catalog)
        self.assertEqual(result["support_denominator"], 1)
        self.assertEqual(result["screen_score"], 0.0)
        self.assertIsNone(result["verified_support_score"])

    def test_supported_claim_scores(self):
        catalog = small_catalog()
        option_set = normalise_option_set({"options": [option("a", inclusion=[
            row("ESR1-mutated disease after prior endocrine therapy.")])]})
        result = reference_accuracy.score_reference_accuracy(option_set, catalog)
        self.assertGreaterEqual(result["support_score"], 0.5)

    def test_uncited_claim_is_reported(self):
        catalog = small_catalog()
        option_set = normalise_option_set({"options": [option("a", inclusion=[row("Anything.", sources=[])])]})
        result = reference_accuracy.score_reference_accuracy(option_set, catalog)
        self.assertEqual(result["counts"]["uncited"], 1)

    def test_sentence_support_picks_the_relevant_sentence(self):
        support = sentence_support("Avoid excluding patients with stable brain metastases.",
                                   "The trial enrolled adults. Avoid unjustified exclusion of stable brain metastases.")
        self.assertIn("brain metastases", support["sentence"])


class RubricTests(unittest.TestCase):
    def good_option_set(self):
        criteria = [row("HR-positive, HER2-low metastatic breast cancer after progression on endocrine therapy plus CDK4/6.", purpose="scope"),
                    row("Require HER2-low disease, IHC 1+ or 2+/ISH-negative."),
                    row("Exclude prior chemotherapy for metastatic disease.", purpose="evidence_alignment",
                        sources=["FDA-CNS"])]
        exclusion = [row("Exclude interstitial lung disease pending assessment.", purpose="safety", sources=["LABEL"]),
                     row("Allow treated stable brain metastases; exclude only uncontrolled CNS disease.",
                         purpose="generalizability", sources=["FDA-CNS"])]
        pros = [row("Matches the label population."), row("Higher chance of showing an effect.")]
        cons = [row("Narrow population may slow accrual."), row("Safety monitoring limits generalisation.")]
        estimates = dict(eligible_share=dict(low=0.1, high=0.2, source_ids=["TRIAL"]),
                         effect_direction=dict(text="Benefit likely in HER2-low.", source_ids=["TRIAL"]))
        out = normalise_option_set({
            "options": [
                option("a", criteria, exclusion, pros, cons, axes=["HER2 expression"], estimates=estimates),
                option("b", criteria + [row("Exclude prior ADC exposure.")], exclusion, pros, cons,
                       axes=["prior ADC"], estimates=estimates),
                option("c", criteria + [row("Require at least 2 prior endocrine lines.")], exclusion, pros, cons,
                       axes=["prior endocrine duration"], estimates=estimates),
            ],
            "recommendation": dict(option_id="a", defense=[row("Chosen over b because it accrues faster."),
                                                           row("Chosen over c because it matches the label.")]),
        })
        for opt in out["options"]:
            opt["defense"] = [row("This candidate is a testable protocol population, but differential benefit remains unknown.")]
        return out

    def test_good_set_scores_high(self):
        result = rubric.score_defense_rubric(self.good_option_set())
        self.assertGreater(result["score"], 0.9, result["failures"])

    def test_blanket_cns_exclusion_fails(self):
        option_set = self.good_option_set()
        for opt in option_set["options"]:
            opt["exclusion"].append(row("Exclude any history of CNS disease.", purpose="safety", sources=["LABEL"]))
        result = rubric.score_defense_rubric(option_set)
        failed = [r["rule"] for r in result["failures"]]
        self.assertIn("cns_not_blanket", failed)

    def test_overclaiming_is_caught(self):
        option_set = self.good_option_set()
        option_set["options"][0]["pros"].append(row("This cohort is proven to benefit more."))
        self.assertIn("no_overclaiming", [r["rule"] for r in rubric.score_defense_rubric(option_set)["failures"]])

    def test_hedged_negation_is_not_an_overclaim(self):
        option_set = self.good_option_set()
        option_set["options"][0]["cons"].append(row("The subgroup result does not prove benefit in wild-type disease."))
        self.assertNotIn("no_overclaiming", [r["rule"] for r in rubric.score_defense_rubric(option_set)["failures"]])

    def test_safety_gate_flags_unsafe_criteria(self):
        option_set = self.good_option_set()
        option_set["options"][0]["exclusion"].append(row("Exclude any CNS disease.", purpose="safety"))
        self.assertFalse(rubric.safety_gate(option_set)["passed"])

    def test_single_option_fails_distinctness(self):
        option_set = self.good_option_set()
        option_set["options"] = option_set["options"][:1]
        self.assertIn("distinct_options", [r["rule"] for r in rubric.score_defense_rubric(option_set)["set_design"]["failures"]])


class AmendmentTests(unittest.TestCase):
    def setUp(self):
        self.gold = dict(pair_id="p1", nct_id="NCT1", kind="snapshot",
                         original_criteria="1. HER2-low disease.\n2. No prior chemotherapy.",
                         amended_criteria="1. HER2-low or HER2-ultralow disease.\n2. No prior chemotherapy.",
                         change=dict(direction="changed", axis="HER2 expression",
                                     clauses=["HER2-low or HER2-ultralow disease"]),
                         cutoff_date="2020-01-01", review_status="approved")

    def score(self, option_set, gold, agent_cutoff=None):
        option_set["provenance"] = dict(model_knowledge_cutoff=agent_cutoff or "2019-06-01", evidence_cutoff="2019-06-01")
        return amendment.score_retrodiction(option_set, gold)

    def test_option_carrying_the_change_scores(self):
        # Agent knowledge must precede the amendment's public date (2020-01-01),
        # otherwise the change could have been copied rather than reasoned to.
        option_set = normalise_option_set({"options": [option("a", [row("Require HER2-ultralow or HER2-low disease.")])]})
        result = self.score(option_set, self.gold, agent_cutoff="2019-06-01")
        self.assertEqual(result["score"], 1.0)
        self.assertFalse(result["provenance_leak"])

    def test_original_wording_does_not_count_as_the_change(self):
        # The amendment widened HER2-low to "HER2-low or ultralow". An option
        # that still requires only HER2-low repeats the original and missed it.
        option_set = normalise_option_set({"options": [option("a", [row("Require HER2-low disease.")])]})
        result = self.score(option_set, self.gold)
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["copies_of_original"], ["a"])

    def test_unrelated_option_scores_zero(self):
        option_set = normalise_option_set({"options": [option("a", [row("Require HER2-positive disease.")])]})
        self.assertEqual(self.score(option_set, self.gold)["score"], 0.0)

    def test_agent_after_cutoff_is_a_provenance_leak(self):
        option_set = normalise_option_set({"options": [option("a", [row("Require HER2-ultralow or HER2-low disease.")])]})
        result = self.score(option_set, self.gold, agent_cutoff="2022-01-01")
        self.assertTrue(result["provenance_leak"])
        self.assertIsNone(result["score"])

    def test_derive_change_from_two_snapshots(self):
        change = amendment.derive_change("1. HER2-low disease.", "1. HER2-low disease.\n2. Exclude prior ADC.")
        self.assertEqual(len(change["added"]), 1)
        self.assertEqual(change["direction"], "unreviewed")


class AccrualTests(unittest.TestCase):
    gold = dict(trial_id="t", nct_id="NCT1", stop_reason="Slow accrual",
                restrictive_criteria=["Exclude prior ADC exposure"])

    def test_con_with_accrual_language_hits(self):
        option_set = normalise_option_set({"options": [option("a", cons=[
            row("Excluding any prior ADC exposure narrows the pool and may slow accrual.")] )]})
        self.assertEqual(accrual.score_accrual_postmortem(option_set, self.gold)["score"], 1.0)

    def test_con_without_accrual_language_is_a_near_miss(self):
        option_set = normalise_option_set({"options": [option("a", cons=[row("Prior ADC exposure is excluded.")])]})
        result = accrual.score_accrual_postmortem(option_set, self.gold)
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(len(result["flag_for_review"]), 1)


class OutcomeAlignmentTests(unittest.TestCase):
    gold = dict(trial_id="t", nct_id="NCT1", drug="T-DXd",
                subgroups=[dict(label="HER2-low", hazard_ratio=0.62, interaction_p=0.04),
                           dict(label="HER2-ultralow", hazard_ratio=0.78, interaction_p=0.04)])

    def test_alignment_to_the_favourable_subgroup(self):
        option_set = normalise_option_set({
            "options": [option("a", [row("Require HER2-low disease, IHC 1+.")])],
            "recommendation": dict(option_id="a", defense=[])})
        result = outcome_alignment.score_outcome_alignment(option_set, self.gold)
        self.assertEqual(result["status"], "aligned")
        self.assertIn("caveat", result)

    def test_misalignment_to_the_unfavourable_subgroup(self):
        option_set = normalise_option_set({
            "options": [option("a", [row("Require HER2-ultralow disease.")])],
            "recommendation": dict(option_id="a", defense=[])})
        self.assertEqual(outcome_alignment.score_outcome_alignment(option_set, self.gold)["status"], "misaligned")

    def test_indistinct_subgroups_get_no_score(self):
        gold = dict(trial_id="t", nct_id="NCT1", subgroups=[
            dict(label="HER2-low", hazard_ratio=0.62, interaction_p=0.04), dict(label="HER2-ultralow", hazard_ratio=0.63, interaction_p=0.04)])
        option_set = normalise_option_set({
            "options": [option("a", [row("Require HER2-low disease.")])],
            "recommendation": dict(option_id="a", defense=[])})
        result = outcome_alignment.score_outcome_alignment(option_set, gold)
        self.assertEqual(result["status"], "indistinct_subgroups")
        self.assertIsNone(result["score"])


class EndToEndTests(unittest.TestCase):
    def test_demo_option_set_has_the_graded_shape(self):
        catalog = SourceCatalog.from_demo(fetch=False)
        option_set = from_demo("elacestrant", catalog)
        self.assertEqual(len(option_set["options"]), 3)
        self.assertTrue(citation_pairs(option_set))
        ref = reference_accuracy.score_reference_accuracy(option_set, catalog)
        self.assertEqual(ref["fabricated_ids"], [])  # the demo cites only catalog ids
        self.assertIsNotNone(ref["support_score"])

    def test_original_criteria_baseline_is_uncited(self):
        option_set = original_criteria("t", dict(nct_id="NCT1", original_criteria="1. HER2-low.\n2. Age 18+."))
        self.assertTrue(all(not p["source_ids"] for p in citation_pairs(option_set)))


if __name__ == "__main__":
    unittest.main()
