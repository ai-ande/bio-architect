"""Pydantic models for supplement label data."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .validators import IngredientCode


class SupplementForm(str, Enum):
    """Physical form of the supplement."""

    CAPSULE = "capsule"
    TABLET = "tablet"
    POWDER = "powder"
    LIQUID = "liquid"
    SOFTGEL = "softgel"
    GUMMY = "gummy"
    LOZENGE = "lozenge"


class IngredientType(str, Enum):
    """Type of ingredient."""

    ACTIVE = "active"
    BLEND = "blend"
    OTHER = "other"


class Ingredient(BaseModel):
    """A unified ingredient model that can represent active, blend, or other ingredients."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    supplement_label_id: Optional[UUID] = Field(
        None, description="FK to SupplementLabel (for active/other ingredients)"
    )
    blend_id: Optional[UUID] = Field(
        None, description="FK to ProprietaryBlend (for blend ingredients)"
    )
    type: IngredientType = Field(..., description="Type of ingredient (active, blend, other)")
    name: str = Field(..., description="Display name of the ingredient")
    code: IngredientCode = Field(..., description="Standardized code for tracking")
    amount: Optional[float] = Field(None, description="Amount per serving")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    percent_dv: Optional[float] = Field(None, description="Percent daily value (active only)")
    form: Optional[str] = Field(None, description="Specific form of the ingredient")


class ProprietaryBlend(BaseModel):
    """A proprietary blend containing multiple ingredients."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    supplement_label_id: UUID = Field(..., description="FK to SupplementLabel")
    name: str = Field(..., description="Name of the blend")
    total_amount: Optional[float] = Field(None, description="Total amount of the blend")
    total_unit: Optional[str] = Field(None, description="Unit for total amount")


class SupplementLabel(BaseModel):
    """Complete supplement label data."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    source_file: Optional[str] = Field(None, description="Source file path")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation time")
    brand: str = Field(..., description="Brand/manufacturer name")
    product_name: str = Field(..., description="Product name")
    form: SupplementForm = Field(..., description="Physical form (capsule, powder, etc.)")
    serving_size: str = Field(..., description="Serving size description")
    servings_per_container: Optional[int] = Field(
        None, description="Number of servings per container"
    )
    suggested_use: Optional[str] = Field(None, description="Suggested usage instructions")
    warnings: list[str] = Field(default_factory=list, description="Warning statements")
    allergen_info: Optional[str] = Field(None, description="Allergen information")
