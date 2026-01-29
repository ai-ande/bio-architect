"""Tests for ProtocolRepository."""

import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement_protocol import (
    Frequency,
    ProtocolSupplement,
    ProtocolSupplementType,
    SupplementProtocol,
)
from src.databases.repositories.protocol import ProtocolRepository


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
    """Create a ProtocolRepository with the test database."""
    return ProtocolRepository(db_client)


@pytest.fixture
def sample_protocol():
    """Create a sample SupplementProtocol."""
    return SupplementProtocol(
        id=uuid4(),
        protocol_date=date(2024, 1, 15),
        prescriber="Dr. Smith",
        next_visit="3 months",
        source_file="protocol.pdf",
        created_at=datetime(2024, 1, 20, 10, 30, 0),
        protein_goal="120g daily",
        lifestyle_notes=["Exercise 3x/week", "Get 8 hours sleep"],
    )


@pytest.fixture
def sample_supplement(sample_protocol):
    """Create a sample ProtocolSupplement."""
    return ProtocolSupplement(
        id=uuid4(),
        protocol_id=sample_protocol.id,
        supplement_label_id=None,
        type=ProtocolSupplementType.SCHEDULED,
        name="Vitamin D3",
        instructions="Take with food",
        dosage="5000 IU",
        frequency=Frequency.DAILY,
        upon_waking=0,
        breakfast=1,
        mid_morning=0,
        lunch=0,
        mid_afternoon=0,
        dinner=0,
        before_sleep=0,
    )


class TestInsertProtocol:
    """Tests for insert_protocol method."""

    def test_insert_protocol_returns_model(self, repository, sample_protocol):
        """insert_protocol returns the inserted SupplementProtocol model."""
        result = repository.insert_protocol(sample_protocol)
        assert isinstance(result, SupplementProtocol)
        assert result.id == sample_protocol.id
        assert result.prescriber == sample_protocol.prescriber

    def test_insert_protocol_persists_data(self, repository, sample_protocol):
        """insert_protocol persists data to database."""
        repository.insert_protocol(sample_protocol)
        retrieved = repository.get_protocol_by_id(sample_protocol.id)
        assert retrieved is not None
        assert retrieved.id == sample_protocol.id
        assert retrieved.prescriber == sample_protocol.prescriber
        assert retrieved.protocol_date == sample_protocol.protocol_date
        assert retrieved.source_file == sample_protocol.source_file

    def test_insert_protocol_preserves_all_fields(self, repository):
        """insert_protocol preserves all fields including created_at and lifestyle_notes."""
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2023, 6, 1),
            prescriber="Dr. Jones",
            next_visit="6 months",
            source_file="protocol_v2.pdf",
            created_at=datetime(2023, 6, 5, 14, 0, 0),
            protein_goal="100g daily",
            lifestyle_notes=["Meditation", "Reduce caffeine"],
        )
        repository.insert_protocol(protocol)
        retrieved = repository.get_protocol_by_id(protocol.id)
        assert retrieved.created_at == protocol.created_at
        assert retrieved.protein_goal == protocol.protein_goal
        assert retrieved.lifestyle_notes == protocol.lifestyle_notes

    def test_insert_protocol_with_null_optional_fields(self, repository):
        """insert_protocol handles null optional fields."""
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 1, 1),
            prescriber=None,
            next_visit=None,
            source_file=None,
            protein_goal=None,
            lifestyle_notes=[],
        )
        repository.insert_protocol(protocol)
        retrieved = repository.get_protocol_by_id(protocol.id)
        assert retrieved.prescriber is None
        assert retrieved.next_visit is None
        assert retrieved.source_file is None
        assert retrieved.protein_goal is None
        assert retrieved.lifestyle_notes == []

    def test_insert_protocol_with_empty_lifestyle_notes(self, repository):
        """insert_protocol handles empty lifestyle_notes list."""
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 2, 1),
            lifestyle_notes=[],
        )
        repository.insert_protocol(protocol)
        retrieved = repository.get_protocol_by_id(protocol.id)
        assert retrieved.lifestyle_notes == []


