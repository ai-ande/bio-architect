"""Tests for BloodworkRepository."""

import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.bloodwork import Biomarker, Flag, LabReport, Panel
from src.databases.repositories.bloodwork import BloodworkRepository


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
    """Create a BloodworkRepository with the test database."""
    return BloodworkRepository(db_client)


@pytest.fixture
def sample_report():
    """Create a sample LabReport."""
    return LabReport(
        id=uuid4(),
        lab_provider="LabCorp",
        collected_date=date(2024, 1, 15),
        source_file="lab_results.pdf",
        created_at=datetime(2024, 1, 20, 10, 30, 0),
    )


@pytest.fixture
def sample_panel(sample_report):
    """Create a sample Panel."""
    return Panel(
        id=uuid4(),
        lab_report_id=sample_report.id,
        name="Lipid Panel",
        comment="Fasting sample",
    )


@pytest.fixture
def sample_biomarker(sample_panel):
    """Create a sample Biomarker."""
    return Biomarker(
        id=uuid4(),
        panel_id=sample_panel.id,
        name="Total Cholesterol",
        code="CHOLESTEROL_TOTAL",
        value=195.0,
        unit="mg/dL",
        reference_low=100.0,
        reference_high=200.0,
        flag=Flag.NORMAL,
    )


class TestInsertReport:
    """Tests for insert_report method."""

    def test_insert_report_returns_model(self, repository, sample_report):
        """insert_report returns the inserted LabReport model."""
        result = repository.insert_report(sample_report)
        assert isinstance(result, LabReport)
        assert result.id == sample_report.id
        assert result.lab_provider == sample_report.lab_provider

    def test_insert_report_persists_data(self, repository, sample_report):
        """insert_report persists data to database."""
        repository.insert_report(sample_report)
        retrieved = repository.get_report_by_id(sample_report.id)
        assert retrieved is not None
        assert retrieved.id == sample_report.id
        assert retrieved.lab_provider == sample_report.lab_provider
        assert retrieved.collected_date == sample_report.collected_date
        assert retrieved.source_file == sample_report.source_file

    def test_insert_report_preserves_all_fields(self, repository):
        """insert_report preserves all fields including created_at."""
        report = LabReport(
            id=uuid4(),
            lab_provider="Quest Diagnostics",
            collected_date=date(2023, 6, 1),
            source_file="quest_labs.pdf",
            created_at=datetime(2023, 6, 5, 14, 0, 0),
        )
        repository.insert_report(report)
        retrieved = repository.get_report_by_id(report.id)
        assert retrieved.created_at == report.created_at

    def test_insert_report_with_null_source_file(self, repository):
        """insert_report handles null source_file."""
        report = LabReport(
            id=uuid4(),
            lab_provider="LabCorp",
            collected_date=date(2024, 1, 1),
            source_file=None,
        )
        repository.insert_report(report)
        retrieved = repository.get_report_by_id(report.id)
        assert retrieved.source_file is None


