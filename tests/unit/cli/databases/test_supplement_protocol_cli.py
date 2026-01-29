"""Tests for supplement protocol CLI import command."""

import argparse
import json
from io import StringIO

import pytest
from sqlmodel import select

from cli.databases.supplement_protocol import cmd_import, parse_protocol_json
from src.databases.datatypes.supplement_protocol import (
    Frequency,
    ProtocolSupplement,
    ProtocolSupplementType,
    SupplementProtocol,
)


class TestParseProtocolJson:
    """Tests for parse_protocol_json function."""

    def test_parse_creates_protocol(self):
        """Parse should create a SupplementProtocol with correct fields."""
        data = {
            "protocol_date": "2024-12-29",
            "prescriber": "Dr. Smith",
            "next_visit": "3 months",
            "supplements": [],
            "own_supplements": [],
            "lifestyle_notes": {
                "protein_goal": "110g/day",
                "other": ["Drink more water", "Sleep 8 hours"],
            },
        }
        protocol, supplements = parse_protocol_json(data, "test.json")

        assert str(protocol.protocol_date) == "2024-12-29"
        assert protocol.prescriber == "Dr. Smith"
        assert protocol.next_visit == "3 months"
        assert protocol.protein_goal == "110g/day"
        assert protocol.lifestyle_notes == ["Drink more water", "Sleep 8 hours"]
        assert protocol.source_file == "test.json"

    def test_parse_creates_scheduled_supplements(self):
        """Parse should create ProtocolSupplement records for scheduled supplements."""
        data = {
            "protocol_date": "2024-12-29",
            "supplements": [
                {
                    "name": "Vitamin D3",
                    "instructions": "Take with food",
                    "frequency": "daily",
                    "schedule": {
                        "upon_waking": 0,
                        "breakfast": 1,
                        "mid_morning": 0,
                        "lunch": 0,
                        "mid_afternoon": 0,
                        "dinner": 0,
                        "before_sleep": 0,
                    },
                },
            ],
            "own_supplements": [],
        }
        protocol, supplements = parse_protocol_json(data, None)

        assert len(supplements) == 1
        assert supplements[0].name == "Vitamin D3"
        assert supplements[0].instructions == "Take with food"
        assert supplements[0].frequency == Frequency.DAILY
        assert supplements[0].type == ProtocolSupplementType.SCHEDULED
        assert supplements[0].breakfast == 1
        assert supplements[0].protocol_id == protocol.id

    def test_parse_creates_own_supplements(self):
        """Parse should create ProtocolSupplement records for own supplements."""
        data = {
            "protocol_date": "2024-12-29",
            "supplements": [],
            "own_supplements": [
                {
                    "name": "Fish Oil",
                    "dosage": "2 capsules",
                    "frequency": "daily",
                },
                {
                    "name": "Probiotic",
                    "dosage": "1 capsule",
                    "frequency": "daily",
                },
            ],
        }
        protocol, supplements = parse_protocol_json(data, None)

        assert len(supplements) == 2
        assert all(s.type == ProtocolSupplementType.OWN for s in supplements)
        assert supplements[0].name == "Fish Oil"
        assert supplements[0].dosage == "2 capsules"
        assert supplements[0].protocol_id == protocol.id

    def test_parse_handles_missing_optional_fields(self):
        """Parse should handle missing optional fields."""
        data = {
            "protocol_date": "2024-12-29",
            "supplements": [],
            "own_supplements": [],
        }
        protocol, supplements = parse_protocol_json(data, None)

        assert protocol.prescriber is None
        assert protocol.next_visit is None
        assert protocol.protein_goal is None
        assert protocol.lifestyle_notes == []


