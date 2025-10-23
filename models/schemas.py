from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

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

