"""Tests for DnaRepository."""

from datetime import date
from uuid import uuid4

import pytest

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.dna import DnaTest, Repute, Snp
from src.databases.datatypes.dna.repository import DnaRepository


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
    """Create a DnaRepository instance."""
    return DnaRepository(db_session)


@pytest.fixture
def sample_test(db_session) -> DnaTest:
    """Create a sample DNA test with SNPs."""
    test = DnaTest(
        source="23andMe",
        collected_date=date(2024, 1, 15),
        source_file="test.json",
    )
    db_session.add(test)
    db_session.flush()

    snp = Snp(
        dna_test_id=test.id,
        rsid="rs1801133",
        genotype="CT",
        magnitude=3.0,
        repute=Repute.BAD,
        gene="MTHFR",
    )
    db_session.add(snp)
    db_session.commit()

    return test


class TestListTests:
    """Tests for list_tests method."""

    def test_returns_empty_list_when_no_tests(self, repo):
        """Should return empty list when no tests exist."""
        tests = repo.list_tests()
        assert tests == []

    def test_returns_all_tests(self, repo, sample_test):
        """Should return all DNA tests."""
        tests = repo.list_tests()
        assert len(tests) == 1
        assert tests[0].id == sample_test.id

    def test_orders_by_collected_date_descending(self, repo, db_session):
        """Should order tests by collected_date descending."""
        older = DnaTest(
            source="Ancestry",
            collected_date=date(2023, 1, 1),
            source_file="older.json",
        )
        db_session.add(older)

        newer = DnaTest(
            source="23andMe",
            collected_date=date(2024, 6, 15),
            source_file="newer.json",
        )
        db_session.add(newer)
        db_session.commit()

        tests = repo.list_tests()
        assert len(tests) == 2
        assert tests[0].collected_date == date(2024, 6, 15)
        assert tests[1].collected_date == date(2023, 1, 1)


class TestGetSnpByRsid:
    """Tests for get_snp_by_rsid method."""

    def test_returns_snp_when_found(self, repo, sample_test):
        """Should return SNP when found."""
        snp = repo.get_snp_by_rsid("rs1801133")
        assert snp is not None
        assert snp.rsid == "rs1801133"
        assert snp.gene == "MTHFR"

    def test_returns_none_when_not_found(self, repo):
        """Should return None when SNP not found."""
        snp = repo.get_snp_by_rsid("rs999999")
        assert snp is None


class TestGetSnpsForGene:
    """Tests for get_snps_for_gene method."""

    def test_returns_snps_for_gene(self, repo, sample_test):
        """Should return all SNPs for a gene."""
        snps = repo.get_snps_for_gene("MTHFR")
        assert len(snps) == 1
        assert snps[0].gene == "MTHFR"

    def test_orders_by_magnitude_descending(self, repo, db_session):
        """Should order SNPs by magnitude descending."""
        test = DnaTest(
            source="23andMe",
            collected_date=date(2024, 1, 15),
            source_file="test.json",
        )
        db_session.add(test)
        db_session.flush()

        low = Snp(
            dna_test_id=test.id,
            rsid="rs1",
            genotype="AA",
            magnitude=1.0,
            gene="COMT",
        )
        high = Snp(
            dna_test_id=test.id,
            rsid="rs2",
            genotype="GG",
            magnitude=4.0,
            gene="COMT",
        )
        db_session.add(low)
        db_session.add(high)
        db_session.commit()

        snps = repo.get_snps_for_gene("COMT")
        assert len(snps) == 2
        assert snps[0].magnitude == 4.0
        assert snps[1].magnitude == 1.0

    def test_returns_empty_when_gene_not_found(self, repo):
        """Should return empty list when no SNPs for gene."""
        snps = repo.get_snps_for_gene("NONEXISTENT")
        assert snps == []


class TestGetHighImpactSnps:
    """Tests for get_high_impact_snps method."""

    def test_returns_snps_with_magnitude_gte_3(self, repo, sample_test):
        """Should return SNPs with magnitude >= 3."""
        snps = repo.get_high_impact_snps()
        assert len(snps) == 1
        assert snps[0].magnitude >= 3.0

    def test_excludes_low_magnitude_snps(self, repo, db_session):
        """Should exclude SNPs with magnitude < 3."""
        test = DnaTest(
            source="23andMe",
            collected_date=date(2024, 1, 15),
            source_file="test.json",
        )
        db_session.add(test)
        db_session.flush()

        low = Snp(
            dna_test_id=test.id,
            rsid="rs1",
            genotype="AA",
            magnitude=1.0,
            gene="COMT",
        )
        db_session.add(low)
        db_session.commit()

        snps = repo.get_high_impact_snps()
        assert len(snps) == 0

    def test_orders_by_magnitude_descending(self, repo, db_session):
        """Should order by magnitude descending."""
        test = DnaTest(
            source="23andMe",
            collected_date=date(2024, 1, 15),
            source_file="test.json",
        )
        db_session.add(test)
        db_session.flush()

        medium = Snp(
            dna_test_id=test.id,
            rsid="rs1",
            genotype="AA",
            magnitude=3.0,
            gene="COMT",
        )
        high = Snp(
            dna_test_id=test.id,
            rsid="rs2",
            genotype="GG",
            magnitude=5.0,
            gene="MTHFR",
        )
        db_session.add(medium)
        db_session.add(high)
        db_session.commit()

        snps = repo.get_high_impact_snps()
        assert len(snps) == 2
        assert snps[0].magnitude == 5.0
        assert snps[1].magnitude == 3.0


class TestSaveTest:
    """Tests for save_test method."""

    def test_saves_test_and_snps(self, repo):
        """Should save DNA test and its SNPs atomically."""
        test = DnaTest(
            source="23andMe",
            collected_date=date(2024, 1, 15),
            source_file="test.json",
        )
        snp = Snp(
            dna_test_id=test.id,
            rsid="rs1801133",
            genotype="CT",
            magnitude=3.0,
            gene="MTHFR",
        )

        repo.save_test(test, [snp])

        saved_tests = repo.list_tests()
        assert len(saved_tests) == 1

        saved_snp = repo.get_snp_by_rsid("rs1801133")
        assert saved_snp is not None
