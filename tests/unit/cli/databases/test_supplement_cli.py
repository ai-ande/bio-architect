"""Tests for supplement CLI import command."""

import argparse
import json
from io import StringIO

import pytest
from pydantic import ValidationError
from sqlmodel import select

from cli.databases.supplement import cmd_import, parse_supplement_json
from src.databases.datatypes.supplement import (
    Ingredient,
    IngredientType,
    ProprietaryBlend,
    SupplementForm,
    SupplementLabel,
)


class TestParseSupplementJson:
    """Tests for parse_supplement_json function."""

    def test_parse_creates_supplement_label(self):
        """Parse should create a SupplementLabel with correct fields."""
        data = {
            "brand": "Thorne",
            "product_name": "Zinc Picolinate",
            "form": "capsule",
            "serving_size": "1 capsule",
            "servings_per_container": 60,
            "suggested_use": "Take 1 capsule daily",
            "active_ingredients": [],
            "other_ingredients": [],
            "proprietary_blends": [],
            "warnings": ["Keep out of reach of children"],
            "allergen_info": None,
        }
        label, blends, ingredients = parse_supplement_json(data, "test.json")

        assert label.brand == "Thorne"
        assert label.product_name == "Zinc Picolinate"
        assert label.form == SupplementForm.CAPSULE
        assert label.serving_size == "1 capsule"
        assert label.servings_per_container == 60
        assert label.suggested_use == "Take 1 capsule daily"
        assert label.warnings == ["Keep out of reach of children"]
        assert label.source_file == "test.json"

    def test_parse_creates_active_ingredients(self):
        """Parse should create Ingredient records for active ingredients."""
        data = {
            "brand": "Thorne",
            "product_name": "Zinc Picolinate",
            "form": "capsule",
            "serving_size": "1 capsule",
            "active_ingredients": [
                {
                    "name": "Zinc (as Zinc Picolinate)",
                    "code": "ZINC",
                    "amount": 30.0,
                    "unit": "mg",
                    "percent_dv": 273,
                    "form": "Zinc Picolinate",
                },
            ],
            "other_ingredients": [],
            "proprietary_blends": [],
        }
        label, blends, ingredients = parse_supplement_json(data, None)

        assert len(ingredients) == 1
        assert ingredients[0].name == "Zinc (as Zinc Picolinate)"
        assert ingredients[0].code == "ZINC"
        assert ingredients[0].amount == 30.0
        assert ingredients[0].unit == "mg"
        assert ingredients[0].percent_dv == 273
        assert ingredients[0].form == "Zinc Picolinate"
        assert ingredients[0].type == IngredientType.ACTIVE
        assert ingredients[0].supplement_label_id == label.id
        assert ingredients[0].blend_id is None

    def test_parse_creates_other_ingredients(self):
        """Parse should create Ingredient records for other ingredients."""
        data = {
            "brand": "Thorne",
            "product_name": "Zinc Picolinate",
            "form": "capsule",
            "serving_size": "1 capsule",
            "active_ingredients": [],
            "other_ingredients": [
                {"name": "Hypromellose", "code": "HYPROMELLOSE"},
                {"name": "Silicon Dioxide", "code": "SILICON_DIOXIDE"},
            ],
            "proprietary_blends": [],
        }
        label, blends, ingredients = parse_supplement_json(data, None)

        assert len(ingredients) == 2
        assert all(i.type == IngredientType.OTHER for i in ingredients)
        assert ingredients[0].code == "HYPROMELLOSE"
        assert ingredients[0].supplement_label_id == label.id

    def test_parse_creates_proprietary_blends(self):
        """Parse should create ProprietaryBlend and linked ingredients."""
        data = {
            "brand": "Thorne",
            "product_name": "Adrenal Support",
            "form": "capsule",
            "serving_size": "1 capsule",
            "active_ingredients": [],
            "other_ingredients": [],
            "proprietary_blends": [
                {
                    "name": "Adrenal Support Blend",
                    "total_amount": 500,
                    "total_unit": "mg",
                    "ingredients": [
                        {"name": "Ashwagandha Extract", "code": "ASHWAGANDHA"},
                    ],
                },
            ],
        }
        label, blends, ingredients = parse_supplement_json(data, None)

        assert len(blends) == 1
        assert blends[0].name == "Adrenal Support Blend"
        assert blends[0].total_amount == 500
        assert blends[0].total_unit == "mg"
        assert blends[0].supplement_label_id == label.id

        assert len(ingredients) == 1
        assert ingredients[0].type == IngredientType.BLEND
        assert ingredients[0].blend_id == blends[0].id
        assert ingredients[0].supplement_label_id is None

    def test_parse_rejects_invalid_ingredient_code(self):
        """Parse should reject invalid ingredient codes."""
        data = {
            "brand": "Thorne",
            "product_name": "Test Product",
            "form": "capsule",
            "serving_size": "1 capsule",
            "active_ingredients": [
                {"name": "Invalid", "code": "NOT_A_VALID_CODE", "amount": 100.0, "unit": "mg"},
            ],
            "other_ingredients": [],
            "proprietary_blends": [],
        }
        with pytest.raises(ValidationError, match="unknown ingredient code"):
            parse_supplement_json(data, None)


