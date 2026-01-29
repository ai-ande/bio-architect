"""Tests for Knowledge models."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.databases.datatypes.knowledge import (
    Knowledge,
    KnowledgeLink,
    KnowledgeStatus,
    KnowledgeTag,
    KnowledgeType,
    LinkType,
)


class TestKnowledgeType:
    """Tests for KnowledgeType enum."""

    def test_knowledge_type_values(self):
        assert KnowledgeType.INSIGHT.value == "insight"
        assert KnowledgeType.RECOMMENDATION.value == "recommendation"
        assert KnowledgeType.CONTRAINDICATION.value == "contraindication"
        assert KnowledgeType.MEMORY.value == "memory"

    def test_knowledge_type_is_string_enum(self):
        assert isinstance(KnowledgeType.INSIGHT, str)
        assert KnowledgeType.INSIGHT == "insight"


class TestKnowledgeStatus:
    """Tests for KnowledgeStatus enum."""

    def test_knowledge_status_values(self):
        assert KnowledgeStatus.ACTIVE.value == "active"
        assert KnowledgeStatus.DEPRECATED.value == "deprecated"

    def test_knowledge_status_is_string_enum(self):
        assert isinstance(KnowledgeStatus.ACTIVE, str)
        assert KnowledgeStatus.ACTIVE == "active"


class TestLinkType:
    """Tests for LinkType enum."""

    def test_link_type_values(self):
        assert LinkType.SNP.value == "snp"
        assert LinkType.BIOMARKER.value == "biomarker"
        assert LinkType.INGREDIENT.value == "ingredient"
        assert LinkType.SUPPLEMENT.value == "supplement"
        assert LinkType.PROTOCOL.value == "protocol"
        assert LinkType.KNOWLEDGE.value == "knowledge"

    def test_link_type_is_string_enum(self):
        assert isinstance(LinkType.SNP, str)
        assert LinkType.SNP == "snp"


class TestKnowledge:
    """Tests for Knowledge model."""

    def test_create_minimal_knowledge(self):
        knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="MTHFR C677T variant detected",
            content="The MTHFR C677T variant may affect folate metabolism.",
            confidence=0.85,
        )
        assert knowledge.type == KnowledgeType.INSIGHT
        assert knowledge.summary == "MTHFR C677T variant detected"
        assert knowledge.content == "The MTHFR C677T variant may affect folate metabolism."
        assert knowledge.confidence == 0.85

    def test_knowledge_has_uuid(self):
        knowledge = Knowledge(
            type=KnowledgeType.RECOMMENDATION,
            summary="Consider methylfolate",
            content="Based on MTHFR status, consider methylated folate supplementation.",
            confidence=0.75,
        )
        assert isinstance(knowledge.id, UUID)

    def test_knowledge_uuid_is_unique(self):
        k1 = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Test insight",
            content="Test content",
            confidence=0.5,
        )
        k2 = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Test insight",
            content="Test content",
            confidence=0.5,
        )
        assert k1.id != k2.id

    def test_knowledge_has_created_at_with_default(self):
        before = datetime.now()
        knowledge = Knowledge(
            type=KnowledgeType.MEMORY,
            summary="User preference",
            content="User prefers morning supplementation.",
            confidence=1.0,
        )
        after = datetime.now()
        assert isinstance(knowledge.created_at, datetime)
        assert before <= knowledge.created_at <= after

    def test_knowledge_status_defaults_to_active(self):
        knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Test",
            content="Test content",
            confidence=0.5,
        )
        assert knowledge.status == KnowledgeStatus.ACTIVE

    def test_knowledge_status_can_be_deprecated(self):
        knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Old insight",
            content="This has been superseded.",
            confidence=0.5,
            status=KnowledgeStatus.DEPRECATED,
        )
        assert knowledge.status == KnowledgeStatus.DEPRECATED

    def test_knowledge_with_supersedes_id(self):
        old_id = uuid4()
        knowledge = Knowledge(
            type=KnowledgeType.RECOMMENDATION,
            summary="Updated recommendation",
            content="New and improved recommendation.",
            confidence=0.9,
            supersedes_id=old_id,
            supersession_reason="New research available",
        )
        assert knowledge.supersedes_id == old_id
        assert knowledge.supersession_reason == "New research available"

    def test_knowledge_supersedes_fields_default_to_none(self):
        knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Test",
            content="Test content",
            confidence=0.5,
        )
        assert knowledge.supersedes_id is None
        assert knowledge.supersession_reason is None

    def test_knowledge_with_contraindication_type(self):
        knowledge = Knowledge(
            type=KnowledgeType.CONTRAINDICATION,
            summary="Avoid high-dose B6",
            content="High dose B6 contraindicated due to existing condition.",
            confidence=0.95,
        )
        assert knowledge.type == KnowledgeType.CONTRAINDICATION

    def test_knowledge_type_accepts_string_value(self):
        """Type should accept string values that match enum."""
        knowledge = Knowledge(
            type="insight",
            summary="Test",
            content="Test content",
            confidence=0.5,
        )
        assert knowledge.type == KnowledgeType.INSIGHT

    def test_knowledge_status_accepts_string_value(self):
        """Status should accept string values that match enum."""
        knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Test",
            content="Test content",
            confidence=0.5,
            status="deprecated",
        )
        assert knowledge.status == KnowledgeStatus.DEPRECATED

    def test_knowledge_confidence_zero(self):
        knowledge = Knowledge(
            type=KnowledgeType.INSIGHT,
            summary="Low confidence",
            content="Uncertain insight.",
            confidence=0.0,
        )
        assert knowledge.confidence == 0.0

    def test_knowledge_confidence_one(self):
        knowledge = Knowledge(
            type=KnowledgeType.MEMORY,
            summary="User stated preference",
            content="User explicitly stated this.",
            confidence=1.0,
        )
        assert knowledge.confidence == 1.0

    def test_knowledge_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError, match="confidence must be between 0.0 and 1.0"):
            Knowledge.model_validate({
                "type": KnowledgeType.INSIGHT,
                "summary": "Test",
                "content": "Test content",
                "confidence": -0.1,
            })

    def test_knowledge_confidence_above_one_raises(self):
        with pytest.raises(ValidationError, match="confidence must be between 0.0 and 1.0"):
            Knowledge.model_validate({
                "type": KnowledgeType.INSIGHT,
                "summary": "Test",
                "content": "Test content",
                "confidence": 1.1,
            })

    def test_knowledge_missing_required_type_raises(self):
        with pytest.raises(ValidationError):
            Knowledge.model_validate({
                "summary": "Test",
                "content": "Test content",
                "confidence": 0.5,
            })

    def test_knowledge_missing_required_summary_raises(self):
        with pytest.raises(ValidationError):
            Knowledge.model_validate({
                "type": KnowledgeType.INSIGHT,
                "content": "Test content",
                "confidence": 0.5,
            })

    def test_knowledge_missing_required_content_raises(self):
        with pytest.raises(ValidationError):
            Knowledge.model_validate({
                "type": KnowledgeType.INSIGHT,
                "summary": "Test",
                "confidence": 0.5,
            })

    def test_knowledge_missing_required_confidence_raises(self):
        with pytest.raises(ValidationError):
            Knowledge.model_validate({
                "type": KnowledgeType.INSIGHT,
                "summary": "Test",
                "content": "Test content",
            })


class TestKnowledgeLink:
    """Tests for KnowledgeLink model."""

    def test_create_knowledge_link(self):
        knowledge_id = uuid4()
        target_id = uuid4()
        link = KnowledgeLink(
            knowledge_id=knowledge_id,
            link_type=LinkType.SNP,
            target_id=target_id,
        )
        assert link.knowledge_id == knowledge_id
        assert link.link_type == LinkType.SNP
        assert link.target_id == target_id

    def test_knowledge_link_has_uuid(self):
        link = KnowledgeLink(
            knowledge_id=uuid4(),
            link_type=LinkType.BIOMARKER,
            target_id=uuid4(),
        )
        assert isinstance(link.id, UUID)

    def test_knowledge_link_uuid_is_unique(self):
        knowledge_id = uuid4()
        target_id = uuid4()
        l1 = KnowledgeLink(
            knowledge_id=knowledge_id,
            link_type=LinkType.INGREDIENT,
            target_id=target_id,
        )
        l2 = KnowledgeLink(
            knowledge_id=knowledge_id,
            link_type=LinkType.INGREDIENT,
            target_id=target_id,
        )
        assert l1.id != l2.id

    def test_knowledge_link_all_link_types(self):
        """Test that all link types work."""
        knowledge_id = uuid4()
        for link_type in LinkType:
            link = KnowledgeLink(
                knowledge_id=knowledge_id,
                link_type=link_type,
                target_id=uuid4(),
            )
            assert link.link_type == link_type

    def test_knowledge_link_type_accepts_string_value(self):
        """Link type should accept string values that match enum."""
        link = KnowledgeLink(
            knowledge_id=uuid4(),
            link_type="supplement",
            target_id=uuid4(),
        )
        assert link.link_type == LinkType.SUPPLEMENT

    def test_knowledge_link_missing_required_knowledge_id_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeLink.model_validate({
                "link_type": LinkType.PROTOCOL,
                "target_id": uuid4(),
            })

    def test_knowledge_link_missing_required_link_type_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeLink.model_validate({
                "knowledge_id": uuid4(),
                "target_id": uuid4(),
            })

    def test_knowledge_link_missing_required_target_id_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeLink.model_validate({
                "knowledge_id": uuid4(),
                "link_type": LinkType.KNOWLEDGE,
            })


class TestKnowledgeTag:
    """Tests for KnowledgeTag model."""

    def test_create_knowledge_tag(self):
        knowledge_id = uuid4()
        tag = KnowledgeTag(
            knowledge_id=knowledge_id,
            tag="methylation",
        )
        assert tag.knowledge_id == knowledge_id
        assert tag.tag == "methylation"

    def test_knowledge_tag_has_uuid(self):
        tag = KnowledgeTag(
            knowledge_id=uuid4(),
            tag="vitamin-d",
        )
        assert isinstance(tag.id, UUID)

    def test_knowledge_tag_uuid_is_unique(self):
        knowledge_id = uuid4()
        t1 = KnowledgeTag(
            knowledge_id=knowledge_id,
            tag="mthfr",
        )
        t2 = KnowledgeTag(
            knowledge_id=knowledge_id,
            tag="mthfr",
        )
        assert t1.id != t2.id

    def test_knowledge_tag_missing_required_knowledge_id_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeTag.model_validate({
                "tag": "test-tag",
            })

    def test_knowledge_tag_missing_required_tag_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeTag.model_validate({
                "knowledge_id": uuid4(),
            })

    def test_knowledge_tag_various_tags(self):
        """Test various tag formats."""
        knowledge_id = uuid4()
        tags = ["mthfr", "vitamin-d", "b12", "folate", "sleep", "energy"]
        for tag_value in tags:
            tag = KnowledgeTag(
                knowledge_id=knowledge_id,
                tag=tag_value,
            )
            assert tag.tag == tag_value
