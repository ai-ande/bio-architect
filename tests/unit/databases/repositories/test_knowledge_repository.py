"""Tests for KnowledgeRepository."""

import tempfile
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.knowledge import (
    Knowledge,
    KnowledgeLink,
    KnowledgeStatus,
    KnowledgeTag,
    KnowledgeType,
    LinkType,
)
from src.databases.repositories.knowledge import KnowledgeRepository


@pytest.fixture
def db_client():
    """Create a temporary database client."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        client = DatabaseClient(db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()


@pytest.fixture
def repository(db_client):
    """Create a KnowledgeRepository with the test database."""
    return KnowledgeRepository(db_client)


@pytest.fixture
def sample_knowledge():
    """Create a sample Knowledge entry."""
    return Knowledge(
        id=uuid4(),
        type=KnowledgeType.INSIGHT,
        status=KnowledgeStatus.ACTIVE,
        summary="Test insight summary",
        content="Full content of the test insight with detailed information.",
        confidence=0.85,
        supersedes_id=None,
        supersession_reason=None,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def sample_link(sample_knowledge):
    """Create a sample KnowledgeLink."""
    return KnowledgeLink(
        id=uuid4(),
        knowledge_id=sample_knowledge.id,
        link_type=LinkType.BIOMARKER,
        target_id=uuid4(),
    )


@pytest.fixture
def sample_tag(sample_knowledge):
    """Create a sample KnowledgeTag."""
    return KnowledgeTag(
        id=uuid4(),
        knowledge_id=sample_knowledge.id,
        tag="nutrition",
    )


class TestInsertKnowledge:
    """Tests for insert_knowledge method."""

    def test_insert_knowledge_returns_model(self, repository, sample_knowledge):
        """insert_knowledge returns the inserted Knowledge model."""
        result = repository.insert_knowledge(sample_knowledge)
        assert isinstance(result, Knowledge)
        assert result.id == sample_knowledge.id
        assert result.summary == sample_knowledge.summary

    def test_insert_knowledge_persists_data(self, repository, sample_knowledge):
        """insert_knowledge persists data to database."""
        repository.insert_knowledge(sample_knowledge)
        retrieved = repository.get_by_id(sample_knowledge.id)
        assert retrieved is not None
        assert retrieved.id == sample_knowledge.id
        assert retrieved.summary == sample_knowledge.summary
        assert retrieved.content == sample_knowledge.content

    def test_insert_knowledge_preserves_all_fields(self, repository):
        """insert_knowledge preserves all fields including type and confidence."""
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.RECOMMENDATION,
            status=KnowledgeStatus.ACTIVE,
            summary="Recommendation summary",
            content="Detailed recommendation content",
            confidence=0.92,
            created_at=datetime(2024, 2, 20, 14, 0, 0),
        )
        repository.insert_knowledge(knowledge)
        retrieved = repository.get_by_id(knowledge.id)
        assert retrieved.type == KnowledgeType.RECOMMENDATION
        assert retrieved.status == KnowledgeStatus.ACTIVE
        assert retrieved.confidence == 0.92
        assert retrieved.created_at == knowledge.created_at

    def test_insert_knowledge_with_null_optional_fields(self, repository):
        """insert_knowledge handles null optional fields."""
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.MEMORY,
            summary="Memory entry",
            content="Memory content",
            confidence=0.5,
            supersedes_id=None,
            supersession_reason=None,
        )
        repository.insert_knowledge(knowledge)
        retrieved = repository.get_by_id(knowledge.id)
        assert retrieved.supersedes_id is None
        assert retrieved.supersession_reason is None

    def test_insert_knowledge_all_types(self, repository):
        """insert_knowledge handles all KnowledgeType values."""
        for ktype in KnowledgeType:
            knowledge = Knowledge(
                id=uuid4(),
                type=ktype,
                summary=f"Summary for {ktype.value}",
                content=f"Content for {ktype.value}",
                confidence=0.7,
            )
            result = repository.insert_knowledge(knowledge)
            assert result.type == ktype

    def test_insert_knowledge_with_deprecated_status(self, repository):
        """insert_knowledge handles deprecated status."""
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            status=KnowledgeStatus.DEPRECATED,
            summary="Deprecated insight",
            content="Old content",
            confidence=0.6,
        )
        repository.insert_knowledge(knowledge)
        retrieved = repository.get_by_id(knowledge.id)
        assert retrieved.status == KnowledgeStatus.DEPRECATED


class TestInsertLink:
    """Tests for insert_link method."""

    def test_insert_link_returns_model(self, repository, sample_knowledge, sample_link):
        """insert_link returns the inserted KnowledgeLink model."""
        repository.insert_knowledge(sample_knowledge)
        result = repository.insert_link(sample_link)
        assert isinstance(result, KnowledgeLink)
        assert result.id == sample_link.id
        assert result.link_type == sample_link.link_type

    def test_insert_link_persists_data(self, repository, sample_knowledge, sample_link):
        """insert_link persists data to database."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_link(sample_link)
        # Verify by querying directly
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_links WHERE id = ?", (str(sample_link.id),))
        row = cursor.fetchone()
        assert row is not None
        assert row["knowledge_id"] == str(sample_knowledge.id)
        assert row["link_type"] == sample_link.link_type.value

    def test_insert_link_all_types(self, repository, sample_knowledge):
        """insert_link handles all LinkType values."""
        repository.insert_knowledge(sample_knowledge)
        for ltype in LinkType:
            link = KnowledgeLink(
                id=uuid4(),
                knowledge_id=sample_knowledge.id,
                link_type=ltype,
                target_id=uuid4(),
            )
            result = repository.insert_link(link)
            assert result.link_type == ltype

    def test_insert_multiple_links_same_knowledge(self, repository, sample_knowledge):
        """insert_link allows multiple links for same knowledge entry."""
        repository.insert_knowledge(sample_knowledge)
        link1 = KnowledgeLink(
            id=uuid4(),
            knowledge_id=sample_knowledge.id,
            link_type=LinkType.SNP,
            target_id=uuid4(),
        )
        link2 = KnowledgeLink(
            id=uuid4(),
            knowledge_id=sample_knowledge.id,
            link_type=LinkType.BIOMARKER,
            target_id=uuid4(),
        )
        repository.insert_link(link1)
        repository.insert_link(link2)
        # Verify both exist
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM knowledge_links WHERE knowledge_id = ?",
            (str(sample_knowledge.id),),
        )
        count = cursor.fetchone()[0]
        assert count == 2


