#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""CLI for storing and querying knowledge entries."""

import argcomplete
import argparse
import json
import sys
from typing import Optional
from uuid import UUID

from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.knowledge import (
    Knowledge,
    KnowledgeLink,
    KnowledgeRepository,
    KnowledgeStatus,
    KnowledgeTag,
    KnowledgeType,
    LinkType,
)


def format_knowledge(knowledge: Knowledge) -> str:
    """Format a knowledge entry for display."""
    status_marker = "[DEPRECATED] " if knowledge.status == KnowledgeStatus.DEPRECATED else ""
    return f"{status_marker}{knowledge.id}\t{knowledge.type.value}\t{knowledge.confidence:.2f}\t{knowledge.summary}"


def format_knowledge_detail(
    knowledge: Knowledge,
    tags: list[KnowledgeTag],
    links: list[KnowledgeLink],
) -> str:
    """Format knowledge entry with full details."""
    lines = []
    lines.append(f"ID: {knowledge.id}")
    lines.append(f"Type: {knowledge.type.value}")
    lines.append(f"Status: {knowledge.status.value}")
    lines.append(f"Confidence: {knowledge.confidence:.2f}")
    lines.append(f"Summary: {knowledge.summary}")
    lines.append(f"Content: {knowledge.content}")
    if knowledge.supersedes_id:
        lines.append(f"Supersedes: {knowledge.supersedes_id}")
    if knowledge.supersession_reason:
        lines.append(f"Supersession Reason: {knowledge.supersession_reason}")
    lines.append(f"Created: {knowledge.created_at.isoformat()}")

    if tags:
        tag_values = [t.tag for t in tags]
        lines.append(f"Tags: {', '.join(tag_values)}")

    if links:
        lines.append("Links:")
        for link in links:
            lines.append(f"  - {link.link_type.value}: {link.target_id}")

    return "\n".join(lines)


def knowledge_to_dict(knowledge: Knowledge) -> dict:
    """Convert a knowledge entry to a JSON-serializable dict."""
    return {
        "id": str(knowledge.id),
        "type": knowledge.type.value,
        "status": knowledge.status.value,
        "summary": knowledge.summary,
        "content": knowledge.content,
        "confidence": knowledge.confidence,
        "supersedes_id": str(knowledge.supersedes_id) if knowledge.supersedes_id else None,
        "supersession_reason": knowledge.supersession_reason,
        "created_at": knowledge.created_at.isoformat(),
    }


def tag_to_dict(tag: KnowledgeTag) -> dict:
    """Convert a knowledge tag to a JSON-serializable dict."""
    return {
        "id": str(tag.id),
        "knowledge_id": str(tag.knowledge_id),
        "tag": tag.tag,
    }


def link_to_dict(link: KnowledgeLink) -> dict:
    """Convert a knowledge link to a JSON-serializable dict."""
    return {
        "id": str(link.id),
        "knowledge_id": str(link.knowledge_id),
        "link_type": link.link_type.value,
        "target_id": str(link.target_id),
    }


