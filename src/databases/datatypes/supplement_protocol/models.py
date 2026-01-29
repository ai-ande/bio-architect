"""SQLModel models for supplement protocol data."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


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


class SupplementProtocol(SQLModel, table=True):
    """A complete supplement protocol from a healthcare provider."""

    __tablename__ = "supplement_protocols"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    protocol_date: date
    prescriber: Optional[str] = None
    next_visit: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    protein_goal: Optional[str] = None
    lifestyle_notes: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class ProtocolSupplement(SQLModel, table=True):
    """A supplement entry in a protocol (either scheduled or own)."""

    __tablename__ = "protocol_supplements"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    protocol_id: UUID = Field(foreign_key="supplement_protocols.id")
    supplement_label_id: Optional[UUID] = Field(
        default=None, foreign_key="supplement_labels.id"
    )
    type: ProtocolSupplementType
    name: str
    instructions: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Frequency
    # Flattened DailySchedule fields
    upon_waking: int = 0
    breakfast: int = 0
    mid_morning: int = 0
    lunch: int = 0
    mid_afternoon: int = 0
    dinner: int = 0
    before_sleep: int = 0
