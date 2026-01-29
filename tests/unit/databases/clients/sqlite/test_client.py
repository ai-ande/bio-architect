"""Tests for SQLite DatabaseClient with SQLModel."""

import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlmodel import Session

from src.databases.clients.sqlite import DatabaseClient, DEFAULT_DB_PATH


class TestDatabaseClientInit:
    """Tests for DatabaseClient initialization."""

    def test_default_db_path(self):
        """Test default database path is set correctly."""
        client = DatabaseClient()
        assert client.db_path == DEFAULT_DB_PATH

    def test_custom_db_path(self):
        """Test custom database path can be specified."""
        custom_path = Path("/tmp/test.db")
        client = DatabaseClient(db_path=custom_path)
        assert client.db_path == custom_path

    def test_engine_initially_none(self):
        """Test engine is None before accessing."""
        client = DatabaseClient()
        assert client._engine is None


class TestDatabaseClientEngine:
    """Tests for DatabaseClient engine management."""

    def test_engine_property_creates_engine(self, tmp_path):
        """Test engine property creates an engine."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        engine = client.engine
        assert engine is not None
        client.close()

    def test_engine_creates_parent_directories(self, tmp_path):
        """Test engine property creates parent directories if needed."""
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        client = DatabaseClient(db_path=db_path)
        _ = client.engine  # Access engine to trigger creation
        assert db_path.parent.exists()
        client.close()

    def test_engine_enables_foreign_keys(self, tmp_path):
        """Test engine enables foreign key constraints."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            row = result.fetchone()
            assert row[0] == 1  # Foreign keys enabled
        client.close()

    def test_close_disposes_engine(self, tmp_path):
        """Test close() disposes the engine."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        _ = client.engine  # Create engine
        client.close()
        assert client._engine is None

    def test_context_manager(self, tmp_path):
        """Test context manager opens and closes properly."""
        db_path = tmp_path / "test.db"
        with DatabaseClient(db_path=db_path) as client:
            _ = client.engine
            assert client._engine is not None
        assert client._engine is None


class TestDatabaseClientSession:
    """Tests for DatabaseClient session management."""

    def test_get_session_returns_session(self, tmp_path):
        """Test get_session() returns a SQLModel Session."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        session = client.get_session()
        assert isinstance(session, Session)
        session.close()
        client.close()

    def test_session_can_execute_queries(self, tmp_path):
        """Test session can execute queries."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.init_schema()
        with client.get_session() as session:
            result = session.exec(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        client.close()


class TestDatabaseClientSchema:
    """Tests for DatabaseClient schema creation."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with temporary database."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        yield client
        client.close()

    def test_init_schema_creates_all_tables(self, client):
        """Test init_schema() creates all 13 tables."""
        client.init_schema()
        with client.engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = [row[0] for row in result.fetchall()]

        expected_tables = [
            "biomarkers",
            "dna_tests",
            "ingredients",
            "knowledge",
            "knowledge_links",
            "knowledge_tags",
            "lab_reports",
            "panels",
            "proprietary_blends",
            "protocol_supplements",
            "snps",
            "supplement_labels",
            "supplement_protocols",
        ]
        assert tables == expected_tables

    def test_init_schema_is_idempotent(self, client):
        """Test init_schema() can be called multiple times safely."""
        client.init_schema()
        client.init_schema()  # Should not raise
        with client.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            )
            count = result.fetchone()[0]
        assert count == 13

    def test_tables_are_empty(self, client):
        """Test tables are created empty (no seed data)."""
        client.init_schema()
        tables = [
            "dna_tests", "snps", "lab_reports", "panels", "biomarkers",
            "supplement_labels", "proprietary_blends", "ingredients",
            "supplement_protocols", "protocol_supplements",
            "knowledge", "knowledge_links", "knowledge_tags"
        ]
        with client.engine.connect() as conn:
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                assert count == 0, f"Table {table} should be empty"


