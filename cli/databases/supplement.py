#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""CLI for querying supplement label data."""

import argcomplete
import argparse
import json
import sys
from typing import Optional
from uuid import UUID

from pydantic import ValidationError

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement import (
    Ingredient,
    IngredientType,
    ProprietaryBlend,
    SupplementForm,
    SupplementLabel,
    SupplementRepository,
)


def format_label(label: SupplementLabel) -> str:
    """Format a supplement label for display."""
    return f"{label.id}\t{label.brand}\t{label.product_name}\t{label.form.value}"


def format_ingredient(ingredient: Ingredient) -> str:
    """Format an ingredient for display."""
    amount_str = f"{ingredient.amount:.1f}" if ingredient.amount is not None else "-"
    unit_str = ingredient.unit if ingredient.unit else ""
    dv_str = f"{ingredient.percent_dv:.0f}%" if ingredient.percent_dv is not None else "-"
    return f"{ingredient.name}\t{amount_str}\t{unit_str}\t{dv_str}\t{ingredient.type.value}"


def label_to_dict(label: SupplementLabel) -> dict:
    """Convert a supplement label to a JSON-serializable dict."""
    return {
        "id": str(label.id),
        "source_file": label.source_file,
        "created_at": label.created_at.isoformat(),
        "brand": label.brand,
        "product_name": label.product_name,
        "form": label.form.value,
        "serving_size": label.serving_size,
        "servings_per_container": label.servings_per_container,
        "suggested_use": label.suggested_use,
        "warnings": label.warnings,
        "allergen_info": label.allergen_info,
    }


def ingredient_to_dict(ingredient: Ingredient) -> dict:
    """Convert an ingredient to a JSON-serializable dict."""
    return {
        "id": str(ingredient.id),
        "supplement_label_id": str(ingredient.supplement_label_id) if ingredient.supplement_label_id else None,
        "blend_id": str(ingredient.blend_id) if ingredient.blend_id else None,
        "type": ingredient.type.value,
        "name": ingredient.name,
        "code": ingredient.code,
        "amount": ingredient.amount,
        "unit": ingredient.unit,
        "percent_dv": ingredient.percent_dv,
        "form": ingredient.form,
    }


def blend_to_dict(blend: ProprietaryBlend) -> dict:
    """Convert a proprietary blend to a JSON-serializable dict."""
    return {
        "id": str(blend.id),
        "supplement_label_id": str(blend.supplement_label_id),
        "name": blend.name,
        "total_amount": blend.total_amount,
        "total_unit": blend.total_unit,
    }


def parse_supplement_json(
    data: dict, source_file: str | None
) -> tuple[SupplementLabel, list[ProprietaryBlend], list[Ingredient]]:
    """Parse JSON into database models.

    All model construction happens here, triggering Pydantic validation.
    If any validation fails, no database operations have occurred yet.

    Args:
        data: JSON dict with supplement data.
        source_file: Optional source file path.

    Returns:
        Tuple of (SupplementLabel, list of ProprietaryBlend, list of Ingredient).

    Raises:
        ValidationError: If model validation fails.
        KeyError: If required fields are missing.
    """
    # Create SupplementLabel
    label = SupplementLabel(
        brand=data["brand"],
        product_name=data["product_name"],
        form=SupplementForm(data["form"]),
        serving_size=data["serving_size"],
        servings_per_container=data.get("servings_per_container"),
        suggested_use=data.get("suggested_use"),
        warnings=data.get("warnings", []),
        allergen_info=data.get("allergen_info"),
        source_file=source_file,
    )

    blends: list[ProprietaryBlend] = []
    ingredients: list[Ingredient] = []

    # Parse active ingredients (linked to label)
    for ing_data in data.get("active_ingredients", []):
        ingredient = Ingredient.model_validate({
            "supplement_label_id": label.id,
            "blend_id": None,
            "type": IngredientType.ACTIVE.value,
            "name": ing_data["name"],
            "code": ing_data["code"],
            "amount": ing_data.get("amount"),
            "unit": ing_data.get("unit"),
            "percent_dv": ing_data.get("percent_dv"),
            "form": ing_data.get("form"),
        })
        ingredients.append(ingredient)

    # Parse other ingredients (linked to label)
    for ing_data in data.get("other_ingredients", []):
        ingredient = Ingredient.model_validate({
            "supplement_label_id": label.id,
            "blend_id": None,
            "type": IngredientType.OTHER.value,
            "name": ing_data["name"],
            "code": ing_data["code"],
            "amount": ing_data.get("amount"),
            "unit": ing_data.get("unit"),
            "percent_dv": ing_data.get("percent_dv"),
            "form": ing_data.get("form"),
        })
        ingredients.append(ingredient)

    # Parse proprietary blends and their ingredients
    for blend_data in data.get("proprietary_blends", []):
        blend = ProprietaryBlend(
            supplement_label_id=label.id,
            name=blend_data["name"],
            total_amount=blend_data.get("total_amount"),
            total_unit=blend_data.get("total_unit"),
        )
        blends.append(blend)

        # Parse blend ingredients (linked to blend, not label)
        for ing_data in blend_data.get("ingredients", []):
            ingredient = Ingredient.model_validate({
                "supplement_label_id": None,
                "blend_id": blend.id,
                "type": IngredientType.BLEND.value,
                "name": ing_data["name"],
                "code": ing_data["code"],
                "amount": ing_data.get("amount"),
                "unit": ing_data.get("unit"),
                "percent_dv": ing_data.get("percent_dv"),
                "form": ing_data.get("form"),
            })
            ingredients.append(ingredient)

    return label, blends, ingredients


