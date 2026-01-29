"""Tests for bloodwork CLI import command."""

import argparse
import json
from io import StringIO

import pytest
from pydantic import ValidationError
from sqlmodel import select

from cli.databases.bloodwork import cmd_import, parse_bloodwork_json
from src.databases.datatypes.bloodwork import (
    Biomarker,
    BloodworkRepository,
    Flag,
    LabReport,
    Panel,
)


class TestParseBloodworkJson:
    """Tests for parse_bloodwork_json function."""

    def test_parse_creates_lab_report(self):
        """Parse should create a LabReport with correct fields."""
        data = {
            "lab_provider": "Quest",
            "collected_date": "2024-01-15",
            "panels": [],
        }
        lab_report, panels, biomarkers = parse_bloodwork_json(data, "test.json")

        assert lab_report.lab_provider == "Quest"
        assert str(lab_report.collected_date) == "2024-01-15"
        assert lab_report.source_file == "test.json"

    def test_parse_creates_panels(self):
        """Parse should create Panel records linked to LabReport."""
        data = {
            "lab_provider": "Quest",
            "collected_date": "2024-01-15",
            "panels": [
                {"name": "Lipid Panel", "comment": "Fasting", "biomarkers": []},
                {"name": "CBC", "comment": None, "biomarkers": []},
            ],
        }
        lab_report, panels, biomarkers = parse_bloodwork_json(data, None)

        assert len(panels) == 2
        assert panels[0].name == "Lipid Panel"
        assert panels[0].comment == "Fasting"
        assert panels[0].lab_report_id == lab_report.id
        assert panels[1].name == "CBC"
        assert panels[1].comment is None

    def test_parse_creates_biomarkers(self):
        """Parse should create Biomarker records linked to Panels."""
        data = {
            "lab_provider": "Quest",
            "collected_date": "2024-01-15",
            "panels": [
                {
                    "name": "Lipid Panel",
                    "biomarkers": [
                        {
                            "name": "Total Cholesterol",
                            "code": "CHOLESTEROL_TOTAL",
                            "value": 195.0,
                            "unit": "mg/dL",
                            "reference_low": 100.0,
                            "reference_high": 199.0,
                            "flag": "normal",
                        },
                        {
                            "name": "LDL Cholesterol",
                            "code": "LDL",
                            "value": 130.0,
                            "unit": "mg/dL",
                            "reference_low": 0.0,
                            "reference_high": 99.0,
                            "flag": "high",
                        },
                    ],
                }
            ],
        }
        lab_report, panels, biomarkers = parse_bloodwork_json(data, None)

        assert len(biomarkers) == 2
        assert biomarkers[0].name == "Total Cholesterol"
        assert biomarkers[0].code == "CHOLESTEROL_TOTAL"
        assert biomarkers[0].value == 195.0
        assert biomarkers[0].flag == Flag.NORMAL
        assert biomarkers[0].panel_id == panels[0].id
        assert biomarkers[1].flag == Flag.HIGH

    def test_parse_handles_missing_optional_fields(self):
        """Parse should handle missing optional fields."""
        data = {
            "lab_provider": "Quest",
            "collected_date": "2024-01-15",
            "panels": [
                {
                    "name": "Test Panel",
                    "biomarkers": [
                        {
                            "name": "Glucose",
                            "code": "GLUCOSE",
                            "value": 95.0,
                            "unit": "mg/dL",
                        },
                    ],
                }
            ],
        }
        lab_report, panels, biomarkers = parse_bloodwork_json(data, None)

        assert biomarkers[0].reference_low is None
        assert biomarkers[0].reference_high is None
        assert biomarkers[0].flag == Flag.NORMAL  # Default

    def test_parse_rejects_invalid_biomarker_code(self):
        """Parse should reject invalid biomarker codes."""
        data = {
            "lab_provider": "Quest",
            "collected_date": "2024-01-15",
            "panels": [
                {
                    "name": "Test Panel",
                    "biomarkers": [
                        {
                            "name": "Custom Marker",
                            "code": "INVALID_CODE_NOT_IN_YAML",
                            "value": 100.0,
                            "unit": "mg/dL",
                        },
                    ],
                }
            ],
        }
        with pytest.raises(ValidationError, match="unknown biomarker code"):
            parse_bloodwork_json(data, None)


