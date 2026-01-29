"""Pydantic models for supplement protocol data."""

from datetime import date
from enum import Enum
from typing import Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Frequency(str, Enum):
    """Frequency of supplement intake."""

    DAILY = "daily"
    TWICE_DAILY = "2x_daily"
    TWICE_WEEKLY = "2x_week"
    AS_NEEDED = "as_needed"


class DailySchedule(BaseModel):
    """Schedule for supplement intake throughout the day."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    upon_waking: int = Field(0, description="Number of doses upon waking")
    breakfast: int = Field(0, description="Number of doses at breakfast")
    mid_morning: int = Field(0, description="Number of doses mid-morning")
    lunch: int = Field(0, description="Number of doses at lunch")
    mid_afternoon: int = Field(0, description="Number of doses mid-afternoon")
    dinner: int = Field(0, description="Number of doses at dinner")
    before_sleep: int = Field(0, description="Number of doses before sleep")


class ScheduledSupplement(BaseModel):
    """A supplement with a prescribed schedule from a protocol."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Name of the supplement")
    supplement_label_id: Optional[UUID] = Field(
        None, description="Reference to linked SupplementLabel"
    )
    instructions: Optional[str] = Field(None, description="Special instructions")
    frequency: Frequency = Field(..., description="How often to take the supplement")
    schedule: DailySchedule = Field(
        default_factory=DailySchedule, description="Daily timing schedule"
    )


class OwnSupplement(BaseModel):
    """A supplement the patient takes on their own (not prescribed in protocol)."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Name of the supplement")
    supplement_label_id: Optional[UUID] = Field(
        None, description="Reference to linked SupplementLabel"
    )
    dosage: Optional[str] = Field(None, description="Dosage description")
    frequency: Frequency = Field(..., description="How often to take the supplement")


class LifestyleNotes(BaseModel):
    """Lifestyle recommendations from the protocol."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    protein_goal: Optional[str] = Field(None, description="Daily protein target")
    other: list[str] = Field(default_factory=list, description="Other lifestyle notes")


class SupplementProtocol(BaseModel):
    """A complete supplement protocol from a healthcare provider."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    patient_name: str = Field(..., description="Name of the patient")
    protocol_date: date = Field(..., description="Date of the protocol")
    prescriber: Optional[str] = Field(None, description="Name of the prescriber")
    supplements: list[ScheduledSupplement] = Field(
        default_factory=list, description="Prescribed supplements with schedules"
    )
    own_supplements: list[OwnSupplement] = Field(
        default_factory=list, description="Patient's own supplements"
    )
    lifestyle_notes: Optional[LifestyleNotes] = Field(
        None, description="Lifestyle recommendations"
    )
    next_visit: Optional[str] = Field(None, description="Next visit timing")
    source_file: Optional[str] = Field(None, description="Source PDF filename")

    def get_all_supplements(
        self,
    ) -> list[Union[ScheduledSupplement, OwnSupplement]]:
        """Get all supplements (scheduled and own)."""
        supplements: list[Union[ScheduledSupplement, OwnSupplement]] = list(
            self.supplements
        )
        supplements.extend(self.own_supplements)
        return supplements

    def get_supplement_by_name(
        self, name: str
    ) -> Optional[Union[ScheduledSupplement, OwnSupplement]]:
        """Find a supplement by name (case-insensitive)."""
        name_lower = name.lower()
        for supp in self.supplements:
            if supp.name.lower() == name_lower:
                return supp
        for supp in self.own_supplements:
            if supp.name.lower() == name_lower:
                return supp
        return None
