#!/usr/bin/env python
"""CLI for querying bloodwork data."""

import argparse
import json
import sys
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.bloodwork import Biomarker, LabReport, Panel
from src.databases.repositories.bloodwork import BloodworkRepository


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


def cmd_list(repo: BloodworkRepository, args: argparse.Namespace) -> None:
    """List all lab reports."""
    reports = repo.get_all_reports()
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


def cmd_report(repo: BloodworkRepository, args: argparse.Namespace) -> None:
    """Show details for a single lab report."""
    try:
        report_id = UUID(args.id)
    except ValueError:
        print(f"Invalid report ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    report = repo.get_report_by_id(report_id)
    if report is None:
        print(f"Report not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    panels = repo.get_panels_by_report(report_id)

    if args.json:
        report_dict = report_to_dict(report)
        report_dict["panels"] = []
        for panel in panels:
            panel_dict = panel_to_dict(panel)
            biomarkers = repo.get_biomarkers_by_panel(panel.id)
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
            biomarkers = repo.get_biomarkers_by_panel(panel.id)
            for biomarker in biomarkers:
                print(format_biomarker(biomarker, str(report.collected_date)))
            print()


def cmd_biomarker(repo: BloodworkRepository, args: argparse.Namespace) -> None:
    """Show biomarker history for a code."""
    limit = args.limit if args.limit else 4
    biomarkers = repo.get_biomarker_history(args.code, limit=limit)

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
            # Get the date from the panel's report
            # We need to join through panels to get collected_date
            # For simplicity, we'll show "-" as date since we don't have it directly
            print(format_biomarker(biomarker))


def cmd_flagged(repo: BloodworkRepository, args: argparse.Namespace) -> None:
    """Show biomarkers with abnormal flags."""
    biomarkers = repo.get_flagged_biomarkers()

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


def cmd_recent(repo: BloodworkRepository, args: argparse.Namespace) -> None:
    """Show most recent value for each biomarker."""
    biomarkers = repo.get_recent_biomarkers()

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
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        repo = BloodworkRepository(client)

        if parsed_args.command == "list":
            cmd_list(repo, parsed_args)
        elif parsed_args.command == "report":
            cmd_report(repo, parsed_args)
        elif parsed_args.command == "biomarker":
            cmd_biomarker(repo, parsed_args)
        elif parsed_args.command == "flagged":
            cmd_flagged(repo, parsed_args)
        elif parsed_args.command == "recent":
            cmd_recent(repo, parsed_args)


if __name__ == "__main__":
    main()
