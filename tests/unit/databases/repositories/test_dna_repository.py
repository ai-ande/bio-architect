"""Tests for DnaRepository."""

import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.dna import DnaTest, Repute, Snp
from src.databases.repositories.dna import DnaRepository


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


class TestInsertTest:
    """Tests for insert_test method."""

    def test_insert_test_returns_model(self, repository, sample_test):
        """insert_test returns the inserted DnaTest model."""
        result = repository.insert_test(sample_test)
        assert isinstance(result, DnaTest)
        assert result.id == sample_test.id
        assert result.source == sample_test.source

    def test_insert_test_persists_data(self, repository, sample_test):
        """insert_test persists data to database."""
        repository.insert_test(sample_test)
        retrieved = repository.get_test_by_id(sample_test.id)
        assert retrieved is not None
        assert retrieved.id == sample_test.id
        assert retrieved.source == sample_test.source
        assert retrieved.collected_date == sample_test.collected_date
        assert retrieved.source_file == sample_test.source_file

    def test_insert_test_preserves_all_fields(self, repository):
        """insert_test preserves all fields including created_at."""
        test = DnaTest(
            id=uuid4(),
            source="AncestryDNA",
            collected_date=date(2023, 6, 1),
            source_file="ancestry_data.txt",
            created_at=datetime(2023, 6, 5, 14, 0, 0),
        )
        repository.insert_test(test)
        retrieved = repository.get_test_by_id(test.id)
        assert retrieved.created_at == test.created_at