def parse_knowledge_json(data: dict) -> tuple[Knowledge, list[KnowledgeTag], list[KnowledgeLink]]:
    """Parse JSON data into Knowledge, tags, and links.

    Args:
        data: JSON dict with knowledge data.

    Returns:
        Tuple of (Knowledge, list of KnowledgeTag, list of KnowledgeLink).

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    # Validate required fields
    required = ["type", "summary", "content", "confidence"]
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Create Knowledge model
    knowledge = Knowledge(
        type=KnowledgeType(data["type"]),
        summary=data["summary"],
        content=data["content"],
        confidence=data["confidence"],
        supersedes_id=UUID(data["supersedes_id"]) if data.get("supersedes_id") else None,
        supersession_reason=data.get("supersession_reason"),
    )

    # Parse tags
    tags = []
    for tag_value in data.get("tags", []):
        tag = KnowledgeTag(knowledge_id=knowledge.id, tag=tag_value)
        tags.append(tag)

    # Parse links
    links = []
    for link_data in data.get("links", []):
        if "link_type" not in link_data or "target_id" not in link_data:
            raise ValueError("Link missing required fields: link_type, target_id")
        link = KnowledgeLink(
            knowledge_id=knowledge.id,
            link_type=LinkType(link_data["link_type"]),
            target_id=UUID(link_data["target_id"]),
        )
        links.append(link)

    return knowledge, tags, links


def cmd_create(repo: KnowledgeRepository, args: argparse.Namespace) -> None:
    """Create a new knowledge entry from JSON."""
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
    else:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        knowledge, tags, links = parse_knowledge_json(data)
    except ValueError as e:
        print(f"Invalid knowledge data: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate links exist
    for link in links:
        if not repo.validate_link_target_exists(link.link_type, link.target_id):
            print(
                f"Link target does not exist: {link.link_type.value} {link.target_id}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Save knowledge with tags and links
    repo.save_knowledge(knowledge, tags, links)

    if args.json:
        result = knowledge_to_dict(knowledge)
        result["tags"] = [tag_to_dict(t) for t in tags]
        result["links"] = [link_to_dict(l) for l in links]
        print(json.dumps(result, indent=2))
    else:
        print(f"Created knowledge entry: {knowledge.id}")


def cmd_get(repo: KnowledgeRepository, args: argparse.Namespace) -> None:
    """Get a single knowledge entry by ID."""
    try:
        knowledge_id = UUID(args.id)
    except ValueError:
        print(f"Invalid knowledge ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    knowledge = repo.get_knowledge(knowledge_id)
    if knowledge is None:
        print(f"Knowledge not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    tags = repo.get_tags_for_knowledge(knowledge_id)
    links = repo.get_links_for_knowledge(knowledge_id)

    if args.json:
        result = knowledge_to_dict(knowledge)
        result["tags"] = [tag_to_dict(t) for t in tags]
        result["links"] = [link_to_dict(l) for l in links]
        print(json.dumps(result, indent=2))
    else:
        print(format_knowledge_detail(knowledge, tags, links))


def cmd_list(repo: KnowledgeRepository, args: argparse.Namespace) -> None:
    """List active knowledge entries."""
    entries = repo.list_active()

    if args.json:
        result = []
        for entry in entries:
            entry_dict = knowledge_to_dict(entry)
            tags = repo.get_tags_for_knowledge(entry.id)
            links = repo.get_links_for_knowledge(entry.id)
            entry_dict["tags"] = [tag_to_dict(t) for t in tags]
            entry_dict["links"] = [link_to_dict(l) for l in links]
            result.append(entry_dict)
        print(json.dumps(result, indent=2))
    else:
        if not entries:
            print("No active knowledge entries found.")
            return
        print("ID\tType\tConfidence\tSummary")
        print("-" * 100)
        for entry in entries:
            print(format_knowledge(entry))


def cmd_tag(repo: KnowledgeRepository, args: argparse.Namespace) -> None:
    """Show knowledge entries by tag."""
    entries = repo.get_by_tag(args.tag)

    if not entries:
        if args.json:
            print(json.dumps([], indent=2))
        else:
            print(f"No knowledge entries found with tag: {args.tag}")
        return

    if args.json:
        result = []
        for entry in entries:
            entry_dict = knowledge_to_dict(entry)
            tags = repo.get_tags_for_knowledge(entry.id)
            links = repo.get_links_for_knowledge(entry.id)
            entry_dict["tags"] = [tag_to_dict(t) for t in tags]
            entry_dict["links"] = [link_to_dict(l) for l in links]
            result.append(entry_dict)
        print(json.dumps(result, indent=2))
    else:
        print(f"Knowledge entries with tag '{args.tag}':")
        print("ID\tType\tConfidence\tSummary")
        print("-" * 100)
        for entry in entries:
            print(format_knowledge(entry))


def cmd_linked(repo: KnowledgeRepository, args: argparse.Namespace) -> None:
    """Show knowledge entries linked to a target."""
    try:
        link_type = LinkType(args.type)
    except ValueError:
        valid_types = ", ".join(t.value for t in LinkType)
        print(f"Invalid link type: {args.type}. Valid types: {valid_types}", file=sys.stderr)
        sys.exit(1)

    try:
        target_id = UUID(args.id)
    except ValueError:
        print(f"Invalid target ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    entries = repo.get_linked_to(link_type, target_id)

    if not entries:
        if args.json:
            print(json.dumps([], indent=2))
        else:
            print(f"No knowledge entries linked to {args.type} {args.id}")
        return

    if args.json:
        result = []
        for entry in entries:
            entry_dict = knowledge_to_dict(entry)
            tags = repo.get_tags_for_knowledge(entry.id)
            links = repo.get_links_for_knowledge(entry.id)
            entry_dict["tags"] = [tag_to_dict(t) for t in tags]
            entry_dict["links"] = [link_to_dict(l) for l in links]
            result.append(entry_dict)
        print(json.dumps(result, indent=2))
    else:
        print(f"Knowledge entries linked to {args.type} {args.id}:")
        print("ID\tType\tConfidence\tSummary")
        print("-" * 100)
        for entry in entries:
            print(format_knowledge(entry))


def cmd_supersede(repo: KnowledgeRepository, args: argparse.Namespace) -> None:
    """Supersede an existing knowledge entry."""
    try:
        old_id = UUID(args.id)
    except ValueError:
        print(f"Invalid knowledge ID: {args.id}", file=sys.stderr)
        sys.exit(1)

    # Verify old knowledge exists
    old_knowledge = repo.get_knowledge(old_id)
    if old_knowledge is None:
        print(f"Knowledge not found: {args.id}", file=sys.stderr)
        sys.exit(1)

    # Read JSON from stdin
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON from stdin: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        knowledge, tags, links = parse_knowledge_json(data)
    except ValueError as e:
        print(f"Invalid knowledge data: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate links exist
    for link in links:
        if not repo.validate_link_target_exists(link.link_type, link.target_id):
            print(
                f"Link target does not exist: {link.link_type.value} {link.target_id}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Supersede via repository
    repo.supersede(old_id, knowledge, tags, links)

    if args.json:
        new_tags = repo.get_tags_for_knowledge(knowledge.id)
        new_links = repo.get_links_for_knowledge(knowledge.id)
        result = knowledge_to_dict(knowledge)
        result["tags"] = [tag_to_dict(t) for t in new_tags]
        result["links"] = [link_to_dict(l) for l in new_links]
        print(json.dumps(result, indent=2))
    else:
        print(f"Superseded knowledge entry {old_id} with new entry: {knowledge.id}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for knowledge CLI."""
    parser = argparse.ArgumentParser(
        prog="knowledge",
        description="Store and query knowledge entries from the command line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of formatted text",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new knowledge entry from JSON")
    create_parser.add_argument(
        "--file", "-f",
        help="JSON file to read (default: stdin)",
    )

    # get command
    get_parser = subparsers.add_parser("get", help="Show a single knowledge entry")
    get_parser.add_argument("id", help="Knowledge ID (UUID)")

    # list command
    subparsers.add_parser("list", help="List active knowledge entries")

    # tag command
    tag_parser = subparsers.add_parser("tag", help="Show knowledge entries by tag")
    tag_parser.add_argument("tag", help="Tag value to search for")

    # linked command
    linked_parser = subparsers.add_parser("linked", help="Show knowledge entries linked to a target")
    linked_parser.add_argument("type", help="Link type (snp, biomarker, ingredient, supplement, protocol, knowledge)")
    linked_parser.add_argument("id", help="Target ID (UUID)")

    # supersede command
    supersede_parser = subparsers.add_parser("supersede", help="Supersede an existing knowledge entry")
    supersede_parser.add_argument("id", help="ID of knowledge entry to supersede (UUID)")

    return parser


def main(args: Optional[list[str]] = None) -> None:
    """Main entry point for knowledge CLI."""
    parser = create_parser()
    argcomplete.autocomplete(parser)
    parsed_args = parser.parse_args(args)

    if parsed_args.command is None:
        parser.print_help()
        sys.exit(1)

    with DatabaseClient() as client:
        with client.get_session() as session:
            repo = KnowledgeRepository(session)
            if parsed_args.command == "create":
                cmd_create(repo, parsed_args)
            elif parsed_args.command == "get":
                cmd_get(repo, parsed_args)
            elif parsed_args.command == "list":
                cmd_list(repo, parsed_args)
            elif parsed_args.command == "tag":
                cmd_tag(repo, parsed_args)
            elif parsed_args.command == "linked":
                cmd_linked(repo, parsed_args)
            elif parsed_args.command == "supersede":
                cmd_supersede(repo, parsed_args)


if __name__ == "__main__":
    main()