class TestProtocolImport:
    """Tests for protocol import command."""

    @pytest.fixture
    def sample_json(self):
        """Sample valid protocol JSON."""
        return {
            "protocol_date": "2024-12-29",
            "prescriber": "Dr. Smith",
            "next_visit": "3 months",
            "supplements": [
                {
                    "name": "Vitamin D3",
                    "instructions": "Take with breakfast",
                    "frequency": "daily",
                    "schedule": {
                        "upon_waking": 0,
                        "breakfast": 1,
                        "mid_morning": 0,
                        "lunch": 0,
                        "mid_afternoon": 0,
                        "dinner": 0,
                        "before_sleep": 0,
                    },
                },
            ],
            "own_supplements": [
                {
                    "name": "Fish Oil",
                    "dosage": "2 capsules",
                    "frequency": "daily",
                },
            ],
            "lifestyle_notes": {
                "protein_goal": "110g/day",
                "other": ["Stay hydrated"],
            },
        }

    def test_import_creates_protocol(self, tmp_path, db_session, sample_json):
        """Import should create a SupplementProtocol record."""
        json_file = tmp_path / "protocol.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        protocols = db_session.exec(select(SupplementProtocol)).all()
        assert len(protocols) == 1
        assert protocols[0].prescriber == "Dr. Smith"

    def test_import_creates_supplements(self, tmp_path, db_session, sample_json):
        """Import should create ProtocolSupplement records."""
        json_file = tmp_path / "protocol.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        supplements = db_session.exec(select(ProtocolSupplement)).all()
        assert len(supplements) == 2
        names = {s.name for s in supplements}
        assert names == {"Vitamin D3", "Fish Oil"}

    def test_import_sets_source_file(self, tmp_path, db_session, sample_json):
        """Import should set source_file to the input file path."""
        json_file = tmp_path / "protocol.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        protocol = db_session.exec(select(SupplementProtocol)).first()
        assert protocol.source_file == str(json_file)

    def test_import_from_stdin(self, db_session, sample_json, monkeypatch):
        """Import should read from stdin when no file provided."""
        stdin_data = json.dumps(sample_json)
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))

        args = argparse.Namespace(file=None, json=False)
        cmd_import(db_session, args)

        protocols = db_session.exec(select(SupplementProtocol)).all()
        assert len(protocols) == 1
        assert protocols[0].source_file is None

    def test_import_json_output(self, tmp_path, db_session, sample_json, capsys):
        """Import with --json should return structured output."""
        json_file = tmp_path / "protocol.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=True)
        cmd_import(db_session, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert "protocol_id" in result
        assert result["supplements_created"] == 2

    def test_import_invalid_json_exits_with_error(self, tmp_path, db_session):
        """Import should exit with error for invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json {{{")

        args = argparse.Namespace(file=str(json_file), json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1

    def test_import_missing_required_fields_exits_with_error(self, tmp_path, db_session):
        """Import should exit with error for missing required fields."""
        json_file = tmp_path / "incomplete.json"
        json_file.write_text(json.dumps({"prescriber": "Dr. Smith"}))  # Missing protocol_date

        args = argparse.Namespace(file=str(json_file), json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1

    def test_import_no_partial_records_on_error(self, tmp_path, db_client):
        """Import should not leave partial records if error occurs."""
        # Invalid frequency value
        data = {
            "protocol_date": "2024-12-29",
            "supplements": [
                {
                    "name": "Test",
                    "frequency": "invalid_frequency",
                },
            ],
            "own_supplements": [],
        }
        json_file = tmp_path / "partial.json"
        json_file.write_text(json.dumps(data))

        with db_client.get_session() as session:
            args = argparse.Namespace(file=str(json_file), json=False)
            with pytest.raises(SystemExit):
                cmd_import(session, args)

        # Verify no partial data was inserted
        with db_client.get_session() as session:
            protocols = session.exec(select(SupplementProtocol)).all()
            supplements = session.exec(select(ProtocolSupplement)).all()
            assert len(protocols) == 0
            assert len(supplements) == 0

    def test_import_file_not_found_exits_with_error(self, db_session):
        """Import should exit with error for non-existent file."""
        args = argparse.Namespace(file="/nonexistent/path.json", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1
