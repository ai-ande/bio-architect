"""SQLite database client with SQLModel for Bio-Architect."""

from pathlib import Path
from typing import Optional

from sqlalchemy import Engine, event
from sqlmodel import SQLModel, Session, create_engine

# Import all models to register them with SQLModel metadata
from src.databases.datatypes.bloodwork.models import LabReport, Panel, Biomarker  # noqa: F401
from src.databases.datatypes.supplement.models import SupplementLabel, ProprietaryBlend, Ingredient  # noqa: F401
from src.databases.datatypes.supplement_protocol.models import SupplementProtocol, ProtocolSupplement  # noqa: F401
from src.databases.datatypes.dna.models import DnaTest, Snp  # noqa: F401
from src.databases.datatypes.knowledge.models import Knowledge, KnowledgeLink, KnowledgeTag  # noqa: F401

# Project root computed from this file's location
# client.py is at src/databases/clients/sqlite/client.py (5 levels deep)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# Default database path (absolute, relative to project root)
DEFAULT_DB_PATH = _PROJECT_ROOT / "data/databases/sqlite/bio.db"


def _enable_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


class DatabaseClient:
    """SQLite database client for Bio-Architect health data."""

    def __init__(self, db_path: Optional[Path] = None, auto_init_schema: bool = True):
        """Initialize database client.

        Args:
            db_path: Path to SQLite database file. Defaults to data/databases/sqlite/bio.db
            auto_init_schema: Whether to automatically initialize schema when engine is created.
                             Defaults to True. Set to False for testing scenarios.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._engine: Optional[Engine] = None
        self._auto_init_schema = auto_init_schema
        self._schema_initialized = False

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine, creating one if needed."""
        if self._engine is None:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            self._engine = create_engine(f"sqlite:///{self.db_path}")
            # Enable foreign keys for all connections
            event.listen(self._engine, "connect", _enable_foreign_keys)

            # Auto-initialize schema if enabled
            if self._auto_init_schema and not self._schema_initialized:
                self.init_schema()

        return self._engine

    def init_schema(self) -> None:
        """Create all database tables from SQLModel metadata.

        This method is idempotent - calling it multiple times is safe
        and will only create tables that don't already exist.
        """
        # Use _engine directly if available to avoid recursion from engine property
        engine = self._engine if self._engine else self.engine
        SQLModel.metadata.create_all(engine)
        self._schema_initialized = True

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLModel Session for database operations.
        """
        return Session(self.engine)

    def close(self) -> None:
        """Dispose of the database engine."""
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def __enter__(self) -> "DatabaseClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