class TestInsertTag:
    """Tests for insert_tag method."""

    def test_insert_tag_returns_model(self, repository, sample_knowledge, sample_tag):
        """insert_tag returns the inserted KnowledgeTag model."""
        repository.insert_knowledge(sample_knowledge)
        result = repository.insert_tag(sample_tag)
        assert isinstance(result, KnowledgeTag)
        assert result.id == sample_tag.id
        assert result.tag == sample_tag.tag

    def test_insert_tag_persists_data(self, repository, sample_knowledge, sample_tag):
        """insert_tag persists data to database."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        # Verify by querying directly
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_tags WHERE id = ?", (str(sample_tag.id),))
        row = cursor.fetchone()
        assert row is not None
        assert row["knowledge_id"] == str(sample_knowledge.id)
        assert row["tag"] == sample_tag.tag

    def test_insert_multiple_tags_same_knowledge(self, repository, sample_knowledge):
        """insert_tag allows multiple tags for same knowledge entry."""
        repository.insert_knowledge(sample_knowledge)
        tags = ["nutrition", "vitamin-d", "bone-health"]
        for tag_value in tags:
            tag = KnowledgeTag(
                id=uuid4(),
                knowledge_id=sample_knowledge.id,
                tag=tag_value,
            )
            repository.insert_tag(tag)
        # Verify all exist
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM knowledge_tags WHERE knowledge_id = ?",
            (str(sample_knowledge.id),),
        )
        count = cursor.fetchone()[0]
        assert count == 3


class TestGetById:
    """Tests for get_by_id method."""

    def test_get_by_id_returns_model(self, repository, sample_knowledge):
        """get_by_id returns Knowledge model."""
        repository.insert_knowledge(sample_knowledge)
        result = repository.get_by_id(sample_knowledge.id)
        assert isinstance(result, Knowledge)

    def test_get_by_id_not_found_returns_none(self, repository):
        """get_by_id returns None when not found."""
        result = repository.get_by_id(uuid4())
        assert result is None

    def test_get_by_id_returns_correct_entry(self, repository):
        """get_by_id returns the correct knowledge entry when multiple exist."""
        knowledge1 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="First insight",
            content="First content",
            confidence=0.7,
        )
        knowledge2 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.RECOMMENDATION,
            summary="Second recommendation",
            content="Second content",
            confidence=0.9,
        )
        repository.insert_knowledge(knowledge1)
        repository.insert_knowledge(knowledge2)
        result = repository.get_by_id(knowledge2.id)
        assert result.summary == "Second recommendation"
        assert result.type == KnowledgeType.RECOMMENDATION


class TestGetActive:
    """Tests for get_active method."""

    def test_get_active_returns_list(self, repository, sample_knowledge):
        """get_active returns a list."""
        repository.insert_knowledge(sample_knowledge)
        result = repository.get_active()
        assert isinstance(result, list)

    def test_get_active_returns_knowledge_models(self, repository, sample_knowledge):
        """get_active returns Knowledge models."""
        repository.insert_knowledge(sample_knowledge)
        result = repository.get_active()
        assert len(result) == 1
        assert isinstance(result[0], Knowledge)

    def test_get_active_returns_empty_list(self, repository):
        """get_active returns empty list when no entries."""
        result = repository.get_active()
        assert result == []

    def test_get_active_excludes_deprecated(self, repository):
        """get_active excludes deprecated entries."""
        active_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            status=KnowledgeStatus.ACTIVE,
            summary="Active insight",
            content="Active content",
            confidence=0.8,
        )
        deprecated_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            status=KnowledgeStatus.DEPRECATED,
            summary="Deprecated insight",
            content="Old content",
            confidence=0.6,
        )
        repository.insert_knowledge(active_knowledge)
        repository.insert_knowledge(deprecated_knowledge)
        result = repository.get_active()
        assert len(result) == 1
        assert result[0].summary == "Active insight"

    def test_get_active_ordered_by_created_at_desc(self, repository):
        """get_active returns results ordered by created_at descending."""
        knowledge1 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Older",
            content="Content",
            confidence=0.7,
            created_at=datetime(2024, 1, 1, 10, 0, 0),
        )
        knowledge2 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Newer",
            content="Content",
            confidence=0.7,
            created_at=datetime(2024, 3, 1, 10, 0, 0),
        )
        knowledge3 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Middle",
            content="Content",
            confidence=0.7,
            created_at=datetime(2024, 2, 1, 10, 0, 0),
        )
        repository.insert_knowledge(knowledge1)
        repository.insert_knowledge(knowledge2)
        repository.insert_knowledge(knowledge3)
        result = repository.get_active()
        assert len(result) == 3
        assert result[0].summary == "Newer"
        assert result[1].summary == "Middle"
        assert result[2].summary == "Older"


class TestGetByTag:
    """Tests for get_by_tag method."""

    def test_get_by_tag_returns_list(self, repository, sample_knowledge, sample_tag):
        """get_by_tag returns a list."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        result = repository.get_by_tag(sample_tag.tag)
        assert isinstance(result, list)

    def test_get_by_tag_returns_matching_entries(self, repository, sample_knowledge, sample_tag):
        """get_by_tag returns knowledge entries with matching tag."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        result = repository.get_by_tag(sample_tag.tag)
        assert len(result) == 1
        assert result[0].id == sample_knowledge.id

    def test_get_by_tag_returns_empty_list_no_match(self, repository, sample_knowledge, sample_tag):
        """get_by_tag returns empty list when no entries match."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        result = repository.get_by_tag("nonexistent-tag")
        assert result == []

    def test_get_by_tag_multiple_entries_same_tag(self, repository):
        """get_by_tag returns all entries with the same tag."""
        knowledge1 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="First",
            content="Content",
            confidence=0.7,
            created_at=datetime(2024, 1, 1),
        )
        knowledge2 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.RECOMMENDATION,
            summary="Second",
            content="Content",
            confidence=0.8,
            created_at=datetime(2024, 2, 1),
        )
        repository.insert_knowledge(knowledge1)
        repository.insert_knowledge(knowledge2)
        repository.insert_tag(KnowledgeTag(id=uuid4(), knowledge_id=knowledge1.id, tag="shared-tag"))
        repository.insert_tag(KnowledgeTag(id=uuid4(), knowledge_id=knowledge2.id, tag="shared-tag"))
        result = repository.get_by_tag("shared-tag")
        assert len(result) == 2

    def test_get_by_tag_does_not_duplicate_entries(self, repository, sample_knowledge):
        """get_by_tag does not return duplicate entries if knowledge has multiple matching tags."""
        repository.insert_knowledge(sample_knowledge)
        # Add same tag twice (different tag ids but same value)
        repository.insert_tag(KnowledgeTag(id=uuid4(), knowledge_id=sample_knowledge.id, tag="nutrition"))
        repository.insert_tag(KnowledgeTag(id=uuid4(), knowledge_id=sample_knowledge.id, tag="nutrition"))
        result = repository.get_by_tag("nutrition")
        # Should only return one entry due to DISTINCT
        assert len(result) == 1


