"""Validators for supplement label data."""

from src.databases.datatypes.validators import Code, load_codes_from_yaml

VALID_INGREDIENT_CODES: set[str] = load_codes_from_yaml("ingredient_codes.yaml")

# Alias for semantic clarity
IngredientCode = Code
