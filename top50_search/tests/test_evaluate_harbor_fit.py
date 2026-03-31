import unittest
from pathlib import Path

from top50_search.src.evaluate_harbor_fit import evaluate_skill_bundle

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "skill_bundles"


class EvaluateHarborFitTests(unittest.TestCase):
    def test_data_quality_bundle_selected(self):
        bundle = FIXTURE_ROOT / "data-quality-audit"
        result = evaluate_skill_bundle(bundle)
        self.assertTrue(result["selected"])

        capability = result["capability_boundary"]
        self.assertIn("data_objective_clarity", capability["positive_hits"])
        self.assertIn("schema_scope", capability["positive_hits"])
        self.assertEqual(capability["negative_hits"], [])

        environment = result["environment_reproducibility"]
        self.assertIn("deterministic_configuration", environment["positive_hits"])
        self.assertIn("resource_specified", environment["positive_hits"])
        self.assertEqual(environment["negative_hits"], [])

        verifier = result["verifier_stability"]
        self.assertIn("explicit_thresholds", verifier["positive_hits"])
        self.assertIn("automated_checks", verifier["positive_hits"])
        self.assertEqual(verifier["negative_hits"], [])

    def test_meta_registry_bundle_rejected(self):
        bundle = FIXTURE_ROOT / "meta-registry-skill"
        result = evaluate_skill_bundle(bundle)
        self.assertFalse(result["selected"])

        capability = result["capability_boundary"]
        self.assertIn("registry_or_session_focus", capability["negative_hits"])
        self.assertIn("installation_or_publication_flow", capability["negative_hits"])
        self.assertLessEqual(capability["score"], 0)

        verifier = result["verifier_stability"]
        self.assertIn("heuristic_judgment", verifier["negative_hits"])
        self.assertLessEqual(verifier["score"], 0)
        self.assertNotIn("explicit_thresholds", verifier["positive_hits"])
        self.assertNotIn("automated_checks", verifier["positive_hits"])

    def test_subjective_workflow_bundle_rejected(self):
        bundle = FIXTURE_ROOT / "subjective-workflow-skill"
        result = evaluate_skill_bundle(bundle)
        self.assertFalse(result["selected"])

        environment = result["environment_reproducibility"]
        self.assertIn("vague_exploration", environment["negative_hits"])
        self.assertIn("marketplace_or_dispatcher_dependency", environment["negative_hits"])
        self.assertLessEqual(environment["score"], 0)

        verifier = result["verifier_stability"]
        self.assertIn("exploratory_only", verifier["negative_hits"])
        self.assertLessEqual(verifier["score"], 0)
        capability = result["capability_boundary"]
        self.assertNotIn("schema_scope", capability["positive_hits"])
        self.assertNotIn("data_engineering_ownership", capability["positive_hits"])

    def test_negation_word_boundaries_allow_known_tokens(self):
        bundle = FIXTURE_ROOT / "negation-regression"
        result = evaluate_skill_bundle(bundle)

        self.assertTrue(result["selected"])
        verifier = result["verifier_stability"]
        self.assertIn("explicit_thresholds", verifier["positive_hits"])
        self.assertIn("automated_checks", verifier["positive_hits"])
        self.assertNotIn("automated_checks", verifier["negative_hits"])

    def test_realistic_data_quality_framework_selected(self):
        bundle = FIXTURE_ROOT / "realistic-data-quality-frameworks"
        result = evaluate_skill_bundle(bundle)

        self.assertTrue(result["selected"])
        self.assertIn("schema_scope", result["capability_boundary"]["positive_hits"])
        self.assertIn("deterministic_configuration", result["environment_reproducibility"]["positive_hits"])
        self.assertIn("automated_checks", result["verifier_stability"]["positive_hits"])
