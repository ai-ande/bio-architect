#!/usr/bin/env python
"""CLI for querying supplement label data."""

import argparse
import json
import sys
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement import (
    Ingredient,
    ProprietaryBlend,
    SupplementLabel,
)
from src.databases.repositories.supplement import SupplementRepository


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


def cmd_list(repo: SupplementRepository, args: argparse.Namespace) -> None:
    """List all supplement labels."""
    labels = repo.get_all_labels()
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

    label = repo.get_label_by_id(label_id)
    if label is None:
        print(f"Label not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    ingredients = repo.get_ingredients_by_label(label_id)
    blends = repo.get_blends_by_label(label_id)

    if args.json:
        label_dict = label_to_dict(label)
        label_dict["ingredients"] = [ingredient_to_dict(i) for i in ingredients]
        label_dict["blends"] = []
        for blend in blends:
            blend_dict = blend_to_dict(blend)
            blend_ingredients = repo.get_ingredients_by_blend(blend.id)
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
            blend_ingredients = repo.get_ingredients_by_blend(blend.id)
            print("Name\tAmount\tUnit\t%DV\tType")
            print("-" * 60)
            for ingredient in blend_ingredients:
                print(format_ingredient(ingredient))
            print()


def cmd_ingredient(repo: SupplementRepository, args: argparse.Namespace) -> None:
    """Show labels containing a given ingredient code."""
    ingredients = repo.get_ingredient_by_code(args.code)

    if args.json:
        # Get unique labels that contain this ingredient
        label_ids = set()
        for ing in ingredients:
            if ing.supplement_label_id:
                label_ids.add(ing.supplement_label_id)
            elif ing.blend_id:
                # Need to find the blend's label
                blends = repo.get_blends_by_label(UUID("00000000-0000-0000-0000-000000000000"))  # Placeholder
                # For blend ingredients, we'll include the ingredient info directly
                pass

        # Get all labels containing this ingredient
        result = []
        for ing in ingredients:
            ing_dict = ingredient_to_dict(ing)
            if ing.supplement_label_id:
                label = repo.get_label_by_id(ing.supplement_label_id)
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
        seen_labels = set()
        for ing in ingredients:
            if ing.supplement_label_id and ing.supplement_label_id not in seen_labels:
                label = repo.get_label_by_id(ing.supplement_label_id)
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
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        repo = SupplementRepository(client)

        if parsed_args.command == "list":
            cmd_list(repo, parsed_args)
        elif parsed_args.command == "label":
            cmd_label(repo, parsed_args)
        elif parsed_args.command == "ingredient":
            cmd_ingredient(repo, parsed_args)
        elif parsed_args.command == "search":
            cmd_search(repo, parsed_args)


if __name__ == "__main__":
    main()
