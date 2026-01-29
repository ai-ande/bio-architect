"""Tests for bloodwork CLI script."""

import argparse
import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.bloodwork import (
    biomarker_to_dict,
    cmd_biomarker,
    cmd_flagged,
    cmd_list,
    cmd_recent,
    cmd_report,
    create_parser,
    format_biomarker,
    format_report,
    main,
    panel_to_dict,
    report_to_dict,
)
from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.bloodwork import Biomarker, Flag, LabReport, Panel
from src.databases.repositories.bloodwork import BloodworkRepository


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_parser_has_json_flag(self):
        """Parser accepts --json flag."""
        parser = create_parser()
        args = parser.parse_args(["--json", "list"])
        assert args.json is True

    def test_parser_json_default_false(self):
        """Parser --json defaults to False."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.json is False

    def test_parser_list_command(self):
        """Parser recognizes list command."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_parser_report_command_requires_id(self):
        """Parser report command requires id argument."""
        parser = create_parser()
        args = parser.parse_args(["report", "123e4567-e89b-12d3-a456-426614174000"])
        assert args.command == "report"
        assert args.id == "123e4567-e89b-12d3-a456-426614174000"

    def test_parser_report_command_missing_id_fails(self):
        """Parser report command fails without id."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["report"])

    def test_parser_biomarker_command_requires_code(self):
        """Parser biomarker command requires code argument."""
        parser = create_parser()
        args = parser.parse_args(["biomarker", "GLUCOSE"])
        assert args.command == "biomarker"
        assert args.code == "GLUCOSE"

    def test_parser_biomarker_command_missing_code_fails(self):
        """Parser biomarker command fails without code."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["biomarker"])

    def test_parser_biomarker_command_accepts_limit(self):
        """Parser biomarker command accepts --limit flag."""
        parser = create_parser()
        args = parser.parse_args(["biomarker", "GLUCOSE", "--limit", "10"])
        assert args.limit == 10

    def test_parser_biomarker_command_accepts_short_limit(self):
        """Parser biomarker command accepts -n flag."""
        parser = create_parser()
        args = parser.parse_args(["biomarker", "GLUCOSE", "-n", "5"])
        assert args.limit == 5

    def test_parser_biomarker_command_limit_default(self):
        """Parser biomarker command defaults limit to 4."""
        parser = create_parser()
        args = parser.parse_args(["biomarker", "GLUCOSE"])
        assert args.limit == 4

    def test_parser_flagged_command(self):
        """Parser recognizes flagged command."""
        parser = create_parser()
        args = parser.parse_args(["flagged"])
        assert args.command == "flagged"

    def test_parser_recent_command(self):
        """Parser recognizes recent command."""
        parser = create_parser()
        args = parser.parse_args(["recent"])
        assert args.command == "recent"

    def test_parser_no_command_returns_none(self):
        """Parser returns None for command when no command given."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestFormatFunctions:
    """Tests for format helper functions."""

    def test_format_report(self):
        """format_report includes all fields."""
        report = LabReport(
            id=uuid4(),
            lab_provider="LabCorp",
            collected_date=date(2024, 1, 15),
            source_file="bloodwork.pdf",
        )
        result = format_report(report)
        assert str(report.id) in result
        assert "LabCorp" in result
        assert "2024-01-15" in result
        assert "bloodwork.pdf" in result

    def test_format_report_no_source_file(self):
        """format_report shows - for null source_file."""
        report = LabReport(
            id=uuid4(),
            lab_provider="LabCorp",
            collected_date=date(2024, 1, 15),
            source_file=None,
        )
        result = format_report(report)
        assert result.endswith("-")

    def test_format_biomarker(self):
        """format_biomarker includes all fields."""
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=uuid4(),
            name="Glucose",
            code="GLUCOSE",
            value=95.5,
            unit="mg/dL",
            reference_low=70.0,
            reference_high=100.0,
            flag=Flag.NORMAL,
        )
        result = format_biomarker(biomarker, "2024-01-15")
        assert "Glucose" in result
        assert "95.50" in result
        assert "mg/dL" in result
        assert "normal" in result
        assert "70.0-100.0" in result
        assert "2024-01-15" in result

    def test_format_biomarker_no_reference_range(self):
        """format_biomarker handles missing reference range."""
        biomarker = Biomarker(
            id=uuid4(),
            panel_id=uuid4(),
            name="Test",
            code="GLUCOSE",
            value=100.0,
            unit="units",
            reference_low=None,
            reference_high=None,
            flag=Flag.NORMAL,
        )
        result = format_biomarker(biomarker)
        assert "---" in result


class TestToDictFunctions:
    """Tests for JSON serialization functions."""

    def test_report_to_dict(self):
        """report_to_dict returns JSON-serializable dict."""
        report_id = uuid4()
        report = LabReport(
            id=report_id,
            lab_provider="LabCorp",
            collected_date=date(2024, 1, 15),
            source_file="bloodwork.pdf",
            created_at=datetime(2024, 1, 20, 10, 30, 0),
        )
        result = report_to_dict(report)
        assert result["id"] == str(report_id)
        assert result["lab_provider"] == "LabCorp"
        assert result["collected_date"] == "2024-01-15"
        assert result["source_file"] == "bloodwork.pdf"
        assert result["created_at"] == "2024-01-20T10:30:00"
        # Verify it's JSON serializable
        json.dumps(result)

    def test_panel_to_dict(self):
        """panel_to_dict returns JSON-serializable dict."""
        panel_id = uuid4()
        report_id = uuid4()
        panel = Panel(
            id=panel_id,
            lab_report_id=report_id,
            name="CBC",
            comment="All normal",
        )
        result = panel_to_dict(panel)
        assert result["id"] == str(panel_id)
        assert result["lab_report_id"] == str(report_id)
        assert result["name"] == "CBC"
        assert result["comment"] == "All normal"
        # Verify it's JSON serializable
        json.dumps(result)

    def test_biomarker_to_dict(self):
        """biomarker_to_dict returns JSON-serializable dict."""
        biomarker_id = uuid4()
        panel_id = uuid4()
        biomarker = Biomarker(
            id=biomarker_id,
            panel_id=panel_id,
            name="Glucose",
            code="GLUCOSE",
            value=95.5,
            unit="mg/dL",
            reference_low=70.0,
            reference_high=100.0,
            flag=Flag.HIGH,
        )
        result = biomarker_to_dict(biomarker)
        assert result["id"] == str(biomarker_id)
        assert result["panel_id"] == str(panel_id)
        assert result["name"] == "Glucose"
        assert result["code"] == "GLUCOSE"
        assert result["value"] == 95.5
        assert result["unit"] == "mg/dL"
        assert result["reference_low"] == 70.0
        assert result["reference_high"] == 100.0
        assert result["flag"] == "high"
        # Verify it's JSON serializable
        json.dumps(result)


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
        source_file="bloodwork.pdf",
        created_at=datetime(2024, 1, 20, 10, 30, 0),
    )


@pytest.fixture
def sample_panel(sample_report):
    """Create a sample Panel."""
    return Panel(
        id=uuid4(),
        lab_report_id=sample_report.id,
        name="Metabolic Panel",
        comment="Fasting sample",
    )


@pytest.fixture
def sample_biomarker(sample_panel):
    """Create a sample Biomarker."""
    return Biomarker(
        id=uuid4(),
        panel_id=sample_panel.id,
        name="Glucose",
        code="GLUCOSE",
        value=95.5,
        unit="mg/dL",
        reference_low=70.0,
        reference_high=100.0,
        flag=Flag.NORMAL,
    )


class TestCmdList:
    """Tests for list command."""

    def test_cmd_list_empty(self, repository, capsys):
        """cmd_list handles empty database."""
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "No lab reports found" in captured.out

    def test_cmd_list_with_reports(self, repository, sample_report, capsys):
        """cmd_list shows reports."""
        repository.insert_report(sample_report)
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "LabCorp" in captured.out
        assert "2024-01-15" in captured.out

    def test_cmd_list_json(self, repository, sample_report, capsys):
        """cmd_list outputs valid JSON."""
        repository.insert_report(sample_report)
        args = argparse.Namespace(json=True)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["lab_provider"] == "LabCorp"


class TestCmdReport:
    """Tests for report command."""

    def test_cmd_report_found(self, repository, sample_report, sample_panel, sample_biomarker, capsys):
        """cmd_report shows report details."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        args = argparse.Namespace(json=False, id=str(sample_report.id))
        cmd_report(repository, args)
        captured = capsys.readouterr()
        assert "LabCorp" in captured.out
        assert "Metabolic Panel" in captured.out
        assert "Glucose" in captured.out

    def test_cmd_report_not_found(self, repository, capsys):
        """cmd_report exits with error when not found."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"
        args = argparse.Namespace(json=False, id=fake_id)
        with pytest.raises(SystemExit) as exc_info:
            cmd_report(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Report not found" in captured.err

    def test_cmd_report_invalid_id(self, repository, capsys):
        """cmd_report exits with error for invalid UUID."""
        args = argparse.Namespace(json=False, id="not-a-uuid")
        with pytest.raises(SystemExit) as exc_info:
            cmd_report(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid report ID" in captured.err

    def test_cmd_report_json(self, repository, sample_report, sample_panel, sample_biomarker, capsys):
        """cmd_report outputs valid JSON."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        args = argparse.Namespace(json=True, id=str(sample_report.id))
        cmd_report(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["lab_provider"] == "LabCorp"
        assert len(data["panels"]) == 1
        assert data["panels"][0]["name"] == "Metabolic Panel"
        assert len(data["panels"][0]["biomarkers"]) == 1


class TestCmdBiomarker:
    """Tests for biomarker command."""

    def test_cmd_biomarker_found(self, repository, sample_report, sample_panel, sample_biomarker, capsys):
        """cmd_biomarker shows biomarker history."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        args = argparse.Namespace(json=False, code="GLUCOSE", limit=4)
        cmd_biomarker(repository, args)
        captured = capsys.readouterr()
        assert "Glucose" in captured.out
        assert "95.50" in captured.out

    def test_cmd_biomarker_not_found(self, repository, capsys):
        """cmd_biomarker shows message when not found."""
        args = argparse.Namespace(json=False, code="NONEXISTENT", limit=4)
        cmd_biomarker(repository, args)
        captured = capsys.readouterr()
        assert "No biomarker found" in captured.out

    def test_cmd_biomarker_json(self, repository, sample_report, sample_panel, sample_biomarker, capsys):
        """cmd_biomarker outputs valid JSON."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        args = argparse.Namespace(json=True, code="GLUCOSE", limit=4)
        cmd_biomarker(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["code"] == "GLUCOSE"


class TestCmdFlagged:
    """Tests for flagged command."""

    def test_cmd_flagged_found(self, repository, sample_report, sample_panel, capsys):
        """cmd_flagged shows flagged biomarkers."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        flagged_biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=150.0,
            unit="mg/dL",
            reference_low=70.0,
            reference_high=100.0,
            flag=Flag.HIGH,
        )
        repository.insert_biomarker(flagged_biomarker)
        args = argparse.Namespace(json=False)
        cmd_flagged(repository, args)
        captured = capsys.readouterr()
        assert "Glucose" in captured.out
        assert "high" in captured.out

    def test_cmd_flagged_none(self, repository, sample_report, sample_panel, sample_biomarker, capsys):
        """cmd_flagged shows message when no flagged biomarkers."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)  # Normal flag
        args = argparse.Namespace(json=False)
        cmd_flagged(repository, args)
        captured = capsys.readouterr()
        assert "No flagged biomarkers found" in captured.out

    def test_cmd_flagged_json(self, repository, sample_report, sample_panel, capsys):
        """cmd_flagged outputs valid JSON."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        flagged_biomarker = Biomarker(
            id=uuid4(),
            panel_id=sample_panel.id,
            name="Glucose",
            code="GLUCOSE",
            value=150.0,
            unit="mg/dL",
            reference_low=70.0,
            reference_high=100.0,
            flag=Flag.HIGH,
        )
        repository.insert_biomarker(flagged_biomarker)
        args = argparse.Namespace(json=True)
        cmd_flagged(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["flag"] == "high"


class TestCmdRecent:
    """Tests for recent command."""

    def test_cmd_recent_found(self, repository, sample_report, sample_panel, sample_biomarker, capsys):
        """cmd_recent shows recent biomarkers."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        args = argparse.Namespace(json=False)
        cmd_recent(repository, args)
        captured = capsys.readouterr()
        assert "Glucose" in captured.out
        assert "95.50" in captured.out

    def test_cmd_recent_empty(self, repository, capsys):
        """cmd_recent shows message when no biomarkers."""
        args = argparse.Namespace(json=False)
        cmd_recent(repository, args)
        captured = capsys.readouterr()
        assert "No biomarkers found" in captured.out

    def test_cmd_recent_json(self, repository, sample_report, sample_panel, sample_biomarker, capsys):
        """cmd_recent outputs valid JSON."""
        repository.insert_report(sample_report)
        repository.insert_panel(sample_panel)
        repository.insert_biomarker(sample_biomarker)
        args = argparse.Namespace(json=True)
        cmd_recent(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["code"] == "GLUCOSE"


class TestMain:
    """Tests for main entry point."""

    def test_main_no_command_shows_help(self, capsys):
        """main shows help when no command given."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1

    def test_main_help_flag(self, capsys):
        """main responds to --help flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()
