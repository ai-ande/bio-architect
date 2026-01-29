"""Tests for supplement protocol models."""

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.databases.datatypes.supplement_protocol import (
    Frequency,
    ProtocolSupplement,
    ProtocolSupplementType,
    SupplementProtocol,
)


class TestFrequency:
    """Tests for Frequency enum."""

    def test_frequency_values(self):
        assert Frequency.DAILY.value == "daily"
        assert Frequency.TWICE_DAILY.value == "2x_daily"
        assert Frequency.TWICE_WEEKLY.value == "2x_week"
        assert Frequency.AS_NEEDED.value == "as_needed"

    def test_frequency_is_string_enum(self):
        assert isinstance(Frequency.DAILY, str)
        assert Frequency.DAILY == "daily"


class TestProtocolSupplementType:
    """Tests for ProtocolSupplementType enum."""

    def test_type_values(self):
        assert ProtocolSupplementType.SCHEDULED.value == "scheduled"
        assert ProtocolSupplementType.OWN.value == "own"

    def test_type_is_string_enum(self):
        assert isinstance(ProtocolSupplementType.SCHEDULED, str)
        assert ProtocolSupplementType.SCHEDULED == "scheduled"


class TestProtocolSupplement:
    """Tests for ProtocolSupplement model."""

    @pytest.fixture
    def protocol_id(self) -> UUID:
        """Create a protocol ID for testing."""
        return uuid4()

    def test_create_scheduled_supplement(self, protocol_id: UUID):
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Vitamin D",
            frequency=Frequency.DAILY,
        )
        assert supp.name == "Vitamin D"
        assert supp.type == ProtocolSupplementType.SCHEDULED
        assert supp.frequency == Frequency.DAILY
        assert supp.protocol_id == protocol_id
        assert supp.instructions is None
        assert supp.dosage is None
        assert supp.supplement_label_id is None

    def test_create_own_supplement(self, protocol_id: UUID):
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.OWN,
            name="Zinc30",
            dosage="1/day",
            frequency=Frequency.DAILY,
        )
        assert supp.name == "Zinc30"
        assert supp.type == ProtocolSupplementType.OWN
        assert supp.dosage == "1/day"
        assert supp.frequency == Frequency.DAILY

    def test_supplement_has_uuid(self, protocol_id: UUID):
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Test",
            frequency=Frequency.DAILY,
        )
        assert isinstance(supp.id, UUID)

    def test_supplement_uuid_is_unique(self, protocol_id: UUID):
        s1 = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Test",
            frequency=Frequency.DAILY,
        )
        s2 = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Test",
            frequency=Frequency.DAILY,
        )
        assert s1.id != s2.id

    def test_supplement_with_instructions(self, protocol_id: UUID):
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Gastro Digest",
            frequency=Frequency.DAILY,
            instructions="5-10 minutes before meals",
        )
        assert supp.instructions == "5-10 minutes before meals"

    def test_supplement_with_label_reference(self, protocol_id: UUID):
        label_id = uuid4()
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Zinc30",
            frequency=Frequency.DAILY,
            supplement_label_id=label_id,
        )
        assert supp.supplement_label_id == label_id

    def test_supplement_default_schedule_values(self, protocol_id: UUID):
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Test",
            frequency=Frequency.DAILY,
        )
        assert supp.upon_waking == 0
        assert supp.breakfast == 0
        assert supp.mid_morning == 0
        assert supp.lunch == 0
        assert supp.mid_afternoon == 0
        assert supp.dinner == 0
        assert supp.before_sleep == 0

    def test_supplement_with_schedule(self, protocol_id: UUID):
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="KL Support",
            frequency=Frequency.DAILY,
            breakfast=1,
            dinner=1,
        )
        assert supp.breakfast == 1
        assert supp.dinner == 1
        assert supp.lunch == 0  # default

    def test_supplement_with_upon_waking(self, protocol_id: UUID):
        supp = ProtocolSupplement(
            protocol_id=protocol_id,
            type=ProtocolSupplementType.SCHEDULED,
            name="Perfect Aminos",
            frequency=Frequency.DAILY,
            instructions="1 scoop",
            upon_waking=1,
        )
        assert supp.upon_waking == 1
        assert supp.instructions == "1 scoop"

    def test_supplement_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            ProtocolSupplement.model_validate({
                "name": "Test",
                "type": ProtocolSupplementType.SCHEDULED,
                "frequency": Frequency.DAILY,
            })  # missing protocol_id

    def test_supplement_missing_type_raises(self):
        with pytest.raises(ValidationError):
            ProtocolSupplement.model_validate({
                "protocol_id": uuid4(),
                "name": "Test",
                "frequency": Frequency.DAILY,
            })  # missing type


