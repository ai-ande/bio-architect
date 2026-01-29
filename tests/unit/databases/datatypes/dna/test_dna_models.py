"""Tests for DNA models."""

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.databases.datatypes.dna import (
    DnaTest,
    Repute,
    Snp,
)


class TestRepute:
    """Tests for Repute enum."""

    def test_repute_values(self):
        assert Repute.GOOD.value == "good"
        assert Repute.BAD.value == "bad"

    def test_repute_is_string_enum(self):
        assert isinstance(Repute.GOOD, str)
        assert Repute.GOOD == "good"


class TestSnp:
    """Tests for Snp model."""

    def test_create_minimal_snp(self):
        dna_test_id = uuid4()
        snp = Snp(
            dna_test_id=dna_test_id,
            rsid="rs1801133",
            genotype="CT",
            magnitude=3.5,
            gene="MTHFR",
        )
        assert snp.rsid == "rs1801133"
        assert snp.genotype == "CT"
        assert snp.magnitude == 3.5
        assert snp.gene == "MTHFR"
        assert snp.dna_test_id == dna_test_id

    def test_snp_has_uuid(self):
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs1801133",
            genotype="CT",
            magnitude=3.5,
            gene="MTHFR",
        )
        assert isinstance(snp.id, UUID)

    def test_snp_uuid_is_unique(self):
        dna_test_id = uuid4()
        s1 = Snp(
            dna_test_id=dna_test_id,
            rsid="rs1801133",
            genotype="CT",
            magnitude=3.5,
            gene="MTHFR",
        )
        s2 = Snp(
            dna_test_id=dna_test_id,
            rsid="rs1801133",
            genotype="CT",
            magnitude=3.5,
            gene="MTHFR",
        )
        assert s1.id != s2.id

    def test_snp_with_good_repute(self):
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs4680",
            genotype="GG",
            magnitude=2.5,
            repute=Repute.GOOD,
            gene="COMT",
        )
        assert snp.repute == Repute.GOOD
        assert snp.repute == "good"

    def test_snp_with_bad_repute(self):
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs1801133",
            genotype="TT",
            magnitude=4.0,
            repute=Repute.BAD,
            gene="MTHFR",
        )
        assert snp.repute == Repute.BAD
        assert snp.repute == "bad"

    def test_snp_with_null_repute(self):
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs1234",
            genotype="AA",
            magnitude=1.0,
            repute=None,
            gene="TEST",
        )
        assert snp.repute is None

    def test_snp_repute_defaults_to_none(self):
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs1234",
            genotype="AA",
            magnitude=1.0,
            gene="TEST",
        )
        assert snp.repute is None

    def test_snp_repute_accepts_string_value(self):
        """Repute should accept string values that match enum."""
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs1234",
            genotype="AA",
            magnitude=1.0,
            repute="good",
            gene="TEST",
        )
        assert snp.repute == Repute.GOOD

    def test_snp_magnitude_zero(self):
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs1234",
            genotype="AA",
            magnitude=0.0,
            gene="TEST",
        )
        assert snp.magnitude == 0.0

    def test_snp_magnitude_ten(self):
        snp = Snp(
            dna_test_id=uuid4(),
            rsid="rs1234",
            genotype="AA",
            magnitude=10.0,
            gene="TEST",
        )
        assert snp.magnitude == 10.0

    def test_snp_magnitude_below_zero_raises(self):
        with pytest.raises(ValidationError, match="magnitude must be between 0 and 10"):
            Snp.model_validate({
                "dna_test_id": uuid4(),
                "rsid": "rs1234",
                "genotype": "AA",
                "magnitude": -0.1,
                "gene": "TEST",
            })

    def test_snp_magnitude_above_ten_raises(self):
        with pytest.raises(ValidationError, match="magnitude must be between 0 and 10"):
            Snp.model_validate({
                "dna_test_id": uuid4(),
                "rsid": "rs1234",
                "genotype": "AA",
                "magnitude": 10.1,
                "gene": "TEST",
            })

    def test_snp_requires_dna_test_id(self):
        with pytest.raises(ValidationError):
            Snp.model_validate({
                "rsid": "rs1234",
                "genotype": "AA",
                "magnitude": 1.0,
                "gene": "TEST",
            })  # missing dna_test_id

    def test_snp_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            Snp.model_validate({
                "dna_test_id": uuid4(),
                "rsid": "rs1234",
                "genotype": "AA",
                "magnitude": 1.0,
            })  # missing gene


class TestDnaTest:
    """Tests for DnaTest model."""

    def test_create_minimal_dna_test(self):
        test = DnaTest(
            source="23andMe",
            collected_date=date(2023, 6, 15),
            source_file="promethease_export.txt",
        )
        assert test.source == "23andMe"
        assert test.collected_date == date(2023, 6, 15)
        assert test.source_file == "promethease_export.txt"

    def test_dna_test_has_uuid(self):
        test = DnaTest(
            source="23andMe",
            collected_date=date(2023, 6, 15),
            source_file="promethease_export.txt",
        )
        assert isinstance(test.id, UUID)

    def test_dna_test_uuid_is_unique(self):
        t1 = DnaTest(
            source="23andMe",
            collected_date=date(2023, 6, 15),
            source_file="promethease_export.txt",
        )
        t2 = DnaTest(
            source="23andMe",
            collected_date=date(2023, 6, 15),
            source_file="promethease_export.txt",
        )
        assert t1.id != t2.id

    def test_dna_test_has_created_at_with_default(self):
        before = datetime.now()
        test = DnaTest(
            source="23andMe",
            collected_date=date(2023, 6, 15),
            source_file="promethease_export.txt",
        )
        after = datetime.now()
        assert isinstance(test.created_at, datetime)
        assert before <= test.created_at <= after

    def test_dna_test_with_ancestry_source(self):
        test = DnaTest(
            source="AncestryDNA",
            collected_date=date(2022, 3, 10),
            source_file="ancestry_raw.txt",
        )
        assert test.source == "AncestryDNA"

    def test_dna_test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            DnaTest.model_validate({
                "source": "23andMe",
                "collected_date": date(2023, 6, 15),
            })  # missing source_file

    def test_dna_test_missing_collected_date_raises(self):
        with pytest.raises(ValidationError):
            DnaTest.model_validate({
                "source": "23andMe",
                "source_file": "promethease_export.txt",
            })  # missing collected_date

    def test_dna_test_missing_source_raises(self):
        with pytest.raises(ValidationError):
            DnaTest.model_validate({
                "collected_date": date(2023, 6, 15),
                "source_file": "promethease_export.txt",
            })  # missing source

    def test_dna_test_is_flat_no_snps_list(self):
        """Verify DnaTest does not have nested SNPs list."""
        test = DnaTest(
            source="23andMe",
            collected_date=date(2023, 6, 15),
            source_file="promethease_export.txt",
        )
        assert not hasattr(test, "snps")
