"""Tests for knowledge CLI script."""

import argparse
import json
import tempfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from scripts.knowledge import (
    cmd_add,
    cmd_get,
    cmd_linked,
    cmd_list,
    cmd_supersede,
    cmd_tag,
    create_parser,
    format_knowledge,
    format_knowledge_detail,
    knowledge_to_dict,
    link_to_dict,
    main,
    parse_knowledge_json,
    tag_to_dict,
    validate_link_target_exists,
)
from src.databases.clients.sqlite import DatabaseClient
from src.databases.datatypes.knowledge import (
    Knowledge,
    KnowledgeLink,
    KnowledgeStatus,
    KnowledgeTag,
    KnowledgeType,
    LinkType,
)
from src.databases.repositories.knowledge import KnowledgeRepository


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_parser_has_json_flag(self):
        """Parser accepts --json flag."""
        parser = create_parser()
        args = parser.parse_args(["--json", "list"])
        assert args.json is True

    def test_parser_json_default_false(self):
        """Parser --json defaults to False."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.json is False

    def test_parser_add_command(self):
        """Parser recognizes add command."""
        parser = create_parser()
        args = parser.parse_args(["add"])
        assert args.command == "add"

    def test_parser_add_command_with_file(self):
        """Parser add command accepts --file option."""
        parser = create_parser()
        args = parser.parse_args(["add", "--file", "input.json"])
        assert args.command == "add"
        assert args.file == "input.json"

    def test_parser_add_command_with_short_file(self):
        """Parser add command accepts -f shorthand."""
        parser = create_parser()
        args = parser.parse_args(["add", "-f", "input.json"])
        assert args.file == "input.json"

    def test_parser_get_command_requires_id(self):
        """Parser get command requires id argument."""
        parser = create_parser()
        args = parser.parse_args(["get", "123e4567-e89b-12d3-a456-426614174000"])
        assert args.command == "get"
        assert args.id == "123e4567-e89b-12d3-a456-426614174000"

    def test_parser_get_command_missing_id_fails(self):
        """Parser get command fails without id."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["get"])

    def test_parser_list_command(self):
        """Parser recognizes list command."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_parser_tag_command_requires_tag(self):
        """Parser tag command requires tag argument."""
        parser = create_parser()
        args = parser.parse_args(["tag", "vitamin-d"])
        assert args.command == "tag"
        assert args.tag == "vitamin-d"

    def test_parser_tag_command_missing_tag_fails(self):
        """Parser tag command fails without tag."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["tag"])

    def test_parser_linked_command_requires_type_and_id(self):
        """Parser linked command requires type and id arguments."""
        parser = create_parser()
        args = parser.parse_args(["linked", "snp", "123e4567-e89b-12d3-a456-426614174000"])
        assert args.command == "linked"
        assert args.type == "snp"
        assert args.id == "123e4567-e89b-12d3-a456-426614174000"

    def test_parser_linked_command_missing_args_fails(self):
        """Parser linked command fails without both arguments."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["linked"])
        with pytest.raises(SystemExit):
            parser.parse_args(["linked", "snp"])

    def test_parser_supersede_command_requires_id(self):
        """Parser supersede command requires id argument."""
        parser = create_parser()
        args = parser.parse_args(["supersede", "123e4567-e89b-12d3-a456-426614174000"])
        assert args.command == "supersede"
        assert args.id == "123e4567-e89b-12d3-a456-426614174000"

    def test_parser_supersede_command_missing_id_fails(self):
        """Parser supersede command fails without id."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["supersede"])

    def test_parser_no_command_returns_none(self):
        """Parser returns None for command when no command given."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestFormatFunctions:
    """Tests for format helper functions."""

    def test_format_knowledge(self):
        """format_knowledge includes all fields."""
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Test insight",
            content="Full content here",
            confidence=0.85,
        )
        result = format_knowledge(knowledge)
        assert str(knowledge.id) in result
        assert "insight" in result
        assert "0.85" in result
        assert "Test insight" in result

    def test_format_knowledge_deprecated(self):
        """format_knowledge shows deprecated marker."""
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            status=KnowledgeStatus.DEPRECATED,
            summary="Old insight",
            content="Old content",
            confidence=0.5,
        )
        result = format_knowledge(knowledge)
        assert "[DEPRECATED]" in result

    def test_format_knowledge_detail(self):
        """format_knowledge_detail includes all fields."""
        knowledge_id = uuid4()
        knowledge = Knowledge(
            id=knowledge_id,
            type=KnowledgeType.RECOMMENDATION,
            summary="Test recommendation",
            content="Detailed content",
            confidence=0.9,
            created_at=datetime(2024, 1, 15, 10, 30, 0),
        )
        tags = [
            KnowledgeTag(knowledge_id=knowledge_id, tag="vitamin-d"),
            KnowledgeTag(knowledge_id=knowledge_id, tag="bone-health"),
        ]
        links = [
            KnowledgeLink(
                knowledge_id=knowledge_id,
                link_type=LinkType.SNP,
                target_id=uuid4(),
            ),
        ]
        result = format_knowledge_detail(knowledge, tags, links)
        assert str(knowledge_id) in result
        assert "recommendation" in result
        assert "0.90" in result
        assert "Test recommendation" in result
        assert "Detailed content" in result
        assert "vitamin-d" in result
        assert "bone-health" in result
        assert "snp" in result

    def test_format_knowledge_detail_with_supersession(self):
        """format_knowledge_detail shows supersession info."""
        old_id = uuid4()
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="New insight",
            content="Updated content",
            confidence=0.95,
            supersedes_id=old_id,
            supersession_reason="Updated based on new research",
        )
        result = format_knowledge_detail(knowledge, [], [])
        assert str(old_id) in result
        assert "Updated based on new research" in result


class TestToDictFunctions:
    """Tests for JSON serialization functions."""

    def test_knowledge_to_dict(self):
        """knowledge_to_dict returns JSON-serializable dict."""
        knowledge_id = uuid4()
        supersedes_id = uuid4()
        knowledge = Knowledge(
            id=knowledge_id,
            type=KnowledgeType.CONTRAINDICATION,
            status=KnowledgeStatus.ACTIVE,
            summary="Drug interaction",
            content="Do not combine X with Y",
            confidence=0.99,
            supersedes_id=supersedes_id,
            supersession_reason="More specific info",
            created_at=datetime(2024, 1, 20, 10, 30, 0),
        )
        result = knowledge_to_dict(knowledge)
        assert result["id"] == str(knowledge_id)
        assert result["type"] == "contraindication"
        assert result["status"] == "active"
        assert result["summary"] == "Drug interaction"
        assert result["content"] == "Do not combine X with Y"
        assert result["confidence"] == 0.99
        assert result["supersedes_id"] == str(supersedes_id)
        assert result["supersession_reason"] == "More specific info"
        assert result["created_at"] == "2024-01-20T10:30:00"
        # Verify it's JSON serializable
        json.dumps(result)

    def test_knowledge_to_dict_null_supersedes(self):
        """knowledge_to_dict handles null supersedes_id."""
        knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.MEMORY,
            summary="User preference",
            content="Prefers morning doses",
            confidence=1.0,
        )
        result = knowledge_to_dict(knowledge)
        assert result["supersedes_id"] is None
        assert result["supersession_reason"] is None
        json.dumps(result)

    def test_tag_to_dict(self):
        """tag_to_dict returns JSON-serializable dict."""
        knowledge_id = uuid4()
        tag_id = uuid4()
        tag = KnowledgeTag(id=tag_id, knowledge_id=knowledge_id, tag="vitamin-d")
        result = tag_to_dict(tag)
        assert result["id"] == str(tag_id)
        assert result["knowledge_id"] == str(knowledge_id)
        assert result["tag"] == "vitamin-d"
        json.dumps(result)

    def test_link_to_dict(self):
        """link_to_dict returns JSON-serializable dict."""
        knowledge_id = uuid4()
        target_id = uuid4()
        link_id = uuid4()
        link = KnowledgeLink(
            id=link_id,
            knowledge_id=knowledge_id,
            link_type=LinkType.BIOMARKER,
            target_id=target_id,
        )
        result = link_to_dict(link)
        assert result["id"] == str(link_id)
        assert result["knowledge_id"] == str(knowledge_id)
        assert result["link_type"] == "biomarker"
        assert result["target_id"] == str(target_id)
        json.dumps(result)


class TestParseKnowledgeJson:
    """Tests for parse_knowledge_json function."""

    def test_parse_knowledge_json_minimal(self):
        """parse_knowledge_json handles minimal valid input."""
        data = {
            "type": "insight",
            "summary": "Test",
            "content": "Test content",
            "confidence": 0.5,
        }
        knowledge, tags, links = parse_knowledge_json(data)
        assert knowledge.type == KnowledgeType.INSIGHT
        assert knowledge.summary == "Test"
        assert knowledge.content == "Test content"
        assert knowledge.confidence == 0.5
        assert tags == []
        assert links == []

    def test_parse_knowledge_json_with_tags(self):
        """parse_knowledge_json parses tags."""
        data = {
            "type": "recommendation",
            "summary": "Test",
            "content": "Test content",
            "confidence": 0.8,
            "tags": ["tag1", "tag2"],
        }
        knowledge, tags, links = parse_knowledge_json(data)
        assert len(tags) == 2
        assert tags[0].tag == "tag1"
        assert tags[1].tag == "tag2"
        assert all(t.knowledge_id == knowledge.id for t in tags)

    def test_parse_knowledge_json_with_links(self):
        """parse_knowledge_json parses links."""
        target_id = str(uuid4())
        data = {
            "type": "contraindication",
            "summary": "Test",
            "content": "Test content",
            "confidence": 0.9,
            "links": [{"link_type": "snp", "target_id": target_id}],
        }
        knowledge, tags, links = parse_knowledge_json(data)
        assert len(links) == 1
        assert links[0].link_type == LinkType.SNP
        assert str(links[0].target_id) == target_id
        assert links[0].knowledge_id == knowledge.id

    def test_parse_knowledge_json_missing_required_field(self):
        """parse_knowledge_json raises on missing required field."""
        data = {
            "type": "insight",
            "summary": "Test",
            # missing content and confidence
        }
        with pytest.raises(ValueError) as exc_info:
            parse_knowledge_json(data)
        assert "Missing required field" in str(exc_info.value)

    def test_parse_knowledge_json_invalid_link(self):
        """parse_knowledge_json raises on invalid link."""
        data = {
            "type": "insight",
            "summary": "Test",
            "content": "Content",
            "confidence": 0.5,
            "links": [{"link_type": "snp"}],  # missing target_id
        }
        with pytest.raises(ValueError) as exc_info:
            parse_knowledge_json(data)
        assert "Link missing required fields" in str(exc_info.value)


@pytest.fixture
def db_client():
    """Create a temporary database client."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        client = DatabaseClient(db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()


