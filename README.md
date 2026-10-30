## doc2ba: Multi‑Agent Business Architecture Miner (LangChain)

This small research project demonstrates a simple, provider‑agnostic multi‑agent pipeline using LangChain to:

1. Extract Business Architecture‑related sentences from unstructured documents (e.g., PDFs).
2. Categorize extracted sentences into high-level categories (Desired Results, Course of Action, Governance, Enablers) based on CAPSICUM business architecture ontology.
3. Classify categorized content into artefact types (e.g., Capability, Goal, Strategy).
4. Infer related artefacts and relationships (e.g., Capability → ValueStream) based on a simplified subset of CAPSICUM ontology.

### Quickstart

1) Create and populate your environment file:

```bash
cp env.example .env
# fill in API keys and provider
```

2) Install dependencies (Python 3.10+ recommended):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

3) Run the pipeline using either the CLI or the Streamlit UI:

#### Using the Launcher Script

The easiest way to get started is to use the launcher script:

```bash
python run.py
```

This will present a menu where you can choose between the web UI or CLI mode.

Or launch directly into a specific mode:

```bash
# Launch the web UI
python run.py ui

# Use the CLI with options
python run.py cli --input ./test_files --provider openai --model gpt-4o-mini
```

#### Command Line Interface

You can also use the CLI directly:

```bash
python cli.py --input ./test_files --provider openai --model gpt-4o-mini
```

Use `--provider anthropic` (e.g., `--model claude-3-5-sonnet-latest`) or `--provider azure` (set `AZURE_OPENAI_*` vars) to switch vendors.

You can also save the output to a JSON file for further processing:

```bash
python cli.py --input ./test_files --provider openai --model gpt-4o --output results.json
```

If you already have structured business architecture objects, skip extraction and
classification and continue from ontology inference:

```bash
python cli.py from-csv --input ./test_files/sample_ba_objects.csv --provider openai --model gpt-4o-mini
python run.py from-csv --input ./test_files/sample_ba_objects.csv --provider openai --model gpt-4o-mini
```

CSV files must include `name` and `type` (column names are case-insensitive). Optional columns: `id`, `confidence`,
`source_sentence_ids`, `attributes` (JSON object text). Extra columns are stored
as artefact attributes. `type` must match an ontology artefact type (for example
Capability, Goal, Strategy, Process, Application, Technology). A sample file is at
`test_files/sample_ba_objects.csv`.

#### Streamlit Web UI

For a more interactive experience, you can directly launch the Streamlit web interface:

```bash
streamlit run streamlit_app.py
```

This will launch a browser with a user-friendly interface where you can:
- Upload document files (PDFs, TXT, MD) directly through the browser
- Or upload a CSV of already structured BA objects (skips extraction/classification)
- Select your preferred LLM provider and model
- Run the complete pipeline with visual progress indicators
- View interactive visualizations of the results
- Download the output as a JSON file

### Implementation Overview

This project leverages LangChain to create a modular, provider-agnostic pipeline for Business Architecture mining:

- **LangChain Integration**: Uses LangChain's chat model abstractions, document loaders, and output parsing
  - `ChatPromptTemplate` for structured, reusable prompts
  - `with_structured_output` for type-safe schema enforcement
  - Document loaders for PDF/text processing with automatic fallbacks

- **Agent Design Pattern**: Each agent focuses on a single responsibility with:
  - Specific system/human prompts tailored to the task
  - Pydantic models for input/output validation
  - Provider-agnostic LLM factory for interchangeable backends

- **Multi-Provider Support**: Abstract factory pattern in `llm/factory.py` supports:
  - OpenAI models (default: gpt-4o-mini, supports GPT-5 and newer models)
  - Anthropic Claude models
  - Azure OpenAI deployments
  - Structured output with strict JSON schema mode for GPT-5+ compatibility

- **Efficient Processing**: Progressive specialization with each step refining outputs from previous stages, maintaining linkage between stages via IDs.

### Structure

```
ba_agents/
  extraction_agent.py
  categorization_agent.py
  classification_agent.py
  inference_agent.py
config/
  ba_config.py           # Configuration from RDF/OWL ontology
  ba_ontology.ttl        # Business architecture ontology in Turtle format
llm/
  factory.py
models/
  schemas.py
utils/
  loaders.py
cli.py                  # Command-line interface
streamlit_app.py        # Web-based UI interface
run.py                  # Unified launcher script
test_files/
  bupa/
    bupa-group-2024-annual-report-and-accounts.pdf
```

### Pipeline Steps

Each step in the pipeline has specific inputs and outputs:

