import unittest
from pathlib import Path

from config.ba_config import BusinessArtefactType
from utils.expert_rules import format_classification_rules, format_inference_rules


class ClassificationRuleFormattingTests(unittest.TestCase):
    def test_formats_classification_rules_as_readable_rows(self):
        rules = {
            BusinessArtefactType.Capability: [
                {
                    "condition": "describes what the organisation can do",
                    "conclusion": "it is a Capability",
                    "examples": ["Claims processing", "Customer management"],
                    "counter_examples": ["Process claims in 24 hours"],
                }
            ]
        }

        self.assertEqual(
            format_classification_rules(rules),
            [
                {
                    "Artefact Type": "Capability",
                    "Condition": "describes what the organisation can do",
                    "Conclusion": "it is a Capability",
                    "Examples": "Claims processing; Customer management",
                    "Counter-examples": "Process claims in 24 hours",
                }
            ],
        )

    def test_empty_classification_rules_produce_no_rows(self):
        self.assertEqual(format_classification_rules({}), [])


class InferenceRuleFormattingTests(unittest.TestCase):
    def test_formats_inference_rules_as_readable_rows(self):
        rules = [
            (
                BusinessArtefactType.Capability,
                BusinessArtefactType.Process,
                "enactedBy",
                "Capabilities are enacted by Processes",
            )
        ]

        self.assertEqual(
            format_inference_rules(rules),
            [
                {
                    "Source Type": "Capability",
                    "Relationship": "enactedBy",
                    "Target Type": "Process",
                    "Description": "Capabilities are enacted by Processes",
                }
            ],
        )

    def test_empty_inference_rules_produce_no_rows(self):
        self.assertEqual(format_inference_rules([]), [])


class ExpertRulesTabIntegrationTests(unittest.TestCase):
    def test_streamlit_app_wires_expert_rules_into_results_tabs(self):
        app_source = (
            Path(__file__).resolve().parents[1] / "streamlit_app.py"
        ).read_text(encoding="utf-8")

        self.assertIn('"Expert Rules"', app_source)
        self.assertIn("format_classification_rules(ARTEFACT_RULES)", app_source)
        self.assertIn("format_inference_rules(INFERENCE_RULES)", app_source)


if __name__ == "__main__":
    unittest.main()