class TestInsertPanel:
    """Tests for insert_panel method."""

    def test_insert_panel_returns_model(self, repository, sample_report, sample_panel):
        """insert_panel returns the inserted Panel model."""
        repository.insert_report(sample_report)
        result = repository.insert_panel(sample_panel)
        assert isinstance(result, Panel)
        assert result.id == sample_panel.id
        assert result.name == sample_panel.name

    def test_insert_panel_persists_data(self, repository, sample_report, sample_panel):
        """insert_panel persists data to database."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        # Verify by querying directly from the connection
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panels WHERE id = ?", (str(sample_panel.id),))
        row = cursor.fetchone()
        assert row is not None
        assert row["name"] == sample_panel.name
        assert row["lab_report_id"] == str(sample_report.id)

    def test_insert_panel_with_null_comment(self, repository, sample_report):
        """insert_panel handles null comment."""
        repository.insert_report(sample_report)
        panel = Panel(
            id=uuid4(),
            lab_report_id=sample_report.id,
            name="CBC",
            comment=None,
        )
        repository.insert_panel(panel)
        conn = repository._client.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM panels WHERE id = ?", (str(panel.id),))
        row = cursor.fetchone()
        assert row["comment"] is None


class TestInsertBiomarker:
    """Tests for insert_biomarker method."""

    def test_insert_biomarker_returns_model(self, repository, sample_report, sample_panel, sample_biomarker):
        """insert_biomarker returns the inserted Biomarker model."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        result = repository.insert_biomarker(sample_biomarker)
        assert isinstance(result, Biomarker)
        assert result.id == sample_biomarker.id
        assert result.code == sample_biomarker.code

    def test_insert_biomarker_persists_data(self, repository, sample_report, sample_panel, sample_biomarker):
        """insert_biomarker persists data to database."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        retrieved = repository.get_biomarker_by_code(sample_biomarker.code)
        assert retrieved is not None
        assert retrieved.id == sample_biomarker.id
        assert retrieved.value == sample_biomarker.value
        assert retrieved.unit == sample_biomarker.unit

    def test_insert_biomarker_with_null_reference_range(self, repository, sample_report, sample_panel):
        """insert_biomarker handles null reference range values."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="HDL",
            code="HDL",
            value=55.0,
            unit="mg/dL",
            reference_low=None,
            reference_high=None,
            flag=Flag.NORMAL,
        )
        repository.insert_biomarker(biomarker)
        retrieved = repository.get_biomarker_by_code(biomarker.code)
        assert retrieved.reference_low is None
        assert retrieved.reference_high is None

    def test_insert_biomarker_with_high_flag(self, repository, sample_report, sample_panel):
        """insert_biomarker handles HIGH flag."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="LDL",
            code="LDL",
            value=180.0,
            unit="mg/dL",
            reference_low=0.0,
            reference_high=100.0,
            flag=Flag.HIGH,
        )
        repository.insert_biomarker(biomarker)
        retrieved = repository.get_biomarker_by_code(biomarker.code)
        assert retrieved.flag == Flag.HIGH


class TestGetReportById:
    """Tests for get_report_by_id method."""

    def test_get_report_by_id_returns_model(self, repository, sample_report):
        """get_report_by_id returns LabReport model."""
        repository.insert_report(sample_report)
        result = repository.get_report_by_id(sample_report.id)
        assert isinstance(result, LabReport)

    def test_get_report_by_id_not_found_returns_none(self, repository):
        """get_report_by_id returns None when not found."""
        result = repository.get_report_by_id(uuid4())
        assert result is None

    def test_get_report_by_id_returns_correct_report(self, repository):
        """get_report_by_id returns the correct report when multiple exist."""
        report1 = LabReport(
            id=uuid4(),
            lab_provider="LabCorp",
            collected_date=date(2024, 1, 1),
            source_file="report1.pdf",
        )
        report2 = LabReport(
            id=uuid4(),
            lab_provider="Quest",
            collected_date=date(2024, 2, 1),
            source_file="report2.pdf",
        )
        repository.insert_report(report1)
        repository.insert_report(report2)
        result = repository.get_report_by_id(report2.id)
        assert result.lab_provider == "Quest"


class TestGetBiomarkerByCode:
    """Tests for get_biomarker_by_code method."""

    def test_get_biomarker_by_code_returns_model(self, repository, sample_report, sample_panel, sample_biomarker):
        """get_biomarker_by_code returns Biomarker model."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        result = repository.get_biomarker_by_code(sample_biomarker.code)
        assert isinstance(result, Biomarker)

    def test_get_biomarker_by_code_not_found_returns_none(self, repository):
        """get_biomarker_by_code returns None when not found."""
        result = repository.get_biomarker_by_code("UNKNOWN_CODE")
        assert result is None

    def test_get_biomarker_by_code_returns_most_recent(self, repository):
        """get_biomarker_by_code returns the most recent biomarker."""
        # Create two reports with different dates
        report1 = LabReport(
            id=uuid4(),
            lab_provider="LabCorp",
            collected_date=date(2024, 1, 1),
            source_file="old.pdf",
        )
        report2 = LabReport(
            id=uuid4(),
            lab_provider="LabCorp",
            collected_date=date(2024, 6, 1),
            source_file="new.pdf",
        )
        repository.insert_report(report1)
        repository.insert_report(report2)

        panel1 = Panel(id=uuid4(), lab_report_id=report1.id, name="CBC")
        panel2 = Panel(id=uuid4(), lab_report_id=report2.id, name="CBC")
        repository.insert_panel(panel1)
        repository.insert_panel(panel2)

        # Insert biomarkers with same code but different values
        biomarker_old = Biomarker(
            id=uuid4(),
            panel_id=panel1.id,
            name="Triglycerides",
            code="TRIGLYCERIDES",
            value=100.0,
            unit="mg/dL",
            flag=Flag.NORMAL,
        )
        biomarker_new = Biomarker(
            id=uuid4(),
            panel_id=panel2.id,
            name="Triglycerides",
            code="TRIGLYCERIDES",
            value=150.0,
            unit="mg/dL",
            flag=Flag.HIGH,
        )
        repository.insert_biomarker(biomarker_old)
        repository.insert_biomarker(biomarker_new)

        result = repository.get_biomarker_by_code("TRIGLYCERIDES")
        assert result.value == 150.0  # Should be from newer report
        assert result.flag == Flag.HIGH


