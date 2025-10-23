from __future__ import annotations

import logging
from typing import Iterable, List, Tuple

from langchain_core.prompts import ChatPromptTemplate

from llm.factory import create_chat_llm
from models.schemas import ExtractionCandidates
from utils.loaders import DocumentChunk


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an expert Business Architect. Extract only sentences that are directly
relevant to Business Architecture concepts (e.g., capabilities, goals, strategies,
value streams, processes, principles, policies, requirements, outcomes). Return
high-confidence sentences only, avoiding boilerplate, headers, and citations.

Return at most 10 sentences per input page. If the text appears garbled or contains
encoding issues, return an empty list of sentences rather than describing the issue.
Only return actual Business Architecture content, not observations about the text quality.
""".strip()


HUMAN_PROMPT = """
Given the following page content (source: {source}, page: {page}), extract relevant
Business Architecture sentences. Respond using the requested JSON schema.

Page content:
{page_text}
""".strip()


class ExtractionAgent:
    def __init__(self, provider: str | None = None, model: str | None = None, temperature: float = 0.0):
        self.llm = create_chat_llm(provider=provider, model=model, temperature=temperature)
        # Use strict mode for better compatibility with GPT-5 and newer models
        self.structured = self.llm.with_structured_output(ExtractionCandidates, method="json_schema", strict=True)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ])

    def run(self, chunks: Iterable[DocumentChunk]) -> List[Tuple[DocumentChunk, ExtractionCandidates]]:
        results: List[Tuple[DocumentChunk, ExtractionCandidates]] = []
        for chunk in chunks:
            # Clean text - remove non-printable characters that might cause issues
            cleaned_text = ''.join(c if c.isprintable() or c.isspace() else ' ' for c in chunk.text)
            
            # Check if text appears to be garbled
            garbled_ratio = sum(1 for c in cleaned_text if not c.isalnum() and not c.isspace()) / max(len(cleaned_text), 1)
            if garbled_ratio > 0.3:  # If more than 30% of non-space chars are non-alphanumeric
                logger.warning(f"Text from {chunk.source}:{chunk.page} appears garbled (ratio: {garbled_ratio:.2f})")
            
            # Limit text length for LLM
            limited_text = cleaned_text[:8000]
            
            # Handle extremely garbled text
            if garbled_ratio > 0.5:  # If more than 50% is non-alphanumeric, skip LLM call
                logger.warning(f"Text from {chunk.source}:{chunk.page} is too garbled (ratio: {garbled_ratio:.2f}), skipping LLM")
                output = ExtractionCandidates(sentences=[])  # Empty result
            else:
                try:
                    chain = self.prompt | self.structured
                    output: ExtractionCandidates = chain.invoke({
                        "source": chunk.source,
                        "page": chunk.page,
                        "page_text": limited_text,
                    })
                    
                    # Ensure we have a valid output object even if the LLM returns None
                    if output is None:
                        logger.warning(f"LLM returned None for {chunk.source}:{chunk.page}, creating empty result")
                        output = ExtractionCandidates(sentences=[])
                     
                    # Filter out meta-responses about garbled text
                    filtered_sentences = []
                    for sentence in output.sentences:
                        text_lower = sentence.text.lower()
                        # Skip sentences that are about the text quality rather than actual content
                        if any(phrase in text_lower for phrase in [
                            "garbled", "encoding issue", "not processable", "cannot extract", 
                            "unable to extract", "text appears to be", "text is not"
                        ]):
                            logger.warning(f"Filtering meta-response: {sentence.text}")
                            continue
                        filtered_sentences.append(sentence)
                    
                    # Replace with filtered sentences
                    output.sentences = filtered_sentences
                        
                except Exception as e:
                    logger.error(f"Error processing {chunk.source}:{chunk.page}: {str(e)}")
                    output = ExtractionCandidates(sentences=[])  # Empty result on error
            
            # Always append a result to maintain document order
            results.append((chunk, output))
            
            # Log extraction results
            if output.sentences:
                logger.info(f"Extracted {len(output.sentences)} sentences from {chunk.source}:{chunk.page}")
                if output.sentences:
                    logger.info(f"First sentence: {output.sentences[0].text[:100]}...")
                    if len(output.sentences) > 1:
                        logger.info(f"Last sentence: {output.sentences[-1].text[:100]}...")
            else:
                logger.warning(f"No sentences extracted from {chunk.source}:{chunk.page}")
                
        return results

