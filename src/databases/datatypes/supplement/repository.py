"""Repository for supplement data access."""

from uuid import UUID

from sqlmodel import Session, or_, select

from .models import Ingredient, ProprietaryBlend, SupplementLabel


class SupplementRepository:
    """Repository for supplement database operations."""

    def __init__(self, session: Session):
        self.session = session

    def list_labels(self) -> list[SupplementLabel]:
        """List all supplement labels ordered by brand and product name."""
        statement = select(SupplementLabel).order_by(
            SupplementLabel.brand, SupplementLabel.product_name
        )
        return list(self.session.exec(statement).all())

    def get_label(self, label_id: UUID) -> SupplementLabel | None:
        """Get a supplement label by ID."""
        return self.session.get(SupplementLabel, label_id)

    def get_ingredients_for_label(self, label_id: UUID) -> list[Ingredient]:
        """Get all ingredients directly linked to a label."""
        statement = (
            select(Ingredient)
            .where(Ingredient.supplement_label_id == label_id)
            .order_by(Ingredient.type, Ingredient.name)
        )
        return list(self.session.exec(statement).all())

    def get_blends_for_label(self, label_id: UUID) -> list[ProprietaryBlend]:
        """Get all proprietary blends for a label."""
        statement = (
            select(ProprietaryBlend)
            .where(ProprietaryBlend.supplement_label_id == label_id)
            .order_by(ProprietaryBlend.name)
        )
        return list(self.session.exec(statement).all())

    def get_ingredients_for_blend(self, blend_id: UUID) -> list[Ingredient]:
        """Get all ingredients for a proprietary blend."""
        statement = (
            select(Ingredient)
            .where(Ingredient.blend_id == blend_id)
            .order_by(Ingredient.name)
        )
        return list(self.session.exec(statement).all())

    def get_ingredients_by_code(self, code: str) -> list[Ingredient]:
        """Get all ingredients matching a code."""
        statement = select(Ingredient).where(Ingredient.code == code)
        return list(self.session.exec(statement).all())

    def search_labels(self, term: str) -> list[SupplementLabel]:
        """Search labels by brand or product name."""
        search_term = f"%{term}%"
        statement = select(SupplementLabel).where(
            or_(
                SupplementLabel.brand.like(search_term),
                SupplementLabel.product_name.like(search_term),
            )
        )
        return list(self.session.exec(statement).all())

    def save_label(
        self,
        label: SupplementLabel,
        blends: list[ProprietaryBlend],
        ingredients: list[Ingredient],
    ) -> None:
        """Save a supplement label with blends and ingredients atomically."""
        self.session.add(label)
        self.session.flush()  # Ensure label exists before blends/ingredients

        for blend in blends:
            self.session.add(blend)
        self.session.flush()  # Ensure blends exist before blend ingredients

        for ingredient in ingredients:
            self.session.add(ingredient)

        self.session.commit()
