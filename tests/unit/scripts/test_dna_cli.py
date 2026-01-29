"""Tests for DNA CLI script."""

import argparse
import json
import tempfile
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from scripts.dna import (
    cmd_gene,
    cmd_high_impact,
    cmd_list,
    cmd_snp,
    create_parser,
    format_snp,
    format_test,
    main,
    snp_to_dict,
    dna_test_to_dict,
)
from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.dna import DnaTest, Repute, Snp
from src.databases.repositories.dna import DnaRepository


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

    def test_parser_snp_command_requires_rsid(self):
        """Parser snp command requires rsid argument."""
        parser = create_parser()
        args = parser.parse_args(["snp", "rs1234"])
        assert args.command == "snp"
        assert args.rsid == "rs1234"

    def test_parser_snp_command_missing_rsid_fails(self):
        """Parser snp command fails without rsid."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["snp"])

    def test_parser_gene_command_requires_gene(self):
        """Parser gene command requires gene argument."""
        parser = create_parser()
        args = parser.parse_args(["gene", "MTHFR"])
        assert args.command == "gene"
        assert args.gene == "MTHFR"

    def test_parser_gene_command_missing_gene_fails(self):
        """Parser gene command fails without gene."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["gene"])

    def test_parser_high_impact_command(self):
        """Parser recognizes high-impact command."""
        parser = create_parser()
        args = parser.parse_args(["high-impact"])
        assert args.command == "high-impact"

    def test_parser_no_command_returns_none(self):
        """Parser returns None for command when no command given."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestFormatFunctions:
    """Tests for format helper functions."""

    def test_format_snp_with_repute(self):
        """format_snp includes repute value."""
        snp = Snp(
            id=uuid4(),
            dna_test_id=uuid4(),
            rsid="rs1234567",
            genotype="AG",
            magnitude=3.5,
            repute=Repute.GOOD,
            gene="MTHFR",
        )
        result = format_snp(snp)
        assert "rs1234567" in result
        assert "AG" in result
        assert "MTHFR" in result
        assert "3.5" in result
        assert "good" in result

    def test_format_snp_without_repute(self):
        """format_snp shows - for null repute."""
        snp = Snp(
            id=uuid4(),
            dna_test_id=uuid4(),
            rsid="rs1234567",
            genotype="AG",
            magnitude=3.5,
            repute=None,
            gene="MTHFR",
        )
        result = format_snp(snp)
        assert result.endswith("-")

    def test_format_test(self):
        """format_test includes all fields."""
        test = DnaTest(
            id=uuid4(),
            source="23andMe",
            collected_date=date(2024, 1, 15),
            source_file="dna_export.txt",
        )
        result = format_test(test)
        assert str(test.id) in result
        assert "23andMe" in result
        assert "2024-01-15" in result
        assert "dna_export.txt" in result


class TestToDictFunctions:
    """Tests for JSON serialization functions."""

    def test_snp_to_dict(self):
        """snp_to_dict returns JSON-serializable dict."""
        snp_id = uuid4()
        test_id = uuid4()
        snp = Snp(
            id=snp_id,
            dna_test_id=test_id,
            rsid="rs1234567",
            genotype="AG",
            magnitude=3.5,
            repute=Repute.BAD,
            gene="MTHFR",
        )
        result = snp_to_dict(snp)
        assert result["id"] == str(snp_id)
        assert result["dna_test_id"] == str(test_id)
        assert result["rsid"] == "rs1234567"
        assert result["genotype"] == "AG"
        assert result["magnitude"] == 3.5
        assert result["repute"] == "bad"
        assert result["gene"] == "MTHFR"
        # Verify it's JSON serializable
        json.dumps(result)

    def test_snp_to_dict_null_repute(self):
        """snp_to_dict handles null repute."""
        snp = Snp(
            id=uuid4(),
            dna_test_id=uuid4(),
            rsid="rs1234567",
            genotype="AG",
            magnitude=3.5,
            repute=None,
            gene="MTHFR",
        )
        result = snp_to_dict(snp)
        assert result["repute"] is None

    def test_dna_test_to_dict(self):
        """dna_test_to_dict returns JSON-serializable dict."""
        test_id = uuid4()
        test = DnaTest(
            id=test_id,
            source="23andMe",
            collected_date=date(2024, 1, 15),
            source_file="dna_export.txt",
            created_at=datetime(2024, 1, 20, 10, 30, 0),
        )
        result = dna_test_to_dict(test)
        assert result["id"] == str(test_id)
        assert result["source"] == "23andMe"
        assert result["collected_date"] == "2024-01-15"
        assert result["source_file"] == "dna_export.txt"
        assert result["created_at"] == "2024-01-20T10:30:00"
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
    """Create a DnaRepository with the test database."""
    return DnaRepository(db_client)


@pytest.fixture
def sample_test():
    """Create a sample DnaTest."""
    return DnaTest(
        id=uuid4(),
        source="23andMe",
        collected_date=date(2024, 1, 15),
        source_file="dna_export.txt",
        created_at=datetime(2024, 1, 20, 10, 30, 0),
    )


@pytest.fixture
def sample_snp(sample_test):
    """Create a sample Snp."""
    return Snp(
        id=uuid4(),
        dna_test_id=sample_test.id,
        rsid="rs1234567",
        genotype="AG",
        magnitude=3.5,
        repute=Repute.GOOD,
        gene="MTHFR",
    )


class TestCmdList:
    """Tests for list command."""

    def test_cmd_list_empty(self, repository, capsys):
        """cmd_list handles empty database."""
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "No DNA tests found" in captured.out

    def test_cmd_list_with_tests(self, repository, sample_test, capsys):
        """cmd_list shows tests."""
        repository.insert_test(sample_test)
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "23andMe" in captured.out
        assert "2024-01-15" in captured.out

    def test_cmd_list_json(self, repository, sample_test, capsys):
        """cmd_list outputs valid JSON."""
        repository.insert_test(sample_test)
        args = argparse.Namespace(json=True)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["source"] == "23andMe"


class TestCmdSnp:
    """Tests for snp command."""

    def test_cmd_snp_found(self, repository, sample_test, sample_snp, capsys):
        """cmd_snp shows SNP details."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        args = argparse.Namespace(json=False, rsid="rs1234567")
        cmd_snp(repository, args)
        captured = capsys.readouterr()
        assert "rs1234567" in captured.out
        assert "AG" in captured.out
        assert "MTHFR" in captured.out

    def test_cmd_snp_not_found(self, repository, capsys):
        """cmd_snp exits with error when not found."""
        args = argparse.Namespace(json=False, rsid="rs9999999")
        with pytest.raises(SystemExit) as exc_info:
            cmd_snp(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "SNP not found" in captured.err

    def test_cmd_snp_json(self, repository, sample_test, sample_snp, capsys):
        """cmd_snp outputs valid JSON."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        args = argparse.Namespace(json=True, rsid="rs1234567")
        cmd_snp(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["rsid"] == "rs1234567"
        assert data["genotype"] == "AG"


class TestCmdGene:
    """Tests for gene command."""

    def test_cmd_gene_found(self, repository, sample_test, sample_snp, capsys):
        """cmd_gene shows SNPs for gene."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        args = argparse.Namespace(json=False, gene="MTHFR")
        cmd_gene(repository, args)
        captured = capsys.readouterr()
        assert "rs1234567" in captured.out
        assert "MTHFR" in captured.out

    def test_cmd_gene_not_found(self, repository, capsys):
        """cmd_gene shows message when no SNPs found."""
        args = argparse.Namespace(json=False, gene="UNKNOWN")
        cmd_gene(repository, args)
        captured = capsys.readouterr()
        assert "No SNPs found" in captured.out

    def test_cmd_gene_json(self, repository, sample_test, sample_snp, capsys):
        """cmd_gene outputs valid JSON."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        args = argparse.Namespace(json=True, gene="MTHFR")
        cmd_gene(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["gene"] == "MTHFR"


class TestCmdHighImpact:
    """Tests for high-impact command."""

    def test_cmd_high_impact_found(self, repository, sample_test, sample_snp, capsys):
        """cmd_high_impact shows high magnitude SNPs."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)  # magnitude 3.5
        args = argparse.Namespace(json=False)
        cmd_high_impact(repository, args)
        captured = capsys.readouterr()
        assert "rs1234567" in captured.out

    def test_cmd_high_impact_excludes_low(self, repository, sample_test, capsys):
        """cmd_high_impact excludes SNPs with magnitude < 3."""
        repository.insert_test(sample_test)
        low_impact_snp = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs9999999",
            genotype="CC",
            magnitude=1.0,
            repute=None,
            gene="TEST",
        )
        repository.insert_snp(low_impact_snp)
        args = argparse.Namespace(json=False)
        cmd_high_impact(repository, args)
        captured = capsys.readouterr()
        assert "No high-impact SNPs found" in captured.out

    def test_cmd_high_impact_json(self, repository, sample_test, sample_snp, capsys):
        """cmd_high_impact outputs valid JSON."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        args = argparse.Namespace(json=True)
        cmd_high_impact(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["magnitude"] == 3.5


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
