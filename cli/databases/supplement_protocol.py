#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""CLI for querying supplement protocol data."""

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
from src.databases.datatypes.supplement_protocol import (
    Frequency,
    ProtocolSupplement,
    ProtocolSupplementType,
    SupplementProtocol,
)


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


def parse_protocol_json(
    data: dict, source_file: str | None
) -> tuple[SupplementProtocol, list[ProtocolSupplement]]:
    """Parse JSON into database models.

    All model construction happens here, triggering Pydantic validation.
    If any validation fails, no database operations have occurred yet.

    Args:
        data: JSON dict with protocol data.
        source_file: Optional source file path.

    Returns:
        Tuple of (SupplementProtocol, list of ProtocolSupplement).

    Raises:
        ValidationError: If model validation fails.
        KeyError: If required fields are missing.
        ValueError: If date parsing fails.
    """
    # Extract lifestyle notes
    lifestyle_notes_data = data.get("lifestyle_notes", {})
    protein_goal = lifestyle_notes_data.get("protein_goal") if lifestyle_notes_data else None
    lifestyle_notes = lifestyle_notes_data.get("other", []) if lifestyle_notes_data else []

    # Create SupplementProtocol
    protocol = SupplementProtocol(
        protocol_date=date.fromisoformat(data["protocol_date"]),
        prescriber=data.get("prescriber"),
        next_visit=data.get("next_visit"),
        protein_goal=protein_goal,
        lifestyle_notes=lifestyle_notes,
        source_file=source_file,
    )

    supplements: list[ProtocolSupplement] = []

    # Parse scheduled supplements
    for supp_data in data.get("supplements", []):
        schedule = supp_data.get("schedule", {})
        supplement = ProtocolSupplement(
            protocol_id=protocol.id,
            type=ProtocolSupplementType.SCHEDULED,
            name=supp_data["name"],
            instructions=supp_data.get("instructions"),
            dosage=supp_data.get("dosage"),
            frequency=Frequency(supp_data["frequency"]),
            upon_waking=schedule.get("upon_waking", 0),
            breakfast=schedule.get("breakfast", 0),
            mid_morning=schedule.get("mid_morning", 0),
            lunch=schedule.get("lunch", 0),
            mid_afternoon=schedule.get("mid_afternoon", 0),
            dinner=schedule.get("dinner", 0),
            before_sleep=schedule.get("before_sleep", 0),
        )
        supplements.append(supplement)

    # Parse own supplements
    for supp_data in data.get("own_supplements", []):
        supplement = ProtocolSupplement(
            protocol_id=protocol.id,
            type=ProtocolSupplementType.OWN,
            name=supp_data["name"],
            instructions=supp_data.get("instructions"),
            dosage=supp_data.get("dosage"),
            frequency=Frequency(supp_data["frequency"]),
        )
        supplements.append(supplement)

    return protocol, supplements


def cmd_import(session: Session, args: argparse.Namespace) -> None:
    """Import protocol from JSON file.

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
        protocol, supplements = parse_protocol_json(data, source_file)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Add all to session with flush() to ensure FK order
    session.add(protocol)
    session.flush()  # Ensure protocol exists before supplements

    for supplement in supplements:
        session.add(supplement)

    # Step 3: Single atomic commit - all or nothing
    session.commit()

    # Output
    if args.json:
        print(json.dumps({
            "protocol_id": str(protocol.id),
            "supplements_created": len(supplements),
        }, indent=2))
    else:
        print(f"Imported protocol: {protocol.id}")
        print(f"  Supplements: {len(supplements)}")


def cmd_current(session: Session, args: argparse.Namespace) -> None:
    """Show the latest protocol."""
    statement = select(SupplementProtocol).order_by(SupplementProtocol.protocol_date.desc()).limit(1)
    protocol = session.exec(statement).first()
    if protocol is None:
        print("No protocols found.")
        return

    if args.json:
        protocol_dict = protocol_to_dict(protocol)
        supplements = session.exec(
            select(ProtocolSupplement).where(ProtocolSupplement.protocol_id == protocol.id)
        ).all()
        protocol_dict["supplements"] = [supplement_to_dict(s) for s in supplements]
        print(json.dumps(protocol_dict, indent=2))
    else:
        print_protocol_details(session, protocol)


def cmd_list(session: Session, args: argparse.Namespace) -> None:
    """List all protocols."""
    statement = select(SupplementProtocol).order_by(SupplementProtocol.protocol_date.desc())
    protocols = session.exec(statement).all()
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


def cmd_protocol(session: Session, args: argparse.Namespace) -> None:
    """Show details for a single protocol."""
    try:
        protocol_id = UUID(args.id)
    except ValueError:
        print(f"Invalid protocol ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    protocol = session.get(SupplementProtocol, protocol_id)
    if protocol is None:
        print(f"Protocol not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        protocol_dict = protocol_to_dict(protocol)
        supplements = session.exec(
            select(ProtocolSupplement).where(ProtocolSupplement.protocol_id == protocol.id)
        ).all()
        protocol_dict["supplements"] = [supplement_to_dict(s) for s in supplements]
        print(json.dumps(protocol_dict, indent=2))
    else:
        print_protocol_details(session, protocol)


def cmd_history(session: Session, args: argparse.Namespace) -> None:
    """Show protocol changes over time."""
    statement = select(SupplementProtocol).order_by(SupplementProtocol.protocol_date.desc())
    protocols = session.exec(statement).all()

    if args.json:
        result = []
        for protocol in protocols:
            protocol_dict = protocol_to_dict(protocol)
            supplements = session.exec(
                select(ProtocolSupplement).where(ProtocolSupplement.protocol_id == protocol.id)
            ).all()
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
            print_protocol_details(session, protocol)


def print_protocol_details(session: Session, protocol: SupplementProtocol) -> None:
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

    supplements = session.exec(
        select(ProtocolSupplement).where(ProtocolSupplement.protocol_id == protocol.id)
    ).all()
    if supplements:
        print("Supplements:")
        print("Name\tFrequency\tDosage\tSchedule\tInstructions")
        print("-" * 100)
        for supplement in supplements:
            print(format_supplement(supplement))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for protocol CLI."""
    parser = argparse.ArgumentParser(
        prog="protocols",
        description="Query supplement protocol data from the command line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of formatted text",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # import command
    import_parser = subparsers.add_parser("import", help="Import protocol from JSON file")
    import_parser.add_argument(
        "--file", "-f",
        help="JSON file to read (default: stdin)",
    )

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
    argcomplete.autocomplete(parser)
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        with client.get_session() as session:
            if parsed_args.command == "import":
                cmd_import(session, parsed_args)
            elif parsed_args.command == "current":
                cmd_current(session, parsed_args)
            elif parsed_args.command == "list":
                cmd_list(session, parsed_args)
            elif parsed_args.command == "protocol":
                cmd_protocol(session, parsed_args)
            elif parsed_args.command == "history":
                cmd_history(session, parsed_args)


if __name__ == "__main__":
    main()