class TestInsertSupplement:
    """Tests for insert_supplement method."""

    def test_insert_supplement_returns_model(self, repository, sample_protocol, sample_supplement):
        """insert_supplement returns the inserted ProtocolSupplement model."""
        repository.insert_protocol(sample_protocol)
        result = repository.insert_supplement(sample_supplement)
        assert isinstance(result, ProtocolSupplement)
        assert result.id == sample_supplement.id
        assert result.name == sample_supplement.name

    def test_insert_supplement_persists_data(self, repository, sample_protocol, sample_supplement):
        """insert_supplement persists data to database."""
        repository.insert_protocol(sample_protocol)
        repository.insert_supplement(sample_supplement)
        # Verify by querying directly from the connection
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM protocol_supplements WHERE id = ?", (str(sample_supplement.id),))
        row = cursor.fetchone()
        assert row is not None
        assert row["name"] == sample_supplement.name
        assert row["protocol_id"] == str(sample_protocol.id)

    def test_insert_supplement_with_own_type(self, repository, sample_protocol):
        """insert_supplement handles OWN type supplements."""
        repository.insert_protocol(sample_protocol)
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=sample_protocol.id,
            type=ProtocolSupplementType.OWN,
            name="Fish Oil",
            dosage="2 capsules",
            frequency=Frequency.DAILY,
        )
        result = repository.insert_supplement(supplement)
        assert result.type == ProtocolSupplementType.OWN

    def test_insert_supplement_with_all_schedule_fields(self, repository, sample_protocol):
        """insert_supplement handles all daily schedule fields."""
        repository.insert_protocol(sample_protocol)
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=sample_protocol.id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Multi-Vitamin",
            frequency=Frequency.TWICE_DAILY,
            upon_waking=1,
            breakfast=2,
            mid_morning=1,
            lunch=2,
            mid_afternoon=1,
            dinner=2,
            before_sleep=1,
        )
        repository.insert_supplement(supplement)
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM protocol_supplements WHERE id = ?", (str(supplement.id),))
        row = cursor.fetchone()
        assert row["upon_waking"] == 1
        assert row["breakfast"] == 2
        assert row["mid_morning"] == 1
        assert row["lunch"] == 2
        assert row["mid_afternoon"] == 1
        assert row["dinner"] == 2
        assert row["before_sleep"] == 1

    def test_insert_supplement_with_null_optional_fields(self, repository, sample_protocol):
        """insert_supplement handles null optional fields."""
        repository.insert_protocol(sample_protocol)
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=sample_protocol.id,
            supplement_label_id=None,
            type=ProtocolSupplementType.SCHEDULED,
            name="Zinc",
            instructions=None,
            dosage=None,
            frequency=Frequency.DAILY,
        )
        repository.insert_supplement(supplement)
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM protocol_supplements WHERE id = ?", (str(supplement.id),))
        row = cursor.fetchone()
        assert row["instructions"] is None
        assert row["dosage"] is None
        assert row["supplement_label_id"] is None

    def test_insert_supplement_with_different_frequencies(self, repository, sample_protocol):
        """insert_supplement handles all frequency types."""
        repository.insert_protocol(sample_protocol)
        frequencies = [Frequency.DAILY, Frequency.TWICE_DAILY, Frequency.TWICE_WEEKLY, Frequency.AS_NEEDED]
        for freq in frequencies:
            supplement = ProtocolSupplement(
                id=uuid4(),
                protocol_id=sample_protocol.id,
                type=ProtocolSupplementType.SCHEDULED,
                name=f"Supplement {freq.value}",
                frequency=freq,
            )
            result = repository.insert_supplement(supplement)
            assert result.frequency == freq


