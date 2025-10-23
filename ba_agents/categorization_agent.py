from __future__ import annotations

import logging
from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate

from llm.factory import create_chat_llm
from models.schemas import CategorizationResult
from config.ba_config import CategoryType, CATEGORY_MAPPINGS


logger = logging.getLogger(__name__)


# Define a template for the system prompt
SYSTEM_PROMPT_TEMPLATE = """
You are an expert Business Architecture categorizer. Your task is to categorize business architecture sentences into one of these high-level categories:

{category_descriptions}

For each sentence, determine the most appropriate category and provide a confidence score (0.0-1.0).
If a sentence doesn't clearly fit any category, classify it as "Unknown" with appropriate confidence.
""".strip()

# Generate the category descriptions dynamically from the config
def generate_category_descriptions() -> str:
    descriptions = []
    
    # Skip Unknown as it's the fallback category during presentation (but still use it for classification)
    unknown_category = next((c for c in CategoryType if c.value == "Unknown"), None)
    primary_categories = [c for c in CategoryType if c != unknown_category]
    for i, category in enumerate(primary_categories, 1):
        mapping = CATEGORY_MAPPINGS[category]
        allowed_types_str = ", ".join(t.value for t in mapping["allowed_types"])
        
        # Get examples directly from the config
        examples = mapping.get("examples", [])
        
        # Format the description
        description = f"{i}. {category.value}: {mapping['description']} ({allowed_types_str})."
        if examples:
            examples_str = '", "'.join(examples[:2])  # Take at most 2 examples for readability
            description += f'\n   - Examples: "{examples_str}"'
        
        descriptions.append(description)
    
    # Add note about Unknown category
    if unknown_category:
        unknown_desc = CATEGORY_MAPPINGS[unknown_category]["description"]
        descriptions.append(f"If none of the above categories clearly apply, classify as \"{unknown_category.value}\": {unknown_desc}")
    
    return "\n\n".join(descriptions)

# Generate the full system prompt
SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.format(
    category_descriptions=generate_category_descriptions()
)


HUMAN_PROMPT = """
Categorize the following business architecture sentences:

{sentences_block}
""".strip()


class CategorizationAgent:
    def __init__(self, provider: str | None = None, model: str | None = None, temperature: float = 0.0):
        self.llm = create_chat_llm(provider=provider, model=model, temperature=temperature)
        # Use strict mode for better compatibility with GPT-5 and newer models
        self.structured = self.llm.with_structured_output(CategorizationResult, method="json_schema", strict=True)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ])

    def run(self, sentence_dict: Dict[str, dict]) -> CategorizationResult:
        """
        Categorize sentences into high-level categories.
        
        Args:
            sentence_dict: Dictionary mapping sentence IDs to their details
                          (including text, source, page, confidence)
        
        Returns:
            CategorizationResult with categorized sentences
        """
        if not sentence_dict:
            logger.warning("No sentences to categorize")
            return CategorizationResult(sentences=[])
            
        # Format sentences for the prompt
        sentences_block = "\n".join(f"ID: {sid}, Text: {details['text']}" 
                                  for sid, details in sentence_dict.items())
        
        try:
            chain = self.prompt | self.structured
            result: CategorizationResult = chain.invoke({"sentences_block": sentences_block[:12000]})
                
            # Log categorization results
            category_counts = {}
            for sent in result.sentences:
                category = sent.category.value
                category_counts[category] = category_counts.get(category, 0) + 1
                
            logger.info(f"Categorized {len(result.sentences)} sentences: {category_counts}")
            return result
            
        except Exception as e:
            logger.error(f"Error during categorization: {str(e)}")
            return CategorizationResult(sentences=[])
