"""Tests for supplements CLI script."""

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.supplements import (
    blend_to_dict,
    cmd_ingredient,
    cmd_label,
    cmd_list,
    cmd_search,
    create_parser,
    format_ingredient,
    format_label,
    ingredient_to_dict,
    label_to_dict,
    main,
)
from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement import (
    Ingredient,
    IngredientType,
    ProprietaryBlend,
    SupplementForm,
    SupplementLabel,
)
from src.databases.repositories.supplement import SupplementRepository


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_parser_has_json_flag(self):
        """Parser accepts --json flag."""
        parser = create_parser()
        args = parser.parse_args(["--json", "list"])
        assert args.json is True

    def test_parser_json_default_false(self):
        """Parser --json defaults to False."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.json is False

    def test_parser_list_command(self):
        """Parser recognizes list command."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_parser_label_command_requires_id(self):
        """Parser label command requires id argument."""
        parser = create_parser()
        args = parser.parse_args(["label", "123e4567-e89b-12d3-a456-426614174000"])
        assert args.command == "label"
        assert args.id == "123e4567-e89b-12d3-a456-426614174000"

    def test_parser_label_command_missing_id_fails(self):
        """Parser label command fails without id."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["label"])

    def test_parser_ingredient_command_requires_code(self):
        """Parser ingredient command requires code argument."""
        parser = create_parser()
        args = parser.parse_args(["ingredient", "VITAMIN_D3"])
        assert args.command == "ingredient"
        assert args.code == "VITAMIN_D3"

    def test_parser_ingredient_command_missing_code_fails(self):
        """Parser ingredient command fails without code."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ingredient"])

    def test_parser_search_command_requires_term(self):
        """Parser search command requires term argument."""
        parser = create_parser()
        args = parser.parse_args(["search", "Thorne"])
        assert args.command == "search"
        assert args.term == "Thorne"

    def test_parser_search_command_missing_term_fails(self):
        """Parser search command fails without term."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["search"])

    def test_parser_no_command_returns_none(self):
        """Parser returns None for command when no command given."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestFormatFunctions:
    """Tests for format helper functions."""

    def test_format_label(self):
        """format_label includes all fields."""
        label = SupplementLabel(
            id=uuid4(),
            brand="Thorne",
            product_name="Vitamin D3",
            form=SupplementForm.CAPSULE,
            serving_size="1 capsule",
        )
        result = format_label(label)
        assert str(label.id) in result
        assert "Thorne" in result
        assert "Vitamin D3" in result
        assert "capsule" in result

    def test_format_ingredient(self):
        """format_ingredient includes all fields."""
        ingredient = Ingredient(
            id=uuid4(),
            supplement_label_id=uuid4(),
            type=IngredientType.ACTIVE,
            name="Vitamin D3",
            code="VITAMIN_D3",
            amount=1000.0,
            unit="IU",
            percent_dv=250.0,
        )
        result = format_ingredient(ingredient)
        assert "Vitamin D3" in result
        assert "1000.0" in result
        assert "IU" in result
        assert "250%" in result
        assert "active" in result

    def test_format_ingredient_no_amount(self):
        """format_ingredient handles missing amount."""
        ingredient = Ingredient(
            id=uuid4(),
            supplement_label_id=uuid4(),
            type=IngredientType.OTHER,
            name="Gelatin",
            code="GELATIN",
            amount=None,
            unit=None,
            percent_dv=None,
        )
        result = format_ingredient(ingredient)
        assert "Gelatin" in result
        assert "-" in result


