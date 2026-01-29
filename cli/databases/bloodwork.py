#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""CLI for querying bloodwork data."""

import argcomplete
import argparse
import json
import sys
from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import ValidationError

from sqlmodel import Session, select

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.bloodwork import Biomarker, Flag, LabReport, Panel


def format_report(report: LabReport) -> str:
    """Format a lab report for display."""
    source = report.source_file if report.source_file else "-"
    return f"{report.id}\t{report.lab_provider}\t{report.collected_date}\t{source}"


def format_biomarker(biomarker: Biomarker, collected_date: Optional[str] = None) -> str:
    """Format a biomarker for display."""
    ref_low = f"{biomarker.reference_low:.1f}" if biomarker.reference_low is not None else "-"
    ref_high = f"{biomarker.reference_high:.1f}" if biomarker.reference_high is not None else "-"
    ref_range = f"{ref_low}-{ref_high}"
    date_str = collected_date if collected_date else "-"
    return f"{biomarker.name}\t{biomarker.value:.2f}\t{biomarker.unit}\t{biomarker.flag.value}\t{ref_range}\t{date_str}"


def report_to_dict(report: LabReport) -> dict:
    """Convert a lab report to a JSON-serializable dict."""
    return {
        "id": str(report.id),
        "lab_provider": report.lab_provider,
        "collected_date": report.collected_date.isoformat(),
        "source_file": report.source_file,
        "created_at": report.created_at.isoformat(),
    }


def panel_to_dict(panel: Panel) -> dict:
    """Convert a panel to a JSON-serializable dict."""
    return {
        "id": str(panel.id),
        "lab_report_id": str(panel.lab_report_id),
        "name": panel.name,
        "comment": panel.comment,
    }


def biomarker_to_dict(biomarker: Biomarker) -> dict:
    """Convert a biomarker to a JSON-serializable dict."""
    return {
        "id": str(biomarker.id),
        "panel_id": str(biomarker.panel_id),
        "name": biomarker.name,
        "code": biomarker.code,
        "value": biomarker.value,
        "unit": biomarker.unit,
        "reference_low": biomarker.reference_low,
        "reference_high": biomarker.reference_high,
        "flag": biomarker.flag.value,
    }


def parse_bloodwork_json(
    data: dict, source_file: str | None
) -> tuple[LabReport, list[Panel], list[Biomarker]]:
    """Parse JSON into database models.

    All model construction happens here, triggering Pydantic validation.
    If any validation fails, no database operations have occurred yet.

    Args:
        data: JSON dict with bloodwork data.
        source_file: Optional source file path.

    Returns:
        Tuple of (LabReport, list of Panel, list of Biomarker).

    Raises:
        ValidationError: If model validation fails.
        KeyError: If required fields are missing.
        ValueError: If date parsing fails.
    """
    # Create LabReport
    lab_report = LabReport(
        lab_provider=data["lab_provider"],
        collected_date=date.fromisoformat(data["collected_date"]),
        source_file=source_file,
    )

    panels: list[Panel] = []
    biomarkers: list[Biomarker] = []

    for panel_data in data.get("panels", []):
        panel = Panel(
            lab_report_id=lab_report.id,
            name=panel_data["name"],
            comment=panel_data.get("comment"),
        )
        panels.append(panel)

        for biomarker_data in panel_data.get("biomarkers", []):
            # Use model_validate to ensure Pydantic validation runs
            biomarker = Biomarker.model_validate({
                "panel_id": panel.id,
                "name": biomarker_data["name"],
                "code": biomarker_data["code"],
                "value": biomarker_data["value"],
                "unit": biomarker_data["unit"],
                "reference_low": biomarker_data.get("reference_low"),
                "reference_high": biomarker_data.get("reference_high"),
                "flag": biomarker_data.get("flag", "normal"),
            })
            biomarkers.append(biomarker)

    return lab_report, panels, biomarkers


