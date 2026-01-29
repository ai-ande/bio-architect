"""Tests for SupplementRepository."""

from uuid import uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement import (
    Ingredient,
    IngredientType,
    ProprietaryBlend,
    SupplementForm,
    SupplementLabel,
)
from src.databases.datatypes.supplement.repository import SupplementRepository


@pytest.fixture
def db_client(tmp_path):
    """Create a test database client with schema initialized."""
    db_path = tmp_path / "test.db"
    client = DatabaseClient(db_path=db_path)
    client.init_schema()
    yield client
    client.close()


@pytest.fixture
def db_session(db_client):
    """Create a database session for testing."""
    with db_client.get_session() as session:
        yield session


@pytest.fixture
def repo(db_session):
    """Create a SupplementRepository instance."""
    return SupplementRepository(db_session)


@pytest.fixture
def sample_label(db_session) -> SupplementLabel:
    """Create a sample supplement label with ingredients."""
    label = SupplementLabel(
        brand="TestBrand",
        product_name="Vitamin D3",
        form=SupplementForm.CAPSULE,
        serving_size="1 capsule",
        source_file="test.json",
    )
    db_session.add(label)
    db_session.flush()

    ingredient = Ingredient(
        supplement_label_id=label.id,
        type=IngredientType.ACTIVE,
        name="Vitamin D3",
        code="VITAMIN_D3",
        amount=5000.0,
        unit="IU",
    )
    db_session.add(ingredient)
    db_session.commit()

    return label


class TestListLabels:
    """Tests for list_labels method."""

    def test_returns_empty_when_no_labels(self, repo):
        """Should return empty list when no labels exist."""
        labels = repo.list_labels()
        assert labels == []

    def test_returns_all_labels(self, repo, sample_label):
        """Should return all supplement labels."""
        labels = repo.list_labels()
        assert len(labels) == 1
        assert labels[0].id == sample_label.id


class TestGetLabel:
    """Tests for get_label method."""

    def test_returns_label_by_id(self, repo, sample_label):
        """Should return label when found."""
        label = repo.get_label(sample_label.id)
        assert label is not None
        assert label.id == sample_label.id

    def test_returns_none_when_not_found(self, repo):
        """Should return None when label not found."""
        label = repo.get_label(uuid4())
        assert label is None


class TestGetIngredientsByCode:
    """Tests for get_ingredients_by_code method."""

    def test_returns_ingredients_with_code(self, repo, sample_label):
        """Should return ingredients matching code."""
        ingredients = repo.get_ingredients_by_code("VITAMIN_D3")
        assert len(ingredients) == 1
        assert ingredients[0].code == "VITAMIN_D3"

    def test_returns_empty_when_code_not_found(self, repo):
        """Should return empty list when code not found."""
        ingredients = repo.get_ingredients_by_code("NONEXISTENT")
        assert ingredients == []


class TestSearchLabels:
    """Tests for search_labels method."""

    def test_finds_by_brand(self, repo, sample_label):
        """Should find labels matching brand."""
        labels = repo.search_labels("TestBrand")
        assert len(labels) == 1
        assert labels[0].brand == "TestBrand"

    def test_finds_by_product_name(self, repo, sample_label):
        """Should find labels matching product name."""
        labels = repo.search_labels("Vitamin")
        assert len(labels) == 1

    def test_returns_empty_when_no_match(self, repo, sample_label):
        """Should return empty list when no match."""
        labels = repo.search_labels("nonexistent")
        assert labels == []


class TestSaveLabel:
    """Tests for save_label method."""

    def test_saves_label_with_ingredients(self, repo):
        """Should save label and ingredients atomically."""
        label = SupplementLabel(
            brand="NewBrand",
            product_name="New Product",
            form=SupplementForm.TABLET,
            serving_size="1 tablet",
        )
        ingredient = Ingredient(
            supplement_label_id=label.id,
            type=IngredientType.ACTIVE,
            name="Zinc",
            code="ZINC",
            amount=15.0,
            unit="mg",
        )

        repo.save_label(label, [], [ingredient])

        saved = repo.get_label(label.id)
        assert saved is not None
        assert saved.brand == "NewBrand"

        ingredients = repo.get_ingredients_for_label(label.id)
        assert len(ingredients) == 1
