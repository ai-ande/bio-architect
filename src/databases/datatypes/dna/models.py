"""Pydantic models for DNA/SNP genetic data."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Repute(str, Enum):
    """SNP reputation indicating whether the variant is beneficial or harmful."""

    GOOD = "good"
    BAD = "bad"


class Snp(BaseModel):
    """A single nucleotide polymorphism from a DNA test."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    dna_test_id: UUID = Field(..., description="FK to DnaTest")
    rsid: str = Field(..., description="Reference SNP ID (e.g., 'rs1234')")
    genotype: str = Field(..., description="Genotype (e.g., 'AG', 'CC')")
    magnitude: float = Field(..., description="Importance score from 0-10")
    repute: Optional[Repute] = Field(None, description="Good, bad, or null")
    gene: str = Field(..., description="Gene name (e.g., 'MTHFR')")

    @field_validator("magnitude")
    @classmethod
    def validate_magnitude(cls, v: float) -> float:
        """Validate magnitude is between 0 and 10."""
        if v < 0 or v > 10:
            raise ValueError("magnitude must be between 0 and 10")
        return v


class DnaTest(BaseModel):
    """A DNA test containing SNP data."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    source: str = Field(..., description="DNA testing provider (e.g., '23andMe', 'AncestryDNA')")
    collected_date: date = Field(..., description="Date DNA sample was collected")
    source_file: str = Field(..., description="Source data filename")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