class TestSupplementImport:
    """Tests for supplement import command."""

    @pytest.fixture
    def sample_json(self):
        """Sample valid supplement JSON."""
        return {
            "brand": "Thorne",
            "product_name": "Zinc Picolinate",
            "form": "capsule",
            "serving_size": "1 capsule",
            "servings_per_container": 60,
            "suggested_use": "Take 1 capsule daily",
            "active_ingredients": [
                {
                    "name": "Zinc (as Zinc Picolinate)",
                    "code": "ZINC",
                    "amount": 30.0,
                    "unit": "mg",
                    "percent_dv": 273,
                    "form": "Zinc Picolinate",
                },
            ],
            "other_ingredients": [
                {"name": "Hypromellose", "code": "HYPROMELLOSE"},
            ],
            "proprietary_blends": [],
            "warnings": ["Keep out of reach of children"],
            "allergen_info": None,
        }

    def test_import_creates_supplement_label(self, tmp_path, db_session, sample_json):
        """Import should create a SupplementLabel record."""
        json_file = tmp_path / "supplement.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        labels = db_session.exec(select(SupplementLabel)).all()
        assert len(labels) == 1
        assert labels[0].brand == "Thorne"
        assert labels[0].product_name == "Zinc Picolinate"

    def test_import_creates_ingredients(self, tmp_path, db_session, sample_json):
        """Import should create Ingredient records."""
        json_file = tmp_path / "supplement.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        ingredients = db_session.exec(select(Ingredient)).all()
        assert len(ingredients) == 2
        codes = {i.code for i in ingredients}
        assert codes == {"ZINC", "HYPROMELLOSE"}

    def test_import_creates_blends(self, tmp_path, db_session):
        """Import should create ProprietaryBlend records."""
        data = {
            "brand": "Test",
            "product_name": "Blend Product",
            "form": "capsule",
            "serving_size": "1 capsule",
            "active_ingredients": [],
            "other_ingredients": [],
            "proprietary_blends": [
                {
                    "name": "Test Blend",
                    "total_amount": 500,
                    "total_unit": "mg",
                    "ingredients": [
                        {"name": "Ingredient A", "code": "ASHWAGANDHA"},
                    ],
                },
            ],
        }
        json_file = tmp_path / "blend.json"
        json_file.write_text(json.dumps(data))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        blends = db_session.exec(select(ProprietaryBlend)).all()
        assert len(blends) == 1
        assert blends[0].name == "Test Blend"

    def test_import_sets_source_file(self, tmp_path, db_session, sample_json):
        """Import should set source_file to the input file path."""
        json_file = tmp_path / "supplement.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        label = db_session.exec(select(SupplementLabel)).first()
        assert label.source_file == str(json_file)

    def test_import_from_stdin(self, db_session, sample_json, monkeypatch):
        """Import should read from stdin when no file provided."""
        stdin_data = json.dumps(sample_json)
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))

        args = argparse.Namespace(file=None, json=False)
        cmd_import(db_session, args)

        labels = db_session.exec(select(SupplementLabel)).all()
        assert len(labels) == 1
        assert labels[0].source_file is None

    def test_import_json_output(self, tmp_path, db_session, sample_json, capsys):
        """Import with --json should return structured output."""
        json_file = tmp_path / "supplement.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=True)
        cmd_import(db_session, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert "supplement_label_id" in result
        assert result["ingredients_created"] == 2
        assert result["blends_created"] == 0

    def test_import_invalid_json_exits_with_error(self, tmp_path, db_session):
        """Import should exit with error for invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json {{{")

        args = argparse.Namespace(file=str(json_file), json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1

    def test_import_missing_required_fields_exits_with_error(self, tmp_path, db_session):
        """Import should exit with error for missing required fields."""
        json_file = tmp_path / "incomplete.json"
        json_file.write_text(json.dumps({"brand": "Test"}))  # Missing required fields

        args = argparse.Namespace(file=str(json_file), json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1

    def test_import_no_partial_records_on_validation_error(self, tmp_path, db_client):
        """Import should not leave partial records if validation fails."""
        # First ingredient valid, second has invalid code
        data = {
            "brand": "Test",
            "product_name": "Test Product",
            "form": "capsule",
            "serving_size": "1 capsule",
            "active_ingredients": [
                {"name": "Zinc", "code": "ZINC", "amount": 30.0, "unit": "mg"},
                {"name": "Invalid", "code": "NOT_VALID_CODE", "amount": 100.0, "unit": "mg"},
            ],
            "other_ingredients": [],
            "proprietary_blends": [],
        }
        json_file = tmp_path / "partial.json"
        json_file.write_text(json.dumps(data))

        with db_client.get_session() as session:
            args = argparse.Namespace(file=str(json_file), json=False)
            with pytest.raises(SystemExit):
                cmd_import(session, args)

        # Verify no partial data was inserted
        with db_client.get_session() as session:
            labels = session.exec(select(SupplementLabel)).all()
            ingredients = session.exec(select(Ingredient)).all()
            assert len(labels) == 0
            assert len(ingredients) == 0

    def test_import_file_not_found_exits_with_error(self, db_session):
        """Import should exit with error for non-existent file."""
        args = argparse.Namespace(file="/nonexistent/path.json", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1
