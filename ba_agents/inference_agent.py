from __future__ import annotations

from typing import List, Dict, Set

from langchain_core.prompts import ChatPromptTemplate

from llm.factory import create_chat_llm
from models.schemas import BusinessArtefact, InferenceResult
from config.ba_config import BusinessArtefactType, INFERENCE_RULES


# Template for individual inference rules in the prompt
INFERENCE_PROMPT_TEMPLATE = """
When you find a {source_type}, consider if there should be related {target_type}(s).
The relationship is '{relationship}', which means {description}.
"""

SYSTEM_PROMPT_BASE = """
You are a Business Architecture inference assistant. Based on existing artefacts,
infer closely related artefacts and relationships between them. Propose only 
high-confidence inferences that are typical within Business Architecture practice. 
Avoid duplicating existing artefacts.

Use concise names and generate unique kebab-case ids for any new artefacts.

The following inference rules will guide your suggestions:
{inference_rules}
""".strip()


HUMAN_PROMPT = """
Given the existing artefacts below, infer related artefacts and relationships.

Existing artefacts (id | type | name):
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
        # Group artefacts by type for easier processing
        artefacts_by_type: Dict[BusinessArtefactType, List[BusinessArtefact]] = {}
        for artefact in artefacts:
            if artefact.type not in artefacts_by_type:
                artefacts_by_type[artefact.type] = []
            artefacts_by_type[artefact.type].append(artefact)
        
        # Format the artefacts block
        artefacts_block = "\n".join(
            f"- {a.id} | {a.type.value} | {a.name}" for a in artefacts
        )
        
        # Run the inference chain
        chain = self.prompt | self.structured
        return chain.invoke({"artefacts_block": artefacts_block[:12000]})

