"""Tests for SupplementProtocolRepository."""

from datetime import date
from uuid import uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement_protocol import (
    Frequency,
    ProtocolSupplement,
    ProtocolSupplementType,
    SupplementProtocol,
)
from src.databases.datatypes.supplement_protocol.repository import (
    SupplementProtocolRepository,
)


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
    """Create a SupplementProtocolRepository instance."""
    return SupplementProtocolRepository(db_session)


@pytest.fixture
def sample_protocol(db_session) -> SupplementProtocol:
    """Create a sample protocol with supplements."""
    protocol = SupplementProtocol(
        protocol_date=date(2024, 1, 15),
        prescriber="Dr. Test",
        source_file="test.json",
    )
    db_session.add(protocol)
    db_session.flush()

    supplement = ProtocolSupplement(
        protocol_id=protocol.id,
        type=ProtocolSupplementType.SCHEDULED,
        name="Vitamin D3",
        frequency=Frequency.DAILY,
        dosage="5000 IU",
    )
    db_session.add(supplement)
    db_session.commit()

    return protocol


class TestListProtocols:
    """Tests for list_protocols method."""

    def test_returns_empty_when_no_protocols(self, repo):
        """Should return empty list when no protocols exist."""
        protocols = repo.list_protocols()
        assert protocols == []

    def test_returns_all_protocols(self, repo, sample_protocol):
        """Should return all protocols."""
        protocols = repo.list_protocols()
        assert len(protocols) == 1
        assert protocols[0].id == sample_protocol.id

    def test_orders_by_date_descending(self, repo, db_session):
        """Should order protocols by date descending."""
        older = SupplementProtocol(
            protocol_date=date(2023, 1, 1),
            prescriber="Dr. Old",
        )
        db_session.add(older)

        newer = SupplementProtocol(
            protocol_date=date(2024, 6, 15),
            prescriber="Dr. New",
        )
        db_session.add(newer)
        db_session.commit()

        protocols = repo.list_protocols()
        assert len(protocols) == 2
        assert protocols[0].protocol_date == date(2024, 6, 15)
        assert protocols[1].protocol_date == date(2023, 1, 1)


class TestGetProtocol:
    """Tests for get_protocol method."""

    def test_returns_protocol_by_id(self, repo, sample_protocol):
        """Should return protocol when found."""
        protocol = repo.get_protocol(sample_protocol.id)
        assert protocol is not None
        assert protocol.id == sample_protocol.id

    def test_returns_none_when_not_found(self, repo):
        """Should return None when protocol not found."""
        protocol = repo.get_protocol(uuid4())
        assert protocol is None


class TestGetCurrentProtocol:
    """Tests for get_current_protocol method."""

    def test_returns_most_recent(self, repo, sample_protocol):
        """Should return the most recent protocol."""
        current = repo.get_current_protocol()
        assert current is not None
        assert current.id == sample_protocol.id

    def test_returns_none_when_no_protocols(self, repo):
        """Should return None when no protocols exist."""
        current = repo.get_current_protocol()
        assert current is None


class TestSaveProtocol:
    """Tests for save_protocol method."""

    def test_saves_protocol_with_supplements(self, repo):
        """Should save protocol and supplements atomically."""
        protocol = SupplementProtocol(
            protocol_date=date(2024, 2, 15),
            prescriber="Dr. New",
        )
        supplement = ProtocolSupplement(
            protocol_id=protocol.id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Magnesium",
            frequency=Frequency.DAILY,
        )

        repo.save_protocol(protocol, [supplement])

        saved = repo.get_protocol(protocol.id)
        assert saved is not None
        assert saved.prescriber == "Dr. New"

        supplements = repo.get_supplements_for_protocol(protocol.id)
        assert len(supplements) == 1
