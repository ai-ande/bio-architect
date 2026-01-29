"""Tests for KnowledgeRepository."""

from uuid import uuid4

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
from src.databases.datatypes.knowledge.repository import KnowledgeRepository


@pytest.fixture
def db_client(tmp_path):
    """Create a test database client with schema initialized."""
    db_path = tmp_path / "test.db"
    client = DatabaseClient(db_path=db_path)
    client.init_schema()
    yield client
    client.close()


@pytest.fixture
def db_session(db_client):
    """Create a database session for testing."""
    with db_client.get_session() as session:
        yield session


@pytest.fixture
def repo(db_session):
    """Create a KnowledgeRepository instance."""
    return KnowledgeRepository(db_session)


@pytest.fixture
def sample_knowledge(db_session) -> Knowledge:
    """Create a sample knowledge entry with tags and links."""
    knowledge = Knowledge(
        type=KnowledgeType.INSIGHT,
        summary="Test insight",
        content="This is a test insight.",
        confidence=0.8,
    )
    db_session.add(knowledge)
    db_session.flush()

    tag = KnowledgeTag(knowledge_id=knowledge.id, tag="test")
    db_session.add(tag)
    db_session.commit()

    return knowledge


class TestGetKnowledge:
    """Tests for get_knowledge method."""

    def test_returns_knowledge_by_id(self, repo, sample_knowledge):
        """Should return knowledge when found."""
        knowledge = repo.get_knowledge(sample_knowledge.id)
        assert knowledge is not None
        assert knowledge.id == sample_knowledge.id

    def test_returns_none_when_not_found(self, repo):
        """Should return None when knowledge not found."""
        knowledge = repo.get_knowledge(uuid4())
        assert knowledge is None


class TestGetTagsForKnowledge:
    """Tests for get_tags_for_knowledge method."""

    def test_returns_tags(self, repo, sample_knowledge):
        """Should return tags for knowledge entry."""
        tags = repo.get_tags_for_knowledge(sample_knowledge.id)
        assert len(tags) == 1
        assert tags[0].tag == "test"


class TestListActive:
    """Tests for list_active method."""

    def test_returns_active_entries(self, repo, sample_knowledge):
        """Should return only active knowledge entries."""
        entries = repo.list_active()
        assert len(entries) == 1
        assert entries[0].status == KnowledgeStatus.ACTIVE

    def test_excludes_deprecated_entries(self, repo, db_session):
        """Should exclude deprecated entries."""
        deprecated = Knowledge(
            type=KnowledgeType.INSIGHT,
            status=KnowledgeStatus.DEPRECATED,
            summary="Deprecated",
            content="This is deprecated.",
            confidence=0.5,
        )
        db_session.add(deprecated)
        db_session.commit()

        entries = repo.list_active()
        assert len(entries) == 0


class TestGetByTag:
    """Tests for get_by_tag method."""

    def test_returns_entries_with_tag(self, repo, sample_knowledge):
        """Should return entries with the specified tag."""
        entries = repo.get_by_tag("test")
        assert len(entries) == 1
        assert entries[0].id == sample_knowledge.id

    def test_returns_empty_when_tag_not_found(self, repo):
        """Should return empty list when tag not found."""
        entries = repo.get_by_tag("nonexistent")
        assert entries == []


class TestSaveKnowledge:
    """Tests for save_knowledge method."""

    def test_saves_knowledge_with_tags_and_links(self, repo):
        """Should save knowledge, tags, and links."""
        knowledge = Knowledge(
            type=KnowledgeType.RECOMMENDATION,
            summary="Test recommendation",
            content="This is a test.",
            confidence=0.9,
        )
        tag = KnowledgeTag(knowledge_id=knowledge.id, tag="new-tag")

        repo.save_knowledge(knowledge, [tag], [])

        saved = repo.get_knowledge(knowledge.id)
        assert saved is not None
        assert saved.summary == "Test recommendation"

        tags = repo.get_tags_for_knowledge(knowledge.id)
        assert len(tags) == 1


class TestSupersede:
    """Tests for supersede method."""

    def test_supersedes_existing_entry(self, repo, sample_knowledge):
        """Should supersede existing entry and mark as deprecated."""
        new_knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Updated insight",
            content="This replaces the old insight.",
            confidence=0.9,
        )
        new_tag = KnowledgeTag(knowledge_id=new_knowledge.id, tag="updated")

        repo.supersede(sample_knowledge.id, new_knowledge, [new_tag], [])

        # Old should be deprecated
        old = repo.get_knowledge(sample_knowledge.id)
        assert old.status == KnowledgeStatus.DEPRECATED

        # New should reference old
        new = repo.get_knowledge(new_knowledge.id)
        assert new.supersedes_id == sample_knowledge.id

    def test_raises_when_old_not_found(self, repo):
        """Should raise when old knowledge not found."""
        new_knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="New insight",
            content="Content",
            confidence=0.9,
        )
        with pytest.raises(ValueError):
            repo.supersede(uuid4(), new_knowledge, [], [])