def cmd_import(session: Session, args: argparse.Namespace) -> None:
    """Import bloodwork from JSON file.

    Transaction handling:
    1. Parse JSON and construct all models (validation happens here)
    2. If validation passes, add all to session
    3. Commit as single atomic transaction
    4. If anything fails, nothing is committed (no dangling records)
    """
    # Read JSON from file or stdin
    if args.file:
        try:
            with open(args.file) as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in file: {e}", file=sys.stderr)
            sys.exit(1)
        source_file = args.file
    else:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)
        source_file = None

    # Step 1: Parse and validate ALL data before any DB operations
    try:
        lab_report, panels, biomarkers = parse_bloodwork_json(data, source_file)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Add all to session with flush() to ensure FK order
    session.add(lab_report)
    session.flush()  # Ensure lab_report exists before panels

    for panel in panels:
        session.add(panel)
    session.flush()  # Ensure panels exist before biomarkers

    for biomarker in biomarkers:
        session.add(biomarker)

    # Step 3: Single atomic commit - all or nothing
    session.commit()

    # Output
    if args.json:
        print(json.dumps({
            "lab_report_id": str(lab_report.id),
            "panels_created": len(panels),
            "biomarkers_created": len(biomarkers),
        }, indent=2))
    else:
        print(f"Imported lab report: {lab_report.id}")
        print(f"  Panels: {len(panels)}")
        print(f"  Biomarkers: {len(biomarkers)}")


def cmd_list(session: Session, args: argparse.Namespace) -> None:
    """List all lab reports."""
    statement = select(LabReport).order_by(LabReport.collected_date.desc())
    reports = session.exec(statement).all()
    if args.json:
        print(json.dumps([report_to_dict(r) for r in reports], indent=2))
    else:
        if not reports:
            print("No lab reports found.")
            return
        print("ID\tProvider\tCollected\tFile")
        print("-" * 80)
        for report in reports:
            print(format_report(report))


