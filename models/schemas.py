from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from config.ba_config import CategoryType, BusinessArtefactType


class ExtractedSentenceCandidate(BaseModel):
    text: str = Field(..., description="A single sentence relevant to Business Architecture")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence 0-1")


class ExtractionCandidates(BaseModel):
    sentences: List[ExtractedSentenceCandidate] = []


class ExtractedSentence(BaseModel):
    id: str = Field(..., description="Stable id for sentence (assigned by the pipeline)")
    text: str
    source: str = Field(..., description="Document/source identifier")
    page: Optional[int] = Field(None, description="Page number if available")
    confidence: float = Field(..., ge=0.0, le=1.0)


class CategorizedSentence(BaseModel):
    id: str = Field(..., description="Stable id for sentence (assigned by the pipeline)")
    text: str
    source: str = Field(..., description="Document/source identifier")
    page: Optional[int] = Field(None, description="Page number if available")
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: CategoryType = Field(..., description="High-level category: Ends, Means, or Governance")
    category_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the category assignment")


class ExtractionResult(BaseModel):
    sentences: List[ExtractedSentence] = []


class CategorizationResult(BaseModel):
    sentences: List[CategorizedSentence] = []


class BusinessArtefact(BaseModel):
    id: str = Field(..., description="Stable id for the artefact")
    name: str = Field(..., description="Concise name/title of the artefact")
    type: BusinessArtefactType
    source_sentence_ids: Optional[List[str]] = Field(
        default=None, description="IDs of sentences supporting the artefact"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    attributes: Optional[Dict[str, str]] = Field(
        default=None, description="Optional key/value attributes"
    )


class ClassificationResult(BaseModel):
    artefacts: List[BusinessArtefact] = []


class Relationship(BaseModel):
    source_id: str = Field(..., description="Source artefact id")
    target_id: str = Field(..., description="Target artefact id")
    type: str = Field(..., description="Relationship type, e.g., 'supports', 'realizes', 'flowsThrough'")
    confidence: float = Field(..., ge=0.0, le=1.0)


class InferenceResult(BaseModel):
    new_artefacts: List[BusinessArtefact] = []
    relationships: List[Relationship] = []


class ArtefactRelevance(BaseModel):
    artefact_type: BusinessArtefactType
    relevance: Literal["high", "medium", "low", "irrelevant"]
    reason: str = Field(..., min_length=1)


class DocumentProfile(BaseModel):
    document_type: str = Field(..., min_length=1)
    document_type_confidence: float = Field(..., ge=0.0, le=1.0)
    industry: str = Field(..., min_length=1)
    industry_confidence: float = Field(..., ge=0.0, le=1.0)
    purpose: str = Field(..., min_length=1)
    audience: List[str] = []
    content_patterns: List[str] = []
    artefact_relevance: List[ArtefactRelevance] = []

    @model_validator(mode="after")
    def relevance_types_are_unique(self):
        types = [item.artefact_type for item in self.artefact_relevance]
        if len(types) != len(set(types)):
            raise ValueError("artefact relevance types must be unique")
        return self


class ContextualRule(BaseModel):
    number: int = Field(..., ge=1)
    directive: str = Field(..., min_length=1)


class ContextualRuleSet(BaseModel):
    artefact_type: BusinessArtefactType
    rules: List[ContextualRule] = Field(..., min_length=3, max_length=5)

    @model_validator(mode="after")
    def rules_are_unique_and_sequential(self):
        if [rule.number for rule in self.rules] != list(
            range(1, len(self.rules) + 1)
        ):
            raise ValueError("rule numbers must be sequential starting at 1")
        directives = [rule.directive.strip().casefold() for rule in self.rules]
        if len(directives) != len(set(directives)):
            raise ValueError("rule directives must be unique")
        return self


class ContextualRuleSets(BaseModel):
    rule_sets: List[ContextualRuleSet] = []


class ContextualRuleGenerationResult(BaseModel):
    profile: DocumentProfile
    rule_sets: List[ContextualRuleSet] = []

    @model_validator(mode="after")
    def rule_sets_match_relevant_types(self):
        relevant = {
            item.artefact_type
            for item in self.profile.artefact_relevance
            if item.relevance != "irrelevant"
        }
        types = [rule_set.artefact_type for rule_set in self.rule_sets]
        if len(types) != len(set(types)):
            raise ValueError("contextual rule set types must be unique")
        if set(types) != relevant:
            raise ValueError(
                "rules must be generated once for every relevant artefact type"
            )
        return self
