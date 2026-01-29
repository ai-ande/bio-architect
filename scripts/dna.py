#!/usr/bin/env python
"""CLI for querying DNA data."""

import argparse
import json
import sys
from typing import Optional

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.dna import DnaTest, Snp
from src.databases.repositories.dna import DnaRepository


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


def cmd_list(repo: DnaRepository, args: argparse.Namespace) -> None:
    """List all DNA tests."""
    tests = repo.get_all_tests()
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


def cmd_snp(repo: DnaRepository, args: argparse.Namespace) -> None:
    """Show details for a single SNP by rsid."""
    snp = repo.get_snp_by_rsid(args.rsid)
    if snp is None:
        print(f"SNP not found: {args.rsid}", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps(snp_to_dict(snp), indent=2))
    else:
        print("rsid\tgenotype\tgene\tmagnitude\trepute")
        print("-" * 60)
        print(format_snp(snp))


def cmd_gene(repo: DnaRepository, args: argparse.Namespace) -> None:
    """Show all SNPs for a gene."""
    snps = repo.get_snps_by_gene(args.gene)
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


def cmd_high_impact(repo: DnaRepository, args: argparse.Namespace) -> None:
    """Show SNPs with magnitude >= 3."""
    snps = repo.get_high_impact_snps(min_magnitude=3.0)
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
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        repo = DnaRepository(client)

        if parsed_args.command == "list":
            cmd_list(repo, parsed_args)
        elif parsed_args.command == "snp":
            cmd_snp(repo, parsed_args)
        elif parsed_args.command == "gene":
            cmd_gene(repo, parsed_args)
        elif parsed_args.command == "high-impact":
            cmd_high_impact(repo, parsed_args)


if __name__ == "__main__":
    main()
