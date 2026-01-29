"""Base repository class with common functionality."""

from typing import TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository:
    """Base repository with common operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_existing_by_source_file(self, model: type[T], source_file: str | None) -> T | None:
        """Check if a record with this source_file already exists.

        Args:
            model: The SQLModel class to query.
            source_file: The source file path to check.

        Returns:
            The existing record if found, None otherwise.
        """
        if not source_file:
            return None
        return self.session.exec(
            select(model).where(model.source_file == source_file)
        ).first()
