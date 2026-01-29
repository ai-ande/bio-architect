"""SQLModel models for DNA/SNP genetic data."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlmodel import SQLModel, Field


class Repute(str, Enum):
    """SNP reputation indicating whether the variant is beneficial or harmful."""

    GOOD = "good"
    BAD = "bad"


class DnaTest(SQLModel, table=True):
    """A DNA test containing SNP data."""

    __tablename__ = "dna_tests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source: str
    collected_date: date
    source_file: str
    created_at: datetime = Field(default_factory=datetime.now)


class Snp(SQLModel, table=True):
    """A single nucleotide polymorphism from a DNA test."""

    __tablename__ = "snps"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    dna_test_id: UUID = Field(foreign_key="dna_tests.id")
    rsid: str
    genotype: str
    magnitude: float
    repute: Optional[Repute] = None
    gene: str

    @field_validator("magnitude")
    @classmethod
    def validate_magnitude(cls, v: float) -> float:
        """Validate magnitude is between 0 and 10."""
        if v < 0 or v > 10:
            raise ValueError("magnitude must be between 0 and 10")
        return v