1. **Extraction Agent**
   - **Input**: Document chunks from PDFs/text files
     ```python
     {
       "source": str,  # Document name/identifier
       "page": int,    # Page number
       "text": str     # Raw text content from the document
     }
     ```
   - **Output**: List of `ExtractedSentence` objects
     ```python
     {
       "id": str,           # Unique ID for sentence (UUID)
       "text": str,         # The extracted sentence text
       "source": str,       # Document it came from
       "page": int,         # Page number
       "confidence": float  # 0.0-1.0 confidence score
     }
     ```
   - **Implementation**: Uses multi-strategy PDF loading (UnstructuredPDFLoader, PDFMinerLoader, PyPDFLoader) with fallback mechanisms for optimal text extraction. Handles garbled text with automatic detection and cleaning. Limits each chunk to 8000 characters for LLM processing efficiency.

2. **Categorization Agent**
   - **Input**: `ExtractedSentence` objects (structure above)
   - **Output**: List of `CategorizedSentence` objects
     ```python
     {
       "id": str,                  # Same ID from extraction phase
       "text": str,                # The extracted sentence text
       "source": str,              # Document it came from
       "page": int,                # Page number
       "confidence": float,        # Original extraction confidence
       "category": str,            # "Desired Results", "Course of Action", "Governance", or "Unknown"
       "category_confidence": float # 0.0-1.0 confidence in categorization
     }
     ```
   - **Implementation**: Categorizes sentences into high-level categories with confidence scores using LangChain structured output schema. Handles "Unknown" category for ambiguous content.

3. **Classification Agent**
   - **Input**: `CategorizedSentence` objects (structure above)
   - **Output**: List of `BusinessArtefact` objects
     ```python
     {
       "id": str,              # Kebab-case ID generated from name
       "name": str,            # Concise name of the artefact
       "type": str,            # One of: Capability, Goal, Strategy, ValueStream, Process, etc.
       "source_sentence_ids": [str],  # IDs of sentences supporting this artefact
       "confidence": float,    # 0.0-1.0 confidence in classification
       "attributes": {         # Optional key/value attributes
         "key": "value"
       }
     }
     ```
   - **Implementation**: Uses category-specific type mapping to constrain classification options (e.g., "Desired Results" maps to Capability/Goal/Outcome/Measure types). Generates stable kebab-case IDs for artefacts and maintains links to source sentences.

4. **Inference Agent**
   - **Input**: List of `BusinessArtefact` objects (structure above)
   - **Output**: 
     - New `BusinessArtefact` objects (same structure as above)
     - List of `Relationship` objects:
       ```python
       {
         "source_id": str,    # ID of source artefact
         "target_id": str,    # ID of target artefact
         "type": str,         # Relationship type (e.g., "supports", "realizes", "flowsThrough")
         "confidence": float  # 0.0-1.0 confidence in relationship
       }
       ```
   - **Implementation**: Infers implicit relationships between artefacts (e.g., "supports", "realizes", "flowsThrough") and potentially missing artefacts based on identified relationships. Maintains consistent naming and ID generation patterns.

### Notes

- The LLM factory (`llm/factory.py`) centralizes vendor/model selection for OpenAI, Anthropic, and Azure.
- The 4-stage pipeline (extract → categorize → classify → infer) improves accuracy through progressive specialization. A structured CSV path loads artefacts directly into classification and continues with inference.
- Agents use Pydantic‑typed structured outputs for reproducibility and type safety.
- Keep prompts small and targeted to encourage consistent JSON.
- The included test files provide examples for experimenting with the pipeline.

### GPT-5 and Modern Model Support

This codebase is compatible with GPT-5 and newer OpenAI models. Key improvements:

- **Pydantic v2**: Uses native Pydantic v2 models for better compatibility with latest LangChain versions
- **Strict JSON Schema Mode**: All agents use `strict=True` with `method="json_schema"` for structured outputs
- **Updated Dependencies**: LangChain 0.3+ and langchain-openai 0.2+ for the latest API features

To use GPT-5:

```bash
# Via CLI
python cli.py run --input ./test_files --provider openai --model gpt-5

# Via environment variable
export DEFAULT_MODEL=gpt-5
python cli.py run --input ./test_files
```

The structured output implementation automatically handles the strict schema requirements for GPT-5's enhanced JSON mode.

### Ontology-Based Configuration

The business architecture configuration is defined using an RDF/OWL ontology stored in Turtle format:

- **Configuration File**: `config/ba_config.py` loads the ontology and provides a programmatic interface
- **Ontology File**: `config/ba_ontology.ttl` contains the RDF triples defining the ontology
- **Key Concepts**:
  - **Categories**: High-level groupings (Desired Results, Course of Action, Governance, Enablers)
  - **Business Artefacts**: Specific types like Capability, Goal, Strategy (as subclasses of categories)
  - **Relationships**: How different artefacts relate to each other
  - **Classification Rules**: Rules for identifying specific artefact types

To use the configuration:

```python
from config.ba_config import (
    CategoryType, 
    BusinessArtefactType, 
    CATEGORY_MAPPINGS, 
    INFERENCE_RULES,
    ARTEFACT_RULES
)
```

The ontology approach enables powerful semantic queries, inference capabilities, and easier extensibility.

### License

MIT (research/demo only).

