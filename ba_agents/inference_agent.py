from __future__ import annotations

from typing import List, Dict

from langchain_core.prompts import ChatPromptTemplate

from llm.factory import create_chat_llm
from models.schemas import BusinessArtefact, InferenceResult
from config.ba_config import BusinessArtefactType, INFERENCE_RULES


# Template for individual inference rules in the prompt
INFERENCE_PROMPT_TEMPLATE = """
When you find a {source_type}, consider if there should be related {target_type}(s).
Likewise, when you find a {target_type}, consider which {source_type}(s) it relates to,
proposing a new {source_type} if none of the existing artefacts fits.
The relationship is '{relationship}' (from {source_type} to {target_type}), which means {description}.
"""

SYSTEM_PROMPT_BASE = """
You are a Business Architecture inference assistant. Based on existing artefacts,
infer closely related artefacts and relationships between them. Propose only 
high-confidence inferences that are typical within Business Architecture practice. 
Avoid duplicating existing artefacts.

Use concise names and generate unique kebab-case ids for any new artefacts.

Relationships may connect two existing artefacts, an existing artefact to a new
one, or two new artefacts. Whenever two existing artefacts already satisfy an
inference rule, propose that relationship rather than a duplicate artefact. Refer
to existing artefacts by their exact ids.

Rules apply in both directions: if the existing artefacts contain only the target
side of a rule (for example only Applications), infer the source side that they
belong to (for example the Capabilities they deliver) and link them. Always
propose at least the high-confidence artefacts and relationships that the rules
support; return nothing only if no rule applies to the existing artefact types.

The following inference rules will guide your suggestions:
{inference_rules}
""".strip()


HUMAN_PROMPT = """
Given the existing artefacts below, infer related artefacts and relationships.

Existing artefacts (id | type | name | description or alias when known):
{artefacts_block}
""".strip()


class InferenceAgent:
    def __init__(self, provider: str | None = None, model: str | None = None, temperature: float = 0.0):
        self.llm = create_chat_llm(provider=provider, model=model, temperature=temperature)
        # Use strict mode for better compatibility with GPT-5 and newer models
        self.structured = self.llm.with_structured_output(InferenceResult, method="json_schema", strict=True)
        
        # Generate the dynamic inference rules from the config
        inference_rules_text = self._generate_inference_rules_text()
        
        # Create the complete system prompt with the dynamic rules
        system_prompt = SYSTEM_PROMPT_BASE.format(inference_rules=inference_rules_text)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", HUMAN_PROMPT),
        ])
    
    def _generate_inference_rules_text(self) -> str:
        """Generate text describing inference rules from the config."""
        rules_text = []
        
        for source_type, target_type, relationship, description in INFERENCE_RULES:
            rule_text = INFERENCE_PROMPT_TEMPLATE.format(
                source_type=source_type.value,
                target_type=target_type.value,
                relationship=relationship,
                description=description
            )
            rules_text.append(rule_text)
        
        return "\n".join(rules_text)

    def run(self, artefacts: List[BusinessArtefact]) -> InferenceResult:
        if not artefacts:
            return InferenceResult()

        chain = self.prompt | self.structured
        batches = _batch_lines([_artefact_line(a) for a in artefacts])
        if len(batches) == 1:
            result = chain.invoke({"artefacts_block": batches[0]})
        else:
            result = _merge_results(
                [chain.invoke({"artefacts_block": batch}) for batch in batches]
            )
        return _drop_invalid(result, artefacts)


MAX_BLOCK_CHARS = 30000
MAX_DESCRIPTION_CHARS = 200


def _artefact_line(artefact: BusinessArtefact) -> str:
    line = f"- {artefact.id} | {artefact.type.value} | {artefact.name}"
    attributes = {k.casefold(): v for k, v in (artefact.attributes or {}).items()}
    details = [
        f"{label}: {attributes[label][:MAX_DESCRIPTION_CHARS]}" if label != "description"
        else attributes[label][:MAX_DESCRIPTION_CHARS]
        for label in ("description", "alias")
        if attributes.get(label)
    ]
    return " | ".join([line, *details])


def _batch_lines(lines: List[str]) -> List[str]:
    """Split artefact lines into prompt blocks instead of silently truncating."""
    batches: List[List[str]] = [[]]
    size = 0
    for line in lines:
        if batches[-1] and size + len(line) + 1 > MAX_BLOCK_CHARS:
            batches.append([])
            size = 0
        batches[-1].append(line)
        size += len(line) + 1
    return ["\n".join(batch) for batch in batches]


def _merge_results(results: List[InferenceResult]) -> InferenceResult:
    artefacts: Dict[str, BusinessArtefact] = {}
    relationships: Dict[tuple, object] = {}
    for result in results:
        for artefact in result.new_artefacts:
            artefacts.setdefault(artefact.id, artefact)
        for rel in result.relationships:
            relationships.setdefault((rel.source_id, rel.type, rel.target_id), rel)
    return InferenceResult(
        new_artefacts=list(artefacts.values()),
        relationships=list(relationships.values()),
    )


def _drop_invalid(
    result: InferenceResult, existing: List[BusinessArtefact]
) -> InferenceResult:
    """Drop new artefacts that reuse an existing id and dangling relationships."""
    existing_ids = {a.id for a in existing}
    new_artefacts = [a for a in result.new_artefacts if a.id not in existing_ids]
    known_ids = existing_ids | {a.id for a in new_artefacts}
    relationships = [
        r
        for r in result.relationships
        if r.source_id in known_ids and r.target_id in known_ids
    ]
    return InferenceResult(new_artefacts=new_artefacts, relationships=relationships)
