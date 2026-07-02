# Expert Rules Reference Tab Design

## Goal

Make the expert rules already stored in the RDF ontology visible at the end of document analysis in a form that is consistent with the application's existing tabular results.

## User Experience

Add a sixth top-level results tab named **Expert Rules** after **Relationship Graph**. The tab is a read-only reference and appears whenever analysis results are displayed.

The tab contains two sections:

1. **Classification Rules** — one row per classification rule, with columns for artefact type, condition, conclusion, examples, and counter-examples.
2. **Relationship Rules** — one row per inference rule, with columns for source type, relationship, target type, and description.

Examples and counter-examples are joined into readable text within their table cells. The view uses Streamlit dataframes with container-width sizing, matching the existing result tabs. If either rule set is empty, that section displays a concise informational message instead of an empty table.

## Architecture and Data Flow

The feature uses the existing `ARTEFACT_RULES` and `INFERENCE_RULES` values exported by `config.ba_config`. Those values are populated from `config/ba_ontology.ttl` at application startup, so the UI must not parse the RDF graph again or duplicate rule definitions.

Pure formatting helpers convert both rule collections into lists of display rows. Keeping formatting outside Streamlit rendering makes the behavior independently testable and keeps the tab implementation small.

## Error Handling

Missing or empty optional fields become empty display strings. An empty rule collection produces an informational empty state. Ontology loading failures remain governed by the existing configuration startup behavior and are outside this feature's scope.

## Testing

Unit tests will verify that:

- classification rules are flattened into readable rows, including joined examples and counter-examples;
- inference rules are mapped to source, relationship, target, and description columns;
- empty inputs produce empty row collections suitable for the UI empty state.

The focused tests and full existing test suite must pass before completion.

## Scope Boundaries

This feature does not edit rules, show raw RDF triples, add rule filtering, change analysis prompts, alter exports, or add rules to the relationship graph visualization.
