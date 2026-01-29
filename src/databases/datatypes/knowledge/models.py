"""Pydantic models for Knowledge entries."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class KnowledgeType(str, Enum):
    """Type of knowledge entry."""

    INSIGHT = "insight"
    RECOMMENDATION = "recommendation"
    CONTRAINDICATION = "contraindication"
    MEMORY = "memory"


class KnowledgeStatus(str, Enum):
    """Status of a knowledge entry."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"


class LinkType(str, Enum):
    """Type of entity a knowledge entry can be linked to."""

    SNP = "snp"
    BIOMARKER = "biomarker"
    INGREDIENT = "ingredient"
    SUPPLEMENT = "supplement"
    PROTOCOL = "protocol"
    KNOWLEDGE = "knowledge"


class Knowledge(BaseModel):
    """A knowledge entry storing insights, recommendations, or contraindications."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    type: KnowledgeType = Field(..., description="Type of knowledge entry")
    status: KnowledgeStatus = Field(
        default=KnowledgeStatus.ACTIVE, description="Status of the entry"
    )
    summary: str = Field(..., description="Brief summary of the knowledge")
    content: str = Field(..., description="Full content/details of the knowledge")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    supersedes_id: Optional[UUID] = Field(
        None, description="FK to Knowledge entry this supersedes"
    )
    supersession_reason: Optional[str] = Field(
        None, description="Reason for superseding the previous entry"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Record creation timestamp"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0.0 and 1.0."""
        if v < 0.0 or v > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class KnowledgeLink(BaseModel):
    """A link between a knowledge entry and another entity."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    knowledge_id: UUID = Field(..., description="FK to Knowledge")
    link_type: LinkType = Field(..., description="Type of linked entity")
    target_id: UUID = Field(..., description="UUID of the linked entity")


class KnowledgeTag(BaseModel):
    """A tag associated with a knowledge entry."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    knowledge_id: UUID = Field(..., description="FK to Knowledge")
    tag: str = Field(..., description="Tag value")
