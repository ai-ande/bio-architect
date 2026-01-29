#!/usr/bin/env python
"""CLI for querying supplement protocol data."""

import argparse
import json
import sys
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.supplement_protocol import (
    ProtocolSupplement,
    SupplementProtocol,
)
from src.databases.repositories.protocol import ProtocolRepository


def format_protocol(protocol: SupplementProtocol) -> str:
    """Format a protocol for display."""
    prescriber = protocol.prescriber if protocol.prescriber else "-"
    return f"{protocol.id}\t{protocol.protocol_date}\t{prescriber}"


def format_supplement(supplement: ProtocolSupplement) -> str:
    """Format a protocol supplement for display."""
    schedule = format_schedule(supplement)
    dosage = supplement.dosage if supplement.dosage else "-"
    instructions = supplement.instructions if supplement.instructions else "-"
    return f"{supplement.name}\t{supplement.frequency.value}\t{dosage}\t{schedule}\t{instructions}"


def format_schedule(supplement: ProtocolSupplement) -> str:
    """Format the daily schedule for a supplement."""
    parts = []
    if supplement.upon_waking:
        parts.append(f"wake:{supplement.upon_waking}")
    if supplement.breakfast:
        parts.append(f"bfast:{supplement.breakfast}")
    if supplement.mid_morning:
        parts.append(f"mid-am:{supplement.mid_morning}")
    if supplement.lunch:
        parts.append(f"lunch:{supplement.lunch}")
    if supplement.mid_afternoon:
        parts.append(f"mid-pm:{supplement.mid_afternoon}")
    if supplement.dinner:
        parts.append(f"dinner:{supplement.dinner}")
    if supplement.before_sleep:
        parts.append(f"sleep:{supplement.before_sleep}")
    return ",".join(parts) if parts else "-"


def protocol_to_dict(protocol: SupplementProtocol) -> dict:
    """Convert a protocol to a JSON-serializable dict."""
    return {
        "id": str(protocol.id),
        "protocol_date": protocol.protocol_date.isoformat(),
        "prescriber": protocol.prescriber,
        "next_visit": protocol.next_visit,
        "source_file": protocol.source_file,
        "created_at": protocol.created_at.isoformat(),
        "protein_goal": protocol.protein_goal,
        "lifestyle_notes": protocol.lifestyle_notes,
    }


def supplement_to_dict(supplement: ProtocolSupplement) -> dict:
    """Convert a protocol supplement to a JSON-serializable dict."""
    return {
        "id": str(supplement.id),
        "protocol_id": str(supplement.protocol_id),
        "supplement_label_id": str(supplement.supplement_label_id) if supplement.supplement_label_id else None,
        "type": supplement.type.value,
        "name": supplement.name,
        "instructions": supplement.instructions,
        "dosage": supplement.dosage,
        "frequency": supplement.frequency.value,
        "schedule": {
            "upon_waking": supplement.upon_waking,
            "breakfast": supplement.breakfast,
            "mid_morning": supplement.mid_morning,
            "lunch": supplement.lunch,
            "mid_afternoon": supplement.mid_afternoon,
            "dinner": supplement.dinner,
            "before_sleep": supplement.before_sleep,
        },
    }


def cmd_current(repo: ProtocolRepository, args: argparse.Namespace) -> None:
    """Show the latest protocol."""
    protocol = repo.get_current_protocol()
    if protocol is None:
        print("No protocols found.")
        return

    if args.json:
        protocol_dict = protocol_to_dict(protocol)
        supplements = repo.get_supplements_by_protocol(protocol.id)
        protocol_dict["supplements"] = [supplement_to_dict(s) for s in supplements]
        print(json.dumps(protocol_dict, indent=2))
    else:
        print_protocol_details(repo, protocol)


def cmd_list(repo: ProtocolRepository, args: argparse.Namespace) -> None:
    """List all protocols."""
    protocols = repo.get_protocol_history()
    if args.json:
        print(json.dumps([protocol_to_dict(p) for p in protocols], indent=2))
    else:
        if not protocols:
            print("No protocols found.")
            return
        print("ID\tDate\tPrescriber")
        print("-" * 80)
        for protocol in protocols:
            print(format_protocol(protocol))


def cmd_protocol(repo: ProtocolRepository, args: argparse.Namespace) -> None:
    """Show details for a single protocol."""
    try:
        protocol_id = UUID(args.id)
    except ValueError:
        print(f"Invalid protocol ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    protocol = repo.get_protocol_by_id(protocol_id)
    if protocol is None:
        print(f"Protocol not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        protocol_dict = protocol_to_dict(protocol)
        supplements = repo.get_supplements_by_protocol(protocol.id)
        protocol_dict["supplements"] = [supplement_to_dict(s) for s in supplements]
        print(json.dumps(protocol_dict, indent=2))
    else:
        print_protocol_details(repo, protocol)


def cmd_history(repo: ProtocolRepository, args: argparse.Namespace) -> None:
    """Show protocol changes over time."""
    protocols = repo.get_protocol_history()

    if args.json:
        result = []
        for protocol in protocols:
            protocol_dict = protocol_to_dict(protocol)
            supplements = repo.get_supplements_by_protocol(protocol.id)
            protocol_dict["supplements"] = [supplement_to_dict(s) for s in supplements]
            result.append(protocol_dict)
        print(json.dumps(result, indent=2))
    else:
        if not protocols:
            print("No protocols found.")
            return
        for i, protocol in enumerate(protocols):
            if i > 0:
                print()
                print("=" * 80)
                print()
            print_protocol_details(repo, protocol)


def print_protocol_details(repo: ProtocolRepository, protocol: SupplementProtocol) -> None:
    """Print formatted protocol details."""
    print(f"Protocol: {protocol.id}")
    print(f"Date: {protocol.protocol_date}")
    if protocol.prescriber:
        print(f"Prescriber: {protocol.prescriber}")
    if protocol.next_visit:
        print(f"Next Visit: {protocol.next_visit}")
    if protocol.protein_goal:
        print(f"Protein Goal: {protocol.protein_goal}")
    if protocol.lifestyle_notes:
        print("Lifestyle Notes:")
        for note in protocol.lifestyle_notes:
            print(f"  - {note}")
    print()

    supplements = repo.get_supplements_by_protocol(protocol.id)
    if supplements:
        print("Supplements:")
        print("Name\tFrequency\tDosage\tSchedule\tInstructions")
        print("-" * 100)
        for supplement in supplements:
            print(format_supplement(supplement))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for protocol CLI."""
    parser = argparse.ArgumentParser(
        prog="protocol",
        description="Query supplement protocol data from the command line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of formatted text",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # current command
    subparsers.add_parser("current", help="Show the latest protocol")

    # list command
    subparsers.add_parser("list", help="List all protocols")

    # protocol command
    protocol_parser = subparsers.add_parser("protocol", help="Show details for a single protocol")
    protocol_parser.add_argument("id", help="Protocol ID (UUID)")

    # history command
    subparsers.add_parser("history", help="Show protocol changes over time")

    return parser


def main(args: Optional[list[str]] = None) -> None:
    """Main entry point for protocol CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        repo = ProtocolRepository(client)

        if parsed_args.command == "current":
            cmd_current(repo, parsed_args)
        elif parsed_args.command == "list":
            cmd_list(repo, parsed_args)
        elif parsed_args.command == "protocol":
            cmd_protocol(repo, parsed_args)
        elif parsed_args.command == "history":
            cmd_history(repo, parsed_args)


if __name__ == "__main__":
    main()
