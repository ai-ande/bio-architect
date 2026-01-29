"""Tests for DNA CLI import command."""

import argparse
import json
from io import StringIO

import pytest
from pydantic import ValidationError
from sqlmodel import select

from cli.databases.dna import cmd_import, parse_dna_json
from src.databases.datatypes.dna import DnaTest, Repute, Snp


class TestParseDnaJson:
    """Tests for parse_dna_json function."""

    def test_parse_creates_dna_test(self):
        """Parse should create a DnaTest with correct fields."""
        data = {
            "source": "Promethease",
            "collected_date": "2023-06-15",
            "snps": [],
        }
        dna_test, snps = parse_dna_json(data, "test.json")

        assert dna_test.source == "Promethease"
        assert str(dna_test.collected_date) == "2023-06-15"
        assert dna_test.source_file == "test.json"

    def test_parse_creates_snps(self):
        """Parse should create Snp records linked to DnaTest."""
        data = {
            "source": "Promethease",
            "collected_date": "2023-06-15",
            "snps": [
                {
                    "rsid": "rs1801133",
                    "genotype": "TT",
                    "magnitude": 2.5,
                    "repute": "bad",
                    "gene": "MTHFR",
                },
                {
                    "rsid": "rs1801131",
                    "genotype": "GT",
                    "magnitude": 1.5,
                    "repute": "good",
                    "gene": "MTHFR",
                },
            ],
        }
        dna_test, snps = parse_dna_json(data, None)

        assert len(snps) == 2
        assert snps[0].rsid == "rs1801133"
        assert snps[0].genotype == "TT"
        assert snps[0].magnitude == 2.5
        assert snps[0].repute == Repute.BAD
        assert snps[0].gene == "MTHFR"
        assert snps[0].dna_test_id == dna_test.id
        assert snps[1].repute == Repute.GOOD

    def test_parse_handles_null_repute(self):
        """Parse should handle null repute values."""
        data = {
            "source": "Promethease",
            "collected_date": "2023-06-15",
            "snps": [
                {
                    "rsid": "rs12345",
                    "genotype": "AA",
                    "magnitude": 0.5,
                    "repute": None,
                    "gene": "TEST",
                },
            ],
        }
        dna_test, snps = parse_dna_json(data, "test.json")

        assert snps[0].repute is None

    def test_parse_rejects_invalid_magnitude(self):
        """Parse should reject magnitude outside 0-10 range."""
        data = {
            "source": "Promethease",
            "collected_date": "2023-06-15",
            "snps": [
                {
                    "rsid": "rs12345",
                    "genotype": "AA",
                    "magnitude": 15.0,  # Invalid - too high
                    "repute": None,
                    "gene": "TEST",
                },
            ],
        }
        with pytest.raises(ValidationError, match="magnitude must be between 0 and 10"):
            parse_dna_json(data, "test.json")


class TestDnaImport:
    """Tests for DNA import command."""

    @pytest.fixture
    def sample_json(self):
        """Sample valid DNA JSON."""
        return {
            "source": "Promethease",
            "collected_date": "2023-06-15",
            "snps": [
                {
                    "rsid": "rs1801133",
                    "genotype": "TT",
                    "magnitude": 2.5,
                    "repute": "bad",
                    "gene": "MTHFR",
                },
                {
                    "rsid": "rs1801131",
                    "genotype": "GT",
                    "magnitude": 1.5,
                    "repute": "good",
                    "gene": "MTHFR",
                },
            ],
        }

    def test_import_creates_dna_test(self, tmp_path, db_session, sample_json):
        """Import should create a DnaTest record."""
        json_file = tmp_path / "dna.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        tests = db_session.exec(select(DnaTest)).all()
        assert len(tests) == 1
        assert tests[0].source == "Promethease"

    def test_import_creates_snps(self, tmp_path, db_session, sample_json):
        """Import should create Snp records linked to DnaTest."""
        json_file = tmp_path / "dna.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        snps = db_session.exec(select(Snp)).all()
        assert len(snps) == 2
        rsids = {s.rsid for s in snps}
        assert rsids == {"rs1801133", "rs1801131"}

    def test_import_sets_source_file(self, tmp_path, db_session, sample_json):
        """Import should set source_file to the input file path."""
        json_file = tmp_path / "dna.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=False)
        cmd_import(db_session, args)

        test = db_session.exec(select(DnaTest)).first()
        assert test.source_file == str(json_file)

    def test_import_from_stdin(self, db_session, sample_json, monkeypatch):
        """Import should read from stdin when no file provided."""
        stdin_data = json.dumps(sample_json)
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))

        args = argparse.Namespace(file=None, json=False)
        cmd_import(db_session, args)

        tests = db_session.exec(select(DnaTest)).all()
        assert len(tests) == 1
        assert tests[0].source_file == "stdin"  # Placeholder for stdin

    def test_import_json_output(self, tmp_path, db_session, sample_json, capsys):
        """Import with --json should return structured output."""
        json_file = tmp_path / "dna.json"
        json_file.write_text(json.dumps(sample_json))

        args = argparse.Namespace(file=str(json_file), json=True)
        cmd_import(db_session, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert "dna_test_id" in result
        assert result["snps_created"] == 2

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
        json_file.write_text(json.dumps({"source": "Promethease"}))  # Missing collected_date

        args = argparse.Namespace(file=str(json_file), json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1

    def test_import_no_partial_records_on_validation_error(self, tmp_path, db_client):
        """Import should not leave partial records if validation fails."""
        # First SNP valid, second has invalid magnitude
        data = {
            "source": "Promethease",
            "collected_date": "2023-06-15",
            "snps": [
                {"rsid": "rs1", "genotype": "AA", "magnitude": 2.0, "gene": "TEST"},
                {"rsid": "rs2", "genotype": "TT", "magnitude": 20.0, "gene": "TEST"},  # Invalid
            ],
        }
        json_file = tmp_path / "partial.json"
        json_file.write_text(json.dumps(data))

        with db_client.get_session() as session:
            args = argparse.Namespace(file=str(json_file), json=False)
            with pytest.raises(SystemExit):
                cmd_import(session, args)

        # Verify no partial data was inserted
        with db_client.get_session() as session:
            tests = session.exec(select(DnaTest)).all()
            snps = session.exec(select(Snp)).all()
            assert len(tests) == 0
            assert len(snps) == 0

    def test_import_file_not_found_exits_with_error(self, db_session):
        """Import should exit with error for non-existent file."""
        args = argparse.Namespace(file="/nonexistent/path.json", json=False)
        with pytest.raises(SystemExit) as exc_info:
            cmd_import(db_session, args)
        assert exc_info.value.code == 1