class TestToDictFunctions:
    """Tests for JSON serialization functions."""

    def test_label_to_dict(self):
        """label_to_dict returns JSON-serializable dict."""
        label_id = uuid4()
        label = SupplementLabel(
            id=label_id,
            source_file="supplement.pdf",
            created_at=datetime(2024, 1, 20, 10, 30, 0),
            brand="Thorne",
            product_name="Vitamin D3",
            form=SupplementForm.CAPSULE,
            serving_size="1 capsule",
            servings_per_container=60,
            suggested_use="Take 1 capsule daily",
            warnings=["Keep out of reach of children"],
            allergen_info="Contains soy",
        )
        result = label_to_dict(label)
        assert result["id"] == str(label_id)
        assert result["brand"] == "Thorne"
        assert result["product_name"] == "Vitamin D3"
        assert result["form"] == "capsule"
        assert result["serving_size"] == "1 capsule"
        assert result["servings_per_container"] == 60
        assert result["suggested_use"] == "Take 1 capsule daily"
        assert result["warnings"] == ["Keep out of reach of children"]
        assert result["allergen_info"] == "Contains soy"
        assert result["created_at"] == "2024-01-20T10:30:00"
        # Verify it's JSON serializable
        json.dumps(result)

    def test_ingredient_to_dict(self):
        """ingredient_to_dict returns JSON-serializable dict."""
        ingredient_id = uuid4()
        label_id = uuid4()
        ingredient = Ingredient(
            id=ingredient_id,
            supplement_label_id=label_id,
            type=IngredientType.ACTIVE,
            name="Vitamin D3",
            code="VITAMIN_D3",
            amount=1000.0,
            unit="IU",
            percent_dv=250.0,
            form="cholecalciferol",
        )
        result = ingredient_to_dict(ingredient)
        assert result["id"] == str(ingredient_id)
        assert result["supplement_label_id"] == str(label_id)
        assert result["blend_id"] is None
        assert result["type"] == "active"
        assert result["name"] == "Vitamin D3"
        assert result["code"] == "VITAMIN_D3"
        assert result["amount"] == 1000.0
        assert result["unit"] == "IU"
        assert result["percent_dv"] == 250.0
        assert result["form"] == "cholecalciferol"
        # Verify it's JSON serializable
        json.dumps(result)

    def test_blend_to_dict(self):
        """blend_to_dict returns JSON-serializable dict."""
        blend_id = uuid4()
        label_id = uuid4()
        blend = ProprietaryBlend(
            id=blend_id,
            supplement_label_id=label_id,
            name="Energy Blend",
            total_amount=500.0,
            total_unit="mg",
        )
        result = blend_to_dict(blend)
        assert result["id"] == str(blend_id)
        assert result["supplement_label_id"] == str(label_id)
        assert result["name"] == "Energy Blend"
        assert result["total_amount"] == 500.0
        assert result["total_unit"] == "mg"
        # Verify it's JSON serializable
        json.dumps(result)


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
        product_name="Vitamin D3",
        form=SupplementForm.CAPSULE,
        serving_size="1 capsule",
        servings_per_container=60,
        suggested_use="Take 1 capsule daily",
        warnings=["Keep out of reach of children"],
        allergen_info="Contains soy",
    )


