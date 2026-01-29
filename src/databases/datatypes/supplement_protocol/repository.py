"""Repository for supplement protocol data access."""

from uuid import UUID

from sqlmodel import Session, select

from .models import ProtocolSupplement, SupplementProtocol


class SupplementProtocolRepository:
    """Repository for supplement protocol database operations."""

    def __init__(self, session: Session):
        self.session = session

    def list_protocols(self) -> list[SupplementProtocol]:
        """List all protocols ordered by date descending."""
        statement = select(SupplementProtocol).order_by(
            SupplementProtocol.protocol_date.desc()
        )
        return list(self.session.exec(statement).all())

    def get_protocol(self, protocol_id: UUID) -> SupplementProtocol | None:
        """Get a protocol by ID."""
        return self.session.get(SupplementProtocol, protocol_id)

    def get_current_protocol(self) -> SupplementProtocol | None:
        """Get the most recent protocol."""
        statement = (
            select(SupplementProtocol)
            .order_by(SupplementProtocol.protocol_date.desc())
            .limit(1)
        )
        return self.session.exec(statement).first()

    def get_supplements_for_protocol(
        self, protocol_id: UUID
    ) -> list[ProtocolSupplement]:
        """Get all supplements for a protocol."""
        statement = select(ProtocolSupplement).where(
            ProtocolSupplement.protocol_id == protocol_id
        )
        return list(self.session.exec(statement).all())

    def save_protocol(
        self,
        protocol: SupplementProtocol,
        supplements: list[ProtocolSupplement],
    ) -> None:
        """Save a protocol with its supplements atomically."""
        self.session.add(protocol)
        self.session.flush()  # Ensure protocol exists before supplements

        for supplement in supplements:
            self.session.add(supplement)

        self.session.commit()
