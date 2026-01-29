"""Tests for SupplementRepository."""

import tempfile
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement import (
    Ingredient,
    IngredientType,
    ProprietaryBlend,
    SupplementForm,
    SupplementLabel,
)
from src.databases.repositories.supplement import SupplementRepository


@pytest.fixture
def db_client():
    """Create a temporary database client."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        client = DatabaseClient(db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()


@pytest.fixture
def repository(db_client):
    """Create a SupplementRepository with the test database."""
    return SupplementRepository(db_client)


@pytest.fixture
def sample_label():
    """Create a sample SupplementLabel."""
    return SupplementLabel(
        id=uuid4(),
        source_file="supplement.pdf",
        created_at=datetime(2024, 1, 20, 10, 30, 0),
        brand="Thorne",
        product_name="Vitamin D-5000",
        form=SupplementForm.CAPSULE,
        serving_size="1 capsule",
        servings_per_container=60,
        suggested_use="Take 1 capsule daily with a meal",
        warnings=["Keep out of reach of children"],
        allergen_info="Contains no major allergens",
    )


@pytest.fixture
def sample_blend(sample_label):
    """Create a sample ProprietaryBlend."""
    return ProprietaryBlend(
        id=uuid4(),
        supplement_label_id=sample_label.id,
        name="Energy Blend",
        total_amount=500.0,
        total_unit="mg",
    )


@pytest.fixture
def sample_ingredient(sample_label):
    """Create a sample Ingredient."""
    return Ingredient(
        id=uuid4(),
        supplement_label_id=sample_label.id,
        blend_id=None,
        type=IngredientType.ACTIVE,
        name="Vitamin D3",
        code="VITAMIN_D3",
        amount=5000.0,
        unit="IU",
        percent_dv=1250.0,
        form="Cholecalciferol",
    )


class TestInsertLabel:
    """Tests for insert_label method."""

    def test_insert_label_returns_model(self, repository, sample_label):
        """insert_label returns the inserted SupplementLabel model."""
        result = repository.insert_label(sample_label)
        assert isinstance(result, SupplementLabel)
        assert result.id == sample_label.id
        assert result.brand == sample_label.brand

    def test_insert_label_persists_data(self, repository, sample_label):
        """insert_label persists data to database."""
        repository.insert_label(sample_label)
        retrieved = repository.get_label_by_id(sample_label.id)
        assert retrieved is not None
        assert retrieved.id == sample_label.id
        assert retrieved.brand == sample_label.brand
        assert retrieved.product_name == sample_label.product_name

    def test_insert_label_preserves_all_fields(self, repository, sample_label):
        """insert_label preserves all fields including created_at."""
        repository.insert_label(sample_label)
        retrieved = repository.get_label_by_id(sample_label.id)
        assert retrieved.created_at == sample_label.created_at
        assert retrieved.form == sample_label.form
        assert retrieved.serving_size == sample_label.serving_size
        assert retrieved.servings_per_container == sample_label.servings_per_container
        assert retrieved.suggested_use == sample_label.suggested_use
        assert retrieved.warnings == sample_label.warnings
        assert retrieved.allergen_info == sample_label.allergen_info

    def test_insert_label_with_null_source_file(self, repository):
        """insert_label handles null source_file."""
        label = SupplementLabel(
            id=uuid4(),
            source_file=None,
            brand="Pure Encapsulations",
            product_name="Magnesium Glycinate",
            form=SupplementForm.CAPSULE,
            serving_size="2 capsules",
        )
        repository.insert_label(label)
        retrieved = repository.get_label_by_id(label.id)
        assert retrieved.source_file is None

    def test_insert_label_with_empty_warnings(self, repository):
        """insert_label handles empty warnings list."""
        label = SupplementLabel(
            id=uuid4(),
            brand="NOW Foods",
            product_name="CoQ10",
            form=SupplementForm.SOFTGEL,
            serving_size="1 softgel",
            warnings=[],
        )
        repository.insert_label(label)
        retrieved = repository.get_label_by_id(label.id)
        assert retrieved.warnings == []

    def test_insert_label_with_multiple_warnings(self, repository):
        """insert_label handles multiple warnings."""
        label = SupplementLabel(
            id=uuid4(),
            brand="Life Extension",
            product_name="Super Omega",
            form=SupplementForm.SOFTGEL,
            serving_size="2 softgels",
            warnings=["Consult a physician", "Keep refrigerated", "Do not exceed dose"],
        )
        repository.insert_label(label)
        retrieved = repository.get_label_by_id(label.id)
        assert len(retrieved.warnings) == 3
        assert "Consult a physician" in retrieved.warnings


class TestInsertBlend:
    """Tests for insert_blend method."""

    def test_insert_blend_returns_model(self, repository, sample_label, sample_blend):
        """insert_blend returns the inserted ProprietaryBlend model."""
        repository.insert_label(sample_label)
        result = repository.insert_blend(sample_blend)
        assert isinstance(result, ProprietaryBlend)
        assert result.id == sample_blend.id
        assert result.name == sample_blend.name

    def test_insert_blend_persists_data(self, repository, sample_label, sample_blend):
        """insert_blend persists data to database."""
        repository.insert_label(sample_label)
        repository.insert_blend(sample_blend)
        # Verify by querying directly
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM proprietary_blends WHERE id = ?", (str(sample_blend.id),))
        row = cursor.fetchone()
        assert row is not None
        assert row["name"] == sample_blend.name
        assert row["supplement_label_id"] == str(sample_label.id)

    def test_insert_blend_with_null_amount(self, repository, sample_label):
        """insert_blend handles null total_amount and total_unit."""
        repository.insert_label(sample_label)
        blend = ProprietaryBlend(
            id=uuid4(),
            supplement_label_id=sample_label.id,
            name="Mystery Blend",
            total_amount=None,
            total_unit=None,
        )
        repository.insert_blend(blend)
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM proprietary_blends WHERE id = ?", (str(blend.id),))
        row = cursor.fetchone()
        assert row["total_amount"] is None
        assert row["total_unit"] is None


class TestInsertIngredient:
    """Tests for insert_ingredient method."""

    def test_insert_ingredient_returns_model(self, repository, sample_label, sample_ingredient):
        """insert_ingredient returns the inserted Ingredient model."""
        repository.insert_label(sample_label)
        result = repository.insert_ingredient(sample_ingredient)
        assert isinstance(result, Ingredient)
        assert result.id == sample_ingredient.id
        assert result.code == sample_ingredient.code

    def test_insert_ingredient_persists_data(self, repository, sample_label, sample_ingredient):
        """insert_ingredient persists data to database."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        retrieved = repository.get_ingredient_by_code(sample_ingredient.code)
        assert len(retrieved) == 1
        assert retrieved[0].id == sample_ingredient.id
        assert retrieved[0].name == sample_ingredient.name

    def test_insert_ingredient_with_blend_id(self, repository, sample_label, sample_blend):
        """insert_ingredient handles blend_id FK."""
        repository.insert_label(sample_label)
        repository.insert_blend(sample_blend)
        ingredient = Ingredient(
            id=uuid4(),
            supplement_label_id=None,
            blend_id=sample_blend.id,
            type=IngredientType.BLEND,
            name="Ashwagandha",
            code="ASHWAGANDHA",
            amount=100.0,
            unit="mg",
        )
        repository.insert_ingredient(ingredient)
        retrieved = repository.get_ingredient_by_code("ASHWAGANDHA")
        assert len(retrieved) == 1
        assert retrieved[0].blend_id == sample_blend.id
        assert retrieved[0].supplement_label_id is None

    def test_insert_ingredient_with_null_optional_fields(self, repository, sample_label):
        """insert_ingredient handles null optional fields."""
        repository.insert_label(sample_label)
        ingredient = Ingredient(
            id=uuid4(),
            supplement_label_id=sample_label.id,
            type=IngredientType.OTHER,
            name="Cellulose",
            code="MICROCRYSTALLINE_CELLULOSE",
            amount=None,
            unit=None,
            percent_dv=None,
            form=None,
        )
        repository.insert_ingredient(ingredient)
        retrieved = repository.get_ingredient_by_code("MICROCRYSTALLINE_CELLULOSE")
        assert len(retrieved) == 1
        assert retrieved[0].amount is None
        assert retrieved[0].unit is None
        assert retrieved[0].percent_dv is None
        assert retrieved[0].form is None


