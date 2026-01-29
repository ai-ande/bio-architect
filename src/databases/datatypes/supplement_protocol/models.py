"""Pydantic models for supplement protocol data."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Frequency(str, Enum):
    """Frequency of supplement intake."""

    DAILY = "daily"
    TWICE_DAILY = "2x_daily"
    TWICE_WEEKLY = "2x_week"
    AS_NEEDED = "as_needed"


class ProtocolSupplementType(str, Enum):
    """Type of protocol supplement."""

    SCHEDULED = "scheduled"
    OWN = "own"


class ProtocolSupplement(BaseModel):
    """A supplement entry in a protocol (either scheduled or own)."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    protocol_id: UUID = Field(..., description="FK to SupplementProtocol")
    supplement_label_id: Optional[UUID] = Field(
        None, description="Reference to linked SupplementLabel"
    )
    type: ProtocolSupplementType = Field(..., description="Type of supplement (scheduled or own)")
    name: str = Field(..., description="Name of the supplement")
    instructions: Optional[str] = Field(None, description="Special instructions")
    dosage: Optional[str] = Field(None, description="Dosage description (for own supplements)")
    frequency: Frequency = Field(..., description="How often to take the supplement")
    # Flattened DailySchedule fields
    upon_waking: int = Field(0, description="Number of doses upon waking")
    breakfast: int = Field(0, description="Number of doses at breakfast")
    mid_morning: int = Field(0, description="Number of doses mid-morning")
    lunch: int = Field(0, description="Number of doses at lunch")
    mid_afternoon: int = Field(0, description="Number of doses mid-afternoon")
    dinner: int = Field(0, description="Number of doses at dinner")
    before_sleep: int = Field(0, description="Number of doses before sleep")


class SupplementProtocol(BaseModel):
    """A complete supplement protocol from a healthcare provider."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    protocol_date: date = Field(..., description="Date of the protocol")
    prescriber: Optional[str] = Field(None, description="Name of the prescriber")
    next_visit: Optional[str] = Field(None, description="Next visit timing")
    source_file: Optional[str] = Field(None, description="Source PDF filename")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
    # Flattened lifestyle notes
    protein_goal: Optional[str] = Field(None, description="Daily protein target")
    lifestyle_notes: list[str] = Field(default_factory=list, description="Other lifestyle notes")