def cmd_import(repo: SupplementRepository, args: argparse.Namespace) -> None:
    """Import supplement from JSON file.

    Transaction handling:
    1. Parse JSON and construct all models (validation happens here)
    2. If validation passes, save via repository
    3. Repository commits as single atomic transaction
    4. If anything fails, nothing is committed (no dangling records)
    """
    # Read JSON from file or stdin
    if args.file:
        try:
            with open(args.file) as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in file: {e}", file=sys.stderr)
            sys.exit(1)
        source_file = args.file
    else:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)
        source_file = None

    # Step 1: Parse and validate ALL data before any DB operations
    try:
        label, blends, ingredients = parse_supplement_json(data, source_file)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Save via repository
    created = repo.save_label(label, blends, ingredients)

    # Output
    if not created:
        if args.json:
            print(json.dumps({"status": "already_imported"}))
        else:
            print(f"Already imported: {source_file}")
    elif args.json:
        print(json.dumps({
            "supplement_label_id": str(label.id),
            "blends_created": len(blends),
            "ingredients_created": len(ingredients),
        }, indent=2))
    else:
        print(f"Imported supplement label: {label.id}")
        print(f"  Blends: {len(blends)}")
        print(f"  Ingredients: {len(ingredients)}")


def cmd_list(repo: SupplementRepository, args: argparse.Namespace) -> None:
    """List all supplement labels."""
    labels = repo.list_labels()
    if args.json:
        print(json.dumps([label_to_dict(l) for l in labels], indent=2))
    else:
        if not labels:
            print("No supplement labels found.")
            return
        print("ID\tBrand\tProduct\tForm")
        print("-" * 80)
        for label in labels:
            print(format_label(label))


