"""Tests for BloodworkRepository."""

from datetime import date
from uuid import uuid4

import pytest
from sqlmodel import Session

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.bloodwork import Biomarker, Flag, LabReport, Panel
from src.databases.datatypes.bloodwork.repository import BloodworkRepository


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
    """Create a BloodworkRepository instance."""
    return BloodworkRepository(db_session)


@pytest.fixture
def sample_report(db_session) -> LabReport:
    """Create a sample lab report with panels and biomarkers."""
    report = LabReport(
        lab_provider="Quest",
        collected_date=date(2024, 1, 15),
        source_file="test.json",
    )
    db_session.add(report)
    db_session.flush()

    panel = Panel(
        lab_report_id=report.id,
        name="Metabolic Panel",
        comment="Fasting",
    )
    db_session.add(panel)
    db_session.flush()

    biomarker = Biomarker(
        panel_id=panel.id,
        name="Glucose",
        code="GLUCOSE",
        value=95.0,
        unit="mg/dL",
        reference_low=70.0,
        reference_high=100.0,
        flag=Flag.NORMAL,
    )
    db_session.add(biomarker)
    db_session.commit()

    return report


class TestListReports:
    """Tests for list_reports method."""

    def test_returns_empty_list_when_no_reports(self, repo):
        """Should return empty list when no reports exist."""
        reports = repo.list_reports()
        assert reports == []

    def test_returns_all_reports(self, repo, sample_report):
        """Should return all lab reports."""
        reports = repo.list_reports()
        assert len(reports) == 1
        assert reports[0].id == sample_report.id

    def test_orders_by_collected_date_descending(self, repo, db_session):
        """Should order reports by collected_date descending."""
        # Create older report
        older = LabReport(
            lab_provider="LabCorp",
            collected_date=date(2023, 1, 1),
        )
        db_session.add(older)

        # Create newer report
        newer = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 6, 15),
        )
        db_session.add(newer)
        db_session.commit()

        reports = repo.list_reports()
        assert len(reports) == 2
        assert reports[0].collected_date == date(2024, 6, 15)
        assert reports[1].collected_date == date(2023, 1, 1)


class TestGetReport:
    """Tests for get_report method."""

    def test_returns_report_by_id(self, repo, sample_report):
        """Should return report when found."""
        report = repo.get_report(sample_report.id)
        assert report is not None
        assert report.id == sample_report.id

    def test_returns_none_when_not_found(self, repo):
        """Should return None when report not found."""
        report = repo.get_report(uuid4())
        assert report is None


class TestGetPanelsForReport:
    """Tests for get_panels_for_report method."""

    def test_returns_panels_for_report(self, repo, sample_report, db_session):
        """Should return all panels for a report."""
        panels = repo.get_panels_for_report(sample_report.id)
        assert len(panels) == 1
        assert panels[0].name == "Metabolic Panel"

    def test_returns_empty_list_when_no_panels(self, repo, db_session):
        """Should return empty list when no panels exist for report."""
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
        )
        db_session.add(report)
        db_session.commit()

        panels = repo.get_panels_for_report(report.id)
        assert panels == []


class TestGetBiomarkersForPanel:
    """Tests for get_biomarkers_for_panel method."""

    def test_returns_biomarkers_for_panel(self, repo, sample_report, db_session):
        """Should return all biomarkers for a panel."""
        panels = repo.get_panels_for_report(sample_report.id)
        biomarkers = repo.get_biomarkers_for_panel(panels[0].id)
        assert len(biomarkers) == 1
        assert biomarkers[0].name == "Glucose"

    def test_returns_empty_list_when_no_biomarkers(self, repo, db_session):
        """Should return empty list when no biomarkers exist for panel."""
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
        )
        db_session.add(report)
        db_session.flush()

        panel = Panel(
            lab_report_id=report.id,
            name="Empty Panel",
        )
        db_session.add(panel)
        db_session.commit()

        biomarkers = repo.get_biomarkers_for_panel(panel.id)
        assert biomarkers == []