def cmd_report(session: Session, args: argparse.Namespace) -> None:
    """Show details for a single lab report."""
    try:
        report_id = UUID(args.id)
    except ValueError:
        print(f"Invalid report ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    report = session.get(LabReport, report_id)
    if report is None:
        print(f"Report not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    panels = session.exec(select(Panel).where(Panel.lab_report_id == report_id)).all()

    if args.json:
        report_dict = report_to_dict(report)
        report_dict["panels"] = []
        for panel in panels:
            panel_dict = panel_to_dict(panel)
            biomarkers = session.exec(select(Biomarker).where(Biomarker.panel_id == panel.id)).all()
            panel_dict["biomarkers"] = [biomarker_to_dict(b) for b in biomarkers]
            report_dict["panels"].append(panel_dict)
        print(json.dumps(report_dict, indent=2))
    else:
        print(f"Report: {report.id}")
        print(f"Provider: {report.lab_provider}")
        print(f"Collected: {report.collected_date}")
        print(f"Source: {report.source_file if report.source_file else '-'}")
        print()
        for panel in panels:
            print(f"Panel: {panel.name}")
            if panel.comment:
                print(f"Comment: {panel.comment}")
            print("Name\tValue\tUnit\tFlag\tRange\tDate")
            print("-" * 80)
            biomarkers = session.exec(select(Biomarker).where(Biomarker.panel_id == panel.id)).all()
            for biomarker in biomarkers:
                print(format_biomarker(biomarker, str(report.collected_date)))
            print()


def cmd_biomarker(session: Session, args: argparse.Namespace) -> None:
    """Show biomarker history for a code."""
    limit = args.limit if args.limit else 4
    # Join through panels and lab_reports to order by collected_date
    statement = (
        select(Biomarker)
        .join(Panel, Biomarker.panel_id == Panel.id)
        .join(LabReport, Panel.lab_report_id == LabReport.id)
        .where(Biomarker.code == args.code)
        .order_by(LabReport.collected_date.desc())
        .limit(limit)
    )
    biomarkers = session.exec(statement).all()

    if args.json:
        print(json.dumps([biomarker_to_dict(b) for b in biomarkers], indent=2))
    else:
        if not biomarkers:
            print(f"No biomarker found with code: {args.code}")
            return
        print(f"History for {args.code}:")
        print("Name\tValue\tUnit\tFlag\tRange\tDate")
        print("-" * 80)
        for biomarker in biomarkers:
            print(format_biomarker(biomarker))


def cmd_flagged(session: Session, args: argparse.Namespace) -> None:
    """Show biomarkers with abnormal flags."""
    statement = select(Biomarker).where(Biomarker.flag != Flag.NORMAL)
    biomarkers = session.exec(statement).all()

    if args.json:
        print(json.dumps([biomarker_to_dict(b) for b in biomarkers], indent=2))
    else:
        if not biomarkers:
            print("No flagged biomarkers found.")
            return
        print("Abnormal Results:")
        print("Name\tValue\tUnit\tFlag\tRange\tDate")
        print("-" * 80)
        for biomarker in biomarkers:
            print(format_biomarker(biomarker))


def cmd_recent(session: Session, args: argparse.Namespace) -> None:
    """Show most recent value for each biomarker."""
    # Get all unique biomarker codes, then get the most recent for each
    # This is a simplified approach - get all biomarkers ordered by date
    statement = (
        select(Biomarker)
        .join(Panel, Biomarker.panel_id == Panel.id)
        .join(LabReport, Panel.lab_report_id == LabReport.id)
        .order_by(LabReport.collected_date.desc())
    )
    all_biomarkers = session.exec(statement).all()

    # Keep only the most recent for each code
    seen_codes: set[str] = set()
    biomarkers: list[Biomarker] = []
    for b in all_biomarkers:
        if b.code not in seen_codes:
            seen_codes.add(b.code)
            biomarkers.append(b)

    # Sort by code for consistent output
    biomarkers.sort(key=lambda b: b.code)

    if args.json:
        print(json.dumps([biomarker_to_dict(b) for b in biomarkers], indent=2))
    else:
        if not biomarkers:
            print("No biomarkers found.")
            return
        print("Recent Values:")
        print("Name\tValue\tUnit\tFlag\tRange\tDate")
        print("-" * 80)
        for biomarker in biomarkers:
            print(format_biomarker(biomarker))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for bloodwork CLI."""
    parser = argparse.ArgumentParser(
        prog="bloodwork",
        description="Query bloodwork data from the command line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of formatted text",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # import command
    import_parser = subparsers.add_parser("import", help="Import bloodwork from JSON file")
    import_parser.add_argument(
        "--file", "-f",
        help="JSON file to read (default: stdin)",
    )

    # list command
    subparsers.add_parser("list", help="List all lab reports")

    # report command
    report_parser = subparsers.add_parser("report", help="Show details for a single report")
    report_parser.add_argument("id", help="Report ID (UUID)")

    # biomarker command
    biomarker_parser = subparsers.add_parser("biomarker", help="Show history for a biomarker code")
    biomarker_parser.add_argument("code", help="Biomarker code (e.g., GLUCOSE, HBA1C)")
    biomarker_parser.add_argument(
        "--limit", "-n", type=int, default=4, help="Number of historical values (default: 4)"
    )

    # flagged command
    subparsers.add_parser("flagged", help="Show abnormal biomarker results")

    # recent command
    subparsers.add_parser("recent", help="Show latest value for each biomarker")

    return parser


def main(args: Optional[list[str]] = None) -> None:
    """Main entry point for bloodwork CLI."""
    parser = create_parser()
    argcomplete.autocomplete(parser)
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        with client.get_session() as session:
            if parsed_args.command == "import":
                cmd_import(session, parsed_args)
            elif parsed_args.command == "list":
                cmd_list(session, parsed_args)
            elif parsed_args.command == "report":
                cmd_report(session, parsed_args)
            elif parsed_args.command == "biomarker":
                cmd_biomarker(session, parsed_args)
            elif parsed_args.command == "flagged":
                cmd_flagged(session, parsed_args)
            elif parsed_args.command == "recent":
                cmd_recent(session, parsed_args)


if __name__ == "__main__":
    main()
