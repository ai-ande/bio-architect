"""Tests for bloodwork models."""

from datetime import date
from uuid import UUID

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
        biomarker = Biomarker(
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
        )
        assert biomarker.code == "GLUCOSE"

    def test_biomarker_accepts_valid_custom_code(self):
        """Custom codes following format rules should be accepted."""
        biomarker = Biomarker(
            name="Custom Biomarker",
            code="CUSTOM_BIOMARKER",
            value=100.0,
            unit="mg/dL",
        )
        assert biomarker.code == "CUSTOM_BIOMARKER"

    def test_biomarker_rejects_lowercase_code(self):
        """Lowercase codes should be rejected."""
        with pytest.raises(ValueError, match="must be uppercase"):
            Biomarker(
                name="Glucose",
                code="glucose",
                value=95.0,
                unit="mg/dL",
            )

    def test_biomarker_rejects_code_with_spaces(self):
        """Codes with spaces should be rejected."""
        with pytest.raises(ValueError, match="must not contain spaces"):
            Biomarker(
                name="Total Cholesterol",
                code="TOTAL CHOLESTEROL",
                value=200.0,
                unit="mg/dL",
            )

    def test_biomarker_rejects_code_with_special_chars(self):
        """Codes with special characters (other than underscore) should be rejected."""
        with pytest.raises(ValueError, match="invalid characters"):
            Biomarker(
                name="Test",
                code="TEST-CODE",
                value=100.0,
                unit="mg/dL",
            )

    def test_biomarker_rejects_empty_code(self):
        """Empty codes should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Biomarker(
                name="Test",
                code="",
                value=100.0,
                unit="mg/dL",
            )

    def test_code_allows_numbers(self):
        """Codes with numbers should be valid."""
        biomarker = Biomarker(
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
        biomarker = Biomarker(
            name="Glucose",
            code="GLUCOSE",
            value=95.0,
            unit="mg/dL",
        )
        assert biomarker.name == "Glucose"
        assert biomarker.code == "GLUCOSE"
        assert biomarker.value == 95.0
        assert biomarker.unit == "mg/dL"

    def test_biomarker_has_uuid(self):
        biomarker = Biomarker(name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL")
        assert isinstance(biomarker.id, UUID)

    def test_biomarker_uuid_is_unique(self):
        b1 = Biomarker(name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL")
        b2 = Biomarker(name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL")
        assert b1.id != b2.id

    def test_biomarker_default_flag_is_normal(self):
        biomarker = Biomarker(name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL")
        assert biomarker.flag == Flag.NORMAL

    def test_biomarker_with_reference_range(self):
        biomarker = Biomarker(
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
            name="Glucose",
            code="GLUCOSE",
            value=150.0,
            unit="mg/dL",
            flag=Flag.HIGH,
        )
        assert biomarker.flag == Flag.HIGH

    def test_biomarker_optional_fields_default_to_none(self):
        biomarker = Biomarker(name="Glucose", code="GLUCOSE", value=95.0, unit="mg/dL")
        assert biomarker.reference_low is None
        assert biomarker.reference_high is None
        assert biomarker.collected_date is None
        assert biomarker.lab_provider is None
        assert biomarker.panel_name is None

    def test_biomarker_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            Biomarker(name="Glucose", code="GLUCOSE", value=95.0)  # missing unit


class TestPanel:
    """Tests for Panel model."""

    def test_create_minimal_panel(self):
        panel = Panel(name="CBC")
        assert panel.name == "CBC"
        assert panel.biomarkers == []

    def test_panel_has_uuid(self):
        panel = Panel(name="CBC")
        assert isinstance(panel.id, UUID)

    def test_panel_with_comment(self):
        panel = Panel(name="CBC", comment="Fasting sample")
        assert panel.comment == "Fasting sample"

    def test_panel_with_biomarkers(self):
        biomarkers = [
            Biomarker(name="WBC", code="WBC", value=7.5, unit="K/uL"),
            Biomarker(name="RBC", code="RBC", value=4.8, unit="M/uL"),
        ]
        panel = Panel(name="CBC", biomarkers=biomarkers)
        assert len(panel.biomarkers) == 2
        assert panel.biomarkers[0].name == "WBC"


class TestLabReport:
    """Tests for LabReport model."""

    @pytest.fixture
    def sample_report(self) -> LabReport:
        """Create a sample lab report for testing."""
        return LabReport(
            lab_provider="LabCorp",
            collected_date=date(2024, 1, 15),
            panels=[
                Panel(
                    name="Lipid Panel",
                    biomarkers=[
                        Biomarker(
                            name="Total Cholesterol",
                            code="CHOLESTEROL_TOTAL",
                            value=210.0,
                            unit="mg/dL",
                            flag=Flag.HIGH,
                        ),
                        Biomarker(
                            name="HDL",
                            code="HDL",
                            value=55.0,
                            unit="mg/dL",
                            flag=Flag.NORMAL,
                        ),
                    ],
                ),
                Panel(
                    name="Metabolic Panel",
                    biomarkers=[
                        Biomarker(
                            name="Glucose",
                            code="GLUCOSE",
                            value=65.0,
                            unit="mg/dL",
                            flag=Flag.LOW,
                        ),
                    ],
                ),
            ],
        )

    def test_create_minimal_report(self):
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
        )
        assert report.lab_provider == "Quest"
        assert report.collected_date == date(2024, 1, 15)
        assert report.panels == []

    def test_report_has_uuid(self):
        report = LabReport(lab_provider="Quest", collected_date=date(2024, 1, 15))
        assert isinstance(report.id, UUID)

    def test_report_optional_dates(self):
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
            received_date=date(2024, 1, 16),
            reported_date=date(2024, 1, 17),
        )
        assert report.received_date == date(2024, 1, 16)
        assert report.reported_date == date(2024, 1, 17)

    def test_get_all_biomarkers(self, sample_report: LabReport):
        biomarkers = sample_report.get_all_biomarkers()
        assert len(biomarkers) == 3
        codes = [b.code for b in biomarkers]
        assert "CHOLESTEROL_TOTAL" in codes
        assert "HDL" in codes
        assert "GLUCOSE" in codes

    def test_get_all_biomarkers_empty_report(self):
        report = LabReport(lab_provider="Quest", collected_date=date(2024, 1, 15))
        assert report.get_all_biomarkers() == []

    def test_get_biomarker_by_code_found(self, sample_report: LabReport):
        biomarker = sample_report.get_biomarker_by_code("HDL")
        assert biomarker is not None
        assert biomarker.name == "HDL"
        assert biomarker.value == 55.0

    def test_get_biomarker_by_code_not_found(self, sample_report: LabReport):
        biomarker = sample_report.get_biomarker_by_code("NONEXISTENT")
        assert biomarker is None

    def test_get_flagged_biomarkers(self, sample_report: LabReport):
        flagged = sample_report.get_flagged_biomarkers()
        assert len(flagged) == 2
        codes = [b.code for b in flagged]
        assert "CHOLESTEROL_TOTAL" in codes  # HIGH
        assert "GLUCOSE" in codes  # LOW
        assert "HDL" not in codes  # NORMAL

    def test_get_flagged_biomarkers_none_flagged(self):
        report = LabReport(
            lab_provider="Quest",
            collected_date=date(2024, 1, 15),
            panels=[
                Panel(
                    name="CBC",
                    biomarkers=[
                        Biomarker(name="WBC", code="WBC", value=7.5, unit="K/uL"),
                    ],
                ),
            ],
        )
        assert report.get_flagged_biomarkers() == []

    def test_report_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            LabReport(lab_provider="Quest")  # missing collected_date
