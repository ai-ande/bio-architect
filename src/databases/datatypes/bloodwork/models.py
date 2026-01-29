"""SQLModel models for bloodwork lab data."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field

from .validators import BiomarkerCode


class Flag(str, Enum):
    """Biomarker result flag indicating normal/abnormal status."""

    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"
    PENDING = "pending"


class LabReport(SQLModel, table=True):
    """A complete lab report containing multiple panels."""

    __tablename__ = "lab_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lab_provider: str
    collected_date: date
    source_file: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class Panel(SQLModel, table=True):
    """A group of related biomarkers tested together."""

    __tablename__ = "panels"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lab_report_id: UUID = Field(foreign_key="lab_reports.id")
    name: str
    comment: Optional[str] = None


class Biomarker(SQLModel, table=True):
    """A single biomarker measurement from a lab test."""

    __tablename__ = "biomarkers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    panel_id: UUID = Field(foreign_key="panels.id")
    name: str
    code: BiomarkerCode
    value: float
    unit: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    flag: Flag = Flag.NORMAL
