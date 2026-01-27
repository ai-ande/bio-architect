"""Validators for bloodwork data."""

from src.databases.datatypes.validators import Code, load_codes_from_yaml

VALID_BIOMARKER_CODES: set[str] = load_codes_from_yaml("biomarker_codes.yaml")

# Alias for semantic clarity
BiomarkerCode = Code