class TestGetBiomarkerHistory:
    """Tests for get_biomarker_history method."""

    def test_returns_history_for_biomarker_code(self, repo, sample_report):
        """Should return biomarker history for a given code."""
        history = repo.get_biomarker_history("GLUCOSE")
        assert len(history) == 1
        assert history[0].code == "GLUCOSE"

    def test_respects_limit(self, repo, db_session):
        """Should respect the limit parameter."""
        # Create multiple reports with glucose readings
        for i in range(5):
            report = LabReport(
                lab_provider="Quest",
                collected_date=date(2024, 1, i + 1),
            )
            db_session.add(report)
            db_session.flush()

            panel = Panel(lab_report_id=report.id, name="Panel")
            db_session.add(panel)
            db_session.flush()

            biomarker = Biomarker(
                panel_id=panel.id,
                name="Glucose",
                code="GLUCOSE",
                value=90.0 + i,
                unit="mg/dL",
            )
            db_session.add(biomarker)
        db_session.commit()

        history = repo.get_biomarker_history("GLUCOSE", limit=3)
        assert len(history) == 3

    def test_orders_by_date_descending(self, repo, db_session):
        """Should return most recent biomarkers first."""
        # Create older report
        older_report = LabReport(
            lab_provider="Quest",
            collected_date=date(2023, 1, 1),
        )
        db_session.add(older_report)
        db_session.flush()

        older_panel = Panel(lab_report_id=older_report.id, name="Panel")
        db_session.add(older_panel)
        db_session.flush()

        older_biomarker = Biomarker(
            panel_id=older_panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=85.0,
            unit="mg/dL",
        )
        db_session.add(older_biomarker)

        # Create newer report
        newer_report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 6, 15),
        )
        db_session.add(newer_report)
        db_session.flush()

        newer_panel = Panel(lab_report_id=newer_report.id, name="Panel")
        db_session.add(newer_panel)
        db_session.flush()

        newer_biomarker = Biomarker(
            panel_id=newer_panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
        )
        db_session.add(newer_biomarker)
        db_session.commit()

        history = repo.get_biomarker_history("GLUCOSE")
        assert history[0].value == 95.0  # Newer first
        assert history[1].value == 85.0

    def test_returns_empty_list_when_code_not_found(self, repo):
        """Should return empty list when biomarker code not found."""
        history = repo.get_biomarker_history("NONEXISTENT")
        assert history == []


class TestGetFlaggedBiomarkers:
    """Tests for get_flagged_biomarkers method."""

    def test_returns_empty_when_no_flagged(self, repo, sample_report):
        """Should return empty list when no flagged biomarkers."""
        flagged = repo.get_flagged_biomarkers()
        assert flagged == []

    def test_returns_flagged_biomarkers(self, repo, db_session):
        """Should return biomarkers with non-normal flags."""
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
        )
        db_session.add(report)
        db_session.flush()

        panel = Panel(lab_report_id=report.id, name="Panel")
        db_session.add(panel)
        db_session.flush()

        high = Biomarker(
            panel_id=panel.id,
            name="LDL",
            code="LDL",
            value=150.0,
            unit="mg/dL",
            flag=Flag.HIGH,
        )
        db_session.add(high)

        low = Biomarker(
            panel_id=panel.id,
            name="Vitamin D",
            code="VITAMIN_D_25_HYDROXY",
            value=15.0,
            unit="ng/mL",
            flag=Flag.LOW,
        )
        db_session.add(low)

        normal = Biomarker(
            panel_id=panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
            flag=Flag.NORMAL,
        )
        db_session.add(normal)
        db_session.commit()

        flagged = repo.get_flagged_biomarkers()
        assert len(flagged) == 2
        codes = {b.code for b in flagged}
        assert codes == {"LDL", "VITAMIN_D_25_HYDROXY"}


class TestGetRecentBiomarkers:
    """Tests for get_recent_biomarkers method."""

    def test_returns_most_recent_for_each_code(self, repo, db_session):
        """Should return only the most recent value for each biomarker code."""
        # Older report
        older_report = LabReport(
            lab_provider="Quest",
            collected_date=date(2023, 1, 1),
        )
        db_session.add(older_report)
        db_session.flush()

        older_panel = Panel(lab_report_id=older_report.id, name="Panel")
        db_session.add(older_panel)
        db_session.flush()

        db_session.add(Biomarker(
            panel_id=older_panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=85.0,
            unit="mg/dL",
        ))

        # Newer report with same biomarker
        newer_report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 6, 15),
        )
        db_session.add(newer_report)
        db_session.flush()

        newer_panel = Panel(lab_report_id=newer_report.id, name="Panel")
        db_session.add(newer_panel)
        db_session.flush()

        db_session.add(Biomarker(
            panel_id=newer_panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
        ))
        db_session.commit()

        recent = repo.get_recent_biomarkers()
        glucose_values = [b for b in recent if b.code == "GLUCOSE"]
        assert len(glucose_values) == 1
        assert glucose_values[0].value == 95.0  # Most recent

    def test_returns_empty_when_no_biomarkers(self, repo):
        """Should return empty list when no biomarkers exist."""
        recent = repo.get_recent_biomarkers()
        assert recent == []


class TestSaveReport:
    """Tests for save_report method."""

    def test_saves_report_panels_and_biomarkers(self, repo, db_session):
        """Should save report, panels, and biomarkers atomically."""
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
            source_file="test.json",
        )
        panel = Panel(
            lab_report_id=report.id,
            name="Metabolic Panel",
        )
        biomarker = Biomarker(
            panel_id=panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
        )

        repo.save_report(report, [panel], [biomarker])

        # Verify all saved
        saved_reports = repo.list_reports()
        assert len(saved_reports) == 1
        assert saved_reports[0].lab_provider == "Quest"

        panels = repo.get_panels_for_report(report.id)
        assert len(panels) == 1

        biomarkers = repo.get_biomarkers_for_panel(panel.id)
        assert len(biomarkers) == 1
