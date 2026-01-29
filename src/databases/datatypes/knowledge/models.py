"""SQLModel models for Knowledge entries."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlmodel import SQLModel, Field


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


class Knowledge(SQLModel, table=True):
    """A knowledge entry storing insights, recommendations, or contraindications."""

    __tablename__ = "knowledge"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: KnowledgeType
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    summary: str
    content: str
    confidence: float
    supersedes_id: Optional[UUID] = Field(default=None, foreign_key="knowledge.id")
    supersession_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0.0 and 1.0."""
        if v < 0.0 or v > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class KnowledgeLink(SQLModel, table=True):
    """A link between a knowledge entry and another entity."""

    __tablename__ = "knowledge_links"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    knowledge_id: UUID = Field(foreign_key="knowledge.id")
    link_type: LinkType
    target_id: UUID  # Polymorphic reference, no FK constraint


class KnowledgeTag(SQLModel, table=True):
    """A tag associated with a knowledge entry."""

    __tablename__ = "knowledge_tags"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    knowledge_id: UUID = Field(foreign_key="knowledge.id")
    tag: str
