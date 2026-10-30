import unittest

from config.ba_config import BusinessArtefactType, INFERENCE_RULES
from ba_agents.inference_agent import (
    MAX_BLOCK_CHARS,
    _artefact_line,
    _batch_lines,
    _drop_invalid,
    _merge_results,
)
from models.schemas import BusinessArtefact, InferenceResult, Relationship


def _artefact(id, type=BusinessArtefactType.Capability, attributes=None):
    return BusinessArtefact(
        id=id, name=id.title(), type=type, confidence=1.0, attributes=attributes
    )


class OntologyEnablerTests(unittest.TestCase):
    def test_capability_is_delivered_by_application_and_supported_by_technology(self):
        rules = {(s, t, r) for s, t, r, _ in INFERENCE_RULES}
        self.assertIn(
            (
                BusinessArtefactType.Capability,
                BusinessArtefactType.Application,
                "deliveredBy",
            ),
            rules,
        )
        self.assertIn(
            (
                BusinessArtefactType.Capability,
                BusinessArtefactType.Technology,
                "supportedBy",
            ),
            rules,
        )


class InferenceHelperTests(unittest.TestCase):
    def test_artefact_line_includes_description_case_insensitively(self):
        line = _artefact_line(_artefact("claims", attributes={"Description": "Handle claims"}))
        self.assertEqual(line, "- claims | Capability | Claims | Handle claims")

    def test_artefact_line_includes_alias(self):
        line = _artefact_line(_artefact("ise", attributes={"alias": "Cisco ISE"}))
        self.assertEqual(line, "- ise | Capability | Ise | alias: Cisco ISE")

    def test_batches_instead_of_truncating(self):
        lines = [f"- artefact-{i} | Capability | {'x' * 500}" for i in range(200)]
        batches = _batch_lines(lines)
        self.assertGreater(len(batches), 1)
        self.assertTrue(all(len(b) <= MAX_BLOCK_CHARS for b in batches))
        self.assertEqual("\n".join(batches).split("\n"), lines)

    def test_merge_dedupes_artefacts_and_relationships(self):
        rel = Relationship(source_id="a", target_id="b", type="realizes", confidence=0.9)
        merged = _merge_results(
            [
                InferenceResult(new_artefacts=[_artefact("b")], relationships=[rel]),
                InferenceResult(new_artefacts=[_artefact("b")], relationships=[rel]),
            ]
        )
        self.assertEqual(len(merged.new_artefacts), 1)
        self.assertEqual(len(merged.relationships), 1)

    def test_drop_invalid_removes_duplicates_and_dangling_relationships(self):
        existing = [_artefact("a"), _artefact("c", BusinessArtefactType.Process)]
        result = InferenceResult(
            new_artefacts=[_artefact("a"), _artefact("b", BusinessArtefactType.ValueStream)],
            relationships=[
                Relationship(source_id="a", target_id="b", type="realizes", confidence=0.9),
                Relationship(source_id="a", target_id="c", type="enactedBy", confidence=0.9),
                Relationship(source_id="a", target_id="zzz", type="realizes", confidence=0.9),
            ],
        )
        cleaned = _drop_invalid(result, existing)
        self.assertEqual([a.id for a in cleaned.new_artefacts], ["b"])
        self.assertEqual(
            [(r.source_id, r.target_id) for r in cleaned.relationships],
            [("a", "b"), ("a", "c")],
        )


if __name__ == "__main__":
    unittest.main()
