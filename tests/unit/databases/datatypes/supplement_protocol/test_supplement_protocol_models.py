"""Tests for supplement protocol models."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from src.databases.datatypes.supplement_protocol import (
    DailySchedule,
    Frequency,
    LifestyleNotes,
    OwnSupplement,
    ScheduledSupplement,
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


class TestDailySchedule:
    """Tests for DailySchedule model."""

    def test_create_default_schedule(self):
        schedule = DailySchedule()
        assert schedule.upon_waking == 0
        assert schedule.breakfast == 0
        assert schedule.mid_morning == 0
        assert schedule.lunch == 0
        assert schedule.mid_afternoon == 0
        assert schedule.dinner == 0
        assert schedule.before_sleep == 0

    def test_create_schedule_with_values(self):
        schedule = DailySchedule(
            upon_waking=1,
            breakfast=2,
            dinner=1,
        )
        assert schedule.upon_waking == 1
        assert schedule.breakfast == 2
        assert schedule.dinner == 1
        assert schedule.lunch == 0  # default

    def test_schedule_has_uuid(self):
        schedule = DailySchedule()
        assert isinstance(schedule.id, UUID)

    def test_schedule_uuid_is_unique(self):
        s1 = DailySchedule()
        s2 = DailySchedule()
        assert s1.id != s2.id


class TestScheduledSupplement:
    """Tests for ScheduledSupplement model."""

    def test_create_minimal_supplement(self):
        supp = ScheduledSupplement(
            name="Vitamin D",
            frequency=Frequency.DAILY,
        )
        assert supp.name == "Vitamin D"
        assert supp.frequency == Frequency.DAILY
        assert supp.instructions is None
        assert supp.schedule is not None
        assert supp.supplement_label_id is None

    def test_supplement_has_uuid(self):
        supp = ScheduledSupplement(name="Test", frequency=Frequency.DAILY)
        assert isinstance(supp.id, UUID)

    def test_supplement_uuid_is_unique(self):
        s1 = ScheduledSupplement(name="Test", frequency=Frequency.DAILY)
        s2 = ScheduledSupplement(name="Test", frequency=Frequency.DAILY)
        assert s1.id != s2.id

    def test_supplement_with_instructions(self):
        supp = ScheduledSupplement(
            name="Gastro Digest",
            frequency=Frequency.DAILY,
            instructions="5-10 minutes before meals",
        )
        assert supp.instructions == "5-10 minutes before meals"

    def test_supplement_with_schedule(self):
        schedule = DailySchedule(breakfast=1, dinner=1)
        supp = ScheduledSupplement(
            name="KL Support",
            frequency=Frequency.DAILY,
            schedule=schedule,
        )
        assert supp.schedule.breakfast == 1
        assert supp.schedule.dinner == 1

    def test_supplement_with_label_reference(self):
        label_id = uuid4()
        supp = ScheduledSupplement(
            name="Zinc30",
            frequency=Frequency.DAILY,
            supplement_label_id=label_id,
        )
        assert supp.supplement_label_id == label_id


class TestOwnSupplement:
    """Tests for OwnSupplement model."""

    def test_create_own_supplement(self):
        supp = OwnSupplement(
            name="Zinc30",
            dosage="1/day",
            frequency=Frequency.DAILY,
        )
        assert supp.name == "Zinc30"
        assert supp.dosage == "1/day"
        assert supp.frequency == Frequency.DAILY
        assert supp.supplement_label_id is None

    def test_own_supplement_has_uuid(self):
        supp = OwnSupplement(name="Test", dosage="1/day", frequency=Frequency.DAILY)
        assert isinstance(supp.id, UUID)

    def test_own_supplement_uuid_is_unique(self):
        s1 = OwnSupplement(name="Test", dosage="1/day", frequency=Frequency.DAILY)
        s2 = OwnSupplement(name="Test", dosage="1/day", frequency=Frequency.DAILY)
        assert s1.id != s2.id

    def test_own_supplement_optional_dosage(self):
        supp = OwnSupplement(name="Test", frequency=Frequency.DAILY)
        assert supp.dosage is None

    def test_own_supplement_with_label_reference(self):
        label_id = uuid4()
        supp = OwnSupplement(
            name="Zinc30",
            frequency=Frequency.DAILY,
            supplement_label_id=label_id,
        )
        assert supp.supplement_label_id == label_id

    def test_own_supplement_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            OwnSupplement(name="Test")  # missing frequency


class TestLifestyleNotes:
    """Tests for LifestyleNotes model."""

    def test_create_lifestyle_notes(self):
        notes = LifestyleNotes(
            protein_goal="110g/day",
            other=["Drink 8 glasses of water"],
        )
        assert notes.protein_goal == "110g/day"
        assert notes.other == ["Drink 8 glasses of water"]

    def test_lifestyle_notes_has_uuid(self):
        notes = LifestyleNotes()
        assert isinstance(notes.id, UUID)

    def test_lifestyle_notes_defaults(self):
        notes = LifestyleNotes()
        assert notes.protein_goal is None
        assert notes.other == []


class TestSupplementProtocol:
    """Tests for SupplementProtocol model."""

    @pytest.fixture
    def simple_protocol(self) -> SupplementProtocol:
        """Create a simple protocol for testing."""
        return SupplementProtocol(
            patient_name="Test Patient",
            protocol_date=date(2025, 12, 29),
            supplements=[
                ScheduledSupplement(
                    name="Perfect Aminos",
                    frequency=Frequency.DAILY,
                    instructions="1 scoop",
                    schedule=DailySchedule(upon_waking=1),
                ),
                ScheduledSupplement(
                    name="KL Support",
                    frequency=Frequency.DAILY,
                    schedule=DailySchedule(breakfast=1, dinner=1),
                ),
            ],
        )

    @pytest.fixture
    def full_protocol(self) -> SupplementProtocol:
        """Create a full protocol with all fields."""
        return SupplementProtocol(
            patient_name="Andy Kaplan",
            protocol_date=date(2025, 12, 29),
            prescriber="Dr. Smith",
            supplements=[
                ScheduledSupplement(
                    name="Methylgenic",
                    frequency=Frequency.DAILY,
                    instructions="take before noon",
                    schedule=DailySchedule(breakfast=2),
                ),
            ],
            own_supplements=[
                OwnSupplement(
                    name="Zinc30",
                    dosage="1/day",
                    frequency=Frequency.DAILY,
                ),
            ],
            lifestyle_notes=LifestyleNotes(
                protein_goal="110g/day",
                other=["Stay hydrated"],
            ),
            next_visit="4 weeks",
            source_file="protocol.pdf",
        )

    def test_create_minimal_protocol(self):
        protocol = SupplementProtocol(
            patient_name="Test Patient",
            protocol_date=date(2025, 1, 1),
        )
        assert protocol.patient_name == "Test Patient"
        assert protocol.protocol_date == date(2025, 1, 1)

    def test_protocol_has_uuid(self):
        protocol = SupplementProtocol(
            patient_name="Test",
            protocol_date=date(2025, 1, 1),
        )
        assert isinstance(protocol.id, UUID)

    def test_protocol_uuid_is_unique(self):
        p1 = SupplementProtocol(patient_name="Test", protocol_date=date(2025, 1, 1))
        p2 = SupplementProtocol(patient_name="Test", protocol_date=date(2025, 1, 1))
        assert p1.id != p2.id

    def test_protocol_optional_fields_default(self):
        protocol = SupplementProtocol(
            patient_name="Test",
            protocol_date=date(2025, 1, 1),
        )
        assert protocol.prescriber is None
        assert protocol.supplements == []
        assert protocol.own_supplements == []
        assert protocol.lifestyle_notes is None
        assert protocol.next_visit is None
        assert protocol.source_file is None

    def test_protocol_with_prescriber(self):
        protocol = SupplementProtocol(
            patient_name="Test",
            protocol_date=date(2025, 1, 1),
            prescriber="Dr. Smith",
        )
        assert protocol.prescriber == "Dr. Smith"

    def test_protocol_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            SupplementProtocol(patient_name="Test")  # missing protocol_date

    def test_get_all_supplements(self, full_protocol: SupplementProtocol):
        all_supps = full_protocol.get_all_supplements()
        assert len(all_supps) == 2
        names = [s.name for s in all_supps]
        assert "Methylgenic" in names
        assert "Zinc30" in names

    def test_get_all_supplements_scheduled_only(self, simple_protocol: SupplementProtocol):
        all_supps = simple_protocol.get_all_supplements()
        assert len(all_supps) == 2

    def test_get_supplement_by_name_found(self, simple_protocol: SupplementProtocol):
        supp = simple_protocol.get_supplement_by_name("Perfect Aminos")
        assert supp is not None
        assert supp.instructions == "1 scoop"

    def test_get_supplement_by_name_not_found(self, simple_protocol: SupplementProtocol):
        supp = simple_protocol.get_supplement_by_name("Nonexistent")
        assert supp is None

    def test_get_supplement_by_name_in_own(self, full_protocol: SupplementProtocol):
        supp = full_protocol.get_supplement_by_name("Zinc30")
        assert supp is not None
        assert supp.dosage == "1/day"

    def test_get_supplement_by_name_case_insensitive(
        self, simple_protocol: SupplementProtocol
    ):
        supp = simple_protocol.get_supplement_by_name("perfect aminos")
        assert supp is not None
        assert supp.name == "Perfect Aminos"