class TestGetLabelById:
    """Tests for get_label_by_id method."""

    def test_get_label_by_id_returns_model(self, repository, sample_label):
        """get_label_by_id returns SupplementLabel model."""
        repository.insert_label(sample_label)
        result = repository.get_label_by_id(sample_label.id)
        assert isinstance(result, SupplementLabel)

    def test_get_label_by_id_not_found_returns_none(self, repository):
        """get_label_by_id returns None when not found."""
        result = repository.get_label_by_id(uuid4())
        assert result is None

    def test_get_label_by_id_returns_correct_label(self, repository):
        """get_label_by_id returns the correct label when multiple exist."""
        label1 = SupplementLabel(
            id=uuid4(),
            brand="Thorne",
            product_name="Product 1",
            form=SupplementForm.CAPSULE,
            serving_size="1 cap",
        )
        label2 = SupplementLabel(
            id=uuid4(),
            brand="Pure",
            product_name="Product 2",
            form=SupplementForm.TABLET,
            serving_size="2 tabs",
        )
        repository.insert_label(label1)
        repository.insert_label(label2)
        result = repository.get_label_by_id(label2.id)
        assert result.brand == "Pure"
        assert result.product_name == "Product 2"


class TestGetIngredientByCode:
    """Tests for get_ingredient_by_code method."""

    def test_get_ingredient_by_code_returns_list(self, repository, sample_label, sample_ingredient):
        """get_ingredient_by_code returns a list."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        result = repository.get_ingredient_by_code(sample_ingredient.code)
        assert isinstance(result, list)

    def test_get_ingredient_by_code_returns_ingredient_models(self, repository, sample_label, sample_ingredient):
        """get_ingredient_by_code returns Ingredient models."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        result = repository.get_ingredient_by_code(sample_ingredient.code)
        assert len(result) == 1
        assert isinstance(result[0], Ingredient)

    def test_get_ingredient_by_code_returns_empty_list(self, repository):
        """get_ingredient_by_code returns empty list when no ingredients match."""
        result = repository.get_ingredient_by_code("UNKNOWN_CODE")
        assert result == []

    def test_get_ingredient_by_code_returns_multiple(self, repository):
        """get_ingredient_by_code returns all ingredients with same code from different labels."""
        label1 = SupplementLabel(
            id=uuid4(),
            brand="Thorne",
            product_name="Vitamin D-5000",
            form=SupplementForm.CAPSULE,
            serving_size="1 cap",
        )
        label2 = SupplementLabel(
            id=uuid4(),
            brand="Pure",
            product_name="Vitamin D3",
            form=SupplementForm.SOFTGEL,
            serving_size="1 softgel",
        )
        repository.insert_label(label1)
        repository.insert_label(label2)

        ingredient1 = Ingredient(
            id=uuid4(),
            supplement_label_id=label1.id,
            type=IngredientType.ACTIVE,
            name="Vitamin D3",
            code="VITAMIN_D3",
            amount=5000.0,
            unit="IU",
        )
        ingredient2 = Ingredient(
            id=uuid4(),
            supplement_label_id=label2.id,
            type=IngredientType.ACTIVE,
            name="Vitamin D3",
            code="VITAMIN_D3",
            amount=2000.0,
            unit="IU",
        )
        repository.insert_ingredient(ingredient1)
        repository.insert_ingredient(ingredient2)

        result = repository.get_ingredient_by_code("VITAMIN_D3")
        assert len(result) == 2


