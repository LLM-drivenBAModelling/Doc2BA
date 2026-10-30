import tempfile
import unittest
from pathlib import Path

from config.ba_config import BusinessArtefactType
from utils.csv_artefacts import (
    CsvArtefactError,
    classification_from_csv,
    resolve_artefact_type,
)


SAMPLE_CSV = """id,name,type,confidence,description
claims-processing,Claims Processing,Capability,1.0,Handle claims end to end
grow-retention,Grow customer retention,Goal,0.9,
digital-first,Digital-first strategy,Strategy,,
"""


class ResolveArtefactTypeTests(unittest.TestCase):
    def test_resolves_label_name_and_spaced_variants(self):
        self.assertEqual(
            resolve_artefact_type("Capability"),
            BusinessArtefactType.Capability,
        )
        self.assertEqual(
            resolve_artefact_type("value stream"),
            BusinessArtefactType.ValueStream,
        )
        self.assertEqual(
            resolve_artefact_type("ValueStream"),
            BusinessArtefactType.ValueStream,
        )

    def test_rejects_unknown_type(self):
        with self.assertRaises(CsvArtefactError) as ctx:
            resolve_artefact_type("Department")
        self.assertIn("unknown artefact type", str(ctx.exception))


class ClassificationFromCsvTests(unittest.TestCase):
    def test_maps_rows_to_classification_artefacts(self):
        result = classification_from_csv(SAMPLE_CSV, filename="ba-objects.csv")

        self.assertEqual(
            [artefact.id for artefact in result.artefacts],
            ["claims-processing", "grow-retention", "digital-first"],
        )
        self.assertEqual(result.artefacts[0].type, BusinessArtefactType.Capability)
        self.assertEqual(result.artefacts[1].type, BusinessArtefactType.Goal)
        self.assertEqual(result.artefacts[2].type, BusinessArtefactType.Strategy)
        self.assertEqual(result.artefacts[2].confidence, 1.0)
        self.assertEqual(
            result.artefacts[0].attributes["description"],
            "Handle claims end to end",
        )
        self.assertEqual(result.artefacts[0].attributes["source"], "ba-objects.csv")

    def test_accepts_column_aliases_and_generates_ids(self):
        csv_text = (
            "artefact,artefact_type\n"
            "Customer Onboarding,Process\n"
            "Customer Onboarding,Process\n"
        )
        result = classification_from_csv(csv_text)

        self.assertEqual(result.artefacts[0].id, "customer-onboarding")
        self.assertEqual(result.artefacts[1].id, "customer-onboarding-2")
        self.assertEqual(result.artefacts[0].type, BusinessArtefactType.Process)

    def test_header_names_are_case_insensitive(self):
        csv_text = (
            "NAME,Artefact_Type,CONFIDENCE,Source_Sentence_IDs,Description\n"
            "Order Management,capability,0.8,s-1;s-2,Takes orders\n"
            "CRM,APPLICATION,,,\n"
        )
        result = classification_from_csv(csv_text)

        self.assertEqual(result.artefacts[0].type, BusinessArtefactType.Capability)
        self.assertEqual(result.artefacts[0].confidence, 0.8)
        self.assertEqual(result.artefacts[0].source_sentence_ids, ["s-1", "s-2"])
        self.assertEqual(result.artefacts[0].attributes["Description"], "Takes orders")
        self.assertEqual(result.artefacts[1].type, BusinessArtefactType.Application)

    def test_accepts_application_and_technology_types(self):
        result = classification_from_csv(
            "name,type\nClaimCenter,Application\nAzure,technology\n"
        )
        self.assertEqual(
            [a.type for a in result.artefacts],
            [BusinessArtefactType.Application, BusinessArtefactType.Technology],
        )

    def test_loads_sample_file_from_repo(self):
        sample = (
            Path(__file__).resolve().parents[1]
            / "test_files"
            / "sample_ba_objects.csv"
        )
        result = classification_from_csv(sample)
        self.assertGreaterEqual(len(result.artefacts), 1)
        self.assertTrue(
            all(artefact.type in BusinessArtefactType for artefact in result.artefacts)
        )

    def test_reads_from_file_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "objects.csv"
            path.write_text(SAMPLE_CSV, encoding="utf-8")
            result = classification_from_csv(path)
        self.assertEqual(len(result.artefacts), 3)
        self.assertEqual(result.artefacts[0].attributes["source"], "objects.csv")

    def test_rejects_missing_required_columns(self):
        with self.assertRaises(CsvArtefactError) as ctx:
            classification_from_csv("name,confidence\nClaims,1.0\n")
        self.assertIn("name", str(ctx.exception))
        self.assertIn("type", str(ctx.exception))

    def test_rejects_invalid_rows_with_locations(self):
        csv_text = "name,type,confidence\nClaims,Capability,1.5\n"
        with self.assertRaises(CsvArtefactError) as ctx:
            classification_from_csv(csv_text)
        self.assertIn("row 2", str(ctx.exception))
        self.assertIn("confidence", str(ctx.exception))


class StreamlitCsvPathWiringTests(unittest.TestCase):
    def test_streamlit_app_exposes_structured_csv_path(self):
        app_source = (
            Path(__file__).resolve().parents[1] / "streamlit_app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("Structured BA CSV", app_source)
        self.assertIn("classification_from_csv", app_source)
        self.assertIn("process_csv_upload", app_source)


if __name__ == "__main__":
    unittest.main()