class TestForeignKeyConstraints:
    """Tests for foreign key constraint enforcement."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.init_schema()
        yield client
        client.close()

    def test_snp_requires_valid_dna_test_id(self, client):
        """Test inserting SNP with invalid dna_test_id fails."""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with client.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO snps (id, dna_test_id, rsid, genotype, magnitude, gene)
                    VALUES (:id, :dna_test_id, 'rs1234', 'AG', 2.5, 'MTHFR')
                """), {"id": str(uuid4()), "dna_test_id": str(uuid4())})
                conn.commit()

    def test_panel_requires_valid_lab_report_id(self, client):
        """Test inserting Panel with invalid lab_report_id fails."""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with client.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO panels (id, lab_report_id, name)
                    VALUES (:id, :lab_report_id, 'CBC')
                """), {"id": str(uuid4()), "lab_report_id": str(uuid4())})
                conn.commit()

    def test_biomarker_requires_valid_panel_id(self, client):
        """Test inserting Biomarker with invalid panel_id fails."""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with client.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO biomarkers (id, panel_id, name, code, value, unit, flag)
                    VALUES (:id, :panel_id, 'Glucose', 'GLUCOSE', 95.0, 'mg/dL', 'normal')
                """), {"id": str(uuid4()), "panel_id": str(uuid4())})
                conn.commit()

    def test_proprietary_blend_requires_valid_supplement_label_id(self, client):
        """Test inserting ProprietaryBlend with invalid supplement_label_id fails."""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with client.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO proprietary_blends (id, supplement_label_id, name)
                    VALUES (:id, :supplement_label_id, 'Energy Blend')
                """), {"id": str(uuid4()), "supplement_label_id": str(uuid4())})
                conn.commit()

    def test_protocol_supplement_requires_valid_protocol_id(self, client):
        """Test inserting ProtocolSupplement with invalid protocol_id fails."""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with client.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO protocol_supplements (
                        id, protocol_id, type, name, frequency,
                        upon_waking, breakfast, mid_morning, lunch, mid_afternoon, dinner, before_sleep
                    )
                    VALUES (:id, :protocol_id, 'scheduled', 'Vitamin D', 'daily', 0, 1, 0, 0, 0, 0, 0)
                """), {"id": str(uuid4()), "protocol_id": str(uuid4())})
                conn.commit()

    def test_knowledge_link_requires_valid_knowledge_id(self, client):
        """Test inserting KnowledgeLink with invalid knowledge_id fails."""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with client.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO knowledge_links (id, knowledge_id, link_type, target_id)
                    VALUES (:id, :knowledge_id, 'snp', :target_id)
                """), {"id": str(uuid4()), "knowledge_id": str(uuid4()), "target_id": str(uuid4())})
                conn.commit()

    def test_knowledge_tag_requires_valid_knowledge_id(self, client):
        """Test inserting KnowledgeTag with invalid knowledge_id fails."""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with client.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO knowledge_tags (id, knowledge_id, tag)
                    VALUES (:id, :knowledge_id, 'methylation')
                """), {"id": str(uuid4()), "knowledge_id": str(uuid4())})
                conn.commit()

    def test_valid_foreign_key_insert_succeeds(self, client):
        """Test inserting with valid foreign keys succeeds."""
        dna_test_id = str(uuid4())
        snp_id = str(uuid4())

        with client.engine.connect() as conn:
            # Insert parent first
            conn.execute(text("""
                INSERT INTO dna_tests (id, source, collected_date, source_file, created_at)
                VALUES (:id, '23andMe', '2024-01-15', 'test.txt', '2024-01-20T10:00:00')
            """), {"id": dna_test_id})

            # Insert child with valid FK
            conn.execute(text("""
                INSERT INTO snps (id, dna_test_id, rsid, genotype, magnitude, gene)
                VALUES (:id, :dna_test_id, 'rs1234', 'AG', 2.5, 'MTHFR')
            """), {"id": snp_id, "dna_test_id": dna_test_id})
            conn.commit()

            # Verify insert succeeded
            result = conn.execute(text("SELECT COUNT(*) FROM snps"))
            assert result.fetchone()[0] == 1


