"""Tests for supplement label models."""

from datetime import datetime
from uuid import UUID

import pytest

from src.databases.datatypes.supplement import (
    Ingredient,
    IngredientType,
    ProprietaryBlend,
    SupplementForm,
    SupplementLabel,
    VALID_INGREDIENT_CODES,
)


class TestIngredientCodeValidation:
    """Tests for ingredient code validation."""

    def test_valid_codes_loaded_from_yaml(self):
        """Verify that valid codes are loaded from the YAML file."""
        assert "VITAMIN_A" in VALID_INGREDIENT_CODES
        assert "ZINC" in VALID_INGREDIENT_CODES
        assert "L_LEUCINE" in VALID_INGREDIENT_CODES
        assert "ASHWAGANDHA" in VALID_INGREDIENT_CODES
        assert "OMEGA_3" in VALID_INGREDIENT_CODES
        assert "COENZYME_Q10" in VALID_INGREDIENT_CODES
        assert "MICROCRYSTALLINE_CELLULOSE" in VALID_INGREDIENT_CODES

    def test_ingredient_accepts_valid_yaml_code(self):
        """Valid codes from YAML should be accepted."""
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="Zinc",
            code="ZINC",
            amount=30,
            unit="mg",
        )
        assert ingredient.code == "ZINC"

    def test_ingredient_accepts_valid_custom_code(self):
        """Custom codes following format rules should be accepted."""
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="Custom Ingredient",
            code="CUSTOM_INGREDIENT",
            amount=100,
            unit="mg",
        )
        assert ingredient.code == "CUSTOM_INGREDIENT"

    def test_ingredient_rejects_lowercase_code(self):
        """Lowercase codes should be rejected."""
        with pytest.raises(ValueError, match="must be uppercase"):
            Ingredient(
                type=IngredientType.ACTIVE,
                name="Zinc",
                code="zinc",
                amount=30,
                unit="mg",
            )

    def test_ingredient_rejects_code_with_spaces(self):
        """Codes with spaces should be rejected."""
        with pytest.raises(ValueError, match="must not contain spaces"):
            Ingredient(
                type=IngredientType.ACTIVE,
                name="Vitamin A",
                code="VITAMIN A",
                amount=100,
                unit="IU",
            )

    def test_ingredient_rejects_code_with_special_chars(self):
        """Codes with special characters (other than underscore) should be rejected."""
        with pytest.raises(ValueError, match="invalid characters"):
            Ingredient(
                type=IngredientType.ACTIVE,
                name="Test",
                code="TEST-CODE",
                amount=100,
                unit="mg",
            )

    def test_ingredient_rejects_empty_code(self):
        """Empty codes should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Ingredient(
                type=IngredientType.ACTIVE,
                name="Test",
                code="",
                amount=100,
                unit="mg",
            )

    def test_code_allows_numbers(self):
        """Codes with numbers should be valid."""
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="Vitamin B12",
            code="VITAMIN_B12",
            amount=1000,
            unit="mcg",
        )
        assert ingredient.code == "VITAMIN_B12"

    def test_code_allows_leading_underscore_for_amino_acids(self):
        """L_ prefix for amino acids should be valid."""
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="L-Glutamine",
            code="L_GLUTAMINE",
            amount=500,
            unit="mg",
        )
        assert ingredient.code == "L_GLUTAMINE"


class TestIngredientType:
    """Tests for IngredientType enum."""

    def test_type_values(self):
        assert IngredientType.ACTIVE.value == "active"
        assert IngredientType.BLEND.value == "blend"
        assert IngredientType.OTHER.value == "other"

    def test_type_is_string_enum(self):
        assert isinstance(IngredientType.ACTIVE, str)
        assert IngredientType.ACTIVE == "active"


class TestSupplementForm:
    """Tests for SupplementForm enum."""

    def test_form_values(self):
        assert SupplementForm.CAPSULE.value == "capsule"
        assert SupplementForm.POWDER.value == "powder"
        assert SupplementForm.TABLET.value == "tablet"
        assert SupplementForm.LIQUID.value == "liquid"
        assert SupplementForm.SOFTGEL.value == "softgel"

    def test_form_is_string_enum(self):
        assert isinstance(SupplementForm.CAPSULE, str)
        assert SupplementForm.CAPSULE == "capsule"


class TestIngredient:
    """Tests for unified Ingredient model."""

    def test_create_active_ingredient(self):
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="Zinc (as Zinc Picolinate)",
            code="ZINC",
            amount=30,
            unit="mg",
        )
        assert ingredient.name == "Zinc (as Zinc Picolinate)"
        assert ingredient.code == "ZINC"
        assert ingredient.amount == 30
        assert ingredient.unit == "mg"
        assert ingredient.type == IngredientType.ACTIVE

    def test_ingredient_has_uuid(self):
        ingredient = Ingredient(type=IngredientType.ACTIVE, name="Zinc", code="ZINC")
        assert isinstance(ingredient.id, UUID)

    def test_ingredient_uuid_is_unique(self):
        i1 = Ingredient(type=IngredientType.ACTIVE, name="Zinc", code="ZINC")
        i2 = Ingredient(type=IngredientType.ACTIVE, name="Zinc", code="ZINC")
        assert i1.id != i2.id

    def test_active_ingredient_with_percent_dv(self):
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="Zinc",
            code="ZINC",
            amount=30,
            unit="mg",
            percent_dv=273,
        )
        assert ingredient.percent_dv == 273

    def test_ingredient_with_form(self):
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="Zinc (as Zinc Picolinate)",
            code="ZINC",
            amount=30,
            unit="mg",
            form="Zinc Picolinate",
        )
        assert ingredient.form == "Zinc Picolinate"

    def test_ingredient_optional_fields_default_to_none(self):
        ingredient = Ingredient(type=IngredientType.ACTIVE, name="Zinc", code="ZINC")
        assert ingredient.amount is None
        assert ingredient.unit is None
        assert ingredient.percent_dv is None
        assert ingredient.form is None
        assert ingredient.supplement_label_id is None
        assert ingredient.blend_id is None

    def test_create_blend_ingredient_without_amount(self):
        """Proprietary blends may not disclose individual amounts."""
        ingredient = Ingredient(
            type=IngredientType.BLEND,
            name="Vidanga (Embelia ribes) (fruit)",
            code="VIDANGA",
            form="fruit",
        )
        assert ingredient.name == "Vidanga (Embelia ribes) (fruit)"
        assert ingredient.amount is None
        assert ingredient.unit is None
        assert ingredient.form == "fruit"
        assert ingredient.type == IngredientType.BLEND

    def test_create_other_ingredient(self):
        ingredient = Ingredient(
            type=IngredientType.OTHER,
            name="Microcrystalline Cellulose",
            code="MICROCRYSTALLINE_CELLULOSE",
        )
        assert ingredient.name == "Microcrystalline Cellulose"
        assert ingredient.code == "MICROCRYSTALLINE_CELLULOSE"
        assert ingredient.type == IngredientType.OTHER

    def test_ingredient_with_supplement_label_id(self):
        label_id = UUID("12345678-1234-1234-1234-123456789012")
        ingredient = Ingredient(
            type=IngredientType.ACTIVE,
            name="Zinc",
            code="ZINC",
            supplement_label_id=label_id,
        )
        assert ingredient.supplement_label_id == label_id

    def test_ingredient_with_blend_id(self):
        blend_id = UUID("12345678-1234-1234-1234-123456789012")
        ingredient = Ingredient(
            type=IngredientType.BLEND,
            name="Vidanga",
            code="VIDANGA",
            blend_id=blend_id,
        )
        assert ingredient.blend_id == blend_id


class TestProprietaryBlend:
    """Tests for ProprietaryBlend model."""

    def test_create_blend(self):
        label_id = UUID("12345678-1234-1234-1234-123456789012")
        blend = ProprietaryBlend(name="Test Blend", supplement_label_id=label_id)
        assert blend.name == "Test Blend"
        assert blend.supplement_label_id == label_id

    def test_blend_has_uuid(self):
        label_id = UUID("12345678-1234-1234-1234-123456789012")
        blend = ProprietaryBlend(name="Test Blend", supplement_label_id=label_id)
        assert isinstance(blend.id, UUID)

    def test_blend_with_total_amount(self):
        label_id = UUID("12345678-1234-1234-1234-123456789012")
        blend = ProprietaryBlend(
            name="Para 2 Blend",
            supplement_label_id=label_id,
            total_amount=1000,
            total_unit="mg",
        )
        assert blend.total_amount == 1000
        assert blend.total_unit == "mg"

    def test_blend_optional_fields_default_to_none(self):
        label_id = UUID("12345678-1234-1234-1234-123456789012")
        blend = ProprietaryBlend(name="Test Blend", supplement_label_id=label_id)
        assert blend.total_amount is None
        assert blend.total_unit is None

    def test_blend_requires_supplement_label_id(self):
        """ProprietaryBlend requires supplement_label_id FK."""
        with pytest.raises(ValueError):
            ProprietaryBlend(name="Test Blend")

    def test_blend_is_flat_no_ingredients_list(self):
        """Verify ProprietaryBlend no longer has nested ingredients list."""
        label_id = UUID("12345678-1234-1234-1234-123456789012")
        blend = ProprietaryBlend(name="Test Blend", supplement_label_id=label_id)
        assert not hasattr(blend, "ingredients")


class TestSupplementLabel:
    """Tests for SupplementLabel model."""

    def test_create_minimal_label(self):
        label = SupplementLabel(
            brand="Test Brand",
            product_name="Test Product",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        assert label.brand == "Test Brand"
        assert label.product_name == "Test Product"
        assert label.form == SupplementForm.CAPSULE
        assert label.serving_size == "1 Capsule"

    def test_label_has_uuid(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        assert isinstance(label.id, UUID)

    def test_label_uuid_is_unique(self):
        l1 = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        l2 = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        assert l1.id != l2.id

    def test_label_has_created_at(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        assert isinstance(label.created_at, datetime)

    def test_label_with_source_file(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
            source_file="supplements/thorne_zinc.pdf",
        )
        assert label.source_file == "supplements/thorne_zinc.pdf"

    def test_label_with_servings_per_container(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
            servings_per_container=30,
        )
        assert label.servings_per_container == 30

    def test_label_with_suggested_use(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
            suggested_use="Take 1 capsule daily with food.",
        )
        assert label.suggested_use == "Take 1 capsule daily with food."

    def test_label_with_warnings(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
            warnings=["Consult physician if pregnant.", "Keep out of reach of children."],
        )
        assert len(label.warnings) == 2

    def test_label_with_allergen_info(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
            allergen_info="Contains soy and tree nuts.",
        )
        assert label.allergen_info == "Contains soy and tree nuts."

    def test_label_optional_fields_default(self):
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        assert label.servings_per_container is None
        assert label.suggested_use is None
        assert label.warnings == []
        assert label.allergen_info is None
        assert label.source_file is None

    def test_label_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            SupplementLabel(brand="Test", product_name="Test", form=SupplementForm.CAPSULE)

    def test_label_is_flat_no_nested_lists(self):
        """Verify SupplementLabel no longer has nested ingredient/blend lists."""
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        assert not hasattr(label, "active_ingredients")
        assert not hasattr(label, "proprietary_blends")
        assert not hasattr(label, "other_ingredients")

    def test_label_has_no_helper_methods(self):
        """Verify SupplementLabel no longer has helper methods for nested data."""
        label = SupplementLabel(
            brand="Test",
            product_name="Test",
            form=SupplementForm.CAPSULE,
            serving_size="1 Capsule",
        )
        assert not hasattr(label, "get_all_ingredients")
        assert not hasattr(label, "get_ingredient_by_code")
