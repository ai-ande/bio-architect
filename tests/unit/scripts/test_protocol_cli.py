"""Tests for protocol CLI script."""

import argparse
import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.protocol import (
    cmd_current,
    cmd_history,
    cmd_list,
    cmd_protocol,
    create_parser,
    format_protocol,
    format_schedule,
    format_supplement,
    main,
    protocol_to_dict,
    supplement_to_dict,
)
from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement_protocol import (
    Frequency,
    ProtocolSupplement,
    ProtocolSupplementType,
    SupplementProtocol,
)
from src.databases.repositories.protocol import ProtocolRepository


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

    def test_parser_current_command(self):
        """Parser recognizes current command."""
        parser = create_parser()
        args = parser.parse_args(["current"])
        assert args.command == "current"

    def test_parser_list_command(self):
        """Parser recognizes list command."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_parser_protocol_command_requires_id(self):
        """Parser protocol command requires id argument."""
        parser = create_parser()
        args = parser.parse_args(["protocol", "123e4567-e89b-12d3-a456-426614174000"])
        assert args.command == "protocol"
        assert args.id == "123e4567-e89b-12d3-a456-426614174000"

    def test_parser_protocol_command_missing_id_fails(self):
        """Parser protocol command fails without id."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["protocol"])

    def test_parser_history_command(self):
        """Parser recognizes history command."""
        parser = create_parser()
        args = parser.parse_args(["history"])
        assert args.command == "history"

    def test_parser_no_command_returns_none(self):
        """Parser returns None for command when no command given."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestFormatFunctions:
    """Tests for format helper functions."""

    def test_format_protocol(self):
        """format_protocol includes all fields."""
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 1, 15),
            prescriber="Dr. Smith",
        )
        result = format_protocol(protocol)
        assert str(protocol.id) in result
        assert "2024-01-15" in result
        assert "Dr. Smith" in result

    def test_format_protocol_no_prescriber(self):
        """format_protocol handles missing prescriber."""
        protocol = SupplementProtocol(
            id=uuid4(),
            protocol_date=date(2024, 1, 15),
            prescriber=None,
        )
        result = format_protocol(protocol)
        assert "-" in result

    def test_format_supplement(self):
        """format_supplement includes all fields."""
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=uuid4(),
            type=ProtocolSupplementType.SCHEDULED,
            name="Vitamin D3",
            dosage="5000 IU",
            frequency=Frequency.DAILY,
            instructions="Take with food",
            breakfast=1,
        )
        result = format_supplement(supplement)
        assert "Vitamin D3" in result
        assert "daily" in result
        assert "5000 IU" in result
        assert "Take with food" in result
        assert "bfast:1" in result

    def test_format_supplement_no_dosage(self):
        """format_supplement handles missing dosage."""
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=uuid4(),
            type=ProtocolSupplementType.SCHEDULED,
            name="Zinc",
            frequency=Frequency.DAILY,
        )
        result = format_supplement(supplement)
        assert "-" in result

    def test_format_schedule_all_times(self):
        """format_schedule includes all schedule times."""
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=uuid4(),
            type=ProtocolSupplementType.SCHEDULED,
            name="Multi",
            frequency=Frequency.DAILY,
            upon_waking=1,
            breakfast=2,
            mid_morning=1,
            lunch=2,
            mid_afternoon=1,
            dinner=2,
            before_sleep=1,
        )
        result = format_schedule(supplement)
        assert "wake:1" in result
        assert "bfast:2" in result
        assert "mid-am:1" in result
        assert "lunch:2" in result
        assert "mid-pm:1" in result
        assert "dinner:2" in result
        assert "sleep:1" in result

    def test_format_schedule_empty(self):
        """format_schedule handles empty schedule."""
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=uuid4(),
            type=ProtocolSupplementType.SCHEDULED,
            name="Test",
            frequency=Frequency.AS_NEEDED,
        )
        result = format_schedule(supplement)
        assert result == "-"


class TestToDictFunctions:
    """Tests for JSON serialization functions."""

    def test_protocol_to_dict(self):
        """protocol_to_dict returns JSON-serializable dict."""
        protocol_id = uuid4()
        protocol = SupplementProtocol(
            id=protocol_id,
            protocol_date=date(2024, 1, 15),
            prescriber="Dr. Smith",
            next_visit="3 months",
            source_file="protocol.pdf",
            created_at=datetime(2024, 1, 20, 10, 30, 0),
            protein_goal="120g daily",
            lifestyle_notes=["Exercise 3x/week", "Sleep 8 hours"],
        )
        result = protocol_to_dict(protocol)
        assert result["id"] == str(protocol_id)
        assert result["protocol_date"] == "2024-01-15"
        assert result["prescriber"] == "Dr. Smith"
        assert result["next_visit"] == "3 months"
        assert result["source_file"] == "protocol.pdf"
        assert result["created_at"] == "2024-01-20T10:30:00"
        assert result["protein_goal"] == "120g daily"
        assert result["lifestyle_notes"] == ["Exercise 3x/week", "Sleep 8 hours"]
        # Verify it's JSON serializable
        json.dumps(result)

    def test_supplement_to_dict(self):
        """supplement_to_dict returns JSON-serializable dict."""
        supplement_id = uuid4()
        protocol_id = uuid4()
        label_id = uuid4()
        supplement = ProtocolSupplement(
            id=supplement_id,
            protocol_id=protocol_id,
            supplement_label_id=label_id,
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
        result = supplement_to_dict(supplement)
        assert result["id"] == str(supplement_id)
        assert result["protocol_id"] == str(protocol_id)
        assert result["supplement_label_id"] == str(label_id)
        assert result["type"] == "scheduled"
        assert result["name"] == "Vitamin D3"
        assert result["instructions"] == "Take with food"
        assert result["dosage"] == "5000 IU"
        assert result["frequency"] == "daily"
        assert result["schedule"]["upon_waking"] == 0
        assert result["schedule"]["breakfast"] == 1
        # Verify it's JSON serializable
        json.dumps(result)

    def test_supplement_to_dict_null_label_id(self):
        """supplement_to_dict handles null supplement_label_id."""
        supplement = ProtocolSupplement(
            id=uuid4(),
            protocol_id=uuid4(),
            supplement_label_id=None,
            type=ProtocolSupplementType.OWN,
            name="Fish Oil",
            frequency=Frequency.DAILY,
        )
        result = supplement_to_dict(supplement)
        assert result["supplement_label_id"] is None
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
        lifestyle_notes=["Exercise 3x/week", "Sleep 8 hours"],
    )


@pytest.fixture
def sample_supplement(sample_protocol):
    """Create a sample ProtocolSupplement."""
    return ProtocolSupplement(
        id=uuid4(),
        protocol_id=sample_protocol.id,
        type=ProtocolSupplementType.SCHEDULED,
        name="Vitamin D3",
        instructions="Take with food",
        dosage="5000 IU",
        frequency=Frequency.DAILY,
        breakfast=1,
    )


class TestCmdCurrent:
    """Tests for current command."""

    def test_cmd_current_empty(self, repository, capsys):
        """cmd_current handles empty database."""
        args = argparse.Namespace(json=False)
        cmd_current(repository, args)
        captured = capsys.readouterr()
        assert "No protocols found" in captured.out

    def test_cmd_current_shows_latest(self, repository, sample_protocol, capsys):
        """cmd_current shows the latest protocol."""
        repository.insert_protocol(sample_protocol)
        args = argparse.Namespace(json=False)
        cmd_current(repository, args)
        captured = capsys.readouterr()
        assert str(sample_protocol.id) in captured.out
        assert "Dr. Smith" in captured.out
        assert "2024-01-15" in captured.out

    def test_cmd_current_shows_supplements(self, repository, sample_protocol, sample_supplement, capsys):
        """cmd_current shows supplements for the protocol."""
        repository.insert_protocol(sample_protocol)
        repository.insert_supplement(sample_supplement)
        args = argparse.Namespace(json=False)
        cmd_current(repository, args)
        captured = capsys.readouterr()
        assert "Vitamin D3" in captured.out
        assert "daily" in captured.out

    def test_cmd_current_json(self, repository, sample_protocol, sample_supplement, capsys):
        """cmd_current outputs valid JSON."""
        repository.insert_protocol(sample_protocol)
        repository.insert_supplement(sample_supplement)
        args = argparse.Namespace(json=True)
        cmd_current(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["prescriber"] == "Dr. Smith"
        assert len(data["supplements"]) == 1
        assert data["supplements"][0]["name"] == "Vitamin D3"

    def test_cmd_current_shows_lifestyle_notes(self, repository, sample_protocol, capsys):
        """cmd_current shows lifestyle notes."""
        repository.insert_protocol(sample_protocol)
        args = argparse.Namespace(json=False)
        cmd_current(repository, args)
        captured = capsys.readouterr()
        assert "Lifestyle Notes" in captured.out
        assert "Exercise 3x/week" in captured.out


class TestCmdList:
    """Tests for list command."""

    def test_cmd_list_empty(self, repository, capsys):
        """cmd_list handles empty database."""
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "No protocols found" in captured.out

    def test_cmd_list_shows_protocols(self, repository, sample_protocol, capsys):
        """cmd_list shows protocols."""
        repository.insert_protocol(sample_protocol)
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert str(sample_protocol.id) in captured.out
        assert "Dr. Smith" in captured.out

    def test_cmd_list_multiple_protocols(self, repository, capsys):
        """cmd_list shows multiple protocols."""
        for i in range(3):
            protocol = SupplementProtocol(
                id=uuid4(),
                protocol_date=date(2024, i + 1, 1),
                prescriber=f"Dr. {i}",
            )
            repository.insert_protocol(protocol)
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "Dr. 0" in captured.out
        assert "Dr. 1" in captured.out
        assert "Dr. 2" in captured.out

    def test_cmd_list_json(self, repository, sample_protocol, capsys):
        """cmd_list outputs valid JSON."""
        repository.insert_protocol(sample_protocol)
        args = argparse.Namespace(json=True)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["prescriber"] == "Dr. Smith"


class TestCmdProtocol:
    """Tests for protocol command."""

    def test_cmd_protocol_found(self, repository, sample_protocol, sample_supplement, capsys):
        """cmd_protocol shows protocol details."""
        repository.insert_protocol(sample_protocol)
        repository.insert_supplement(sample_supplement)
        args = argparse.Namespace(json=False, id=str(sample_protocol.id))
        cmd_protocol(repository, args)
        captured = capsys.readouterr()
        assert "Dr. Smith" in captured.out
        assert "Vitamin D3" in captured.out

    def test_cmd_protocol_not_found(self, repository, capsys):
        """cmd_protocol exits with error when not found."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"
        args = argparse.Namespace(json=False, id=fake_id)
        with pytest.raises(SystemExit) as exc_info:
            cmd_protocol(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Protocol not found" in captured.err

    def test_cmd_protocol_invalid_id(self, repository, capsys):
        """cmd_protocol exits with error for invalid UUID."""
        args = argparse.Namespace(json=False, id="not-a-uuid")
        with pytest.raises(SystemExit) as exc_info:
            cmd_protocol(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid protocol ID" in captured.err

    def test_cmd_protocol_json(self, repository, sample_protocol, sample_supplement, capsys):
        """cmd_protocol outputs valid JSON."""
        repository.insert_protocol(sample_protocol)
        repository.insert_supplement(sample_supplement)
        args = argparse.Namespace(json=True, id=str(sample_protocol.id))
        cmd_protocol(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["prescriber"] == "Dr. Smith"
        assert len(data["supplements"]) == 1
        assert data["supplements"][0]["name"] == "Vitamin D3"


class TestCmdHistory:
    """Tests for history command."""

    def test_cmd_history_empty(self, repository, capsys):
        """cmd_history handles empty database."""
        args = argparse.Namespace(json=False)
        cmd_history(repository, args)
        captured = capsys.readouterr()
        assert "No protocols found" in captured.out

    def test_cmd_history_shows_all_protocols(self, repository, capsys):
        """cmd_history shows all protocols."""
        for i in range(3):
            protocol = SupplementProtocol(
                id=uuid4(),
                protocol_date=date(2024, i + 1, 1),
                prescriber=f"Dr. {i}",
            )
            repository.insert_protocol(protocol)
        args = argparse.Namespace(json=False)
        cmd_history(repository, args)
        captured = capsys.readouterr()
        assert "Dr. 0" in captured.out
        assert "Dr. 1" in captured.out
        assert "Dr. 2" in captured.out

    def test_cmd_history_shows_supplements(self, repository, sample_protocol, sample_supplement, capsys):
        """cmd_history shows supplements for each protocol."""
        repository.insert_protocol(sample_protocol)
        repository.insert_supplement(sample_supplement)
        args = argparse.Namespace(json=False)
        cmd_history(repository, args)
        captured = capsys.readouterr()
        assert "Vitamin D3" in captured.out

    def test_cmd_history_json(self, repository, sample_protocol, sample_supplement, capsys):
        """cmd_history outputs valid JSON."""
        repository.insert_protocol(sample_protocol)
        repository.insert_supplement(sample_supplement)
        args = argparse.Namespace(json=True)
        cmd_history(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["prescriber"] == "Dr. Smith"
        assert len(data[0]["supplements"]) == 1

    def test_cmd_history_ordered_by_date_desc(self, repository, capsys):
        """cmd_history shows protocols in descending date order."""
        dates = [date(2024, 1, 1), date(2024, 3, 1), date(2024, 2, 1)]
        for d in dates:
            protocol = SupplementProtocol(
                id=uuid4(),
                protocol_date=d,
                prescriber=f"Dr. {d.month}",
            )
            repository.insert_protocol(protocol)
        args = argparse.Namespace(json=True)
        cmd_history(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        # Should be ordered: March, Feb, Jan
        assert data[0]["protocol_date"] == "2024-03-01"
        assert data[1]["protocol_date"] == "2024-02-01"
        assert data[2]["protocol_date"] == "2024-01-01"


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
