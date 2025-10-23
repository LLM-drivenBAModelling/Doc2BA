from __future__ import annotations

import logging
from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate

from llm.factory import create_chat_llm
from models.schemas import ClassificationResult
from config.ba_config import CategoryType, CATEGORY_MAPPINGS, BusinessArtefactType, ARTEFACT_RULES


logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """
You are a Business Architecture classifier. From provided sentences, propose
concise artefacts with types from the allowed set. Prefer fewer, higher
confidence artefacts. Use names that are short but specific.

The sentences have been categorized as "{category}" which means they relate to {category_description}.
You should ONLY classify them as one of these allowed types: {allowed_types}

For each artefact, include a confidence 0-1 and the list of supporting sentence ids.
For the id, generate a short kebab-case slug from the name, unique within the set.

Use these ripple-down rules to help differentiate between artefact types:
{rules_text}
""".strip()


HUMAN_PROMPT = """
Classify artefacts from the following extracted sentences.

Sentences (id -> text):
{sentences_block}
""".strip()

class ClassificationAgent:
    def __init__(self, provider: str | None = None, model: str | None = None, temperature: float = 0.0):
        self.llm = create_chat_llm(provider=provider, model=model, temperature=temperature)
        # Use strict mode for better compatibility with GPT-5 and newer models
        self.structured = self.llm.with_structured_output(ClassificationResult, method="json_schema", strict=True)
        
        # Create a system prompt for each category using the mappings
        category_prompts = {}
        for category, mapping in CATEGORY_MAPPINGS.items():
            # Convert the list of BusinessArtefactType to a comma-separated string of their values
            allowed_types_str = ", ".join(artefact_type.value for artefact_type in mapping["allowed_types"])
            
            # Generate the ripple down rules text for the allowed artefact types
            rules_text = self._generate_rules_text(mapping["allowed_types"])
            
            category_prompts[category] = SYSTEM_PROMPT_TEMPLATE.format(
                category=category.value,
                category_description=mapping["description"],
                allowed_types=allowed_types_str,
                rules_text=rules_text
            )
            
        self.category_prompts = category_prompts
        
        # Default to using the human prompt, system prompt will be selected based on category
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", ""),  # Placeholder, will be replaced at runtime
            ("human", HUMAN_PROMPT),
        ])
        
    def _generate_rules_text(self, allowed_types: List[BusinessArtefactType]) -> str:
        """Generate formatted text of ripple down rules for the allowed artefact types."""
        rules_text_parts = []
        
        for artefact_type in allowed_types:
            rules = ARTEFACT_RULES.get(artefact_type, [])
            if not rules:
                continue
                
            type_rules = [
                f"For {artefact_type.value}:"
            ]
            
            for i, rule in enumerate(rules, 1):
                rule_text = f"  Rule {i}: IF {rule['condition']}, THEN {rule['conclusion']}."
                type_rules.append(rule_text)
                
                if rule['examples']:
                    examples_text = "    Examples: " + "; ".join(f'"{ex}"' for ex in rule['examples'])
                    type_rules.append(examples_text)
                    
                if rule['counter_examples']:
                    counter_examples_text = "    Counter-examples: " + "; ".join(f'"{ex}"' for ex in rule['counter_examples'])
                    type_rules.append(counter_examples_text)
                    
            rules_text_parts.append("\n".join(type_rules))
            
        return "\n\n".join(rules_text_parts)

    def run(self, sentence_details: Dict[str, Dict]) -> ClassificationResult:
        # Get the Unknown category
        unknown_category = next((c for c in CategoryType if c.value == "Unknown"), None)
        
        # Group sentences by category
        category_to_sentences = {}
        for sid, details in sentence_details.items():
            category = details.get('category', unknown_category)
            if category not in category_to_sentences:
                category_to_sentences[category] = []
            category_to_sentences[category].append((sid, details['text']))
        
        # Process each category with the appropriate prompt
        all_artefacts = []
        for category, sentences in category_to_sentences.items():
            if not sentences:
                continue
                
            # Format the sentences block for this category
            sentences_block = "\n".join(f"- {sid}: {text}" for sid, text in sentences)
            
            # Select the right system prompt for this category
            if category in self.category_prompts:
                system_prompt = self.category_prompts[category]
            elif unknown_category and unknown_category in self.category_prompts:
                system_prompt = self.category_prompts[unknown_category]
            else:
                # Create a generic system prompt as fallback
                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                    category="Unknown",
                    category_description="business architecture elements that don't clearly fit other categories",
                    allowed_types=", ".join([t.value for t in BusinessArtefactType]),
                    rules_text="Use your best judgment to classify these items."
                )
            
            # Create a new prompt with the category-specific system prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", HUMAN_PROMPT),
            ])
            
            # Run the chain
            chain = prompt | self.structured
            result = chain.invoke({"sentences_block": sentences_block[:12000]})
            
            # Add artefacts to the combined list
            all_artefacts.extend(result.artefacts)
        
        # Return combined results
        return ClassificationResult(artefacts=all_artefacts)