class TestGetProtocolById:
    """Tests for get_protocol_by_id method."""

    def test_get_protocol_by_id_returns_model(self, repository, sample_protocol):
        """get_protocol_by_id returns SupplementProtocol model."""
        repository.insert_protocol(sample_protocol)
        result = repository.get_protocol_by_id(sample_protocol.id)
        assert isinstance(result, SupplementProtocol)

    def test_get_protocol_by_id_not_found_returns_none(self, repository):
        """get_protocol_by_id returns None when not found."""
        result = repository.get_protocol_by_id(uuid4())
        assert result is None

    def test_get_protocol_by_id_returns_correct_protocol(self, repository):
        """get_protocol_by_id returns the correct protocol when multiple exist."""
        protocol1 = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 1, 1),
            prescriber="Dr. Smith",
        )
        protocol2 = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 2, 1),
            prescriber="Dr. Jones",
        )
        repository.insert_protocol(protocol1)
        repository.insert_protocol(protocol2)
        result = repository.get_protocol_by_id(protocol2.id)
        assert result.prescriber == "Dr. Jones"


class TestGetCurrentProtocol:
    """Tests for get_current_protocol method."""

    def test_get_current_protocol_returns_model(self, repository, sample_protocol):
        """get_current_protocol returns SupplementProtocol model."""
        repository.insert_protocol(sample_protocol)
        result = repository.get_current_protocol()
        assert isinstance(result, SupplementProtocol)

    def test_get_current_protocol_returns_none_when_empty(self, repository):
        """get_current_protocol returns None when no protocols exist."""
        result = repository.get_current_protocol()
        assert result is None

    def test_get_current_protocol_returns_most_recent(self, repository):
        """get_current_protocol returns the most recent protocol by date."""
        protocol_old = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 1, 1),
            prescriber="Dr. Old",
        )
        protocol_new = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 6, 1),
            prescriber="Dr. New",
        )
        # Insert in reverse order to ensure ordering works
        repository.insert_protocol(protocol_new)
        repository.insert_protocol(protocol_old)
        result = repository.get_current_protocol()
        assert result.prescriber == "Dr. New"
        assert result.protocol_date == date(2024, 6, 1)

    def test_get_current_protocol_with_multiple_protocols(self, repository):
        """get_current_protocol returns correct protocol when many exist."""
        dates = [date(2024, 3, 1), date(2024, 1, 1), date(2024, 5, 1), date(2024, 2, 1)]
        for i, d in enumerate(dates):
            protocol = SupplementProtocol(
                id=uuid4(),
                protocol_date=d,
                prescriber=f"Dr. {i}",
            )
            repository.insert_protocol(protocol)
        result = repository.get_current_protocol()
        # May (5th month) is most recent
        assert result.protocol_date == date(2024, 5, 1)


class TestGetProtocolHistory:
    """Tests for get_protocol_history method."""

    def test_get_protocol_history_returns_list(self, repository, sample_protocol):
        """get_protocol_history returns a list."""
        repository.insert_protocol(sample_protocol)
        result = repository.get_protocol_history()
        assert isinstance(result, list)

    def test_get_protocol_history_returns_protocol_models(self, repository, sample_protocol):
        """get_protocol_history returns SupplementProtocol models."""
        repository.insert_protocol(sample_protocol)
        result = repository.get_protocol_history()
        assert len(result) == 1
        assert isinstance(result[0], SupplementProtocol)

    def test_get_protocol_history_returns_empty_list(self, repository):
        """get_protocol_history returns empty list when no protocols."""
        result = repository.get_protocol_history()
        assert result == []

    def test_get_protocol_history_ordered_by_date_desc(self, repository):
        """get_protocol_history returns results ordered by protocol_date descending."""
        dates = [date(2024, 1, 1), date(2024, 3, 1), date(2024, 2, 1)]
        for d in dates:
            protocol = SupplementProtocol(
                id=uuid4(),
                protocol_date=d,
                prescriber=f"Dr. {d.month}",
            )
            repository.insert_protocol(protocol)
        result = repository.get_protocol_history()
        assert len(result) == 3
        # Should be ordered: March, Feb, Jan
        assert result[0].protocol_date == date(2024, 3, 1)
        assert result[1].protocol_date == date(2024, 2, 1)
        assert result[2].protocol_date == date(2024, 1, 1)

    def test_get_protocol_history_returns_all_protocols(self, repository):
        """get_protocol_history returns all protocols."""
        for i in range(5):
            protocol = SupplementProtocol(
                id=uuid4(),
                protocol_date=date(2024, i + 1, 1),
            )
            repository.insert_protocol(protocol)
        result = repository.get_protocol_history()
        assert len(result) == 5


