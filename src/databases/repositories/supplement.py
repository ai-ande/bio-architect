"""Repository for supplement data access."""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement import (
    Ingredient,
    IngredientType,
    ProprietaryBlend,
    SupplementForm,
    SupplementLabel,
)


class SupplementRepository:
    """Repository for supplement label, blend, and ingredient data access."""

    def __init__(self, client: DatabaseClient):
        """Initialize repository with database client.

        Args:
            client: DatabaseClient instance for database operations.
        """
        self._client = client

    def insert_label(self, label: SupplementLabel) -> SupplementLabel:
        """Insert a supplement label record.

        Args:
            label: SupplementLabel model to insert.

        Returns:
            The inserted SupplementLabel model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO supplement_labels (
                id, source_file, created_at, brand, product_name, form,
                serving_size, servings_per_container, suggested_use,
                warnings, allergen_info
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(label.id),
                label.source_file,
                label.created_at.isoformat(),
                label.brand,
                label.product_name,
                label.form.value,
                label.serving_size,
                label.servings_per_container,
                label.suggested_use,
                json.dumps(label.warnings),
                label.allergen_info,
            ),
        )
        conn.commit()
        return label

    def insert_blend(self, blend: ProprietaryBlend) -> ProprietaryBlend:
        """Insert a proprietary blend record.

        Args:
            blend: ProprietaryBlend model to insert.

        Returns:
            The inserted ProprietaryBlend model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO proprietary_blends (
                id, supplement_label_id, name, total_amount, total_unit
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(blend.id),
                str(blend.supplement_label_id),
                blend.name,
                blend.total_amount,
                blend.total_unit,
            ),
        )
        conn.commit()
        return blend

    def insert_ingredient(self, ingredient: Ingredient) -> Ingredient:
        """Insert an ingredient record.

        Args:
            ingredient: Ingredient model to insert.

        Returns:
            The inserted Ingredient model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ingredients (
                id, supplement_label_id, blend_id, type, name, code,
                amount, unit, percent_dv, form
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(ingredient.id),
                str(ingredient.supplement_label_id) if ingredient.supplement_label_id else None,
                str(ingredient.blend_id) if ingredient.blend_id else None,
                ingredient.type.value,
                ingredient.name,
                ingredient.code,
                ingredient.amount,
                ingredient.unit,
                ingredient.percent_dv,
                ingredient.form,
            ),
        )
        conn.commit()
        return ingredient

    def get_label_by_id(self, label_id: UUID) -> Optional[SupplementLabel]:
        """Get a supplement label by ID.

        Args:
            label_id: UUID of the supplement label.

        Returns:
            SupplementLabel model if found, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, source_file, created_at, brand, product_name, form,
                   serving_size, servings_per_container, suggested_use,
                   warnings, allergen_info
            FROM supplement_labels
            WHERE id = ?
            """,
            (str(label_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_label(row)

    def get_ingredient_by_code(self, code: str) -> list[Ingredient]:
        """Get all ingredients matching a given code.

        Args:
            code: Ingredient code (e.g., 'VITAMIN_D', 'MAGNESIUM').

        Returns:
            List of Ingredient models matching the code.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, supplement_label_id, blend_id, type, name, code,
                   amount, unit, percent_dv, form
            FROM ingredients
            WHERE code = ?
            """,
            (code,),
        )
        rows = cursor.fetchall()
        return [self._row_to_ingredient(row) for row in rows]

    def search_labels(self, term: str) -> list[SupplementLabel]:
        """Search supplement labels by brand or product name.

        Args:
            term: Search term to match against brand or product_name.

        Returns:
            List of SupplementLabel models matching the search term.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        search_term = f"%{term}%"
        cursor.execute(
            """
            SELECT id, source_file, created_at, brand, product_name, form,
                   serving_size, servings_per_container, suggested_use,
                   warnings, allergen_info
            FROM supplement_labels
            WHERE brand LIKE ? OR product_name LIKE ?
            """,
            (search_term, search_term),
        )
        rows = cursor.fetchall()
        return [self._row_to_label(row) for row in rows]

    def _row_to_label(self, row) -> SupplementLabel:
        """Convert a database row to a SupplementLabel model.

        Args:
            row: SQLite Row object.

        Returns:
            SupplementLabel model.
        """
        return SupplementLabel(
            id=UUID(row["id"]),
            source_file=row["source_file"],
            created_at=datetime.fromisoformat(row["created_at"]),
            brand=row["brand"],
            product_name=row["product_name"],
            form=SupplementForm(row["form"]),
            serving_size=row["serving_size"],
            servings_per_container=row["servings_per_container"],
            suggested_use=row["suggested_use"],
            warnings=json.loads(row["warnings"]),
            allergen_info=row["allergen_info"],
        )

    def _row_to_ingredient(self, row) -> Ingredient:
        """Convert a database row to an Ingredient model.

        Args:
            row: SQLite Row object.

        Returns:
            Ingredient model.
        """
        return Ingredient(
            id=UUID(row["id"]),
            supplement_label_id=UUID(row["supplement_label_id"]) if row["supplement_label_id"] else None,
            blend_id=UUID(row["blend_id"]) if row["blend_id"] else None,
            type=IngredientType(row["type"]),
            name=row["name"],
            code=row["code"],
            amount=row["amount"],
            unit=row["unit"],
            percent_dv=row["percent_dv"],
            form=row["form"],
        )
