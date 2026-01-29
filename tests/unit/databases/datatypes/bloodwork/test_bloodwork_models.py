"""Tests for bloodwork models."""

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest

from src.databases.datatypes.bloodwork import (
    Biomarker,
    Flag,
    LabReport,
    Panel,
    VALID_BIOMARKER_CODES,
)


class TestBiomarkerCodeValidation:
    """Tests for biomarker code validation."""

    def test_valid_codes_loaded_from_yaml(self):
        """Verify that valid codes are loaded from the YAML file."""
        assert "GLUCOSE" in VALID_BIOMARKER_CODES
        assert "HDL" in VALID_BIOMARKER_CODES
        assert "TSH" in VALID_BIOMARKER_CODES
        assert "HEMOGLOBIN" in VALID_BIOMARKER_CODES
        assert "VITAMIN_D" in VALID_BIOMARKER_CODES
        assert "HS_CRP" in VALID_BIOMARKER_CODES

    def test_biomarker_accepts_valid_yaml_code(self):
        """Valid codes from YAML should be accepted."""
        panel_id = uuid4()
        biomarker = Biomarker(
            panel_id=panel_id,
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
        )
        assert biomarker.code == "GLUCOSE"

    def test_biomarker_rejects_unknown_code(self):
        """Codes not in biomarker_codes.yaml should be rejected."""
        with pytest.raises(ValueError, match="unknown biomarker code"):
            Biomarker(
                panel_id=uuid4(),
                name="Custom Biomarker",
                code="CUSTOM_BIOMARKER",
                value=100.0,
                unit="mg/dL",
            )

    def test_biomarker_rejects_lowercase_code(self):
        """Lowercase codes should be rejected."""
        with pytest.raises(ValueError, match="must be uppercase"):
            Biomarker(
                panel_id=uuid4(),
                name="Glucose",
                code="glucose",
                value=95.0,
                unit="mg/dL",
            )

    def test_biomarker_rejects_code_with_spaces(self):
        """Codes with spaces should be rejected."""
        with pytest.raises(ValueError, match="must not contain spaces"):
            Biomarker(
                panel_id=uuid4(),
                name="Total Cholesterol",
                code="TOTAL CHOLESTEROL",
                value=200.0,
                unit="mg/dL",
            )

    def test_biomarker_rejects_code_with_special_chars(self):
        """Codes with special characters (other than underscore) should be rejected."""
        with pytest.raises(ValueError, match="invalid characters"):
            Biomarker(
                panel_id=uuid4(),
                name="Test",
                code="TEST-CODE",
                value=100.0,
                unit="mg/dL",
            )

    def test_biomarker_rejects_empty_code(self):
        """Empty codes should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Biomarker(
                panel_id=uuid4(),
                name="Test",
                code="",
                value=100.0,
                unit="mg/dL",
            )

    def test_code_allows_numbers(self):
        """Codes with numbers should be valid."""
        panel_id = uuid4()
        biomarker = Biomarker(
            panel_id=panel_id,
            name="Vitamin B12",
            code="VITAMIN_B12",
            value=500.0,
            unit="pg/mL",
        )
        assert biomarker.code == "VITAMIN_B12"


class TestFlag:
    """Tests for Flag enum."""

    def test_flag_values(self):
        assert Flag.NORMAL.value == "normal"
        assert Flag.HIGH.value == "high"
        assert Flag.LOW.value == "low"

    def test_flag_is_string_enum(self):
        assert isinstance(Flag.NORMAL, str)
        assert Flag.NORMAL == "normal"


class TestBiomarker:
    """Tests for Biomarker model."""

    def test_create_minimal_biomarker(self):
        panel_id = uuid4()
        biomarker = Biomarker(
            panel_id=panel_id,
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
        )
        assert biomarker.name == "Glucose"
        assert biomarker.code == "GLUCOSE"
        assert biomarker.value == 95.0
        assert biomarker.unit == "mg/dL"
        assert biomarker.panel_id == panel_id

    def test_biomarker_has_uuid(self):
        biomarker = Biomarker(
            panel_id=uuid4(), name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL"
        )
        assert isinstance(biomarker.id, UUID)

    def test_biomarker_uuid_is_unique(self):
        panel_id = uuid4()
        b1 = Biomarker(
            panel_id=panel_id, name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL"
        )
        b2 = Biomarker(
            panel_id=panel_id, name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL"
        )
        assert b1.id != b2.id

    def test_biomarker_default_flag_is_normal(self):
        biomarker = Biomarker(
            panel_id=uuid4(), name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL"
        )
        assert biomarker.flag == Flag.NORMAL

    def test_biomarker_with_reference_range(self):
        biomarker = Biomarker(
            panel_id=uuid4(),
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
            reference_low=70.0,
            reference_high=100.0,
        )
        assert biomarker.reference_low == 70.0
        assert biomarker.reference_high == 100.0

    def test_biomarker_with_flag(self):
        biomarker = Biomarker(
            panel_id=uuid4(),
            name="Glucose",
            code="GLUCOSE",
            value=150.0,
            unit="mg/dL",
            flag=Flag.HIGH,
        )
        assert biomarker.flag == Flag.HIGH

    def test_biomarker_optional_fields_default_to_none(self):
        biomarker = Biomarker(
            panel_id=uuid4(), name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL"
        )
        assert biomarker.reference_low is None
        assert biomarker.reference_high is None

    def test_biomarker_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            Biomarker(
                panel_id=uuid4(), name="Glucose", code="GLUCOSE", value=95.0
            )  # missing unit

    def test_biomarker_requires_panel_id(self):
        with pytest.raises(ValueError):
            Biomarker(
                name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL"
            )  # missing panel_id

    def test_biomarker_no_temporal_context_fields(self):
        """Verify temporal context fields were removed."""
        biomarker = Biomarker(
            panel_id=uuid4(), name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL"
        )
        assert not hasattr(biomarker, "collected_date")
        assert not hasattr(biomarker, "lab_provider")
        assert not hasattr(biomarker, "panel_name")


class TestPanel:
    """Tests for Panel model."""

    def test_create_minimal_panel(self):
        lab_report_id = uuid4()
        panel = Panel(lab_report_id=lab_report_id, name="CBC")
        assert panel.name == "CBC"
        assert panel.lab_report_id == lab_report_id

    def test_panel_has_uuid(self):
        panel = Panel(lab_report_id=uuid4(), name="CBC")
        assert isinstance(panel.id, UUID)

    def test_panel_with_comment(self):
        panel = Panel(lab_report_id=uuid4(), name="CBC", comment="Fasting sample")
        assert panel.comment == "Fasting sample"

    def test_panel_requires_lab_report_id(self):
        with pytest.raises(ValueError):
            Panel(name="CBC")  # missing lab_report_id

    def test_panel_is_flat_no_biomarkers_list(self):
        """Verify Panel does not have nested biomarkers list."""
        panel = Panel(lab_report_id=uuid4(), name="CBC")
        assert not hasattr(panel, "biomarkers")


class TestLabReport:
    """Tests for LabReport model."""

    def test_create_minimal_report(self):
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
        )
        assert report.lab_provider == "Quest"
        assert report.collected_date == date(2024, 1, 15)

    def test_report_has_uuid(self):
        report = LabReport(lab_provider="Quest", collected_date=date(2024, 1, 15))
        assert isinstance(report.id, UUID)

    def test_report_has_created_at_with_default(self):
        before = datetime.now()
        report = LabReport(lab_provider="Quest", collected_date=date(2024, 1, 15))
        after = datetime.now()
        assert isinstance(report.created_at, datetime)
        assert before <= report.created_at <= after

    def test_report_with_source_file(self):
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
            source_file="labcorp_2024.pdf",
        )
        assert report.source_file == "labcorp_2024.pdf"

    def test_report_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            LabReport(lab_provider="Quest")  # missing collected_date

    def test_report_is_flat_no_panels_list(self):
        """Verify LabReport does not have nested panels list."""
        report = LabReport(lab_provider="Quest", collected_date=date(2024, 1, 15))
        assert not hasattr(report, "panels")

    def test_report_no_received_or_reported_date(self):
        """Verify received_date and reported_date were removed."""
        report = LabReport(lab_provider="Quest", collected_date=date(2024, 1, 15))
        assert not hasattr(report, "received_date")
        assert not hasattr(report, "reported_date")

    def test_report_no_helper_methods(self):
        """Verify helper methods were removed (flat models don't need them)."""
        report = LabReport(lab_provider="Quest", collected_date=date(2024, 1, 15))
        assert not hasattr(report, "get_all_biomarkers")
        assert not hasattr(report, "get_biomarker_by_code")
        assert not hasattr(report, "get_flagged_biomarkers")
