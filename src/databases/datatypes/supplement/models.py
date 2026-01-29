"""SQLModel models for supplement label data."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field

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


class SupplementLabel(SQLModel, table=True):
    """Complete supplement label data."""

    __tablename__ = "supplement_labels"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_file: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    brand: str
    product_name: str
    form: SupplementForm
    serving_size: str
    servings_per_container: Optional[int] = None
    suggested_use: Optional[str] = None
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    allergen_info: Optional[str] = None


class ProprietaryBlend(SQLModel, table=True):
    """A proprietary blend containing multiple ingredients."""

    __tablename__ = "proprietary_blends"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    supplement_label_id: UUID = Field(foreign_key="supplement_labels.id")
    name: str
    total_amount: Optional[float] = None
    total_unit: Optional[str] = None


class Ingredient(SQLModel, table=True):
    """A unified ingredient model that can represent active, blend, or other ingredients."""

    __tablename__ = "ingredients"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    supplement_label_id: Optional[UUID] = Field(
        default=None, foreign_key="supplement_labels.id"
    )
    blend_id: Optional[UUID] = Field(
        default=None, foreign_key="proprietary_blends.id"
    )
    type: IngredientType
    name: str
    code: IngredientCode
    amount: Optional[float] = None
    unit: Optional[str] = None
    percent_dv: Optional[float] = None
    form: Optional[str] = None
