# Contextual Rule Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate temporary document-specific artefact discovery rules from ontology definitions and expert rules, then augment extraction and classification while preserving ontology-only fallback behavior.

**Architecture:** A focused context builder samples ordered document chunks; a new two-stage `RuleGenerationAgent` profiles the document and produces validated contextual rules. Pure ontology/rule formatters feed the prompts, while the existing extraction and classification agents accept optional generated guidance. Streamlit orchestrates the new pre-extraction stage and exposes its structured results.

**Tech Stack:** Python 3, Pydantic 2, LangChain structured output, RDFLib-backed ontology configuration, Streamlit, unittest/pytest.

---

### Task 1: Add structured profile and rule models

**Files:**
- Modify: `models/schemas.py`
- Create: `tests/test_contextual_rules.py`

- [ ] Write tests proving confidence bounds, relevance values, exact ontology artefact types, three-to-five directives, sequential numbering, and duplicate-directive rejection.
- [ ] Run `pytest tests/test_contextual_rules.py -v` and confirm schema imports or validation fail.
- [ ] Add `ArtefactRelevance`, `DocumentProfile`, `ContextualRule`, `ContextualRuleSet`, and `ContextualRuleGenerationResult` Pydantic models. Use validators to require one unique rule set per artefact type, three-to-five non-empty unique directives, and sequential numbering.
- [ ] Run `pytest tests/test_contextual_rules.py -v` and confirm the schema tests pass.

### Task 2: Build bounded document and ontology prompt context

**Files:**
- Create: `utils/rule_context.py`
- Modify: `config/ba_config.py`
- Modify: `tests/test_contextual_rules.py`

- [ ] Add failing tests for deterministic distributed chunk selection, document-order preservation, maximum-character enforcement, ontology definition lookup, and expert-rule serialization.
- [ ] Run the focused tests and confirm failures identify the missing helpers.
- [ ] Add `OntologyConfig.get_artefact_definitions()` returning ontology labels/comments keyed by `BusinessArtefactType`.
- [ ] Implement `build_representative_context(chunks, max_chars=24000)` using evenly distributed indices and bounded excerpts with source/page markers.
- [ ] Implement `format_ontology_context(definitions, rules, artefact_types=None)` so every entry includes the exact type, definition, conditions, conclusions, examples, and counterexamples.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Implement the two-stage rule-generation agent

**Files:**
- Create: `ba_agents/rule_generation_agent.py`
- Modify: `ba_agents/__init__.py`
- Modify: `tests/test_contextual_rules.py`

- [ ] Add failing tests using a fake LLM for profiler/generator prompt construction, prompt-injection boundaries, authoritative expert-rule precedence, relevant-type filtering, and malformed-output fallback.
- [ ] Run the focused tests and confirm failures.
- [ ] Implement the approved profiler and generator system prompts plus human templates carrying representative document content and ontology context.
- [ ] Implement `RuleGenerationAgent.run(chunks) -> ContextualRuleGenerationResult | None`: profile first, select non-irrelevant types, generate rules, reject unknown/irrelevant/malformed sets, log errors, and return `None` on failure.
- [ ] Expose pure `format_contextual_rules(result, artefact_types=None)` guidance formatting for downstream prompts.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Augment extraction and classification prompts

**Files:**
- Modify: `ba_agents/extraction_agent.py`
- Modify: `ba_agents/classification_agent.py`
- Modify: `tests/test_contextual_rules.py`

- [ ] Add failing tests proving extraction receives ontology definitions, expert rules, and generated rules; classification retains its current expert rules and appends only matching generated rules; and `None` preserves current behavior.
- [ ] Run the focused tests and confirm failures.
- [ ] Update `ExtractionAgent` to accept optional contextual rules, construct one bounded authoritative-plus-contextual guidance block, and include explicit precedence in the system prompt.
- [ ] Update `ClassificationAgent` to accept optional contextual rules and append only rules whose artefact types are allowed in each category prompt, after existing expert rules.
- [ ] Run the focused tests and confirm they pass.

### Task 5: Wire orchestration, visibility, export, and fallback

**Files:**
- Modify: `streamlit_app.py`
- Modify: `utils/expert_rules.py`
- Modify: `tests/test_contextual_rules.py`

- [ ] Add failing integration-source and formatter tests for pre-extraction rule generation, ontology-only fallback, result rendering, generated-rule formatting, session isolation, and JSON export.
- [ ] Run the focused tests and confirm failures.
- [ ] Initialize `rule_generation_result` session state and reset it at the start of every analysis.
- [ ] Run `RuleGenerationAgent` after loading chunks; pass its validated result into extraction and classification; catch/log failure and continue with `None`.
- [ ] Extend the Expert Rules tab with inferred profile and contextual-rule sections clearly labelled as temporary; preserve existing classification and relationship rule sections.
- [ ] Add document profile and contextual rules to JSON export when available.
- [ ] Run the focused tests and confirm they pass.

### Task 6: Verify the complete feature

**Files:**
- Verify all modified implementation and test files; do not commit tests or plan documents.

- [ ] Run `pytest tests/test_contextual_rules.py -v` and confirm all contextual-rule tests pass.
- [ ] Run `pytest -q` and confirm the full suite passes.
- [ ] Run `python -m compileall ba_agents config models utils streamlit_app.py` and confirm there are no syntax errors.
- [ ] Run `git diff --check` and confirm there are no whitespace errors.
- [ ] Review `git status --short` and distinguish new implementation/test changes from the user's pre-existing changes.
