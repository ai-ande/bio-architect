"""Validators for bloodwork data."""

from typing import Annotated

from pydantic import AfterValidator

from src.databases.datatypes.validators import load_codes_from_yaml, validate_code

VALID_BIOMARKER_CODES: set[str] = load_codes_from_yaml("biomarker_codes.yaml")


def validate_biomarker_code(v: str) -> str:
    """Validate biomarker code format and existence in YAML.

    Raises:
        ValueError: If code format is invalid or code is not in biomarker_codes.yaml.
    """
    v = validate_code(v)
    if v not in VALID_BIOMARKER_CODES:
        raise ValueError(f"unknown biomarker code: {v}")
    return v


# Annotated type for use in Pydantic models
BiomarkerCode = Annotated[str, AfterValidator(validate_biomarker_code)]