class TestInsertSnp:
    """Tests for insert_snp method."""

    def test_insert_snp_returns_model(self, repository, sample_test, sample_snp):
        """insert_snp returns the inserted Snp model."""
        repository.insert_test(sample_test)
        result = repository.insert_snp(sample_snp)
        assert isinstance(result, Snp)
        assert result.id == sample_snp.id
        assert result.rsid == sample_snp.rsid

    def test_insert_snp_persists_data(self, repository, sample_test, sample_snp):
        """insert_snp persists data to database."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        retrieved = repository.get_snp_by_rsid(sample_snp.rsid)
        assert retrieved is not None
        assert retrieved.id == sample_snp.id
        assert retrieved.genotype == sample_snp.genotype
        assert retrieved.magnitude == sample_snp.magnitude
        assert retrieved.repute == sample_snp.repute
        assert retrieved.gene == sample_snp.gene

    def test_insert_snp_with_null_repute(self, repository, sample_test):
        """insert_snp handles null repute."""
        repository.insert_test(sample_test)
        snp = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs9999999",
            genotype="CC",
            magnitude=1.0,
            repute=None,
            gene="APOE",
        )
        repository.insert_snp(snp)
        retrieved = repository.get_snp_by_rsid(snp.rsid)
        assert retrieved is not None
        assert retrieved.repute is None

    def test_insert_snp_with_bad_repute(self, repository, sample_test):
        """insert_snp handles bad repute."""
        repository.insert_test(sample_test)
        snp = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs8888888",
            genotype="TT",
            magnitude=5.0,
            repute=Repute.BAD,
            gene="COMT",
        )
        repository.insert_snp(snp)
        retrieved = repository.get_snp_by_rsid(snp.rsid)
        assert retrieved.repute == Repute.BAD


class TestGetTestById:
    """Tests for get_test_by_id method."""

    def test_get_test_by_id_returns_model(self, repository, sample_test):
        """get_test_by_id returns DnaTest model."""
        repository.insert_test(sample_test)
        result = repository.get_test_by_id(sample_test.id)
        assert isinstance(result, DnaTest)

    def test_get_test_by_id_not_found_returns_none(self, repository):
        """get_test_by_id returns None when not found."""
        result = repository.get_test_by_id(uuid4())
        assert result is None

    def test_get_test_by_id_returns_correct_test(self, repository):
        """get_test_by_id returns the correct test when multiple exist."""
        test1 = DnaTest(
            id=uuid4(),
            source="23andMe",
            collected_date=date(2024, 1, 1),
            source_file="test1.txt",
        )
        test2 = DnaTest(
            id=uuid4(),
            source="AncestryDNA",
            collected_date=date(2024, 2, 1),
            source_file="test2.txt",
        )
        repository.insert_test(test1)
        repository.insert_test(test2)
        result = repository.get_test_by_id(test2.id)
        assert result.source == "AncestryDNA"


class TestGetSnpsByTest:
    """Tests for get_snps_by_test method."""

    def test_get_snps_by_test_returns_list(self, repository, sample_test, sample_snp):
        """get_snps_by_test returns a list."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        result = repository.get_snps_by_test(sample_test.id)
        assert isinstance(result, list)

    def test_get_snps_by_test_returns_snp_models(self, repository, sample_test, sample_snp):
        """get_snps_by_test returns Snp models."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        result = repository.get_snps_by_test(sample_test.id)
        assert len(result) == 1
        assert isinstance(result[0], Snp)

    def test_get_snps_by_test_returns_empty_list(self, repository, sample_test):
        """get_snps_by_test returns empty list when no SNPs."""
        repository.insert_test(sample_test)
        result = repository.get_snps_by_test(sample_test.id)
        assert result == []

    def test_get_snps_by_test_returns_multiple_snps(self, repository, sample_test):
        """get_snps_by_test returns all SNPs for the test."""
        repository.insert_test(sample_test)
        snp1 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs1111111",
            genotype="AA",
            magnitude=2.0,
            repute=Repute.GOOD,
            gene="MTHFR",
        )
        snp2 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs2222222",
            genotype="GG",
            magnitude=3.0,
            repute=Repute.BAD,
            gene="COMT",
        )
        repository.insert_snp(snp1)
        repository.insert_snp(snp2)
        result = repository.get_snps_by_test(sample_test.id)
        assert len(result) == 2

    def test_get_snps_by_test_only_returns_matching_test(self, repository):
        """get_snps_by_test only returns SNPs for the specified test."""
        test1 = DnaTest(
            id=uuid4(),
            source="23andMe",
            collected_date=date(2024, 1, 1),
            source_file="test1.txt",
        )
        test2 = DnaTest(
            id=uuid4(),
            source="AncestryDNA",
            collected_date=date(2024, 2, 1),
            source_file="test2.txt",
        )
        repository.insert_test(test1)
        repository.insert_test(test2)

        snp1 = Snp(
            id=uuid4(),
            dna_test_id=test1.id,
            rsid="rs1111111",
            genotype="AA",
            magnitude=2.0,
            repute=None,
            gene="MTHFR",
        )
        snp2 = Snp(
            id=uuid4(),
            dna_test_id=test2.id,
            rsid="rs2222222",
            genotype="GG",
            magnitude=3.0,
            repute=None,
            gene="COMT",
        )
        repository.insert_snp(snp1)
        repository.insert_snp(snp2)

        result = repository.get_snps_by_test(test1.id)
        assert len(result) == 1
        assert result[0].rsid == "rs1111111"


class TestGetSnpByRsid:
    """Tests for get_snp_by_rsid method."""

    def test_get_snp_by_rsid_returns_snp(self, repository, sample_test, sample_snp):
        """get_snp_by_rsid returns Snp model."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        result = repository.get_snp_by_rsid(sample_snp.rsid)
        assert isinstance(result, Snp)
        assert result.rsid == sample_snp.rsid

    def test_get_snp_by_rsid_not_found_returns_none(self, repository):
        """get_snp_by_rsid returns None when not found."""
        result = repository.get_snp_by_rsid("rs9999999")
        assert result is None

    def test_get_snp_by_rsid_returns_correct_snp(self, repository, sample_test):
        """get_snp_by_rsid returns the correct SNP when multiple exist."""
        repository.insert_test(sample_test)
        snp1 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs1111111",
            genotype="AA",
            magnitude=2.0,
            repute=Repute.GOOD,
            gene="MTHFR",
        )
        snp2 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs2222222",
            genotype="GG",
            magnitude=3.0,
            repute=Repute.BAD,
            gene="COMT",
        )
        repository.insert_snp(snp1)
        repository.insert_snp(snp2)
        result = repository.get_snp_by_rsid("rs2222222")
        assert result.genotype == "GG"
        assert result.gene == "COMT"