class TestDnaTablesSchema:
    """Tests for DNA table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.init_schema()
        yield client
        client.close()

    def test_dna_tests_columns(self, client):
        """Test dna_tests table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(dna_tests)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "source" in columns
        assert "collected_date" in columns
        assert "source_file" in columns
        assert "created_at" in columns

    def test_snps_columns(self, client):
        """Test snps table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(snps)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "dna_test_id" in columns
        assert "rsid" in columns
        assert "genotype" in columns
        assert "magnitude" in columns
        assert "repute" in columns
        assert "gene" in columns


class TestBloodworkTablesSchema:
    """Tests for bloodwork table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.init_schema()
        yield client
        client.close()

    def test_lab_reports_columns(self, client):
        """Test lab_reports table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(lab_reports)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "lab_provider" in columns
        assert "collected_date" in columns
        assert "source_file" in columns
        assert "created_at" in columns

    def test_panels_columns(self, client):
        """Test panels table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(panels)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "lab_report_id" in columns
        assert "name" in columns
        assert "comment" in columns

    def test_biomarkers_columns(self, client):
        """Test biomarkers table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(biomarkers)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "panel_id" in columns
        assert "name" in columns
        assert "code" in columns
        assert "value" in columns
        assert "unit" in columns
        assert "reference_low" in columns
        assert "reference_high" in columns
        assert "flag" in columns


class TestSupplementTablesSchema:
    """Tests for supplement table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.init_schema()
        yield client
        client.close()

    def test_supplement_labels_columns(self, client):
        """Test supplement_labels table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(supplement_labels)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "source_file" in columns
        assert "created_at" in columns
        assert "brand" in columns
        assert "product_name" in columns
        assert "form" in columns
        assert "serving_size" in columns
        assert "servings_per_container" in columns
        assert "suggested_use" in columns
        assert "warnings" in columns
        assert "allergen_info" in columns

    def test_proprietary_blends_columns(self, client):
        """Test proprietary_blends table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(proprietary_blends)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "supplement_label_id" in columns
        assert "name" in columns
        assert "total_amount" in columns
        assert "total_unit" in columns

    def test_ingredients_columns(self, client):
        """Test ingredients table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(ingredients)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "supplement_label_id" in columns
        assert "blend_id" in columns
        assert "type" in columns
        assert "name" in columns
        assert "code" in columns
        assert "amount" in columns
        assert "unit" in columns
        assert "percent_dv" in columns
        assert "form" in columns


class TestProtocolTablesSchema:
    """Tests for protocol table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.init_schema()
        yield client
        client.close()

    def test_supplement_protocols_columns(self, client):
        """Test supplement_protocols table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(supplement_protocols)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "protocol_date" in columns
        assert "prescriber" in columns
        assert "next_visit" in columns
        assert "source_file" in columns
        assert "created_at" in columns
        assert "protein_goal" in columns
        assert "lifestyle_notes" in columns

    def test_protocol_supplements_columns(self, client):
        """Test protocol_supplements table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(protocol_supplements)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "protocol_id" in columns
        assert "supplement_label_id" in columns
        assert "type" in columns
        assert "name" in columns
        assert "instructions" in columns
        assert "dosage" in columns
        assert "frequency" in columns
        assert "upon_waking" in columns
        assert "breakfast" in columns
        assert "mid_morning" in columns
        assert "lunch" in columns
        assert "mid_afternoon" in columns
        assert "dinner" in columns
        assert "before_sleep" in columns


class TestKnowledgeTablesSchema:
    """Tests for knowledge table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.init_schema()
        yield client
        client.close()

    def test_knowledge_columns(self, client):
        """Test knowledge table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(knowledge)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "type" in columns
        assert "status" in columns
        assert "summary" in columns
        assert "content" in columns
        assert "confidence" in columns
        assert "supersedes_id" in columns
        assert "supersession_reason" in columns
        assert "created_at" in columns

    def test_knowledge_links_columns(self, client):
        """Test knowledge_links table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(knowledge_links)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "knowledge_id" in columns
        assert "link_type" in columns
        assert "target_id" in columns

    def test_knowledge_tags_columns(self, client):
        """Test knowledge_tags table has correct columns."""
        with client.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(knowledge_tags)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
        assert "id" in columns
        assert "knowledge_id" in columns
        assert "tag" in columns
