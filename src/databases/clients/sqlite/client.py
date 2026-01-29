"""SQLite database client with schema management for Bio-Architect."""

import sqlite3
from pathlib import Path
from typing import Optional

# Default database path
DEFAULT_DB_PATH = Path("data/databases/sqlite/bio.db")


class DatabaseClient:
    """SQLite database client for Bio-Architect health data."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database client.

        Args:
            db_path: Path to SQLite database file. Defaults to data/databases/sqlite/bio.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Create and return a database connection with foreign keys enabled.

        Returns:
            SQLite connection with foreign key constraints enabled.
        """
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        # Enable foreign key constraints
        self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the current connection, creating one if needed."""
        if self._connection is None:
            return self.connect()
        return self._connection

    def init_schema(self) -> None:
        """Create all database tables.

        Creates 13 tables:
        - dna_tests, snps
        - lab_reports, panels, biomarkers
        - supplement_labels, proprietary_blends, ingredients
        - supplement_protocols, protocol_supplements
        - knowledge, knowledge_links, knowledge_tags
        """
        conn = self.connection
        cursor = conn.cursor()

        # DNA tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dna_tests (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                collected_date TEXT NOT NULL,
                source_file TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snps (
                id TEXT PRIMARY KEY,
                dna_test_id TEXT NOT NULL,
                rsid TEXT NOT NULL,
                genotype TEXT NOT NULL,
                magnitude REAL NOT NULL,
                repute TEXT,
                gene TEXT NOT NULL,
                FOREIGN KEY (dna_test_id) REFERENCES dna_tests(id)
            )
        """)

        # Bloodwork tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lab_reports (
                id TEXT PRIMARY KEY,
                lab_provider TEXT NOT NULL,
                collected_date TEXT NOT NULL,
                source_file TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS panels (
                id TEXT PRIMARY KEY,
                lab_report_id TEXT NOT NULL,
                name TEXT NOT NULL,
                comment TEXT,
                FOREIGN KEY (lab_report_id) REFERENCES lab_reports(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS biomarkers (
                id TEXT PRIMARY KEY,
                panel_id TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                reference_low REAL,
                reference_high REAL,
                flag TEXT NOT NULL,
                FOREIGN KEY (panel_id) REFERENCES panels(id)
            )
        """)

        # Supplement tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplement_labels (
                id TEXT PRIMARY KEY,
                source_file TEXT,
                created_at TEXT NOT NULL,
                brand TEXT NOT NULL,
                product_name TEXT NOT NULL,
                form TEXT NOT NULL,
                serving_size TEXT NOT NULL,
                servings_per_container INTEGER,
                suggested_use TEXT,
                warnings TEXT NOT NULL,
                allergen_info TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proprietary_blends (
                id TEXT PRIMARY KEY,
                supplement_label_id TEXT NOT NULL,
                name TEXT NOT NULL,
                total_amount REAL,
                total_unit TEXT,
                FOREIGN KEY (supplement_label_id) REFERENCES supplement_labels(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                id TEXT PRIMARY KEY,
                supplement_label_id TEXT,
                blend_id TEXT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                amount REAL,
                unit TEXT,
                percent_dv REAL,
                form TEXT,
                FOREIGN KEY (supplement_label_id) REFERENCES supplement_labels(id),
                FOREIGN KEY (blend_id) REFERENCES proprietary_blends(id)
            )
        """)

        # Protocol tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplement_protocols (
                id TEXT PRIMARY KEY,
                protocol_date TEXT NOT NULL,
                prescriber TEXT,
                next_visit TEXT,
                source_file TEXT,
                created_at TEXT NOT NULL,
                protein_goal TEXT,
                lifestyle_notes TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS protocol_supplements (
                id TEXT PRIMARY KEY,
                protocol_id TEXT NOT NULL,
                supplement_label_id TEXT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                instructions TEXT,
                dosage TEXT,
                frequency TEXT NOT NULL,
                upon_waking INTEGER NOT NULL,
                breakfast INTEGER NOT NULL,
                mid_morning INTEGER NOT NULL,
                lunch INTEGER NOT NULL,
                mid_afternoon INTEGER NOT NULL,
                dinner INTEGER NOT NULL,
                before_sleep INTEGER NOT NULL,
                FOREIGN KEY (protocol_id) REFERENCES supplement_protocols(id),
                FOREIGN KEY (supplement_label_id) REFERENCES supplement_labels(id)
            )
        """)

        # Knowledge tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL NOT NULL,
                supersedes_id TEXT,
                supersession_reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (supersedes_id) REFERENCES knowledge(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_links (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT NOT NULL,
                link_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_tags (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge(id)
            )
        """)

        # Create indexes on FK columns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snps_dna_test_id ON snps(dna_test_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_panels_lab_report_id ON panels(lab_report_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_biomarkers_panel_id ON biomarkers(panel_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proprietary_blends_supplement_label_id ON proprietary_blends(supplement_label_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredients_supplement_label_id ON ingredients(supplement_label_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredients_blend_id ON ingredients(blend_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_protocol_supplements_protocol_id ON protocol_supplements(protocol_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_protocol_supplements_supplement_label_id ON protocol_supplements(supplement_label_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_supersedes_id ON knowledge(supersedes_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_links_knowledge_id ON knowledge_links(knowledge_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_tags_knowledge_id ON knowledge_tags(knowledge_id)")

        # Create indexes on code fields
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_biomarkers_code ON biomarkers(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredients_code ON ingredients(code)")

        # Create index on rsid
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snps_rsid ON snps(rsid)")

        # Create indexes on status fields
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_status ON knowledge(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_biomarkers_flag ON biomarkers(flag)")

        # Create indexes on created_at fields
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dna_tests_created_at ON dna_tests(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lab_reports_created_at ON lab_reports(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplement_labels_created_at ON supplement_labels(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplement_protocols_created_at ON supplement_protocols(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_created_at ON knowledge(created_at)")

        conn.commit()

    def __enter__(self) -> "DatabaseClient":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