class TestGetBiomarkerHistory:
    """Tests for get_biomarker_history method."""

    def test_get_biomarker_history_returns_list(self, repository, sample_report, sample_panel, sample_biomarker):
        """get_biomarker_history returns a list."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        result = repository.get_biomarker_history(sample_biomarker.code)
        assert isinstance(result, list)

    def test_get_biomarker_history_returns_biomarker_models(self, repository, sample_report, sample_panel, sample_biomarker):
        """get_biomarker_history returns Biomarker models."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        result = repository.get_biomarker_history(sample_biomarker.code)
        assert len(result) == 1
        assert isinstance(result[0], Biomarker)

    def test_get_biomarker_history_returns_empty_list(self, repository):
        """get_biomarker_history returns empty list when no biomarkers."""
        result = repository.get_biomarker_history("UNKNOWN_CODE")
        assert result == []

    def test_get_biomarker_history_ordered_by_date_desc(self, repository):
        """get_biomarker_history returns results ordered by collected date descending."""
        # Create reports with different dates
        dates = [date(2024, 1, 1), date(2024, 3, 1), date(2024, 2, 1)]
        expected_values = [100.0, 300.0, 200.0]  # Values match the date order

        for i, (d, val) in enumerate(zip(dates, expected_values)):
            report = LabReport(
                id=uuid4(),
                lab_provider="LabCorp",
                collected_date=d,
            )
            repository.insert_report(report)
            panel = Panel(id=uuid4(), lab_report_id=report.id, name="Lipid Panel")
            repository.insert_panel(panel)
            biomarker = Biomarker(
                id=uuid4(),
                panel_id=panel.id,
                name="HDL",
                code="HDL",
                value=val,
                unit="mg/dL",
                flag=Flag.NORMAL,
            )
            repository.insert_biomarker(biomarker)

        result = repository.get_biomarker_history("HDL")
        assert len(result) == 3
        # Should be ordered: March (300), Feb (200), Jan (100)
        assert result[0].value == 300.0
        assert result[1].value == 200.0
        assert result[2].value == 100.0

    def test_get_biomarker_history_respects_limit(self, repository):
        """get_biomarker_history respects the limit parameter."""
        # Create 5 reports
        for i in range(5):
            report = LabReport(
                id=uuid4(),
                lab_provider="LabCorp",
                collected_date=date(2024, i + 1, 1),
            )
            repository.insert_report(report)
            panel = Panel(id=uuid4(), lab_report_id=report.id, name="Lipid Panel")
            repository.insert_panel(panel)
            biomarker = Biomarker(
                id=uuid4(),
                panel_id=panel.id,
                name="LDL",
                code="LDL",
                value=float(100 + i * 10),
                unit="mg/dL",
                flag=Flag.NORMAL,
            )
            repository.insert_biomarker(biomarker)

        result = repository.get_biomarker_history("LDL", limit=3)
        assert len(result) == 3

    def test_get_biomarker_history_default_limit_is_4(self, repository):
        """get_biomarker_history defaults to limit of 4."""
        # Create 6 reports
        for i in range(6):
            report = LabReport(
                id=uuid4(),
                lab_provider="LabCorp",
                collected_date=date(2024, i + 1, 1),
            )
            repository.insert_report(report)
            panel = Panel(id=uuid4(), lab_report_id=report.id, name="Panel")
            repository.insert_panel(panel)
            biomarker = Biomarker(
                id=uuid4(),
                panel_id=panel.id,
                name="VLDL",
                code="VLDL",
                value=float(i),
                unit="mg/dL",
                flag=Flag.NORMAL,
            )
            repository.insert_biomarker(biomarker)

        result = repository.get_biomarker_history("VLDL")
        assert len(result) == 4


