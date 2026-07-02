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