class TestGetByLink:
    """Tests for get_by_link method."""

    def test_get_by_link_returns_list(self, repository, sample_knowledge, sample_link):
        """get_by_link returns a list."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_link(sample_link)
        result = repository.get_by_link(sample_link.link_type, sample_link.target_id)
        assert isinstance(result, list)

    def test_get_by_link_returns_matching_entries(self, repository, sample_knowledge, sample_link):
        """get_by_link returns knowledge entries linked to target."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_link(sample_link)
        result = repository.get_by_link(sample_link.link_type, sample_link.target_id)
        assert len(result) == 1
        assert result[0].id == sample_knowledge.id

    def test_get_by_link_returns_empty_list_no_match(self, repository, sample_knowledge, sample_link):
        """get_by_link returns empty list when no entries match."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_link(sample_link)
        result = repository.get_by_link(LinkType.SNP, uuid4())
        assert result == []

    def test_get_by_link_multiple_entries_same_target(self, repository):
        """get_by_link returns all entries linked to the same target."""
        target_id = uuid4()
        knowledge1 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="First",
            content="Content",
            confidence=0.7,
            created_at=datetime(2024, 1, 1),
        )
        knowledge2 = Knowledge(
            id=uuid4(),
            type=KnowledgeType.CONTRAINDICATION,
            summary="Second",
            content="Content",
            confidence=0.9,
            created_at=datetime(2024, 2, 1),
        )
        repository.insert_knowledge(knowledge1)
        repository.insert_knowledge(knowledge2)
        repository.insert_link(
            KnowledgeLink(id=uuid4(), knowledge_id=knowledge1.id, link_type=LinkType.SNP, target_id=target_id)
        )
        repository.insert_link(
            KnowledgeLink(id=uuid4(), knowledge_id=knowledge2.id, link_type=LinkType.SNP, target_id=target_id)
        )
        result = repository.get_by_link(LinkType.SNP, target_id)
        assert len(result) == 2

    def test_get_by_link_requires_matching_type(self, repository, sample_knowledge):
        """get_by_link requires both link_type and target_id to match."""
        target_id = uuid4()
        repository.insert_knowledge(sample_knowledge)
        repository.insert_link(
            KnowledgeLink(id=uuid4(), knowledge_id=sample_knowledge.id, link_type=LinkType.SNP, target_id=target_id)
        )
        # Same target but different type should return empty
        result = repository.get_by_link(LinkType.BIOMARKER, target_id)
        assert result == []

    def test_get_by_link_all_link_types(self, repository, sample_knowledge):
        """get_by_link works with all LinkType values."""
        repository.insert_knowledge(sample_knowledge)
        for ltype in LinkType:
            target_id = uuid4()
            link = KnowledgeLink(
                id=uuid4(),
                knowledge_id=sample_knowledge.id,
                link_type=ltype,
                target_id=target_id,
            )
            repository.insert_link(link)
            result = repository.get_by_link(ltype, target_id)
            assert len(result) == 1


class TestSupersede:
    """Tests for supersede method."""

    def test_supersede_returns_new_model(self, repository, sample_knowledge):
        """supersede returns the new Knowledge model."""
        repository.insert_knowledge(sample_knowledge)
        new_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Updated insight",
            content="New content that supersedes the old",
            confidence=0.95,
            supersession_reason="New research available",
        )
        result = repository.supersede(sample_knowledge.id, new_knowledge)
        assert isinstance(result, Knowledge)
        assert result.id == new_knowledge.id
        assert result.summary == new_knowledge.summary

    def test_supersede_sets_supersedes_id(self, repository, sample_knowledge):
        """supersede sets supersedes_id on the new entry."""
        repository.insert_knowledge(sample_knowledge)
        new_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Updated",
            content="New content",
            confidence=0.9,
            supersession_reason="Correction",
        )
        result = repository.supersede(sample_knowledge.id, new_knowledge)
        assert result.supersedes_id == sample_knowledge.id

    def test_supersede_deprecates_old_entry(self, repository, sample_knowledge):
        """supersede marks the old entry as deprecated."""
        repository.insert_knowledge(sample_knowledge)
        new_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Updated",
            content="New content",
            confidence=0.9,
            supersession_reason="Better data",
        )
        repository.supersede(sample_knowledge.id, new_knowledge)
        old_entry = repository.get_by_id(sample_knowledge.id)
        assert old_entry.status == KnowledgeStatus.DEPRECATED

    def test_supersede_persists_new_entry(self, repository, sample_knowledge):
        """supersede persists the new entry to database."""
        repository.insert_knowledge(sample_knowledge)
        new_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.RECOMMENDATION,
            summary="New recommendation",
            content="Updated recommendation content",
            confidence=0.88,
            supersession_reason="Improved analysis",
        )
        result = repository.supersede(sample_knowledge.id, new_knowledge)
        retrieved = repository.get_by_id(result.id)
        assert retrieved is not None
        assert retrieved.summary == new_knowledge.summary
        assert retrieved.supersedes_id == sample_knowledge.id

    def test_supersede_preserves_supersession_reason(self, repository, sample_knowledge):
        """supersede preserves the supersession_reason."""
        repository.insert_knowledge(sample_knowledge)
        new_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Updated",
            content="New content",
            confidence=0.9,
            supersession_reason="Important correction based on new study",
        )
        result = repository.supersede(sample_knowledge.id, new_knowledge)
        retrieved = repository.get_by_id(result.id)
        assert retrieved.supersession_reason == "Important correction based on new study"

    def test_supersede_new_entry_is_active(self, repository, sample_knowledge):
        """supersede creates new entry with active status."""
        repository.insert_knowledge(sample_knowledge)
        new_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Updated",
            content="New content",
            confidence=0.9,
        )
        result = repository.supersede(sample_knowledge.id, new_knowledge)
        assert result.status == KnowledgeStatus.ACTIVE


class TestEdgeCases:
    """Edge case tests."""

    def test_uuid_roundtrip(self, repository, sample_knowledge):
        """UUIDs are correctly stored and retrieved."""
        repository.insert_knowledge(sample_knowledge)
        retrieved = repository.get_by_id(sample_knowledge.id)
        assert isinstance(retrieved.id, UUID)
        assert retrieved.id == sample_knowledge.id

    def test_datetime_roundtrip(self, repository):
        """Datetimes are correctly stored and retrieved."""
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.MEMORY,
            summary="Memory",
            content="Content",
            confidence=0.5,
            created_at=datetime(2021, 6, 15, 14, 30, 45),
        )
        repository.insert_knowledge(knowledge)
        retrieved = repository.get_by_id(knowledge.id)
        assert isinstance(retrieved.created_at, datetime)
        assert retrieved.created_at == datetime(2021, 6, 15, 14, 30, 45)

    def test_confidence_boundary_values(self, repository):
        """Confidence accepts boundary values 0.0 and 1.0."""
        knowledge_min = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Low confidence",
            content="Content",
            confidence=0.0,
        )
        knowledge_max = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="High confidence",
            content="Content",
            confidence=1.0,
        )
        repository.insert_knowledge(knowledge_min)
        repository.insert_knowledge(knowledge_max)
        retrieved_min = repository.get_by_id(knowledge_min.id)
        retrieved_max = repository.get_by_id(knowledge_max.id)
        assert retrieved_min.confidence == 0.0
        assert retrieved_max.confidence == 1.0

    def test_knowledge_type_roundtrip(self, repository):
        """KnowledgeType enum is correctly stored and retrieved."""
        for ktype in KnowledgeType:
            knowledge = Knowledge(
                id=uuid4(),
                type=ktype,
                summary=f"Summary {ktype.value}",
                content="Content",
                confidence=0.7,
            )
            repository.insert_knowledge(knowledge)
            retrieved = repository.get_by_id(knowledge.id)
            assert retrieved.type == ktype

    def test_knowledge_status_roundtrip(self, repository):
        """KnowledgeStatus enum is correctly stored and retrieved."""
        for status in KnowledgeStatus:
            knowledge = Knowledge(
                id=uuid4(),
                type=KnowledgeType.INSIGHT,
                status=status,
                summary=f"Summary {status.value}",
                content="Content",
                confidence=0.7,
            )
            repository.insert_knowledge(knowledge)
            retrieved = repository.get_by_id(knowledge.id)
            assert retrieved.status == status

    def test_link_type_roundtrip(self, repository, sample_knowledge):
        """LinkType enum is correctly stored and retrieved."""
        repository.insert_knowledge(sample_knowledge)
        for ltype in LinkType:
            link = KnowledgeLink(
                id=uuid4(),
                knowledge_id=sample_knowledge.id,
                link_type=ltype,
                target_id=uuid4(),
            )
            repository.insert_link(link)
            conn = repository._client.connection
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_links WHERE id = ?", (str(link.id),))
            row = cursor.fetchone()
            converted = repository._row_to_link(row)
            assert converted.link_type == ltype

    def test_supersedes_id_roundtrip(self, repository):
        """supersedes_id is correctly stored and retrieved."""
        old_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Old",
            content="Old content",
            confidence=0.6,
        )
        repository.insert_knowledge(old_knowledge)
        new_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="New",
            content="New content",
            confidence=0.9,
            supersedes_id=old_knowledge.id,
            supersession_reason="Update",
        )
        repository.insert_knowledge(new_knowledge)
        retrieved = repository.get_by_id(new_knowledge.id)
        assert isinstance(retrieved.supersedes_id, UUID)
        assert retrieved.supersedes_id == old_knowledge.id

    def test_long_content_roundtrip(self, repository):
        """Long content strings are correctly stored and retrieved."""
        long_content = "A" * 10000  # 10k characters
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Long content test",
            content=long_content,
            confidence=0.7,
        )
        repository.insert_knowledge(knowledge)
        retrieved = repository.get_by_id(knowledge.id)
        assert len(retrieved.content) == 10000
        assert retrieved.content == long_content

    def test_special_characters_in_tag(self, repository, sample_knowledge):
        """Tags with special characters are handled correctly."""
        repository.insert_knowledge(sample_knowledge)
        special_tags = ["vitamin-d3", "omega_3", "b12/folate", "iron (ferritin)"]
        for tag_value in special_tags:
            tag = KnowledgeTag(
                id=uuid4(),
                knowledge_id=sample_knowledge.id,
                tag=tag_value,
            )
            repository.insert_tag(tag)
            result = repository.get_by_tag(tag_value)
            assert len(result) == 1

    def test_empty_database_queries(self, repository):
        """Queries on empty database return appropriate empty results."""
        assert repository.get_by_id(uuid4()) is None
        assert repository.get_active() == []
        assert repository.get_by_tag("any-tag") == []
        assert repository.get_by_link(LinkType.SNP, uuid4()) == []
