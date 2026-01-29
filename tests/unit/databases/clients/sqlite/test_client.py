"""Tests for SQLite DatabaseClient."""

import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

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

    def test_connection_initially_none(self):
        """Test connection is None before connecting."""
        client = DatabaseClient()
        assert client._connection is None


class TestDatabaseClientConnection:
    """Tests for DatabaseClient connection management."""

    def test_connect_creates_connection(self, tmp_path):
        """Test connect() creates a connection."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        conn = client.connect()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        client.close()

    def test_connect_creates_parent_directories(self, tmp_path):
        """Test connect() creates parent directories if needed."""
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        assert db_path.parent.exists()
        client.close()

    def test_connect_enables_foreign_keys(self, tmp_path):
        """Test connect() enables foreign key constraints."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        conn = client.connect()
        cursor = conn.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1  # Foreign keys enabled
        client.close()

    def test_connect_sets_row_factory(self, tmp_path):
        """Test connect() sets row_factory to sqlite3.Row."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        conn = client.connect()
        assert conn.row_factory == sqlite3.Row
        client.close()

    def test_close_closes_connection(self, tmp_path):
        """Test close() closes the connection."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        client.close()
        assert client._connection is None

    def test_connection_property_creates_if_needed(self, tmp_path):
        """Test connection property creates connection if none exists."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        conn = client.connection
        assert conn is not None
        client.close()

    def test_context_manager(self, tmp_path):
        """Test context manager opens and closes connection."""
        db_path = tmp_path / "test.db"
        with DatabaseClient(db_path=db_path) as client:
            assert client._connection is not None
        assert client._connection is None


class TestDatabaseClientSchema:
    """Tests for DatabaseClient schema creation."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with temporary database."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        yield client
        client.close()

    def test_init_schema_creates_all_tables(self, client):
        """Test init_schema() creates all 13 tables."""
        client.init_schema()
        cursor = client.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

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

    def test_init_schema_creates_indexes(self, client):
        """Test init_schema() creates expected indexes."""
        client.init_schema()
        cursor = client.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        expected_indexes = [
            "idx_biomarkers_code",
            "idx_biomarkers_flag",
            "idx_biomarkers_panel_id",
            "idx_dna_tests_created_at",
            "idx_ingredients_blend_id",
            "idx_ingredients_code",
            "idx_ingredients_supplement_label_id",
            "idx_knowledge_created_at",
            "idx_knowledge_links_knowledge_id",
            "idx_knowledge_status",
            "idx_knowledge_supersedes_id",
            "idx_knowledge_tags_knowledge_id",
            "idx_lab_reports_created_at",
            "idx_panels_lab_report_id",
            "idx_proprietary_blends_supplement_label_id",
            "idx_protocol_supplements_protocol_id",
            "idx_protocol_supplements_supplement_label_id",
            "idx_snps_dna_test_id",
            "idx_snps_rsid",
            "idx_supplement_labels_created_at",
            "idx_supplement_protocols_created_at",
        ]
        assert indexes == expected_indexes

    def test_init_schema_is_idempotent(self, client):
        """Test init_schema() can be called multiple times safely."""
        client.init_schema()
        client.init_schema()  # Should not raise
        cursor = client.connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        )
        count = cursor.fetchone()[0]
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
        for table in tables:
            cursor = client.connection.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            assert count == 0, f"Table {table} should be empty"