def cmd_label(repo: SupplementRepository, args: argparse.Namespace) -> None:
    """Show details for a single supplement label."""
    try:
        label_id = UUID(args.id)
    except ValueError:
        print(f"Invalid label ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    label = repo.get_label(label_id)
    if label is None:
        print(f"Label not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    ingredients = repo.get_ingredients_for_label(label_id)
    blends = repo.get_blends_for_label(label_id)

    if args.json:
        label_dict = label_to_dict(label)
        label_dict["ingredients"] = [ingredient_to_dict(i) for i in ingredients]
        label_dict["blends"] = []
        for blend in blends:
            blend_dict = blend_to_dict(blend)
            blend_ingredients = repo.get_ingredients_for_blend(blend.id)
            blend_dict["ingredients"] = [ingredient_to_dict(i) for i in blend_ingredients]
            label_dict["blends"].append(blend_dict)
        print(json.dumps(label_dict, indent=2))
    else:
        print(f"Label: {label.id}")
        print(f"Brand: {label.brand}")
        print(f"Product: {label.product_name}")
        print(f"Form: {label.form.value}")
        print(f"Serving Size: {label.serving_size}")
        if label.servings_per_container:
            print(f"Servings: {label.servings_per_container}")
        if label.suggested_use:
            print(f"Suggested Use: {label.suggested_use}")
        print()
        if ingredients:
            print("Ingredients:")
            print("Name\tAmount\tUnit\t%DV\tType")
            print("-" * 80)
            for ingredient in ingredients:
                print(format_ingredient(ingredient))
            print()
        for blend in blends:
            amount_str = f"{blend.total_amount} {blend.total_unit}" if blend.total_amount else ""
            print(f"Blend: {blend.name} {amount_str}")
            blend_ingredients = repo.get_ingredients_for_blend(blend.id)
            print("Name\tAmount\tUnit\t%DV\tType")
            print("-" * 60)
            for ingredient in blend_ingredients:
                print(format_ingredient(ingredient))
            print()


def cmd_ingredient(repo: SupplementRepository, args: argparse.Namespace) -> None:
    """Show labels containing a given ingredient code."""
    ingredients = repo.get_ingredients_by_code(args.code)

    if args.json:
        result = []
        for ing in ingredients:
            ing_dict = ingredient_to_dict(ing)
            if ing.supplement_label_id:
                label = repo.get_label(ing.supplement_label_id)
                if label:
                    ing_dict["label"] = label_to_dict(label)
            result.append(ing_dict)
        print(json.dumps(result, indent=2))
    else:
        if not ingredients:
            print(f"No supplements found containing: {args.code}")
            return
        print(f"Supplements containing {args.code}:")
        print("Brand\tProduct\tAmount\tUnit")
        print("-" * 80)
        seen_labels: set[UUID] = set()
        for ing in ingredients:
            if ing.supplement_label_id and ing.supplement_label_id not in seen_labels:
                label = repo.get_label(ing.supplement_label_id)
                if label:
                    amount_str = f"{ing.amount:.1f}" if ing.amount else "-"
                    unit_str = ing.unit if ing.unit else ""
                    print(f"{label.brand}\t{label.product_name}\t{amount_str}\t{unit_str}")
                    seen_labels.add(ing.supplement_label_id)


def cmd_search(repo: SupplementRepository, args: argparse.Namespace) -> None:
    """Search supplement labels by brand or product name."""
    labels = repo.search_labels(args.term)

    if args.json:
        print(json.dumps([label_to_dict(l) for l in labels], indent=2))
    else:
        if not labels:
            print(f"No supplements found matching: {args.term}")
            return
        print(f"Supplements matching '{args.term}':")
        print("ID\tBrand\tProduct\tForm")
        print("-" * 80)
        for label in labels:
            print(format_label(label))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for supplements CLI."""
    parser = argparse.ArgumentParser(
        prog="supplements",
        description="Query supplement label data from the command line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of formatted text",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # import command
    import_parser = subparsers.add_parser("import", help="Import supplement from JSON file")
    import_parser.add_argument(
        "--file", "-f",
        help="JSON file to read (default: stdin)",
    )

    # list command
    subparsers.add_parser("list", help="List all supplement labels")

    # label command
    label_parser = subparsers.add_parser("label", help="Show details for a single label")
    label_parser.add_argument("id", help="Label ID (UUID)")

    # ingredient command
    ingredient_parser = subparsers.add_parser("ingredient", help="Show labels containing an ingredient")
    ingredient_parser.add_argument("code", help="Ingredient code (e.g., VITAMIN_D3, MAGNESIUM)")

    # search command
    search_parser = subparsers.add_parser("search", help="Search by brand or product name")
    search_parser.add_argument("term", help="Search term")

    return parser


def main(args: Optional[list[str]] = None) -> None:
    """Main entry point for supplements CLI."""
    parser = create_parser()
    argcomplete.autocomplete(parser)
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        with client.get_session() as session:
            repo = SupplementRepository(session)
            if parsed_args.command == "import":
                cmd_import(repo, parsed_args)
            elif parsed_args.command == "list":
                cmd_list(repo, parsed_args)
            elif parsed_args.command == "label":
                cmd_label(repo, parsed_args)
            elif parsed_args.command == "ingredient":
                cmd_ingredient(repo, parsed_args)
            elif parsed_args.command == "search":
                cmd_search(repo, parsed_args)


if __name__ == "__main__":
    main()
