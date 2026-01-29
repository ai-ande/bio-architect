"""Pydantic models for bloodwork lab data."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .validators import BiomarkerCode


class Flag(str, Enum):
    """Biomarker result flag indicating normal/abnormal status."""

    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"
    PENDING = "pending"


class Biomarker(BaseModel):
    """A single biomarker measurement from a lab test."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    panel_id: UUID = Field(..., description="FK to Panel")
    name: str = Field(..., description="Display name of the biomarker")
    code: BiomarkerCode = Field(..., description="Standardized code for temporal tracking")
    value: float = Field(..., description="Measured value")
    unit: str = Field(..., description="Unit of measurement")
    reference_low: Optional[float] = Field(
        None, description="Low end of reference range"
    )
    reference_high: Optional[float] = Field(
        None, description="High end of reference range"
    )
    flag: Flag = Field(Flag.NORMAL, description="Normal/high/low indicator")


class Panel(BaseModel):
    """A group of related biomarkers tested together."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    lab_report_id: UUID = Field(..., description="FK to LabReport")
    name: str = Field(..., description="Panel name (e.g., 'CBC', 'Lipid Panel')")
    comment: Optional[str] = Field(None, description="Lab comments about the panel")


class LabReport(BaseModel):
    """A complete lab report containing multiple panels."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    lab_provider: str = Field(..., description="Lab company (e.g., 'LabCorp', 'Quest')")
    collected_date: date = Field(..., description="Date sample was collected")
    source_file: Optional[str] = Field(None, description="Source PDF filename")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