class TestForeignKeyConstraints:
    """Tests for foreign key constraint enforcement."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()

    def test_snp_requires_valid_dna_test_id(self, client):
        """Test inserting SNP with invalid dna_test_id fails."""
        with pytest.raises(sqlite3.IntegrityError):
            client.connection.execute("""
                INSERT INTO snps (id, dna_test_id, rsid, genotype, magnitude, gene)
                VALUES (?, ?, 'rs1234', 'AG', 2.5, 'MTHFR')
            """, (str(uuid4()), str(uuid4())))
            client.connection.commit()

    def test_panel_requires_valid_lab_report_id(self, client):
        """Test inserting Panel with invalid lab_report_id fails."""
        with pytest.raises(sqlite3.IntegrityError):
            client.connection.execute("""
                INSERT INTO panels (id, lab_report_id, name)
                VALUES (?, ?, 'CBC')
            """, (str(uuid4()), str(uuid4())))
            client.connection.commit()

    def test_biomarker_requires_valid_panel_id(self, client):
        """Test inserting Biomarker with invalid panel_id fails."""
        with pytest.raises(sqlite3.IntegrityError):
            client.connection.execute("""
                INSERT INTO biomarkers (id, panel_id, name, code, value, unit, flag)
                VALUES (?, ?, 'Glucose', 'GLUCOSE', 95.0, 'mg/dL', 'normal')
            """, (str(uuid4()), str(uuid4())))
            client.connection.commit()

    def test_proprietary_blend_requires_valid_supplement_label_id(self, client):
        """Test inserting ProprietaryBlend with invalid supplement_label_id fails."""
        with pytest.raises(sqlite3.IntegrityError):
            client.connection.execute("""
                INSERT INTO proprietary_blends (id, supplement_label_id, name)
                VALUES (?, ?, 'Energy Blend')
            """, (str(uuid4()), str(uuid4())))
            client.connection.commit()

    def test_protocol_supplement_requires_valid_protocol_id(self, client):
        """Test inserting ProtocolSupplement with invalid protocol_id fails."""
        with pytest.raises(sqlite3.IntegrityError):
            client.connection.execute("""
                INSERT INTO protocol_supplements (
                    id, protocol_id, type, name, frequency,
                    upon_waking, breakfast, mid_morning, lunch, mid_afternoon, dinner, before_sleep
                )
                VALUES (?, ?, 'scheduled', 'Vitamin D', 'daily', 0, 1, 0, 0, 0, 0, 0)
            """, (str(uuid4()), str(uuid4())))
            client.connection.commit()

    def test_knowledge_link_requires_valid_knowledge_id(self, client):
        """Test inserting KnowledgeLink with invalid knowledge_id fails."""
        with pytest.raises(sqlite3.IntegrityError):
            client.connection.execute("""
                INSERT INTO knowledge_links (id, knowledge_id, link_type, target_id)
                VALUES (?, ?, 'snp', ?)
            """, (str(uuid4()), str(uuid4()), str(uuid4())))
            client.connection.commit()

    def test_knowledge_tag_requires_valid_knowledge_id(self, client):
        """Test inserting KnowledgeTag with invalid knowledge_id fails."""
        with pytest.raises(sqlite3.IntegrityError):
            client.connection.execute("""
                INSERT INTO knowledge_tags (id, knowledge_id, tag)
                VALUES (?, ?, 'methylation')
            """, (str(uuid4()), str(uuid4())))
            client.connection.commit()

    def test_valid_foreign_key_insert_succeeds(self, client):
        """Test inserting with valid foreign keys succeeds."""
        dna_test_id = str(uuid4())
        snp_id = str(uuid4())

        # Insert parent first
        client.connection.execute("""
            INSERT INTO dna_tests (id, source, collected_date, source_file, created_at)
            VALUES (?, '23andMe', '2024-01-15', 'test.txt', '2024-01-20T10:00:00')
        """, (dna_test_id,))

        # Insert child with valid FK
        client.connection.execute("""
            INSERT INTO snps (id, dna_test_id, rsid, genotype, magnitude, gene)
            VALUES (?, ?, 'rs1234', 'AG', 2.5, 'MTHFR')
        """, (snp_id, dna_test_id))
        client.connection.commit()

        # Verify insert succeeded
        cursor = client.connection.execute("SELECT COUNT(*) FROM snps")
        assert cursor.fetchone()[0] == 1


class TestDnaTablesSchema:
    """Tests for DNA table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()

    def test_dna_tests_columns(self, client):
        """Test dna_tests table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(dna_tests)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "source": "TEXT",
            "collected_date": "TEXT",
            "source_file": "TEXT",
            "created_at": "TEXT",
        }

    def test_snps_columns(self, client):
        """Test snps table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(snps)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "dna_test_id": "TEXT",
            "rsid": "TEXT",
            "genotype": "TEXT",
            "magnitude": "REAL",
            "repute": "TEXT",
            "gene": "TEXT",
        }