class TestGetSnpsByGene:
    """Tests for get_snps_by_gene method."""

    def test_get_snps_by_gene_returns_list(self, repository, sample_test, sample_snp):
        """get_snps_by_gene returns a list."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        result = repository.get_snps_by_gene(sample_snp.gene)
        assert isinstance(result, list)

    def test_get_snps_by_gene_returns_snp_models(self, repository, sample_test, sample_snp):
        """get_snps_by_gene returns Snp models."""
        repository.insert_test(sample_test)
        repository.insert_snp(sample_snp)
        result = repository.get_snps_by_gene(sample_snp.gene)
        assert len(result) == 1
        assert isinstance(result[0], Snp)

    def test_get_snps_by_gene_returns_empty_list(self, repository, sample_test):
        """get_snps_by_gene returns empty list when no SNPs for gene."""
        repository.insert_test(sample_test)
        result = repository.get_snps_by_gene("UNKNOWN_GENE")
        assert result == []

    def test_get_snps_by_gene_returns_multiple_snps(self, repository, sample_test):
        """get_snps_by_gene returns all SNPs for the gene."""
        repository.insert_test(sample_test)
        snp1 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs1801133",
            genotype="CT",
            magnitude=3.5,
            repute=Repute.BAD,
            gene="MTHFR",
        )
        snp2 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs1801131",
            genotype="AC",
            magnitude=2.5,
            repute=Repute.BAD,
            gene="MTHFR",
        )
        repository.insert_snp(snp1)
        repository.insert_snp(snp2)
        result = repository.get_snps_by_gene("MTHFR")
        assert len(result) == 2

    def test_get_snps_by_gene_only_returns_matching_gene(self, repository, sample_test):
        """get_snps_by_gene only returns SNPs for the specified gene."""
        repository.insert_test(sample_test)
        snp1 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs1801133",
            genotype="CT",
            magnitude=3.5,
            repute=Repute.BAD,
            gene="MTHFR",
        )
        snp2 = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs4680",
            genotype="AA",
            magnitude=2.0,
            repute=Repute.BAD,
            gene="COMT",
        )
        repository.insert_snp(snp1)
        repository.insert_snp(snp2)
        result = repository.get_snps_by_gene("COMT")
        assert len(result) == 1
        assert result[0].rsid == "rs4680"


class TestEdgeCases:
    """Edge case tests."""

    def test_uuid_roundtrip(self, repository, sample_test):
        """UUIDs are correctly stored and retrieved."""
        repository.insert_test(sample_test)
        retrieved = repository.get_test_by_id(sample_test.id)
        assert isinstance(retrieved.id, UUID)
        assert retrieved.id == sample_test.id

    def test_date_roundtrip(self, repository):
        """Dates are correctly stored and retrieved."""
        test = DnaTest(
            id=uuid4(),
            source="Test",
            collected_date=date(2020, 12, 31),
            source_file="test.txt",
        )
        repository.insert_test(test)
        retrieved = repository.get_test_by_id(test.id)
        assert isinstance(retrieved.collected_date, date)
        assert retrieved.collected_date == date(2020, 12, 31)

    def test_datetime_roundtrip(self, repository):
        """Datetimes are correctly stored and retrieved."""
        test = DnaTest(
            id=uuid4(),
            source="Test",
            collected_date=date(2020, 12, 31),
            source_file="test.txt",
            created_at=datetime(2021, 1, 1, 12, 30, 45),
        )
        repository.insert_test(test)
        retrieved = repository.get_test_by_id(test.id)
        assert isinstance(retrieved.created_at, datetime)
        assert retrieved.created_at == datetime(2021, 1, 1, 12, 30, 45)

    def test_float_magnitude_roundtrip(self, repository, sample_test):
        """Float magnitudes are correctly stored and retrieved."""
        repository.insert_test(sample_test)
        snp = Snp(
            id=uuid4(),
            dna_test_id=sample_test.id,
            rsid="rs1234567",
            genotype="AG",
            magnitude=3.14159,
            repute=None,
            gene="TEST",
        )
        repository.insert_snp(snp)
        retrieved = repository.get_snp_by_rsid(snp.rsid)
        assert retrieved.magnitude == pytest.approx(3.14159)
