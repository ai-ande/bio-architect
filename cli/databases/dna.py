#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""CLI for querying DNA data."""

import argcomplete
import argparse
import json
import sys
from datetime import date
from typing import Optional

from pydantic import ValidationError
from sqlmodel import Session, select

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.dna import DnaTest, Repute, Snp


def format_snp(snp: Snp) -> str:
    """Format a SNP for display."""
    repute_str = snp.repute.value if snp.repute else "-"
    return f"{snp.rsid}\t{snp.genotype}\t{snp.gene}\t{snp.magnitude:.1f}\t{repute_str}"


def format_test(test: DnaTest) -> str:
    """Format a DNA test for display."""
    return f"{test.id}\t{test.source}\t{test.collected_date}\t{test.source_file}"


def snp_to_dict(snp: Snp) -> dict:
    """Convert a SNP to a JSON-serializable dict."""
    return {
        "id": str(snp.id),
        "dna_test_id": str(snp.dna_test_id),
        "rsid": snp.rsid,
        "genotype": snp.genotype,
        "magnitude": snp.magnitude,
        "repute": snp.repute.value if snp.repute else None,
        "gene": snp.gene,
    }


def dna_test_to_dict(test: DnaTest) -> dict:
    """Convert a DNA test to a JSON-serializable dict."""
    return {
        "id": str(test.id),
        "source": test.source,
        "collected_date": test.collected_date.isoformat(),
        "source_file": test.source_file,
        "created_at": test.created_at.isoformat(),
    }


def parse_dna_json(
    data: dict, source_file: str | None
) -> tuple[DnaTest, list[Snp]]:
    """Parse JSON into database models.

    All model construction happens here, triggering Pydantic validation.
    If any validation fails, no database operations have occurred yet.

    Args:
        data: JSON dict with DNA data.
        source_file: Source file path (required, will use "stdin" if None).

    Returns:
        Tuple of (DnaTest, list of Snp).

    Raises:
        ValidationError: If model validation fails.
        KeyError: If required fields are missing.
        ValueError: If date parsing fails.
    """
    # Create DnaTest (source_file is required, use "stdin" if from stdin)
    dna_test = DnaTest(
        source=data["source"],
        collected_date=date.fromisoformat(data["collected_date"]),
        source_file=source_file if source_file else "stdin",
    )

    snps: list[Snp] = []

    for snp_data in data.get("snps", []):
        # Parse repute - can be None, "good", or "bad"
        repute_value = snp_data.get("repute")
        repute = Repute(repute_value) if repute_value else None

        snp = Snp.model_validate({
            "dna_test_id": dna_test.id,
            "rsid": snp_data["rsid"],
            "genotype": snp_data["genotype"],
            "magnitude": snp_data["magnitude"],
            "repute": repute,
            "gene": snp_data["gene"],
        })
        snps.append(snp)

    return dna_test, snps


def cmd_import(session: Session, args: argparse.Namespace) -> None:
    """Import DNA data from JSON file.

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
        dna_test, snps = parse_dna_json(data, source_file)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Add all to session with flush() to ensure FK order
    session.add(dna_test)
    session.flush()  # Ensure dna_test exists before snps

    for snp in snps:
        session.add(snp)

    # Step 3: Single atomic commit - all or nothing
    session.commit()

    # Output
    if args.json:
        print(json.dumps({
            "dna_test_id": str(dna_test.id),
            "snps_created": len(snps),
        }, indent=2))
    else:
        print(f"Imported DNA test: {dna_test.id}")
        print(f"  SNPs: {len(snps)}")


def cmd_list(session: Session, args: argparse.Namespace) -> None:
    """List all DNA tests."""
    statement = select(DnaTest).order_by(DnaTest.collected_date.desc())
    tests = session.exec(statement).all()
    if args.json:
        print(json.dumps([dna_test_to_dict(t) for t in tests], indent=2))
    else:
        if not tests:
            print("No DNA tests found.")
            return
        print("ID\tSource\tCollected\tFile")
        print("-" * 80)
        for test in tests:
            print(format_test(test))


def cmd_snp(session: Session, args: argparse.Namespace) -> None:
    """Show details for a single SNP by rsid."""
    statement = select(Snp).where(Snp.rsid == args.rsid)
    snp = session.exec(statement).first()
    if snp is None:
        print(f"SNP not found: {args.rsid}", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps(snp_to_dict(snp), indent=2))
    else:
        print("rsid\tgenotype\tgene\tmagnitude\trepute")
        print("-" * 60)
        print(format_snp(snp))


def cmd_gene(session: Session, args: argparse.Namespace) -> None:
    """Show all SNPs for a gene."""
    statement = select(Snp).where(Snp.gene == args.gene).order_by(Snp.magnitude.desc())
    snps = session.exec(statement).all()
    if args.json:
        print(json.dumps([snp_to_dict(s) for s in snps], indent=2))
    else:
        if not snps:
            print(f"No SNPs found for gene: {args.gene}")
            return
        print("rsid\tgenotype\tgene\tmagnitude\trepute")
        print("-" * 60)
        for snp in snps:
            print(format_snp(snp))


def cmd_high_impact(session: Session, args: argparse.Namespace) -> None:
    """Show SNPs with magnitude >= 3."""
    statement = select(Snp).where(Snp.magnitude >= 3.0).order_by(Snp.magnitude.desc())
    snps = session.exec(statement).all()
    if args.json:
        print(json.dumps([snp_to_dict(s) for s in snps], indent=2))
    else:
        if not snps:
            print("No high-impact SNPs found (magnitude >= 3).")
            return
        print("rsid\tgenotype\tgene\tmagnitude\trepute")
        print("-" * 60)
        for snp in snps:
            print(format_snp(snp))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for DNA CLI."""
    parser = argparse.ArgumentParser(
        prog="dna",
        description="Query DNA data from the command line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of formatted text",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # import command
    import_parser = subparsers.add_parser("import", help="Import DNA data from JSON file")
    import_parser.add_argument(
        "--file", "-f",
        help="JSON file to read (default: stdin)",
    )

    # list command
    subparsers.add_parser("list", help="List all DNA tests")

    # snp command
    snp_parser = subparsers.add_parser("snp", help="Show details for a single SNP")
    snp_parser.add_argument("rsid", help="Reference SNP ID (e.g., rs1234)")

    # gene command
    gene_parser = subparsers.add_parser("gene", help="Show all SNPs for a gene")
    gene_parser.add_argument("gene", help="Gene name (e.g., MTHFR)")

    # high-impact command
    subparsers.add_parser("high-impact", help="Show SNPs with magnitude >= 3")

    return parser


def main(args: Optional[list[str]] = None) -> None:
    """Main entry point for DNA CLI."""
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
            elif parsed_args.command == "snp":
                cmd_snp(session, parsed_args)
            elif parsed_args.command == "gene":
                cmd_gene(session, parsed_args)
            elif parsed_args.command == "high-impact":
                cmd_high_impact(session, parsed_args)


if __name__ == "__main__":
    main()