@pytest.fixture
def sample_ingredient(sample_label):
    """Create a sample Ingredient."""
    return Ingredient(
        id=uuid4(),
        supplement_label_id=sample_label.id,
        type=IngredientType.ACTIVE,
        name="Vitamin D3",
        code="VITAMIN_D3",
        amount=1000.0,
        unit="IU",
        percent_dv=250.0,
        form="cholecalciferol",
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


class TestCmdList:
    """Tests for list command."""

    def test_cmd_list_empty(self, repository, capsys):
        """cmd_list handles empty database."""
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "No supplement labels found" in captured.out

    def test_cmd_list_with_labels(self, repository, sample_label, capsys):
        """cmd_list shows labels."""
        repository.insert_label(sample_label)
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "Thorne" in captured.out
        assert "Vitamin D3" in captured.out

    def test_cmd_list_json(self, repository, sample_label, capsys):
        """cmd_list outputs valid JSON."""
        repository.insert_label(sample_label)
        args = argparse.Namespace(json=True)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["brand"] == "Thorne"


class TestCmdLabel:
    """Tests for label command."""

    def test_cmd_label_found(self, repository, sample_label, sample_ingredient, capsys):
        """cmd_label shows label details."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        args = argparse.Namespace(json=False, id=str(sample_label.id))
        cmd_label(repository, args)
        captured = capsys.readouterr()
        assert "Thorne" in captured.out
        assert "Vitamin D3" in captured.out
        assert "1 capsule" in captured.out

    def test_cmd_label_not_found(self, repository, capsys):
        """cmd_label exits with error when not found."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"
        args = argparse.Namespace(json=False, id=fake_id)
        with pytest.raises(SystemExit) as exc_info:
            cmd_label(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Label not found" in captured.err

    def test_cmd_label_invalid_id(self, repository, capsys):
        """cmd_label exits with error for invalid UUID."""
        args = argparse.Namespace(json=False, id="not-a-uuid")
        with pytest.raises(SystemExit) as exc_info:
            cmd_label(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid label ID" in captured.err

    def test_cmd_label_json(self, repository, sample_label, sample_ingredient, capsys):
        """cmd_label outputs valid JSON."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        args = argparse.Namespace(json=True, id=str(sample_label.id))
        cmd_label(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["brand"] == "Thorne"
        assert len(data["ingredients"]) == 1
        assert data["ingredients"][0]["name"] == "Vitamin D3"

    def test_cmd_label_with_blend(self, repository, sample_label, sample_blend, capsys):
        """cmd_label shows blends and their ingredients."""
        repository.insert_label(sample_label)
        repository.insert_blend(sample_blend)
        blend_ingredient = Ingredient(
            id=uuid4(),
            blend_id=sample_blend.id,
            type=IngredientType.BLEND,
            name="Ashwagandha",
            code="ASHWAGANDHA",
            amount=100.0,
            unit="mg",
        )
        repository.insert_ingredient(blend_ingredient)
        args = argparse.Namespace(json=False, id=str(sample_label.id))
        cmd_label(repository, args)
        captured = capsys.readouterr()
        assert "Energy Blend" in captured.out
        assert "Ashwagandha" in captured.out


class TestCmdIngredient:
    """Tests for ingredient command."""

    def test_cmd_ingredient_found(self, repository, sample_label, sample_ingredient, capsys):
        """cmd_ingredient shows labels containing ingredient."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        args = argparse.Namespace(json=False, code="VITAMIN_D3")
        cmd_ingredient(repository, args)
        captured = capsys.readouterr()
        assert "Thorne" in captured.out
        assert "Vitamin D3" in captured.out
        assert "1000.0" in captured.out

    def test_cmd_ingredient_not_found(self, repository, capsys):
        """cmd_ingredient shows message when not found."""
        args = argparse.Namespace(json=False, code="NONEXISTENT")
        cmd_ingredient(repository, args)
        captured = capsys.readouterr()
        assert "No supplements found" in captured.out

    def test_cmd_ingredient_json(self, repository, sample_label, sample_ingredient, capsys):
        """cmd_ingredient outputs valid JSON."""
        repository.insert_label(sample_label)
        repository.insert_ingredient(sample_ingredient)
        args = argparse.Namespace(json=True, code="VITAMIN_D3")
        cmd_ingredient(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["code"] == "VITAMIN_D3"


class TestCmdSearch:
    """Tests for search command."""

    def test_cmd_search_found_by_brand(self, repository, sample_label, capsys):
        """cmd_search finds labels by brand."""
        repository.insert_label(sample_label)
        args = argparse.Namespace(json=False, term="Thorne")
        cmd_search(repository, args)
        captured = capsys.readouterr()
        assert "Thorne" in captured.out
        assert "Vitamin D3" in captured.out

    def test_cmd_search_found_by_product(self, repository, sample_label, capsys):
        """cmd_search finds labels by product name."""
        repository.insert_label(sample_label)
        args = argparse.Namespace(json=False, term="Vitamin")
        cmd_search(repository, args)
        captured = capsys.readouterr()
        assert "Thorne" in captured.out
        assert "Vitamin D3" in captured.out

    def test_cmd_search_not_found(self, repository, capsys):
        """cmd_search shows message when not found."""
        args = argparse.Namespace(json=False, term="Nonexistent")
        cmd_search(repository, args)
        captured = capsys.readouterr()
        assert "No supplements found matching" in captured.out

    def test_cmd_search_json(self, repository, sample_label, capsys):
        """cmd_search outputs valid JSON."""
        repository.insert_label(sample_label)
        args = argparse.Namespace(json=True, term="Thorne")
        cmd_search(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["brand"] == "Thorne"


class TestMain:
    """Tests for main entry point."""

    def test_main_no_command_shows_help(self, capsys):
        """main shows help when no command given."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1

    def test_main_help_flag(self, capsys):
        """main responds to --help flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()
