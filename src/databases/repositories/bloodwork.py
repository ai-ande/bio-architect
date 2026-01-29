"""Repository for bloodwork data access."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.bloodwork import Biomarker, Flag, LabReport, Panel


class BloodworkRepository:
    """Repository for bloodwork lab report, panel, and biomarker data access."""

    def __init__(self, client: DatabaseClient):
        """Initialize repository with database client.

        Args:
            client: DatabaseClient instance for database operations.
        """
        self._client = client

    def insert_report(self, report: LabReport) -> LabReport:
        """Insert a lab report record.

        Args:
            report: LabReport model to insert.

        Returns:
            The inserted LabReport model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO lab_reports (id, lab_provider, collected_date, source_file, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(report.id),
                report.lab_provider,
                report.collected_date.isoformat(),
                report.source_file,
                report.created_at.isoformat(),
            ),
        )
        conn.commit()
        return report

    def insert_panel(self, panel: Panel) -> Panel:
        """Insert a panel record.

        Args:
            panel: Panel model to insert.

        Returns:
            The inserted Panel model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO panels (id, lab_report_id, name, comment)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(panel.id),
                str(panel.lab_report_id),
                panel.name,
                panel.comment,
            ),
        )
        conn.commit()
        return panel

    def insert_biomarker(self, biomarker: Biomarker) -> Biomarker:
        """Insert a biomarker record.

        Args:
            biomarker: Biomarker model to insert.

        Returns:
            The inserted Biomarker model.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO biomarkers (id, panel_id, name, code, value, unit, reference_low, reference_high, flag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(biomarker.id),
                str(biomarker.panel_id),
                biomarker.name,
                biomarker.code,
                biomarker.value,
                biomarker.unit,
                biomarker.reference_low,
                biomarker.reference_high,
                biomarker.flag.value,
            ),
        )
        conn.commit()
        return biomarker

    def get_report_by_id(self, report_id: UUID) -> Optional[LabReport]:
        """Get a lab report by ID.

        Args:
            report_id: UUID of the lab report.

        Returns:
            LabReport model if found, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, lab_provider, collected_date, source_file, created_at
            FROM lab_reports
            WHERE id = ?
            """,
            (str(report_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_report(row)

    def get_biomarker_by_code(self, code: str) -> Optional[Biomarker]:
        """Get the most recent biomarker for a given code.

        Args:
            code: Biomarker code (e.g., 'GLUCOSE', 'HBA1C').

        Returns:
            Most recent Biomarker model if found, None otherwise.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.id, b.panel_id, b.name, b.code, b.value, b.unit,
                   b.reference_low, b.reference_high, b.flag
            FROM biomarkers b
            JOIN panels p ON b.panel_id = p.id
            JOIN lab_reports r ON p.lab_report_id = r.id
            WHERE b.code = ?
            ORDER BY r.collected_date DESC
            LIMIT 1
            """,
            (code,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_biomarker(row)

    def get_biomarker_history(self, code: str, limit: int = 4) -> list[Biomarker]:
        """Get historical biomarker values for a given code.

        Args:
            code: Biomarker code (e.g., 'GLUCOSE', 'HBA1C').
            limit: Maximum number of results to return (default 4).

        Returns:
            List of Biomarker models ordered by collected date descending.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.id, b.panel_id, b.name, b.code, b.value, b.unit,
                   b.reference_low, b.reference_high, b.flag
            FROM biomarkers b
            JOIN panels p ON b.panel_id = p.id
            JOIN lab_reports r ON p.lab_report_id = r.id
            WHERE b.code = ?
            ORDER BY r.collected_date DESC
            LIMIT ?
            """,
            (code, limit),
        )
        rows = cursor.fetchall()
        return [self._row_to_biomarker(row) for row in rows]

    def get_flagged_biomarkers(self) -> list[Biomarker]:
        """Get all biomarkers with non-normal flags.

        Returns:
            List of Biomarker models with HIGH, LOW, CRITICAL_HIGH, CRITICAL_LOW, or PENDING flags.
        """
        conn = self._client.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, panel_id, name, code, value, unit, reference_low, reference_high, flag
            FROM biomarkers
            WHERE flag != ?
            """,
            (Flag.NORMAL.value,),
        )
        rows = cursor.fetchall()
        return [self._row_to_biomarker(row) for row in rows]

    def _row_to_report(self, row) -> LabReport:
        """Convert a database row to a LabReport model.

        Args:
            row: SQLite Row object.

        Returns:
            LabReport model.
        """
        return LabReport(
            id=UUID(row["id"]),
            lab_provider=row["lab_provider"],
            collected_date=date.fromisoformat(row["collected_date"]),
            source_file=row["source_file"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_biomarker(self, row) -> Biomarker:
        """Convert a database row to a Biomarker model.

        Args:
            row: SQLite Row object.

        Returns:
            Biomarker model.
        """
        return Biomarker(
            id=UUID(row["id"]),
            panel_id=UUID(row["panel_id"]),
            name=row["name"],
            code=row["code"],
            value=row["value"],
            unit=row["unit"],
            reference_low=row["reference_low"],
            reference_high=row["reference_high"],
            flag=Flag(row["flag"]),
        )
