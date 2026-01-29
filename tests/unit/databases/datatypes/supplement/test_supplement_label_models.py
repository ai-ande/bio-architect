"""Tests for supplement label models."""

from uuid import UUID

import pytest

from src.databases.datatypes.supplement import (
    ActiveIngredient,
    BlendIngredient,
    OtherIngredient,
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

    def test_active_ingredient_accepts_valid_yaml_code(self):
        """Valid codes from YAML should be accepted."""
        ingredient = ActiveIngredient(
            name="Zinc",
            code="ZINC",
            amount=30,
            unit="mg",
        )
        assert ingredient.code == "ZINC"

    def test_active_ingredient_accepts_valid_custom_code(self):
        """Custom codes following format rules should be accepted."""
        ingredient = ActiveIngredient(
            name="Custom Ingredient",
            code="CUSTOM_INGREDIENT",
            amount=100,
            unit="mg",
        )
        assert ingredient.code == "CUSTOM_INGREDIENT"

    def test_active_ingredient_rejects_lowercase_code(self):
        """Lowercase codes should be rejected."""
        with pytest.raises(ValueError, match="must be uppercase"):
            ActiveIngredient(
                name="Zinc",
                code="zinc",
                amount=30,
                unit="mg",
            )

    def test_active_ingredient_rejects_code_with_spaces(self):
        """Codes with spaces should be rejected."""
        with pytest.raises(ValueError, match="must not contain spaces"):
            ActiveIngredient(
                name="Vitamin A",
                code="VITAMIN A",
                amount=100,
                unit="IU",
            )

    def test_active_ingredient_rejects_code_with_special_chars(self):
        """Codes with special characters (other than underscore) should be rejected."""
        with pytest.raises(ValueError, match="invalid characters"):
            ActiveIngredient(
                name="Test",
                code="TEST-CODE",
                amount=100,
                unit="mg",
            )

    def test_active_ingredient_rejects_empty_code(self):
        """Empty codes should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ActiveIngredient(
                name="Test",
                code="",
                amount=100,
                unit="mg",
            )

    def test_blend_ingredient_validates_code(self):
        """BlendIngredient should also validate codes."""
        with pytest.raises(ValueError, match="must be uppercase"):
            BlendIngredient(
                name="Invalid",
                code="invalid_code",
            )

    def test_blend_ingredient_accepts_valid_code(self):
        """BlendIngredient should accept valid codes."""
        ingredient = BlendIngredient(
            name="Valerian",
            code="VALERIAN",
        )
        assert ingredient.code == "VALERIAN"

    def test_other_ingredient_validates_code(self):
        """OtherIngredient should also validate codes."""
        with pytest.raises(ValueError, match="must be uppercase"):
            OtherIngredient(
                name="Invalid",
                code="invalid_code",
            )

    def test_other_ingredient_accepts_valid_code(self):
        """OtherIngredient should accept valid codes."""
        ingredient = OtherIngredient(
            name="Hypromellose",
            code="HYPROMELLOSE",
        )
        assert ingredient.code == "HYPROMELLOSE"

    def test_code_allows_numbers(self):
        """Codes with numbers should be valid."""
        ingredient = ActiveIngredient(
            name="Vitamin B12",
            code="VITAMIN_B12",
            amount=1000,
            unit="mcg",
        )
        assert ingredient.code == "VITAMIN_B12"

    def test_code_allows_leading_underscore_for_amino_acids(self):
        """L_ prefix for amino acids should be valid."""
        ingredient = ActiveIngredient(
            name="L-Glutamine",
            code="L_GLUTAMINE",
            amount=500,
            unit="mg",
        )
        assert ingredient.code == "L_GLUTAMINE"


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


class TestActiveIngredient:
    """Tests for ActiveIngredient model."""

    def test_create_minimal_ingredient(self):
        ingredient = ActiveIngredient(
            name="Zinc (as Zinc Picolinate)",
            code="ZINC",
            amount=30,
            unit="mg",
        )
        assert ingredient.name == "Zinc (as Zinc Picolinate)"
        assert ingredient.code == "ZINC"
        assert ingredient.amount == 30
        assert ingredient.unit == "mg"

    def test_ingredient_has_uuid(self):
        ingredient = ActiveIngredient(name="Zinc", code="ZINC", amount=30, unit="mg")
        assert isinstance(ingredient.id, UUID)

    def test_ingredient_uuid_is_unique(self):
        i1 = ActiveIngredient(name="Zinc", code="ZINC", amount=30, unit="mg")
        i2 = ActiveIngredient(name="Zinc", code="ZINC", amount=30, unit="mg")
        assert i1.id != i2.id

    def test_ingredient_with_percent_dv(self):
        ingredient = ActiveIngredient(
            name="Zinc",
            code="ZINC",
            amount=30,
            unit="mg",
            percent_dv=273,
        )
        assert ingredient.percent_dv == 273

    def test_ingredient_with_form(self):
        ingredient = ActiveIngredient(
            name="Zinc (as Zinc Picolinate)",
            code="ZINC",
            amount=30,
            unit="mg",
            form="Zinc Picolinate",
        )
        assert ingredient.form == "Zinc Picolinate"

    def test_ingredient_optional_fields_default_to_none(self):
        ingredient = ActiveIngredient(name="Zinc", code="ZINC", amount=30, unit="mg")
        assert ingredient.percent_dv is None
        assert ingredient.form is None

    def test_ingredient_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            ActiveIngredient(name="Zinc", code="ZINC", amount=30)  # missing unit


class TestBlendIngredient:
    """Tests for BlendIngredient model (used in proprietary blends)."""

    def test_create_blend_ingredient_with_amount(self):
        ingredient = BlendIngredient(
            name="Barley grass leaf powder",
            code="BARLEY_GRASS_LEAF_POWDER",
            amount=750,
            unit="mg",
            form="certified organic",
        )
        assert ingredient.name == "Barley grass leaf powder"
        assert ingredient.amount == 750
        assert ingredient.unit == "mg"

    def test_create_blend_ingredient_without_amount(self):
        """Proprietary blends may not disclose individual amounts."""
        ingredient = BlendIngredient(
            name="Vidanga (Embelia ribes) (fruit)",
            code="VIDANGA",
            form="fruit",
        )
        assert ingredient.name == "Vidanga (Embelia ribes) (fruit)"
        assert ingredient.amount is None
        assert ingredient.unit is None
        assert ingredient.form == "fruit"

    def test_blend_ingredient_has_uuid(self):
        ingredient = BlendIngredient(name="Test", code="TEST")
        assert isinstance(ingredient.id, UUID)


class TestOtherIngredient:
    """Tests for OtherIngredient model."""

    def test_create_other_ingredient_minimal(self):
        ingredient = OtherIngredient(
            name="Microcrystalline Cellulose",
            code="MICROCRYSTALLINE_CELLULOSE",
        )
        assert ingredient.name == "Microcrystalline Cellulose"
        assert ingredient.code == "MICROCRYSTALLINE_CELLULOSE"

    def test_other_ingredient_with_amount(self):
        ingredient = OtherIngredient(
            name="Rhovanil Natural Delica natural flavor",
            code="RHOVANIL_NATURAL_FLAVOR",
            amount=32.9,
            unit="mg",
        )
        assert ingredient.amount == 32.9
        assert ingredient.unit == "mg"

    def test_other_ingredient_has_uuid(self):
        ingredient = OtherIngredient(name="Test", code="TEST")
        assert isinstance(ingredient.id, UUID)


class TestProprietaryBlend:
    """Tests for ProprietaryBlend model."""

    def test_create_minimal_blend(self):
        blend = ProprietaryBlend(name="Test Blend")
        assert blend.name == "Test Blend"
        assert blend.ingredients == []

    def test_blend_has_uuid(self):
        blend = ProprietaryBlend(name="Test Blend")
        assert isinstance(blend.id, UUID)

    def test_blend_with_total_amount(self):
        blend = ProprietaryBlend(
            name="Para 2 Blend",
            total_amount=1000,
            total_unit="mg",
        )
        assert blend.total_amount == 1000
        assert blend.total_unit == "mg"

    def test_blend_with_ingredients(self):
        ingredients = [
            BlendIngredient(name="Ingredient A", code="ING_A"),
            BlendIngredient(name="Ingredient B", code="ING_B"),
        ]
        blend = ProprietaryBlend(name="Test Blend", ingredients=ingredients)
        assert len(blend.ingredients) == 2

    def test_blend_optional_fields_default_to_none(self):
        blend = ProprietaryBlend(name="Test Blend")
        assert blend.total_amount is None
        assert blend.total_unit is None


class TestSupplementLabel:
    """Tests for SupplementLabel model."""

    @pytest.fixture
    def simple_label(self) -> SupplementLabel:
        """Create a simple supplement label for testing."""
        return SupplementLabel(
            brand="Thorne",
            product_name="Zinc Picolinate 30 mg",
            form=SupplementForm.CAPSULE,
            serving_size="One Capsule",
            active_ingredients=[
                ActiveIngredient(
                    name="Zinc (as Zinc Picolinate)",
                    code="ZINC",
                    amount=30,
                    unit="mg",
                    percent_dv=273,
                    form="Zinc Picolinate",
                ),
            ],
            other_ingredients=[
                OtherIngredient(
                    name="Microcrystalline Cellulose",
                    code="MICROCRYSTALLINE_CELLULOSE",
                ),
            ],
        )

    @pytest.fixture
    def complex_label(self) -> SupplementLabel:
        """Create a label with proprietary blends for testing."""
        return SupplementLabel(
            brand="CellCore",
            product_name="Para 2",
            form=SupplementForm.CAPSULE,
            serving_size="2 Capsules",
            servings_per_container=60,
            proprietary_blends=[
                ProprietaryBlend(
                    name="Para 2 Blend",
                    total_amount=1000,
                    total_unit="mg",
                    ingredients=[
                        BlendIngredient(name="Vidanga", code="VIDANGA", form="fruit"),
                        BlendIngredient(name="Neem", code="NEEM", form="leaf"),
                    ],
                ),
            ],
        )

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
        assert label.active_ingredients == []
        assert label.proprietary_blends == []
        assert label.other_ingredients == []
        assert label.warnings == []
        assert label.allergen_info is None

    def test_label_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            SupplementLabel(brand="Test", product_name="Test", form=SupplementForm.CAPSULE)

    def test_get_all_ingredients(self, simple_label: SupplementLabel):
        ingredients = simple_label.get_all_ingredients()
        assert len(ingredients) == 1
        assert ingredients[0].code == "ZINC"

    def test_get_all_ingredients_excludes_other(self, simple_label: SupplementLabel):
        ingredients = simple_label.get_all_ingredients()
        codes = [i.code for i in ingredients]
        assert "MICROCRYSTALLINE_CELLULOSE" not in codes

    def test_get_all_ingredients_with_blends(self, complex_label: SupplementLabel):
        ingredients = complex_label.get_all_ingredients()
        assert len(ingredients) == 2
        codes = [i.code for i in ingredients]
        assert "VIDANGA" in codes
        assert "NEEM" in codes

    def test_get_ingredient_by_code_found(self, simple_label: SupplementLabel):
        ingredient = simple_label.get_ingredient_by_code("ZINC")
        assert ingredient is not None
        assert ingredient.name == "Zinc (as Zinc Picolinate)"

    def test_get_ingredient_by_code_not_found(self, simple_label: SupplementLabel):
        ingredient = simple_label.get_ingredient_by_code("NONEXISTENT")
        assert ingredient is None

    def test_get_ingredient_by_code_in_blend(self, complex_label: SupplementLabel):
        ingredient = complex_label.get_ingredient_by_code("VIDANGA")
        assert ingredient is not None
        assert ingredient.form == "fruit"

    def test_get_ingredient_by_code_excludes_other(self, simple_label: SupplementLabel):
        ingredient = simple_label.get_ingredient_by_code("MICROCRYSTALLINE_CELLULOSE")
        assert ingredient is None
