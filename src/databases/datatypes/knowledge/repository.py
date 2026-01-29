"""Repository for knowledge data access."""

from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session, select

from .models import (
    Knowledge,
    KnowledgeLink,
    KnowledgeStatus,
    KnowledgeTag,
    LinkType,
)


class KnowledgeRepository:
    """Repository for knowledge database operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_knowledge(self, knowledge_id: UUID) -> Knowledge | None:
        """Get a knowledge entry by ID."""
        return self.session.get(Knowledge, knowledge_id)

    def get_tags_for_knowledge(self, knowledge_id: UUID) -> list[KnowledgeTag]:
        """Get all tags for a knowledge entry."""
        statement = (
            select(KnowledgeTag)
            .where(KnowledgeTag.knowledge_id == knowledge_id)
            .order_by(KnowledgeTag.tag)
        )
        return list(self.session.exec(statement).all())

    def get_links_for_knowledge(self, knowledge_id: UUID) -> list[KnowledgeLink]:
        """Get all links for a knowledge entry."""
        statement = (
            select(KnowledgeLink)
            .where(KnowledgeLink.knowledge_id == knowledge_id)
            .order_by(KnowledgeLink.link_type)
        )
        return list(self.session.exec(statement).all())

    def list_active(self) -> list[Knowledge]:
        """List all active knowledge entries."""
        statement = select(Knowledge).where(Knowledge.status == KnowledgeStatus.ACTIVE)
        return list(self.session.exec(statement).all())

    def get_by_tag(self, tag: str) -> list[Knowledge]:
        """Get knowledge entries by tag."""
        tag_results = self.session.exec(
            select(KnowledgeTag.knowledge_id)
            .where(KnowledgeTag.tag == tag)
            .distinct()
        ).all()

        entries = []
        for knowledge_id in tag_results:
            knowledge = self.session.get(Knowledge, knowledge_id)
            if knowledge:
                entries.append(knowledge)
        return entries

    def get_linked_to(self, link_type: LinkType, target_id: UUID) -> list[Knowledge]:
        """Get knowledge entries linked to a target."""
        link_results = self.session.exec(
            select(KnowledgeLink.knowledge_id)
            .where(
                KnowledgeLink.link_type == link_type,
                KnowledgeLink.target_id == target_id,
            )
            .distinct()
        ).all()

        entries = []
        for knowledge_id in link_results:
            knowledge = self.session.get(Knowledge, knowledge_id)
            if knowledge:
                entries.append(knowledge)
        return entries

    def validate_link_target_exists(self, link_type: LinkType, target_id: UUID) -> bool:
        """Check if a link target exists in the database."""
        table_map = {
            LinkType.SNP: "snps",
            LinkType.BIOMARKER: "biomarkers",
            LinkType.INGREDIENT: "ingredients",
            LinkType.SUPPLEMENT: "supplement_labels",
            LinkType.PROTOCOL: "supplement_protocols",
            LinkType.KNOWLEDGE: "knowledge",
        }

        table = table_map.get(link_type)
        if table is None:
            return False

        result = self.session.exec(
            text(f"SELECT 1 FROM {table} WHERE id = :id"), {"id": str(target_id)}
        )
        return result.first() is not None

    def save_knowledge(
        self,
        knowledge: Knowledge,
        tags: list[KnowledgeTag],
        links: list[KnowledgeLink],
    ) -> None:
        """Save a knowledge entry with its tags and links."""
        self.session.add(knowledge)
        for tag in tags:
            self.session.add(tag)
        for link in links:
            self.session.add(link)
        self.session.commit()

    def supersede(
        self,
        old_id: UUID,
        new_knowledge: Knowledge,
        tags: list[KnowledgeTag],
        links: list[KnowledgeLink],
    ) -> None:
        """Supersede an existing knowledge entry with a new one."""
        old_knowledge = self.session.get(Knowledge, old_id)
        if old_knowledge is None:
            raise ValueError(f"Knowledge entry not found: {old_id}")

        # Set supersedes reference
        new_knowledge.supersedes_id = old_id

        # Mark old entry as deprecated
        old_knowledge.status = KnowledgeStatus.DEPRECATED

        # Save new knowledge with tags and links
        self.session.add(new_knowledge)
        self.session.add(old_knowledge)

        for tag in tags:
            new_tag = KnowledgeTag(knowledge_id=new_knowledge.id, tag=tag.tag)
            self.session.add(new_tag)

        for link in links:
            new_link = KnowledgeLink(
                knowledge_id=new_knowledge.id,
                link_type=link.link_type,
                target_id=link.target_id,
            )
            self.session.add(new_link)

        self.session.commit()
