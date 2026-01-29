"""Repository for bloodwork data access."""

from uuid import UUID

from sqlmodel import Session, select

from .models import Biomarker, Flag, LabReport, Panel


class BloodworkRepository:
    """Repository for bloodwork database operations."""

    def __init__(self, session: Session):
        self.session = session

    def list_reports(self) -> list[LabReport]:
        """List all lab reports ordered by collected_date descending."""
        statement = select(LabReport).order_by(LabReport.collected_date.desc())
        return list(self.session.exec(statement).all())

    def get_report(self, report_id: UUID) -> LabReport | None:
        """Get a lab report by ID."""
        return self.session.get(LabReport, report_id)

    def get_panels_for_report(self, report_id: UUID) -> list[Panel]:
        """Get all panels for a lab report."""
        statement = select(Panel).where(Panel.lab_report_id == report_id)
        return list(self.session.exec(statement).all())

    def get_biomarkers_for_panel(self, panel_id: UUID) -> list[Biomarker]:
        """Get all biomarkers for a panel."""
        statement = select(Biomarker).where(Biomarker.panel_id == panel_id)
        return list(self.session.exec(statement).all())

    def get_biomarker_history(self, code: str, limit: int = 4) -> list[Biomarker]:
        """Get biomarker history for a code, ordered by date descending."""
        statement = (
            select(Biomarker)
            .join(Panel, Biomarker.panel_id == Panel.id)
            .join(LabReport, Panel.lab_report_id == LabReport.id)
            .where(Biomarker.code == code)
            .order_by(LabReport.collected_date.desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def get_flagged_biomarkers(self) -> list[Biomarker]:
        """Get all biomarkers with non-normal flags."""
        statement = select(Biomarker).where(Biomarker.flag != Flag.NORMAL)
        return list(self.session.exec(statement).all())

    def get_recent_biomarkers(self) -> list[Biomarker]:
        """Get the most recent value for each biomarker code."""
        # Get all biomarkers ordered by date descending
        statement = (
            select(Biomarker)
            .join(Panel, Biomarker.panel_id == Panel.id)
            .join(LabReport, Panel.lab_report_id == LabReport.id)
            .order_by(LabReport.collected_date.desc())
        )
        all_biomarkers = self.session.exec(statement).all()

        # Keep only the most recent for each code
        seen_codes: set[str] = set()
        biomarkers: list[Biomarker] = []
        for b in all_biomarkers:
            if b.code not in seen_codes:
                seen_codes.add(b.code)
                biomarkers.append(b)

        # Sort by code for consistent output
        biomarkers.sort(key=lambda b: b.code)
        return biomarkers

    def save_report(
        self,
        report: LabReport,
        panels: list[Panel],
        biomarkers: list[Biomarker],
    ) -> None:
        """Save a lab report with its panels and biomarkers atomically."""
        self.session.add(report)
        self.session.flush()  # Ensure report exists before panels

        for panel in panels:
            self.session.add(panel)
        self.session.flush()  # Ensure panels exist before biomarkers

        for biomarker in biomarkers:
            self.session.add(biomarker)

        self.session.commit()