class TestSearchLabels:
    """Tests for search_labels method."""

    def test_search_labels_returns_list(self, repository, sample_label):
        """search_labels returns a list."""
        repository.insert_label(sample_label)
        result = repository.search_labels("Thorne")
        assert isinstance(result, list)

    def test_search_labels_returns_label_models(self, repository, sample_label):
        """search_labels returns SupplementLabel models."""
        repository.insert_label(sample_label)
        result = repository.search_labels("Thorne")
        assert len(result) == 1
        assert isinstance(result[0], SupplementLabel)

    def test_search_labels_returns_empty_list(self, repository):
        """search_labels returns empty list when no matches."""
        result = repository.search_labels("NonexistentBrand")
        assert result == []

    def test_search_labels_matches_brand(self, repository):
        """search_labels matches on brand."""
        label = SupplementLabel(
            id=uuid4(),
            brand="Pure Encapsulations",
            product_name="CoQ10",
            form=SupplementForm.CAPSULE,
            serving_size="1 cap",
        )
        repository.insert_label(label)
        result = repository.search_labels("Pure")
        assert len(result) == 1
        assert result[0].brand == "Pure Encapsulations"

    def test_search_labels_matches_product_name(self, repository):
        """search_labels matches on product_name."""
        label = SupplementLabel(
            id=uuid4(),
            brand="NOW Foods",
            product_name="Super Omega-3",
            form=SupplementForm.SOFTGEL,
            serving_size="2 softgels",
        )
        repository.insert_label(label)
        result = repository.search_labels("Omega")
        assert len(result) == 1
        assert result[0].product_name == "Super Omega-3"

    def test_search_labels_case_insensitive(self, repository):
        """search_labels is case insensitive."""
        label = SupplementLabel(
            id=uuid4(),
            brand="Life Extension",
            product_name="Super K",
            form=SupplementForm.SOFTGEL,
            serving_size="1 softgel",
        )
        repository.insert_label(label)
        result = repository.search_labels("life extension")
        assert len(result) == 1

    def test_search_labels_partial_match(self, repository):
        """search_labels matches partial strings."""
        label = SupplementLabel(
            id=uuid4(),
            brand="Jarrow Formulas",
            product_name="Curcumin 95",
            form=SupplementForm.CAPSULE,
            serving_size="1 cap",
        )
        repository.insert_label(label)
        result = repository.search_labels("Curc")
        assert len(result) == 1

    def test_search_labels_returns_multiple(self, repository):
        """search_labels returns multiple matching labels."""
        label1 = SupplementLabel(
            id=uuid4(),
            brand="Thorne",
            product_name="Vitamin D-5000",
            form=SupplementForm.CAPSULE,
            serving_size="1 cap",
        )
        label2 = SupplementLabel(
            id=uuid4(),
            brand="Thorne",
            product_name="Basic Nutrients",
            form=SupplementForm.CAPSULE,
            serving_size="4 caps",
        )
        label3 = SupplementLabel(
            id=uuid4(),
            brand="Pure Encapsulations",
            product_name="Multi",
            form=SupplementForm.CAPSULE,
            serving_size="3 caps",
        )
        repository.insert_label(label1)
        repository.insert_label(label2)
        repository.insert_label(label3)

        result = repository.search_labels("Thorne")
        assert len(result) == 2

    def test_search_labels_matches_either_brand_or_product(self, repository):
        """search_labels matches if term appears in brand OR product_name."""
        label1 = SupplementLabel(
            id=uuid4(),
            brand="Omega Labs",
            product_name="Fish Oil",
            form=SupplementForm.SOFTGEL,
            serving_size="1 softgel",
        )
        label2 = SupplementLabel(
            id=uuid4(),
            brand="Nordic Naturals",
            product_name="Omega-3 Complete",
            form=SupplementForm.SOFTGEL,
            serving_size="2 softgels",
        )
        repository.insert_label(label1)
        repository.insert_label(label2)

        result = repository.search_labels("Omega")
        assert len(result) == 2


