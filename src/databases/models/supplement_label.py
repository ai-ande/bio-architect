"""Pydantic models for supplement label data."""

from enum import Enum
from typing import Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SupplementForm(str, Enum):
    """Physical form of the supplement."""

    CAPSULE = "capsule"
    TABLET = "tablet"
    POWDER = "powder"
    LIQUID = "liquid"
    SOFTGEL = "softgel"
    GUMMY = "gummy"
    LOZENGE = "lozenge"


class ActiveIngredient(BaseModel):
    """An active ingredient with a specified amount per serving."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Display name of the ingredient")
    code: str = Field(..., description="Standardized code for tracking")
    amount: float = Field(..., description="Amount per serving")
    unit: str = Field(..., description="Unit of measurement")
    percent_dv: Optional[float] = Field(None, description="Percent daily value")
    form: Optional[str] = Field(None, description="Specific form of the ingredient")


class BlendIngredient(BaseModel):
    """An ingredient within a proprietary blend (amount may not be disclosed)."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Display name of the ingredient")
    code: str = Field(..., description="Standardized code for tracking")
    amount: Optional[float] = Field(None, description="Amount per serving (if disclosed)")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    form: Optional[str] = Field(None, description="Specific form of the ingredient")


class OtherIngredient(BaseModel):
    """A non-active ingredient (excipient, filler, capsule material, etc.)."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Display name of the ingredient")
    code: str = Field(..., description="Standardized code for tracking")
    amount: Optional[float] = Field(None, description="Amount if specified")
    unit: Optional[str] = Field(None, description="Unit of measurement")


class ProprietaryBlend(BaseModel):
    """A proprietary blend containing multiple ingredients."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., description="Name of the blend")
    total_amount: Optional[float] = Field(None, description="Total amount of the blend")
    total_unit: Optional[str] = Field(None, description="Unit for total amount")
    ingredients: list[BlendIngredient] = Field(
        default_factory=list, description="Ingredients in this blend"
    )


class SupplementLabel(BaseModel):
    """Complete supplement label data."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    brand: str = Field(..., description="Brand/manufacturer name")
    product_name: str = Field(..., description="Product name")
    form: SupplementForm = Field(..., description="Physical form (capsule, powder, etc.)")
    serving_size: str = Field(..., description="Serving size description")
    servings_per_container: Optional[int] = Field(
        None, description="Number of servings per container"
    )
    suggested_use: Optional[str] = Field(None, description="Suggested usage instructions")
    active_ingredients: list[ActiveIngredient] = Field(
        default_factory=list, description="Active ingredients with amounts"
    )
    proprietary_blends: list[ProprietaryBlend] = Field(
        default_factory=list, description="Proprietary blends"
    )
    other_ingredients: list[OtherIngredient] = Field(
        default_factory=list, description="Non-active ingredients"
    )
    warnings: list[str] = Field(default_factory=list, description="Warning statements")
    allergen_info: Optional[str] = Field(None, description="Allergen information")

    def get_all_ingredients(self) -> list[Union[ActiveIngredient, BlendIngredient]]:
        """Get all active and blend ingredients (excludes excipients)."""
        ingredients: list[Union[ActiveIngredient, BlendIngredient]] = list(
            self.active_ingredients
        )
        for blend in self.proprietary_blends:
            ingredients.extend(blend.ingredients)
        return ingredients

    def get_ingredient_by_code(
        self, code: str
    ) -> Optional[Union[ActiveIngredient, BlendIngredient]]:
        """Find an active or blend ingredient by its standardized code."""
        for ingredient in self.active_ingredients:
            if ingredient.code == code:
                return ingredient
        for blend in self.proprietary_blends:
            for ingredient in blend.ingredients:
                if ingredient.code == code:
                    return ingredient
        return None
