"""Shared validators for database datatypes using Pydantic Annotated types."""

import re
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import AfterValidator

# Pattern for valid codes: uppercase letters, numbers, and underscores
CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def load_codes_from_yaml(yaml_filename: str) -> set[str]:
    """Load valid codes from a normalization YAML file.

    Args:
        yaml_filename: Name of the YAML file in data/public/normalization/

    Returns:
        Set of valid codes from the YAML file.
    """
    yaml_path = Path(__file__).parents[3] / f"data/public/normalization/{yaml_filename}"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    codes: set[str] = set()
    for category, items in data.items():
        if category.startswith("_"):
            continue
        for code in items.keys():
            codes.add(code)
    return codes


def validate_code(v: str) -> str:
    """Validate code format (uppercase, no spaces, valid characters).

    Raises:
        ValueError: If code is empty, contains spaces, is not uppercase,
            or contains invalid characters.
    """
    if not v:
        raise ValueError("code cannot be empty")
    if " " in v:
        raise ValueError("code must not contain spaces")
    if v != v.upper():
        raise ValueError("code must be uppercase")
    if not CODE_PATTERN.match(v):
        raise ValueError(
            "code contains invalid characters (only uppercase letters, numbers, and underscores allowed)"
        )
    return v


# Annotated type for use in Pydantic models
Code = Annotated[str, AfterValidator(validate_code)]