class TestSupplementProtocol:
    """Tests for SupplementProtocol model."""

    def test_create_minimal_protocol(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 1, 1),
        )
        assert protocol.protocol_date == date(2025, 1, 1)

    def test_protocol_has_uuid(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 1, 1),
        )
        assert isinstance(protocol.id, UUID)

    def test_protocol_uuid_is_unique(self):
        p1 = SupplementProtocol(protocol_date=date(2025, 1, 1))
        p2 = SupplementProtocol(protocol_date=date(2025, 1, 1))
        assert p1.id != p2.id

    def test_protocol_has_created_at(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 1, 1),
        )
        assert isinstance(protocol.created_at, datetime)

    def test_protocol_optional_fields_default(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 1, 1),
        )
        assert protocol.prescriber is None
        assert protocol.next_visit is None
        assert protocol.source_file is None
        assert protocol.protein_goal is None
        assert protocol.lifestyle_notes == []

    def test_protocol_with_prescriber(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 1, 1),
            prescriber="Dr. Smith",
        )
        assert protocol.prescriber == "Dr. Smith"

    def test_protocol_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            SupplementProtocol.model_validate({})  # missing protocol_date

    def test_protocol_with_protein_goal(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 12, 29),
            protein_goal="110g/day",
        )
        assert protocol.protein_goal == "110g/day"

    def test_protocol_with_lifestyle_notes(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 12, 29),
            lifestyle_notes=["Stay hydrated", "Exercise daily"],
        )
        assert len(protocol.lifestyle_notes) == 2
        assert "Stay hydrated" in protocol.lifestyle_notes
        assert "Exercise daily" in protocol.lifestyle_notes

    def test_protocol_with_next_visit(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 12, 29),
            next_visit="4 weeks",
        )
        assert protocol.next_visit == "4 weeks"

    def test_protocol_with_source_file(self):
        protocol = SupplementProtocol(
            protocol_date=date(2025, 12, 29),
            source_file="protocol.pdf",
        )
        assert protocol.source_file == "protocol.pdf"

    def test_protocol_does_not_have_patient_name(self):
        """Verify patient_name field was removed."""
        protocol = SupplementProtocol(protocol_date=date(2025, 1, 1))
        assert not hasattr(protocol, "patient_name") or "patient_name" not in protocol.model_fields

    def test_protocol_does_not_have_nested_supplements(self):
        """Verify nested supplements and own_supplements lists were removed."""
        protocol = SupplementProtocol(protocol_date=date(2025, 1, 1))
        assert not hasattr(protocol, "supplements") or "supplements" not in protocol.model_fields
        assert not hasattr(protocol, "own_supplements") or "own_supplements" not in protocol.model_fields

    def test_protocol_does_not_have_helper_methods(self):
        """Verify helper methods were removed."""
        protocol = SupplementProtocol(protocol_date=date(2025, 1, 1))
        assert not hasattr(protocol, "get_all_supplements")
        assert not hasattr(protocol, "get_supplement_by_name")


class TestRemovedModels:
    """Tests to verify old models were removed."""

    def test_daily_schedule_not_exported(self):
        """Verify DailySchedule is no longer exported."""
        from src.databases.datatypes import supplement_protocol
        assert not hasattr(supplement_protocol, "DailySchedule")

    def test_scheduled_supplement_not_exported(self):
        """Verify ScheduledSupplement is no longer exported."""
        from src.databases.datatypes import supplement_protocol
        assert not hasattr(supplement_protocol, "ScheduledSupplement")

    def test_own_supplement_not_exported(self):
        """Verify OwnSupplement is no longer exported."""
        from src.databases.datatypes import supplement_protocol
        assert not hasattr(supplement_protocol, "OwnSupplement")

    def test_lifestyle_notes_not_exported(self):
        """Verify LifestyleNotes is no longer exported."""
        from src.databases.datatypes import supplement_protocol
        assert not hasattr(supplement_protocol, "LifestyleNotes")
