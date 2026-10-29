# Centralized dotenv Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make LLM factory configuration consistently load values from the repository-root `.env` file.

**Architecture:** `llm/factory.py` will derive the repository root from its own file location and call `load_dotenv` before resolving configuration. The default non-overriding dotenv behavior preserves the precedence of exported environment variables and explicit function arguments.

**Tech Stack:** Python, python-dotenv, pytest

---

### Task 1: Load repository dotenv configuration in the LLM factory

**Files:**
- Create: `tests/test_llm_factory.py`
- Modify: `llm/factory.py`

- [ ] **Step 1: Write the failing tests**

Create tests that temporarily replace `llm.factory.load_dotenv`, reload the module, and assert that loading uses the repository-root `.env` path with `override=False` semantics. Also test with `monkeypatch` that an exported `LLM_PROVIDER` remains authoritative after loading dotenv.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_llm_factory.py -v`

Expected: FAIL because `llm.factory` does not load the repository-root `.env` file.

- [ ] **Step 3: Write the minimal implementation**

Add `Path` and `load_dotenv` imports to `llm/factory.py`, derive `.env` as `Path(__file__).resolve().parent.parent / ".env"`, and load it with `load_dotenv(dotenv_path=..., override=False)` before factory calls resolve environment variables.

- [ ] **Step 4: Run focused and full verification**

Run: `python -m pytest tests/test_llm_factory.py -v`

Expected: all focused tests PASS.

Run: `python -m pytest -v`

Expected: all repository tests PASS.

- [ ] **Step 5: Inspect the final diff**

Run: `git diff --check && git diff -- llm/factory.py tests/test_llm_factory.py`

Expected: no whitespace errors and only the intended dotenv-loading changes.