class TestGetFlaggedBiomarkers:
    """Tests for get_flagged_biomarkers method."""

    def test_get_flagged_biomarkers_returns_list(self, repository):
        """get_flagged_biomarkers returns a list."""
        result = repository.get_flagged_biomarkers()
        assert isinstance(result, list)

    def test_get_flagged_biomarkers_returns_empty_when_no_flagged(self, repository, sample_report, sample_panel, sample_biomarker):
        """get_flagged_biomarkers returns empty list when all biomarkers are normal."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)  # Has NORMAL flag
        result = repository.get_flagged_biomarkers()
        assert result == []

    def test_get_flagged_biomarkers_returns_high_flag(self, repository, sample_report, sample_panel):
        """get_flagged_biomarkers returns biomarkers with HIGH flag."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="LDL",
            code="LDL",
            value=200.0,
            unit="mg/dL",
            flag=Flag.HIGH,
        )
        repository.insert_biomarker(biomarker)
        result = repository.get_flagged_biomarkers()
        assert len(result) == 1
        assert result[0].flag == Flag.HIGH

    def test_get_flagged_biomarkers_returns_low_flag(self, repository, sample_report, sample_panel):
        """get_flagged_biomarkers returns biomarkers with LOW flag."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="HDL",
            code="HDL",
            value=25.0,
            unit="mg/dL",
            flag=Flag.LOW,
        )
        repository.insert_biomarker(biomarker)
        result = repository.get_flagged_biomarkers()
        assert len(result) == 1
        assert result[0].flag == Flag.LOW

    def test_get_flagged_biomarkers_returns_critical_flags(self, repository, sample_report, sample_panel):
        """get_flagged_biomarkers returns biomarkers with CRITICAL_HIGH and CRITICAL_LOW flags."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker1 = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="Glucose",
            code="CHOLESTEROL_TOTAL",
            value=400.0,
            unit="mg/dL",
            flag=Flag.CRITICAL_HIGH,
        )
        biomarker2 = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="HDL",
            code="HDL",
            value=10.0,
            unit="mg/dL",
            flag=Flag.CRITICAL_LOW,
        )
        repository.insert_biomarker(biomarker1)
        repository.insert_biomarker(biomarker2)
        result = repository.get_flagged_biomarkers()
        assert len(result) == 2
        flags = {r.flag for r in result}
        assert Flag.CRITICAL_HIGH in flags
        assert Flag.CRITICAL_LOW in flags

    def test_get_flagged_biomarkers_returns_pending_flag(self, repository, sample_report, sample_panel):
        """get_flagged_biomarkers returns biomarkers with PENDING flag."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="Triglycerides",
            code="TRIGLYCERIDES",
            value=0.0,
            unit="mg/dL",
            flag=Flag.PENDING,
        )
        repository.insert_biomarker(biomarker)
        result = repository.get_flagged_biomarkers()
        assert len(result) == 1
        assert result[0].flag == Flag.PENDING

    def test_get_flagged_biomarkers_excludes_normal(self, repository, sample_report, sample_panel):
        """get_flagged_biomarkers excludes biomarkers with NORMAL flag."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        normal_biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="HDL",
            code="HDL",
            value=60.0,
            unit="mg/dL",
            flag=Flag.NORMAL,
        )
        high_biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="LDL",
            code="LDL",
            value=180.0,
            unit="mg/dL",
            flag=Flag.HIGH,
        )
        repository.insert_biomarker(normal_biomarker)
        repository.insert_biomarker(high_biomarker)
        result = repository.get_flagged_biomarkers()
        assert len(result) == 1
        assert result[0].code == "LDL"


class TestEdgeCases:
    """Edge case tests."""

    def test_uuid_roundtrip(self, repository, sample_report):
        """UUIDs are correctly stored and retrieved."""
        repository.insert_report(sample_report)
        retrieved = repository.get_report_by_id(sample_report.id)
        assert isinstance(retrieved.id, UUID)
        assert retrieved.id == sample_report.id

    def test_date_roundtrip(self, repository):
        """Dates are correctly stored and retrieved."""
        report = LabReport(
            id=uuid4(),
            lab_provider="Test",
            collected_date=date(2020, 12, 31),
        )
        repository.insert_report(report)
        retrieved = repository.get_report_by_id(report.id)
        assert isinstance(retrieved.collected_date, date)
        assert retrieved.collected_date == date(2020, 12, 31)

    def test_datetime_roundtrip(self, repository):
        """Datetimes are correctly stored and retrieved."""
        report = LabReport(
            id=uuid4(),
            lab_provider="Test",
            collected_date=date(2020, 12, 31),
            created_at=datetime(2021, 1, 1, 12, 30, 45),
        )
        repository.insert_report(report)
        retrieved = repository.get_report_by_id(report.id)
        assert isinstance(retrieved.created_at, datetime)
        assert retrieved.created_at == datetime(2021, 1, 1, 12, 30, 45)

    def test_float_value_roundtrip(self, repository, sample_report, sample_panel):
        """Float values are correctly stored and retrieved."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="Triglycerides",
            code="TRIGLYCERIDES",
            value=123.456,
            unit="mg/dL",
            flag=Flag.NORMAL,
        )
        repository.insert_biomarker(biomarker)
        retrieved = repository.get_biomarker_by_code(biomarker.code)
        assert retrieved.value == pytest.approx(123.456)

    def test_reference_range_roundtrip(self, repository, sample_report, sample_panel):
        """Reference range values are correctly stored and retrieved."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="HDL",
            code="HDL",
            value=55.0,
            unit="mg/dL",
            reference_low=40.0,
            reference_high=60.0,
            flag=Flag.NORMAL,
        )
        repository.insert_biomarker(biomarker)
        retrieved = repository.get_biomarker_by_code(biomarker.code)
        assert retrieved.reference_low == pytest.approx(40.0)
        assert retrieved.reference_high == pytest.approx(60.0)
