"""Repository for knowledge data access."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.knowledge import (
    Knowledge,
    KnowledgeLink,
    KnowledgeStatus,
    KnowledgeTag,
    KnowledgeType,
    LinkType,
)


class KnowledgeRepository:
    """Repository for knowledge, knowledge links, and knowledge tags data access."""

    def __init__(self, client: DatabaseClient):
        """Initialize repository with database client.

        Args:
            client: DatabaseClient instance for database operations.
        """
        self._client = client

    def insert_knowledge(self, knowledge: Knowledge) -> Knowledge:
        """Insert a knowledge record.

        Args:
            knowledge: Knowledge model to insert.

        Returns:
            The inserted Knowledge model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO knowledge (
                id, type, status, summary, content, confidence,
                supersedes_id, supersession_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(knowledge.id),
                knowledge.type.value,
                knowledge.status.value,
                knowledge.summary,
                knowledge.content,
                knowledge.confidence,
                str(knowledge.supersedes_id) if knowledge.supersedes_id else None,
                knowledge.supersession_reason,
                knowledge.created_at.isoformat(),
            ),
        )
        conn.commit()
        return knowledge

    def insert_link(self, link: KnowledgeLink) -> KnowledgeLink:
        """Insert a knowledge link record.

        Args:
            link: KnowledgeLink model to insert.

        Returns:
            The inserted KnowledgeLink model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO knowledge_links (id, knowledge_id, link_type, target_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(link.id),
                str(link.knowledge_id),
                link.link_type.value,
                str(link.target_id),
            ),
        )
        conn.commit()
        return link

    def insert_tag(self, tag: KnowledgeTag) -> KnowledgeTag:
        """Insert a knowledge tag record.

        Args:
            tag: KnowledgeTag model to insert.

        Returns:
            The inserted KnowledgeTag model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO knowledge_tags (id, knowledge_id, tag)
            VALUES (?, ?, ?)
            """,
            (
                str(tag.id),
                str(tag.knowledge_id),
                tag.tag,
            ),
        )
        conn.commit()
        return tag

    def get_by_id(self, knowledge_id: UUID) -> Optional[Knowledge]:
        """Get a knowledge entry by ID.

        Args:
            knowledge_id: UUID of the knowledge entry.

        Returns:
            Knowledge model if found, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, type, status, summary, content, confidence,
                   supersedes_id, supersession_reason, created_at
            FROM knowledge
            WHERE id = ?
            """,
            (str(knowledge_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_knowledge(row)

    def get_active(self) -> list[Knowledge]:
        """Get all active knowledge entries.

        Returns:
            List of Knowledge models with status=active.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, type, status, summary, content, confidence,
                   supersedes_id, supersession_reason, created_at
            FROM knowledge
            WHERE status = ?
            ORDER BY created_at DESC
            """,
            (KnowledgeStatus.ACTIVE.value,),
        )
        rows = cursor.fetchall()
        return [self._row_to_knowledge(row) for row in rows]

    def get_by_tag(self, tag: str) -> list[Knowledge]:
        """Get knowledge entries by tag.

        Args:
            tag: Tag value to search for.

        Returns:
            List of Knowledge models matching the tag.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT k.id, k.type, k.status, k.summary, k.content, k.confidence,
                   k.supersedes_id, k.supersession_reason, k.created_at
            FROM knowledge k
            JOIN knowledge_tags kt ON k.id = kt.knowledge_id
            WHERE kt.tag = ?
            ORDER BY k.created_at DESC
            """,
            (tag,),
        )
        rows = cursor.fetchall()
        return [self._row_to_knowledge(row) for row in rows]

    def get_by_link(self, link_type: LinkType, target_id: UUID) -> list[Knowledge]:
        """Get knowledge entries linked to a target.

        Args:
            link_type: Type of link to search for.
            target_id: UUID of the target entity.

        Returns:
            List of Knowledge models linked to the target.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT k.id, k.type, k.status, k.summary, k.content, k.confidence,
                   k.supersedes_id, k.supersession_reason, k.created_at
            FROM knowledge k
            JOIN knowledge_links kl ON k.id = kl.knowledge_id
            WHERE kl.link_type = ? AND kl.target_id = ?
            ORDER BY k.created_at DESC
            """,
            (link_type.value, str(target_id)),
        )
        rows = cursor.fetchall()
        return [self._row_to_knowledge(row) for row in rows]

    def supersede(self, old_id: UUID, new_knowledge: Knowledge) -> Knowledge:
        """Supersede an existing knowledge entry with a new one.

        This method:
        1. Inserts the new knowledge entry with supersedes_id set to old_id
        2. Marks the old entry as deprecated

        Args:
            old_id: UUID of the knowledge entry to deprecate.
            new_knowledge: New Knowledge model (should have supersedes_id and supersession_reason set).

        Returns:
            The inserted new Knowledge model.
        """
        conn = self._client.connection
        cursor = conn.cursor()

        # Insert new knowledge entry
        cursor.execute(
            """
            INSERT INTO knowledge (
                id, type, status, summary, content, confidence,
                supersedes_id, supersession_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(new_knowledge.id),
                new_knowledge.type.value,
                new_knowledge.status.value,
                new_knowledge.summary,
                new_knowledge.content,
                new_knowledge.confidence,
                str(old_id),
                new_knowledge.supersession_reason,
                new_knowledge.created_at.isoformat(),
            ),
        )

        # Mark old entry as deprecated
        cursor.execute(
            """
            UPDATE knowledge
            SET status = ?
            WHERE id = ?
            """,
            (KnowledgeStatus.DEPRECATED.value, str(old_id)),
        )

        conn.commit()

        # Return the new knowledge with supersedes_id set correctly
        return Knowledge(
            id=new_knowledge.id,
            type=new_knowledge.type,
            status=new_knowledge.status,
            summary=new_knowledge.summary,
            content=new_knowledge.content,
            confidence=new_knowledge.confidence,
            supersedes_id=old_id,
            supersession_reason=new_knowledge.supersession_reason,
            created_at=new_knowledge.created_at,
        )

    def _row_to_knowledge(self, row) -> Knowledge:
        """Convert a database row to a Knowledge model.

        Args:
            row: SQLite Row object.

        Returns:
            Knowledge model.
        """
        return Knowledge(
            id=UUID(row["id"]),
            type=KnowledgeType(row["type"]),
            status=KnowledgeStatus(row["status"]),
            summary=row["summary"],
            content=row["content"],
            confidence=row["confidence"],
            supersedes_id=UUID(row["supersedes_id"]) if row["supersedes_id"] else None,
            supersession_reason=row["supersession_reason"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_link(self, row) -> KnowledgeLink:
        """Convert a database row to a KnowledgeLink model.

        Args:
            row: SQLite Row object.

        Returns:
            KnowledgeLink model.
        """
        return KnowledgeLink(
            id=UUID(row["id"]),
            knowledge_id=UUID(row["knowledge_id"]),
            link_type=LinkType(row["link_type"]),
            target_id=UUID(row["target_id"]),
        )

    def _row_to_tag(self, row) -> KnowledgeTag:
        """Convert a database row to a KnowledgeTag model.

        Args:
            row: SQLite Row object.

        Returns:
            KnowledgeTag model.
        """
        return KnowledgeTag(
            id=UUID(row["id"]),
            knowledge_id=UUID(row["knowledge_id"]),
            tag=row["tag"],
        )

    def get_all(self) -> list[Knowledge]:
        """Get all knowledge entries.

        Returns:
            List of Knowledge models ordered by created_at DESC.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, type, status, summary, content, confidence,
                   supersedes_id, supersession_reason, created_at
            FROM knowledge
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()
        return [self._row_to_knowledge(row) for row in rows]

    def get_tags_by_knowledge(self, knowledge_id: UUID) -> list[KnowledgeTag]:
        """Get all tags for a knowledge entry.

        Args:
            knowledge_id: UUID of the knowledge entry.

        Returns:
            List of KnowledgeTag models for the knowledge entry.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, knowledge_id, tag
            FROM knowledge_tags
            WHERE knowledge_id = ?
            ORDER BY tag
            """,
            (str(knowledge_id),),
        )
        rows = cursor.fetchall()
        return [self._row_to_tag(row) for row in rows]

    def get_links_by_knowledge(self, knowledge_id: UUID) -> list[KnowledgeLink]:
        """Get all links for a knowledge entry.

        Args:
            knowledge_id: UUID of the knowledge entry.

        Returns:
            List of KnowledgeLink models for the knowledge entry.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, knowledge_id, link_type, target_id
            FROM knowledge_links
            WHERE knowledge_id = ?
            ORDER BY link_type
            """,
            (str(knowledge_id),),
        )
        rows = cursor.fetchall()
        return [self._row_to_link(row) for row in rows]
