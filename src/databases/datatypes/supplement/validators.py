"""Validators for supplement label data."""

from typing import Annotated

from pydantic import AfterValidator

from src.databases.datatypes.validators import load_codes_from_yaml, validate_code

VALID_INGREDIENT_CODES: set[str] = load_codes_from_yaml("ingredient_codes.yaml")


def validate_ingredient_code(v: str) -> str:
    """Validate ingredient code format and existence in YAML.

    Raises:
        ValueError: If code format is invalid or code is not in ingredient_codes.yaml.
    """
    v = validate_code(v)
    if v not in VALID_INGREDIENT_CODES:
        raise ValueError(f"unknown ingredient code: {v}")
    return v


# Annotated type for use in Pydantic models
IngredientCode = Annotated[str, AfterValidator(validate_ingredient_code)]