class TestBloodworkTablesSchema:
    """Tests for bloodwork table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()

    def test_lab_reports_columns(self, client):
        """Test lab_reports table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(lab_reports)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "lab_provider": "TEXT",
            "collected_date": "TEXT",
            "source_file": "TEXT",
            "created_at": "TEXT",
        }

    def test_panels_columns(self, client):
        """Test panels table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(panels)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "lab_report_id": "TEXT",
            "name": "TEXT",
            "comment": "TEXT",
        }

    def test_biomarkers_columns(self, client):
        """Test biomarkers table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(biomarkers)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "panel_id": "TEXT",
            "name": "TEXT",
            "code": "TEXT",
            "value": "REAL",
            "unit": "TEXT",
            "reference_low": "REAL",
            "reference_high": "REAL",
            "flag": "TEXT",
        }


class TestSupplementTablesSchema:
    """Tests for supplement table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()

    def test_supplement_labels_columns(self, client):
        """Test supplement_labels table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(supplement_labels)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "source_file": "TEXT",
            "created_at": "TEXT",
            "brand": "TEXT",
            "product_name": "TEXT",
            "form": "TEXT",
            "serving_size": "TEXT",
            "servings_per_container": "INTEGER",
            "suggested_use": "TEXT",
            "warnings": "TEXT",
            "allergen_info": "TEXT",
        }

    def test_proprietary_blends_columns(self, client):
        """Test proprietary_blends table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(proprietary_blends)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "supplement_label_id": "TEXT",
            "name": "TEXT",
            "total_amount": "REAL",
            "total_unit": "TEXT",
        }

    def test_ingredients_columns(self, client):
        """Test ingredients table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(ingredients)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "supplement_label_id": "TEXT",
            "blend_id": "TEXT",
            "type": "TEXT",
            "name": "TEXT",
            "code": "TEXT",
            "amount": "REAL",
            "unit": "TEXT",
            "percent_dv": "REAL",
            "form": "TEXT",
        }


class TestProtocolTablesSchema:
    """Tests for protocol table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()

    def test_supplement_protocols_columns(self, client):
        """Test supplement_protocols table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(supplement_protocols)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "protocol_date": "TEXT",
            "prescriber": "TEXT",
            "next_visit": "TEXT",
            "source_file": "TEXT",
            "created_at": "TEXT",
            "protein_goal": "TEXT",
            "lifestyle_notes": "TEXT",
        }

    def test_protocol_supplements_columns(self, client):
        """Test protocol_supplements table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(protocol_supplements)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "protocol_id": "TEXT",
            "supplement_label_id": "TEXT",
            "type": "TEXT",
            "name": "TEXT",
            "instructions": "TEXT",
            "dosage": "TEXT",
            "frequency": "TEXT",
            "upon_waking": "INTEGER",
            "breakfast": "INTEGER",
            "mid_morning": "INTEGER",
            "lunch": "INTEGER",
            "mid_afternoon": "INTEGER",
            "dinner": "INTEGER",
            "before_sleep": "INTEGER",
        }


class TestKnowledgeTablesSchema:
    """Tests for knowledge table schema."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with schema initialized."""
        db_path = tmp_path / "test.db"
        client = DatabaseClient(db_path=db_path)
        client.connect()
        client.init_schema()
        yield client
        client.close()

    def test_knowledge_columns(self, client):
        """Test knowledge table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(knowledge)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "type": "TEXT",
            "status": "TEXT",
            "summary": "TEXT",
            "content": "TEXT",
            "confidence": "REAL",
            "supersedes_id": "TEXT",
            "supersession_reason": "TEXT",
            "created_at": "TEXT",
        }

    def test_knowledge_links_columns(self, client):
        """Test knowledge_links table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(knowledge_links)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "knowledge_id": "TEXT",
            "link_type": "TEXT",
            "target_id": "TEXT",
        }

    def test_knowledge_tags_columns(self, client):
        """Test knowledge_tags table has correct columns."""
        cursor = client.connection.execute("PRAGMA table_info(knowledge_tags)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert columns == {
            "id": "TEXT",
            "knowledge_id": "TEXT",
            "tag": "TEXT",
        }