class TestBloodworkImport:
    """Tests for bloodwork import command."""

    @pytest.fixture
    def repo(self, db_session):
        """Create a BloodworkRepository instance."""
        return BloodworkRepository(db_session)

    @pytest.fixture
    def sample_json(self):
        """Sample valid bloodwork JSON."""
        return {
            "lab_provider": "Quest",
            "collected_date": "2024-01-15",
            "panels": [
                {
                    "name": "Metabolic Panel",
                    "comment": "Fasting",
                    "biomarkers": [
                        {
                            "name": "Glucose",
                            "code": "GLUCOSE",
                            "value": 95.0,
                            "unit": "mg/dL",
                            "reference_low": 70.0,
                            "reference_high": 100.0,
                            "flag": "normal",
                        },
                        {
                            "name": "BUN",
                            "code": "BUN",
                            "value": 15.0,
                            "unit": "mg/dL",
                            "reference_low": 6.0,
                            "reference_high": 20.0,
                            "flag": "normal",
                        },
                    ],
                }
            ],
        }

    def test_import_creates_lab_report(self, tmp_path, repo, sample_json):
        """Import should create a LabReport record."""
        json_file = tmp_path / "labs.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(repo, args)

        reports = repo.list_reports()
        assert len(reports) == 1
        assert reports[0].lab_provider == "Quest"

    def test_import_creates_panels(self, tmp_path, repo, sample_json):
        """Import should create Panel records linked to LabReport."""
        json_file = tmp_path / "labs.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(repo, args)

        reports = repo.list_reports()
        panels = repo.get_panels_for_report(reports[0].id)
        assert len(panels) == 1
        assert panels[0].name == "Metabolic Panel"

    def test_import_creates_biomarkers(self, tmp_path, repo, sample_json):
        """Import should create Biomarker records linked to Panels."""
        json_file = tmp_path / "labs.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(repo, args)

        reports = repo.list_reports()
        panels = repo.get_panels_for_report(reports[0].id)
        biomarkers = repo.get_biomarkers_for_panel(panels[0].id)
        assert len(biomarkers) == 2
        codes = {b.code for b in biomarkers}
        assert codes == {"GLUCOSE", "BUN"}

    def test_import_sets_source_file(self, tmp_path, repo, sample_json):
        """Import should set source_file to the input file path."""
        json_file = tmp_path / "labs.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(repo, args)

        reports = repo.list_reports()
        assert reports[0].source_file == str(json_file)

    def test_import_from_stdin(self, repo, sample_json, monkeypatch):
        """Import should read from stdin when no file provided."""
        stdin_data = json.dumps(sample_json)
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))

        args = argparse.Namespace(file=None, json=False)
        cmd_import(repo, args)

        reports = repo.list_reports()
        assert len(reports) == 1
        assert reports[0].source_file is None  # No file path from stdin

    def test_import_json_output(self, tmp_path, repo, sample_json, capsys):
        """Import with --json should return structured output."""
        json_file = tmp_path / "labs.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=True)
        cmd_import(repo, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert "lab_report_id" in result
        assert result["panels_created"] == 1
        assert result["biomarkers_created"] == 2

    def test_import_invalid_json_exits_with_error(self, tmp_path, repo):
        """Import should exit with error for invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json {{{")

        args = argparse.Namespace(file=str(json_file), json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(repo, args)
        assert exc_info.value.code == 1

    def test_import_missing_required_fields_exits_with_error(self, tmp_path, repo):
        """Import should exit with error for missing required fields."""
        json_file = tmp_path / "incomplete.json"
        json_file.write_text(json.dumps({"lab_provider": "Quest"}))  # Missing collected_date

        args = argparse.Namespace(file=str(json_file), json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(repo, args)
        assert exc_info.value.code == 1

    def test_import_no_partial_records_on_validation_error(self, tmp_path, db_client):
        """Import should not leave partial records if validation fails."""
        # First panel valid, second panel has invalid biomarker code
        data = {
            "lab_provider": "Quest",
            "collected_date": "2024-01-15",
            "panels": [
                {
                    "name": "Valid Panel",
                    "biomarkers": [
                        {"name": "Glucose", "code": "GLUCOSE", "value": 95.0, "unit": "mg/dL"},
                    ],
                },
                {
                    "name": "Invalid Panel",
                    "biomarkers": [
                        {"name": "Invalid", "code": "NOT_A_REAL_CODE", "value": 100.0, "unit": "mg/dL"},
                    ],
                },
            ],
        }
        json_file = tmp_path / "partial.json"
        json_file.write_text(json.dumps(data))

        # Use a fresh session to ensure we can check the DB state after failure
        with db_client.get_session() as session:
            repo = BloodworkRepository(session)
            args = argparse.Namespace(file=str(json_file), json=False)
            with pytest.raises(SystemExit):
                cmd_import(repo, args)

        # Verify no partial data was inserted (check with fresh session)
        with db_client.get_session() as session:
            repo = BloodworkRepository(session)
            assert len(repo.list_reports()) == 0

    def test_import_file_not_found_exits_with_error(self, repo):
        """Import should exit with error for non-existent file."""
        args = argparse.Namespace(file="/nonexistent/path.json", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(repo, args)
        assert exc_info.value.code == 1
