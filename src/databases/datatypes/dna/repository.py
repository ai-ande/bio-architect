"""Repository for DNA data access."""

from sqlmodel import select

from ..base import BaseRepository
from .models import DnaTest, Snp


class DnaRepository(BaseRepository):
    """Repository for DNA database operations."""

    def list_tests(self) -> list[DnaTest]:
        """List all DNA tests ordered by collected_date descending."""
        statement = select(DnaTest).order_by(DnaTest.collected_date.desc())
        return list(self.session.exec(statement).all())

    def get_snp_by_rsid(self, rsid: str) -> Snp | None:
        """Get a SNP by its rsid."""
        statement = select(Snp).where(Snp.rsid == rsid)
        return self.session.exec(statement).first()

    def get_snps_for_gene(self, gene: str) -> list[Snp]:
        """Get all SNPs for a gene, ordered by magnitude descending."""
        statement = select(Snp).where(Snp.gene == gene).order_by(Snp.magnitude.desc())
        return list(self.session.exec(statement).all())

    def get_high_impact_snps(self) -> list[Snp]:
        """Get SNPs with magnitude >= 3, ordered by magnitude descending."""
        statement = select(Snp).where(Snp.magnitude >= 3.0).order_by(Snp.magnitude.desc())
        return list(self.session.exec(statement).all())

    def save_test(self, dna_test: DnaTest, snps: list[Snp]) -> bool:
        """Save a DNA test with its SNPs atomically.

        Returns:
            True if newly created, False if already imported.
        """
        if self.get_existing_by_source_file(DnaTest, dna_test.source_file):
            return False

        self.session.add(dna_test)
        self.session.flush()

        for snp in snps:
            self.session.add(snp)

        self.session.commit()
        return True