class TestEdgeCases:
    """Edge case tests."""

    def test_uuid_roundtrip(self, repository, sample_protocol):
        """UUIDs are correctly stored and retrieved."""
        repository.insert_protocol(sample_protocol)
        retrieved = repository.get_protocol_by_id(sample_protocol.id)
        assert isinstance(retrieved.id, UUID)
        assert retrieved.id == sample_protocol.id

    def test_date_roundtrip(self, repository):
        """Dates are correctly stored and retrieved."""
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2020, 12, 31),
        )
        repository.insert_protocol(protocol)
        retrieved = repository.get_protocol_by_id(protocol.id)
        assert isinstance(retrieved.protocol_date, date)
        assert retrieved.protocol_date == date(2020, 12, 31)

    def test_datetime_roundtrip(self, repository):
        """Datetimes are correctly stored and retrieved."""
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2020, 12, 31),
            created_at=datetime(2021, 1, 1, 12, 30, 45),
        )
        repository.insert_protocol(protocol)
        retrieved = repository.get_protocol_by_id(protocol.id)
        assert isinstance(retrieved.created_at, datetime)
        assert retrieved.created_at == datetime(2021, 1, 1, 12, 30, 45)

    def test_lifestyle_notes_roundtrip(self, repository):
        """Lifestyle notes list is correctly stored and retrieved."""
        notes = ["Exercise daily", "Limit sugar", "Stay hydrated", "Sleep 8 hours"]
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 1, 1),
            lifestyle_notes=notes,
        )
        repository.insert_protocol(protocol)
        retrieved = repository.get_protocol_by_id(protocol.id)
        assert retrieved.lifestyle_notes == notes

    def test_protocol_supplement_type_roundtrip(self, repository, sample_protocol):
        """ProtocolSupplementType enum is correctly stored and retrieved."""
        repository.insert_protocol(sample_protocol)
        for ptype in [ProtocolSupplementType.SCHEDULED, ProtocolSupplementType.OWN]:
            supplement = ProtocolSupplement(
                id=uuid4(),
                protocol_id=sample_protocol.id,
                type=ptype,
                name=f"Supplement {ptype.value}",
                frequency=Frequency.DAILY,
            )
            repository.insert_supplement(supplement)
            # Verify via direct query using _row_to_supplement
            conn = repository._client.connection
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM protocol_supplements WHERE id = ?", (str(supplement.id),))
            row = cursor.fetchone()
            converted = repository._row_to_supplement(row)
            assert converted.type == ptype

    def test_frequency_roundtrip(self, repository, sample_protocol):
        """Frequency enum is correctly stored and retrieved."""
        repository.insert_protocol(sample_protocol)
        for freq in Frequency:
            supplement = ProtocolSupplement(
                id=uuid4(),
                protocol_id=sample_protocol.id,
                type=ProtocolSupplementType.SCHEDULED,
                name=f"Supplement {freq.value}",
                frequency=freq,
            )
            repository.insert_supplement(supplement)
            conn = repository._client.connection
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM protocol_supplements WHERE id = ?", (str(supplement.id),))
            row = cursor.fetchone()
            converted = repository._row_to_supplement(row)
            assert converted.frequency == freq

    def test_schedule_fields_default_to_zero(self, repository, sample_protocol):
        """Schedule fields default to 0 when not specified."""
        repository.insert_protocol(sample_protocol)
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=sample_protocol.id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Magnesium",
            frequency=Frequency.DAILY,
        )
        repository.insert_supplement(supplement)
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM protocol_supplements WHERE id = ?", (str(supplement.id),))
        row = cursor.fetchone()
        assert row["upon_waking"] == 0
        assert row["breakfast"] == 0
        assert row["mid_morning"] == 0
        assert row["lunch"] == 0
        assert row["mid_afternoon"] == 0
        assert row["dinner"] == 0
        assert row["before_sleep"] == 0
