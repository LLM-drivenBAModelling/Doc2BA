from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from config.ba_config import BusinessArtefactType
from models.schemas import ContextualRuleGenerationResult
from utils.loaders import DocumentChunk


def _distributed_indices(length: int, count: int) -> list[int]:
    if count >= length:
        return list(range(length))
    return sorted(
        {round(position * (length - 1) / (count - 1)) for position in range(count)}
    )


def build_representative_context(
    chunks: Iterable[DocumentChunk], max_chars: int = 24000
) -> str:
    ordered = list(chunks)
    if not ordered or max_chars <= 0:
        return ""

    selected = [ordered[index] for index in _distributed_indices(len(ordered), min(4, len(ordered)))]
    headers = [f"[source: {chunk.source}, page: {chunk.page}]\n" for chunk in selected]
    separators_size = max(0, len(selected) - 1) * 2
    text_budget = max_chars - sum(map(len, headers)) - separators_size
    if text_budget < 0:
        return "\n\n".join(headers)[:max_chars]

    per_chunk = text_budget // len(selected)
    remainder = text_budget % len(selected)
    sections = []
    for index, (header, chunk) in enumerate(zip(headers, selected)):
        allowance = per_chunk + (1 if index < remainder else 0)
        sections.append(header + chunk.text.strip()[:allowance])
    return "\n\n".join(sections)[:max_chars]


def format_ontology_context(
    definitions: Mapping[Any, str],
    rules: Mapping[Any, Sequence[Mapping[str, Any]]],
    artefact_types: Sequence[BusinessArtefactType] | None = None,
) -> str:
    selected = list(artefact_types or BusinessArtefactType)
    sections = []
    for artefact_type in selected:
        lines = [
            f"Artefact Type: {artefact_type.value}",
            f"Definition: {definitions.get(artefact_type, '')}",
            "Authoritative Expert Rules:",
        ]
        for index, rule in enumerate(rules.get(artefact_type, []), start=1):
            lines.append(
                f"{index}. IF {rule.get('condition', '')}, THEN {rule.get('conclusion', '')}."
            )
            examples = rule.get("examples", [])
            if examples:
                lines.append("   Examples: " + "; ".join(map(str, examples)))
            counter_examples = rule.get("counter_examples", [])
            if counter_examples:
                lines.append(
                    "   Counter-examples: " + "; ".join(map(str, counter_examples))
                )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def format_contextual_rules(
    result: ContextualRuleGenerationResult | None,
    artefact_types: Sequence[BusinessArtefactType] | None = None,
) -> str:
    if result is None:
        return ""
    allowed = set(artefact_types) if artefact_types is not None else None
    sections = []
    for rule_set in result.rule_sets:
        if allowed is not None and rule_set.artefact_type not in allowed:
            continue
        lines = [f"For {rule_set.artefact_type.value}:"]
        lines.extend(
            f"  {rule.number}. {rule.directive}" for rule in rule_set.rules
        )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)