class TestEdgeCases:
    """Edge case tests."""

    def test_uuid_roundtrip(self, repository, sample_label):
        """UUIDs are correctly stored and retrieved."""
        repository.insert_label(sample_label)
        retrieved = repository.get_label_by_id(sample_label.id)
        assert isinstance(retrieved.id, UUID)
        assert retrieved.id == sample_label.id

    def test_datetime_roundtrip(self, repository):
        """Datetimes are correctly stored and retrieved."""
        label = SupplementLabel(
            id=uuid4(),
            brand="Test",
            product_name="Test Product",
            form=SupplementForm.CAPSULE,
            serving_size="1 cap",
            created_at=datetime(2021, 1, 1, 12, 30, 45),
        )
        repository.insert_label(label)
        retrieved = repository.get_label_by_id(label.id)
        assert isinstance(retrieved.created_at, datetime)
        assert retrieved.created_at == datetime(2021, 1, 1, 12, 30, 45)

    def test_float_value_roundtrip(self, repository, sample_label, sample_ingredient):
        """Float values are correctly stored and retrieved."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        retrieved = repository.get_ingredient_by_code(sample_ingredient.code)
        assert retrieved[0].amount == pytest.approx(5000.0)
        assert retrieved[0].percent_dv == pytest.approx(1250.0)

    def test_supplement_form_enum_roundtrip(self, repository):
        """SupplementForm enum is correctly stored and retrieved."""
        for form in SupplementForm:
            label = SupplementLabel(
                id=uuid4(),
                brand="Test",
                product_name=f"Test {form.value}",
                form=form,
                serving_size="1 serving",
            )
            repository.insert_label(label)
            retrieved = repository.get_label_by_id(label.id)
            assert retrieved.form == form

    def test_ingredient_type_enum_roundtrip(self, repository, sample_label):
        """IngredientType enum is correctly stored and retrieved."""
        repository.insert_label(sample_label)
        for ing_type in IngredientType:
            ingredient = Ingredient(
                id=uuid4(),
                supplement_label_id=sample_label.id,
                type=ing_type,
                name=f"Test {ing_type.value}",
                code="VITAMIN_D3",
            )
            repository.insert_ingredient(ingredient)
            retrieved = repository.get_ingredient_by_code("VITAMIN_D3")
            matching = [i for i in retrieved if i.id == ingredient.id][0]
            assert matching.type == ing_type

    def test_special_characters_in_search(self, repository):
        """search_labels handles special characters."""
        label = SupplementLabel(
            id=uuid4(),
            brand="Nature's Way",
            product_name="Vitamin B-12 (1000mcg)",
            form=SupplementForm.LOZENGE,
            serving_size="1 lozenge",
        )
        repository.insert_label(label)
        result = repository.search_labels("Nature's")
        assert len(result) == 1

    def test_empty_search_term(self, repository, sample_label):
        """search_labels with empty string returns all labels."""
        repository.insert_label(sample_label)
        label2 = SupplementLabel(
            id=uuid4(),
            brand="Pure",
            product_name="Product",
            form=SupplementForm.CAPSULE,
            serving_size="1 cap",
        )
        repository.insert_label(label2)
        result = repository.search_labels("")
        assert len(result) == 2
