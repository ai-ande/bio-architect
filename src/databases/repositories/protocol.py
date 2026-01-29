"""Repository for protocol data access."""

import json
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement_protocol import (
    Frequency,
    ProtocolSupplement,
    ProtocolSupplementType,
    SupplementProtocol,
)


class ProtocolRepository:
    """Repository for supplement protocol and protocol supplement data access."""

    def __init__(self, client: DatabaseClient):
        """Initialize repository with database client.

        Args:
            client: DatabaseClient instance for database operations.
        """
        self._client = client

    def insert_protocol(self, protocol: SupplementProtocol) -> SupplementProtocol:
        """Insert a supplement protocol record.

        Args:
            protocol: SupplementProtocol model to insert.

        Returns:
            The inserted SupplementProtocol model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO supplement_protocols (
                id, protocol_date, prescriber, next_visit, source_file,
                created_at, protein_goal, lifestyle_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(protocol.id),
                protocol.protocol_date.isoformat(),
                protocol.prescriber,
                protocol.next_visit,
                protocol.source_file,
                protocol.created_at.isoformat(),
                protocol.protein_goal,
                json.dumps(protocol.lifestyle_notes),
            ),
        )
        conn.commit()
        return protocol

    def insert_supplement(self, supplement: ProtocolSupplement) -> ProtocolSupplement:
        """Insert a protocol supplement record.

        Args:
            supplement: ProtocolSupplement model to insert.

        Returns:
            The inserted ProtocolSupplement model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO protocol_supplements (
                id, protocol_id, supplement_label_id, type, name, instructions,
                dosage, frequency, upon_waking, breakfast, mid_morning,
                lunch, mid_afternoon, dinner, before_sleep
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(supplement.id),
                str(supplement.protocol_id),
                str(supplement.supplement_label_id) if supplement.supplement_label_id else None,
                supplement.type.value,
                supplement.name,
                supplement.instructions,
                supplement.dosage,
                supplement.frequency.value,
                supplement.upon_waking,
                supplement.breakfast,
                supplement.mid_morning,
                supplement.lunch,
                supplement.mid_afternoon,
                supplement.dinner,
                supplement.before_sleep,
            ),
        )
        conn.commit()
        return supplement

    def get_protocol_by_id(self, protocol_id: UUID) -> Optional[SupplementProtocol]:
        """Get a supplement protocol by ID.

        Args:
            protocol_id: UUID of the supplement protocol.

        Returns:
            SupplementProtocol model if found, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, protocol_date, prescriber, next_visit, source_file,
                   created_at, protein_goal, lifestyle_notes
            FROM supplement_protocols
            WHERE id = ?
            """,
            (str(protocol_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_protocol(row)

    def get_current_protocol(self) -> Optional[SupplementProtocol]:
        """Get the most recent supplement protocol.

        Returns:
            Most recent SupplementProtocol model if any exist, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, protocol_date, prescriber, next_visit, source_file,
                   created_at, protein_goal, lifestyle_notes
            FROM supplement_protocols
            ORDER BY protocol_date DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_protocol(row)

    def get_protocol_history(self) -> list[SupplementProtocol]:
        """Get all supplement protocols ordered by date descending.

        Returns:
            List of SupplementProtocol models ordered by protocol_date descending.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, protocol_date, prescriber, next_visit, source_file,
                   created_at, protein_goal, lifestyle_notes
            FROM supplement_protocols
            ORDER BY protocol_date DESC
            """
        )
        rows = cursor.fetchall()
        return [self._row_to_protocol(row) for row in rows]

    def _row_to_protocol(self, row) -> SupplementProtocol:
        """Convert a database row to a SupplementProtocol model.

        Args:
            row: SQLite Row object.

        Returns:
            SupplementProtocol model.
        """
        return SupplementProtocol(
            id=UUID(row["id"]),
            protocol_date=date.fromisoformat(row["protocol_date"]),
            prescriber=row["prescriber"],
            next_visit=row["next_visit"],
            source_file=row["source_file"],
            created_at=datetime.fromisoformat(row["created_at"]),
            protein_goal=row["protein_goal"],
            lifestyle_notes=json.loads(row["lifestyle_notes"]),
        )

    def _row_to_supplement(self, row) -> ProtocolSupplement:
        """Convert a database row to a ProtocolSupplement model.

        Args:
            row: SQLite Row object.

        Returns:
            ProtocolSupplement model.
        """
        return ProtocolSupplement(
            id=UUID(row["id"]),
            protocol_id=UUID(row["protocol_id"]),
            supplement_label_id=UUID(row["supplement_label_id"]) if row["supplement_label_id"] else None,
            type=ProtocolSupplementType(row["type"]),
            name=row["name"],
            instructions=row["instructions"],
            dosage=row["dosage"],
            frequency=Frequency(row["frequency"]),
            upon_waking=row["upon_waking"],
            breakfast=row["breakfast"],
            mid_morning=row["mid_morning"],
            lunch=row["lunch"],
            mid_afternoon=row["mid_afternoon"],
            dinner=row["dinner"],
            before_sleep=row["before_sleep"],
        )
