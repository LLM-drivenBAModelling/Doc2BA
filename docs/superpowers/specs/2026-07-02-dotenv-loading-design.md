# Centralized dotenv Loading

## Problem

`llm/factory.py` reads configuration with `os.getenv`, but `.env` is loaded only by selected entry points. Importing or invoking the LLM factory from another entry point therefore misses values stored in the repository's `.env` file.

## Design

The LLM factory will load the repository-root `.env` file before resolving provider configuration. The path will be derived from `llm/factory.py`, avoiding dependence on the process working directory. `python-dotenv` will retain its default `override=False` behavior so explicitly exported environment variables continue to take precedence over `.env` values.

Provider and model selection will continue to use `os.getenv` after dotenv populates `os.environ`; this is the intended integration model for `python-dotenv`. Existing explicit function arguments remain the highest-precedence configuration source.

## Alternatives Considered

1. Load `.env` in every application entry point. This is the current pattern and is fragile when new entry points are added.
2. Load `.env` centrally in `llm/factory.py` using an explicit repository-root path. This is selected because all LLM creation flows pass through the factory and behavior does not depend on the current directory.
3. Parse `.env` with `dotenv_values` and avoid `os.getenv`. This would require manually merging `.env` values with exported environment variables and duplicating configuration precedence logic.

## Verification

A focused test will create an isolated `.env`, clear the relevant process variables, and verify that factory configuration is populated from the file. It will also verify that an already-exported value is not overwritten.
