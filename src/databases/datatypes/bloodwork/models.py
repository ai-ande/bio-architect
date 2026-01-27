"""Pydantic models for bloodwork lab data."""

from datetime import date
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
    name: str = Field(..., description="Display name of the biomarker")
    code: BiomarkerCode = Field(..., description="Standardized code for temporal tracking")
    value: float = Field(..., description="Measured value")
    unit: str = Field(..., description="Unit of measurement")
    reference_low: Optional[float] = Field(
        None, description="High end of reference range"
    )
    reference_high: Optional[float] = Field(
        None, description="Low end of reference range"
    )
    flag: Flag = Field(Flag.NORMAL, description="Normal/high/low indicator")
    # Temporal context (populated when returned from queries)
    collected_date: Optional[date] = Field(None, description="Date sample was collected")
    lab_provider: Optional[str] = Field(None, description="Lab company")
    panel_name: Optional[str] = Field(None, description="Panel this biomarker belongs to")


class Panel(BaseModel):
    """A group of related biomarkers tested together."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Panel name (e.g., 'CBC', 'Lipid Panel')")
    comment: Optional[str] = Field(None, description="Lab comments about the panel")
    biomarkers: list[Biomarker] = Field(
        default_factory=list, description="Biomarker results in this panel"
    )


class LabReport(BaseModel):
    """A complete lab report containing multiple panels."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    lab_provider: str = Field(..., description="Lab company (e.g., 'LabCorp', 'Quest')")
    collected_date: date = Field(..., description="Date sample was collected")
    received_date: Optional[date] = Field(None, description="Date lab received sample")
    reported_date: Optional[date] = Field(None, description="Date results were reported")
    source_file: Optional[str] = Field(None, description="Source PDF filename")
    panels: list[Panel] = Field(default_factory=list, description="Test panels")

    def get_all_biomarkers(self) -> list[Biomarker]:
        """Flatten all biomarkers from all panels."""
        return [
            biomarker for panel in self.panels for biomarker in panel.biomarkers
        ]

    def get_biomarker_by_code(self, code: str) -> Optional[Biomarker]:
        """Find a biomarker by its standardized code."""
        for panel in self.panels:
            for biomarker in panel.biomarkers:
                if biomarker.code == code:
                    return biomarker
        return None
    

    def get_flagged_biomarkers(self) -> list[Biomarker]:
        """Return only biomarkers with abnormal flags."""
        return [b for b in self.get_all_biomarkers() if b.flag != Flag.NORMAL]