@pytest.fixture
def repository(db_client):
    """Create a KnowledgeRepository with the test database."""
    return KnowledgeRepository(db_client)


@pytest.fixture
def sample_knowledge():
    """Create a sample Knowledge entry."""
    return Knowledge(
        id=uuid4(),
        type=KnowledgeType.INSIGHT,
        summary="Vitamin D affects bone health",
        content="Research shows vitamin D is essential for calcium absorption.",
        confidence=0.85,
        created_at=datetime(2024, 1, 20, 10, 30, 0),
    )


@pytest.fixture
def sample_tag(sample_knowledge):
    """Create a sample KnowledgeTag."""
    return KnowledgeTag(
        knowledge_id=sample_knowledge.id,
        tag="vitamin-d",
    )


@pytest.fixture
def sample_link(sample_knowledge):
    """Create a sample KnowledgeLink."""
    return KnowledgeLink(
        knowledge_id=sample_knowledge.id,
        link_type=LinkType.KNOWLEDGE,
        target_id=uuid4(),  # Link to another knowledge entry
    )


class TestCmdGet:
    """Tests for get command."""

    def test_cmd_get_found(self, repository, sample_knowledge, sample_tag, capsys):
        """cmd_get shows knowledge details."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        args = argparse.Namespace(json=False, id=str(sample_knowledge.id))
        cmd_get(repository, args)
        captured = capsys.readouterr()
        assert str(sample_knowledge.id) in captured.out
        assert "Vitamin D affects bone health" in captured.out
        assert "vitamin-d" in captured.out

    def test_cmd_get_not_found(self, repository, capsys):
        """cmd_get exits with error when not found."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"
        args = argparse.Namespace(json=False, id=fake_id)
        with pytest.raises(SystemExit) as exc_info:
            cmd_get(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Knowledge not found" in captured.err

    def test_cmd_get_invalid_id(self, repository, capsys):
        """cmd_get exits with error for invalid UUID."""
        args = argparse.Namespace(json=False, id="not-a-uuid")
        with pytest.raises(SystemExit) as exc_info:
            cmd_get(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid knowledge ID" in captured.err

    def test_cmd_get_json(self, repository, sample_knowledge, sample_tag, capsys):
        """cmd_get outputs valid JSON."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        args = argparse.Namespace(json=True, id=str(sample_knowledge.id))
        cmd_get(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["summary"] == "Vitamin D affects bone health"
        assert "vitamin-d" in [t["tag"] for t in data["tags"]]


class TestCmdList:
    """Tests for list command."""

    def test_cmd_list_empty(self, repository, capsys):
        """cmd_list handles empty database."""
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "No active knowledge entries found" in captured.out

    def test_cmd_list_shows_entries(self, repository, sample_knowledge, capsys):
        """cmd_list shows knowledge entries."""
        repository.insert_knowledge(sample_knowledge)
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert str(sample_knowledge.id) in captured.out
        assert "insight" in captured.out
        assert "Vitamin D" in captured.out

    def test_cmd_list_excludes_deprecated(self, repository, capsys):
        """cmd_list excludes deprecated entries."""
        deprecated = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            status=KnowledgeStatus.DEPRECATED,
            summary="Old insight",
            content="Old content",
            confidence=0.5,
        )
        active = Knowledge(
            id=uuid4(),
            type=KnowledgeType.INSIGHT,
            summary="Active insight",
            content="Active content",
            confidence=0.8,
        )
        repository.insert_knowledge(deprecated)
        repository.insert_knowledge(active)
        args = argparse.Namespace(json=False)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        assert "Active insight" in captured.out
        assert "Old insight" not in captured.out

    def test_cmd_list_json(self, repository, sample_knowledge, sample_tag, capsys):
        """cmd_list outputs valid JSON."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        args = argparse.Namespace(json=True)
        cmd_list(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["summary"] == "Vitamin D affects bone health"


class TestCmdTag:
    """Tests for tag command."""

    def test_cmd_tag_found(self, repository, sample_knowledge, sample_tag, capsys):
        """cmd_tag shows entries with matching tag."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        args = argparse.Namespace(json=False, tag="vitamin-d")
        cmd_tag(repository, args)
        captured = capsys.readouterr()
        assert str(sample_knowledge.id) in captured.out
        assert "Vitamin D" in captured.out

    def test_cmd_tag_not_found(self, repository, sample_knowledge, sample_tag, capsys):
        """cmd_tag handles no matches."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        args = argparse.Namespace(json=False, tag="nonexistent")
        cmd_tag(repository, args)
        captured = capsys.readouterr()
        assert "No knowledge entries found" in captured.out

    def test_cmd_tag_json(self, repository, sample_knowledge, sample_tag, capsys):
        """cmd_tag outputs valid JSON."""
        repository.insert_knowledge(sample_knowledge)
        repository.insert_tag(sample_tag)
        args = argparse.Namespace(json=True, tag="vitamin-d")
        cmd_tag(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1


class TestCmdLinked:
    """Tests for linked command."""

    def test_cmd_linked_found(self, repository, sample_knowledge, capsys):
        """cmd_linked shows entries linked to target."""
        # Create another knowledge to link to
        target_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.MEMORY,
            summary="Target entry",
            content="Target content",
            confidence=1.0,
        )
        repository.insert_knowledge(target_knowledge)
        repository.insert_knowledge(sample_knowledge)

        link = KnowledgeLink(
            knowledge_id=sample_knowledge.id,
            link_type=LinkType.KNOWLEDGE,
            target_id=target_knowledge.id,
        )
        repository.insert_link(link)

        args = argparse.Namespace(json=False, type="knowledge", id=str(target_knowledge.id))
        cmd_linked(repository, args)
        captured = capsys.readouterr()
        assert str(sample_knowledge.id) in captured.out

    def test_cmd_linked_invalid_type(self, repository, capsys):
        """cmd_linked exits with error for invalid link type."""
        args = argparse.Namespace(json=False, type="invalid", id=str(uuid4()))
        with pytest.raises(SystemExit) as exc_info:
            cmd_linked(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid link type" in captured.err

    def test_cmd_linked_invalid_id(self, repository, capsys):
        """cmd_linked exits with error for invalid UUID."""
        args = argparse.Namespace(json=False, type="snp", id="not-a-uuid")
        with pytest.raises(SystemExit) as exc_info:
            cmd_linked(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid target ID" in captured.err

    def test_cmd_linked_not_found(self, repository, capsys):
        """cmd_linked handles no matches."""
        args = argparse.Namespace(json=False, type="snp", id=str(uuid4()))
        cmd_linked(repository, args)
        captured = capsys.readouterr()
        assert "No knowledge entries linked to" in captured.out

    def test_cmd_linked_json(self, repository, sample_knowledge, capsys):
        """cmd_linked outputs valid JSON."""
        target_knowledge = Knowledge(
            id=uuid4(),
            type=KnowledgeType.MEMORY,
            summary="Target entry",
            content="Target content",
            confidence=1.0,
        )
        repository.insert_knowledge(target_knowledge)
        repository.insert_knowledge(sample_knowledge)

        link = KnowledgeLink(
            knowledge_id=sample_knowledge.id,
            link_type=LinkType.KNOWLEDGE,
            target_id=target_knowledge.id,
        )
        repository.insert_link(link)

        args = argparse.Namespace(json=True, type="knowledge", id=str(target_knowledge.id))
        cmd_linked(repository, args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1


class TestCmdAdd:
    """Tests for add command."""

    def test_cmd_add_from_stdin(self, repository, capsys):
        """cmd_add reads JSON from stdin."""
        data = {
            "type": "insight",
            "summary": "New insight",
            "content": "New content",
            "confidence": 0.75,
        }
        with patch("sys.stdin", StringIO(json.dumps(data))):
            args = argparse.Namespace(json=False, file=None)
            cmd_add(repository, args)
        captured = capsys.readouterr()
        assert "Added knowledge entry" in captured.out

    def test_cmd_add_from_file(self, repository, capsys):
        """cmd_add reads JSON from file."""
        data = {
            "type": "recommendation",
            "summary": "File recommendation",
            "content": "File content",
            "confidence": 0.9,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            args = argparse.Namespace(json=False, file=temp_path)
            cmd_add(repository, args)
            captured = capsys.readouterr()
            assert "Added knowledge entry" in captured.out
        finally:
            Path(temp_path).unlink()

    def test_cmd_add_with_tags(self, repository, capsys):
        """cmd_add handles tags."""
        data = {
            "type": "insight",
            "summary": "Tagged insight",
            "content": "Tagged content",
            "confidence": 0.8,
            "tags": ["tag1", "tag2"],
        }
        with patch("sys.stdin", StringIO(json.dumps(data))):
            args = argparse.Namespace(json=True, file=None)
            cmd_add(repository, args)
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert len(result["tags"]) == 2

    def test_cmd_add_validates_links(self, repository, capsys):
        """cmd_add validates that link targets exist."""
        data = {
            "type": "insight",
            "summary": "Linked insight",
            "content": "Linked content",
            "confidence": 0.8,
            "links": [{"link_type": "snp", "target_id": str(uuid4())}],
        }
        with patch("sys.stdin", StringIO(json.dumps(data))):
            args = argparse.Namespace(json=False, file=None)
            with pytest.raises(SystemExit) as exc_info:
                cmd_add(repository, args)
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Link target does not exist" in captured.err

    def test_cmd_add_invalid_json(self, repository, capsys):
        """cmd_add exits on invalid JSON."""
        with patch("sys.stdin", StringIO("not valid json")):
            args = argparse.Namespace(json=False, file=None)
            with pytest.raises(SystemExit) as exc_info:
                cmd_add(repository, args)
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.err

    def test_cmd_add_file_not_found(self, repository, capsys):
        """cmd_add exits on missing file."""
        args = argparse.Namespace(json=False, file="/nonexistent/file.json")
        with pytest.raises(SystemExit) as exc_info:
            cmd_add(repository, args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "File not found" in captured.err


class TestCmdSupersede:
    """Tests for supersede command."""

    def test_cmd_supersede_success(self, repository, sample_knowledge, capsys):
        """cmd_supersede replaces old entry."""
        repository.insert_knowledge(sample_knowledge)
        new_data = {
            "type": "insight",
            "summary": "Updated insight",
            "content": "Updated content",
            "confidence": 0.95,
            "supersession_reason": "New research",
        }
        with patch("sys.stdin", StringIO(json.dumps(new_data))):
            args = argparse.Namespace(json=False, id=str(sample_knowledge.id))
            cmd_supersede(repository, args)
        captured = capsys.readouterr()
        assert "Superseded knowledge entry" in captured.out

        # Verify old entry is deprecated
        old_entry = repository.get_by_id(sample_knowledge.id)
        assert old_entry.status == KnowledgeStatus.DEPRECATED

    def test_cmd_supersede_not_found(self, repository, capsys):
        """cmd_supersede exits when old entry not found."""
        new_data = {
            "type": "insight",
            "summary": "New",
            "content": "Content",
            "confidence": 0.5,
        }
        with patch("sys.stdin", StringIO(json.dumps(new_data))):
            args = argparse.Namespace(json=False, id="123e4567-e89b-12d3-a456-426614174000")
            with pytest.raises(SystemExit) as exc_info:
                cmd_supersede(repository, args)
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Knowledge not found" in captured.err

    def test_cmd_supersede_invalid_id(self, repository, capsys):
        """cmd_supersede exits for invalid UUID."""
        new_data = {
            "type": "insight",
            "summary": "New",
            "content": "Content",
            "confidence": 0.5,
        }
        with patch("sys.stdin", StringIO(json.dumps(new_data))):
            args = argparse.Namespace(json=False, id="not-a-uuid")
            with pytest.raises(SystemExit) as exc_info:
                cmd_supersede(repository, args)
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid knowledge ID" in captured.err

    def test_cmd_supersede_json(self, repository, sample_knowledge, capsys):
        """cmd_supersede outputs valid JSON."""
        repository.insert_knowledge(sample_knowledge)
        new_data = {
            "type": "insight",
            "summary": "Updated insight",
            "content": "Updated content",
            "confidence": 0.95,
        }
        with patch("sys.stdin", StringIO(json.dumps(new_data))):
            args = argparse.Namespace(json=True, id=str(sample_knowledge.id))
            cmd_supersede(repository, args)
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["summary"] == "Updated insight"
        assert result["supersedes_id"] == str(sample_knowledge.id)


class TestValidateLinkTargetExists:
    """Tests for validate_link_target_exists function."""

    def test_knowledge_link_exists(self, repository, sample_knowledge):
        """validate_link_target_exists returns True for existing knowledge."""
        repository.insert_knowledge(sample_knowledge)
        result = validate_link_target_exists(repository, LinkType.KNOWLEDGE, sample_knowledge.id)
        assert result is True

    def test_knowledge_link_not_exists(self, repository):
        """validate_link_target_exists returns False for missing knowledge."""
        result = validate_link_target_exists(repository, LinkType.KNOWLEDGE, uuid4())
        assert result is False


class TestMain:
    """Tests for main entry point."""

    def test_main_no_command_shows_help(self, capsys):
        """main shows help when no command given."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1

    def test_main_help_flag(self, capsys):
        """main responds to --help flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()
