# Expert Rules Reference Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an easy-to-read Expert Rules results tab that displays classification and relationship rules loaded from the RDF ontology.

**Architecture:** Add pure row-formatting helpers in a focused utility module, then render their output in a sixth Streamlit results tab. The UI consumes the existing `ARTEFACT_RULES` and `INFERENCE_RULES` exports, avoiding duplicate ontology parsing or rule definitions.

**Tech Stack:** Python 3.10+, Streamlit, RDFLib-backed configuration, `unittest`

---

## File Structure

- Create `utils/expert_rules.py`: pure transformations from ontology rule collections to Streamlit-ready row dictionaries.
- Create `tests/test_expert_rules.py`: unit coverage for classification rows, inference rows, and empty inputs.
- Modify `streamlit_app.py`: import the ontology rule exports and formatting helpers, add the sixth tab, and render both rule tables with empty states.

### Task 1: Format ontology rules for display

**Files:**
- Create: `utils/expert_rules.py`
- Test: `tests/test_expert_rules.py`

- [ ] **Step 1: Write the failing classification-rule tests**

```python
import unittest

from config.ba_config import BusinessArtefactType
from utils.expert_rules import format_classification_rules


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
```

- [ ] **Step 2: Run the classification tests to verify they fail**

Run: `python -m unittest tests.test_expert_rules.ClassificationRuleFormattingTests -v`

Expected: ERROR with `ModuleNotFoundError: No module named 'utils.expert_rules'`.

- [ ] **Step 3: Implement the classification formatter**

Create `utils/expert_rules.py`:

```python
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


def _join_values(values: Iterable[Any]) -> str:
    return "; ".join(str(value) for value in values)


def format_classification_rules(
    rules: Mapping[Any, Sequence[Mapping[str, Any]]],
) -> List[Dict[str, str]]:
    rows = []
    for artefact_type, type_rules in rules.items():
        for rule in type_rules:
            rows.append(
                {
                    "Artefact Type": str(artefact_type.value),
                    "Condition": str(rule.get("condition", "")),
                    "Conclusion": str(rule.get("conclusion", "")),
                    "Examples": _join_values(rule.get("examples", [])),
                    "Counter-examples": _join_values(
                        rule.get("counter_examples", [])
                    ),
                }
            )
    return rows
```

- [ ] **Step 4: Run the classification tests to verify they pass**

Run: `python -m unittest tests.test_expert_rules.ClassificationRuleFormattingTests -v`

Expected: 2 tests pass.

- [ ] **Step 5: Write the failing relationship-rule tests**

Append to `tests/test_expert_rules.py` and add `format_inference_rules` to its import:

```python
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
```

- [ ] **Step 6: Run the relationship tests to verify they fail**

Run: `python -m unittest tests.test_expert_rules.InferenceRuleFormattingTests -v`

Expected: ERROR because `format_inference_rules` is not defined in `utils.expert_rules`.

- [ ] **Step 7: Implement the relationship formatter**

Append to `utils/expert_rules.py`:

```python
def format_inference_rules(
    rules: Sequence[Tuple[Any, Any, str, str]],
) -> List[Dict[str, str]]:
    return [
        {
            "Source Type": str(source_type.value),
            "Relationship": str(relationship),
            "Target Type": str(target_type.value),
            "Description": str(description),
        }
        for source_type, target_type, relationship, description in rules
    ]
```

- [ ] **Step 8: Run all formatter tests**

Run: `python -m unittest tests.test_expert_rules -v`

Expected: 4 tests pass.

- [ ] **Step 9: Commit the formatter and tests**

```bash
git add utils/expert_rules.py tests/test_expert_rules.py
git commit -m "Add expert rule display formatters"
```

### Task 2: Render the Expert Rules Streamlit tab

**Files:**
- Modify: `streamlit_app.py:20-28`
- Modify: `streamlit_app.py:271-279`
- Modify: `streamlit_app.py:426-454`

- [ ] **Step 1: Add a failing source-level integration test**

Append to `tests/test_expert_rules.py`:

```python
from pathlib import Path


class ExpertRulesTabIntegrationTests(unittest.TestCase):
    def test_streamlit_app_wires_expert_rules_into_results_tabs(self):
        app_source = (
            Path(__file__).resolve().parents[1] / "streamlit_app.py"
        ).read_text(encoding="utf-8")

        self.assertIn('"Expert Rules"', app_source)
        self.assertIn("format_classification_rules(ARTEFACT_RULES)", app_source)
        self.assertIn("format_inference_rules(INFERENCE_RULES)", app_source)
```

- [ ] **Step 2: Run the integration test to verify it fails**

Run: `python -m unittest tests.test_expert_rules.ExpertRulesTabIntegrationTests -v`

Expected: FAIL because `streamlit_app.py` does not yet contain the Expert Rules tab wiring.

- [ ] **Step 3: Import the rule data and formatters**

Replace the existing configuration import in `streamlit_app.py` with:

```python
from config.ba_config import (
    ARTEFACT_RULES,
    INFERENCE_RULES,
    BusinessArtefactType,
)
from utils.expert_rules import (
    format_classification_rules,
    format_inference_rules,
)
```

- [ ] **Step 4: Add the sixth results tab**

Replace the results tab declaration with:

```python
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        f"Extraction ({len(st.session_state.extraction_result.sentences)})",
        f"Categorization ({len(st.session_state.categorization_result.sentences)})",
        f"Classification ({len(st.session_state.classification_result.artefacts)})",
        "Inference",
        "Relationship Graph",
        "Expert Rules",
    ])
```

- [ ] **Step 5: Render both reference tables**

Insert after the Relationship Graph tab and before Export Results:

```python
    # Tab 6: Expert Rules
    with tab6:
        st.subheader("Classification Rules")
        st.caption(
            "Rules used to distinguish each business architecture artefact type."
        )
        classification_rule_rows = format_classification_rules(ARTEFACT_RULES)
        if classification_rule_rows:
            st.dataframe(classification_rule_rows, use_container_width=True)
        else:
            st.info("No classification rules are available in the ontology.")

        st.subheader("Relationship Rules")
        st.caption(
            "Rules describing which artefact types can be related during inference."
        )
        inference_rule_rows = format_inference_rules(INFERENCE_RULES)
        if inference_rule_rows:
            st.dataframe(inference_rule_rows, use_container_width=True)
        else:
            st.info("No relationship rules are available in the ontology.")
```

- [ ] **Step 6: Run the focused tests**

Run: `python -m unittest tests.test_expert_rules -v`

Expected: 5 tests pass.

- [ ] **Step 7: Run syntax validation and the full test suite**

Run: `python -m py_compile streamlit_app.py utils/expert_rules.py`

Expected: command exits successfully with no output.

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 8: Review the final diff for scope and whitespace errors**

Run: `git diff --check && git diff -- streamlit_app.py utils/expert_rules.py tests/test_expert_rules.py`

Expected: no whitespace errors; the diff contains only the formatting helpers, tests, imports, sixth tab declaration, and Expert Rules rendering block.

- [ ] **Step 9: Commit the Streamlit tab**

```bash
git add streamlit_app.py tests/test_expert_rules.py
git commit -m "Show ontology expert rules in analysis results"
```
