"""Repository for DNA data access."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.dna import DnaTest, Repute, Snp


class DnaRepository:
    """Repository for DNA test and SNP data access."""

    def __init__(self, client: DatabaseClient):
        """Initialize repository with database client.

        Args:
            client: DatabaseClient instance for database operations.
        """
        self._client = client

    def insert_test(self, test: DnaTest) -> DnaTest:
        """Insert a DNA test record.

        Args:
            test: DnaTest model to insert.

        Returns:
            The inserted DnaTest model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dna_tests (id, source, collected_date, source_file, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(test.id),
                test.source,
                test.collected_date.isoformat(),
                test.source_file,
                test.created_at.isoformat(),
            ),
        )
        conn.commit()
        return test

    def insert_snp(self, snp: Snp) -> Snp:
        """Insert a SNP record.

        Args:
            snp: Snp model to insert.

        Returns:
            The inserted Snp model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO snps (id, dna_test_id, rsid, genotype, magnitude, repute, gene)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(snp.id),
                str(snp.dna_test_id),
                snp.rsid,
                snp.genotype,
                snp.magnitude,
                snp.repute.value if snp.repute else None,
                snp.gene,
            ),
        )
        conn.commit()
        return snp

    def get_test_by_id(self, test_id: UUID) -> Optional[DnaTest]:
        """Get a DNA test by ID.

        Args:
            test_id: UUID of the DNA test.

        Returns:
            DnaTest model if found, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, source, collected_date, source_file, created_at
            FROM dna_tests
            WHERE id = ?
            """,
            (str(test_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return DnaTest(
            id=UUID(row["id"]),
            source=row["source"],
            collected_date=date.fromisoformat(row["collected_date"]),
            source_file=row["source_file"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_snps_by_test(self, test_id: UUID) -> list[Snp]:
        """Get all SNPs for a DNA test.

        Args:
            test_id: UUID of the DNA test.

        Returns:
            List of Snp models for the test.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, dna_test_id, rsid, genotype, magnitude, repute, gene
            FROM snps
            WHERE dna_test_id = ?
            """,
            (str(test_id),),
        )
        rows = cursor.fetchall()
        return [self._row_to_snp(row) for row in rows]

    def get_snp_by_rsid(self, rsid: str) -> Optional[Snp]:
        """Get a SNP by rsid.

        Args:
            rsid: Reference SNP ID (e.g., 'rs1234').

        Returns:
            Snp model if found, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, dna_test_id, rsid, genotype, magnitude, repute, gene
            FROM snps
            WHERE rsid = ?
            """,
            (rsid,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_snp(row)

    def get_snps_by_gene(self, gene: str) -> list[Snp]:
        """Get all SNPs for a gene.

        Args:
            gene: Gene name (e.g., 'MTHFR').

        Returns:
            List of Snp models for the gene.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, dna_test_id, rsid, genotype, magnitude, repute, gene
            FROM snps
            WHERE gene = ?
            """,
            (gene,),
        )
        rows = cursor.fetchall()
        return [self._row_to_snp(row) for row in rows]

    def _row_to_snp(self, row) -> Snp:
        """Convert a database row to a Snp model.

        Args:
            row: SQLite Row object.

        Returns:
            Snp model.
        """
        repute = None
        if row["repute"]:
            repute = Repute(row["repute"])
        return Snp(
            id=UUID(row["id"]),
            dna_test_id=UUID(row["dna_test_id"]),
            rsid=row["rsid"],
            genotype=row["genotype"],
            magnitude=row["magnitude"],
            repute=repute,
            gene=row["gene"],
        )
