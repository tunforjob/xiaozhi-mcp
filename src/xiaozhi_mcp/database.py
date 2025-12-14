"""
CRUD database operations module.
"""

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Generator, Generic, TypeVar

T = TypeVar("T")


@dataclass
class BaseModel:
    """Base model with id field."""

    id: int | None = None

    @classmethod
    def table_name(cls) -> str:
        """Return table name based on class name."""
        return cls.__name__.lower() + "s"

    @classmethod
    def field_names(cls) -> list[str]:
        """Return list of field names excluding id."""
        return [f.name for f in fields(cls) if f.name != "id"]

    @classmethod
    def all_field_names(cls) -> list[str]:
        """Return list of all field names including id."""
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def values(self) -> tuple[Any, ...]:
        """Return values excluding id."""
        return tuple(getattr(self, f) for f in self.field_names())


class Database:
    """SQLite database connection manager."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database cursor."""
        cur = self.connection.cursor()
        try:
            yield cur
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


class CRUDRepository(ABC, Generic[T]):
    """Abstract CRUD repository."""

    @abstractmethod
    def create(self, item: T) -> T:
        """Create a new item."""
        ...

    @abstractmethod
    def get(self, item_id: int) -> T | None:
        """Get item by id."""
        ...

    @abstractmethod
    def get_all(self) -> list[T]:
        """Get all items."""
        ...

    @abstractmethod
    def update(self, item: T) -> T | None:
        """Update an existing item."""
        ...

    @abstractmethod
    def delete(self, item_id: int) -> bool:
        """Delete item by id."""
        ...


class SQLiteCRUD(CRUDRepository[T]):
    """SQLite CRUD implementation."""

    def __init__(self, db: Database, model_class: type[T]) -> None:
        self.db = db
        self.model_class = model_class
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create table if not exists."""
        field_defs = []
        for f in fields(self.model_class):
            if f.name == "id":
                field_defs.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
            elif f.type == int or f.type == "int":
                field_defs.append(f"{f.name} INTEGER")
            elif f.type == float or f.type == "float":
                field_defs.append(f"{f.name} REAL")
            elif f.type == bool or f.type == "bool":
                field_defs.append(f"{f.name} INTEGER")
            else:
                field_defs.append(f"{f.name} TEXT")

        sql = f"""
            CREATE TABLE IF NOT EXISTS {self.model_class.table_name()} (
                {', '.join(field_defs)}
            )
        """
        with self.db.cursor() as cur:
            cur.execute(sql)

    def _row_to_model(self, row: sqlite3.Row) -> T:
        """Convert database row to model instance."""
        return self.model_class(**dict(row))

    def create(self, item: T) -> T:
        """Create a new item and return it with id."""
        field_names = self.model_class.field_names()
        placeholders = ", ".join("?" * len(field_names))
        columns = ", ".join(field_names)

        sql = f"""
            INSERT INTO {self.model_class.table_name()} ({columns})
            VALUES ({placeholders})
        """

        with self.db.cursor() as cur:
            cur.execute(sql, item.values())
            item.id = cur.lastrowid

        return item

    def get(self, item_id: int) -> T | None:
        """Get item by id."""
        sql = f"""
            SELECT * FROM {self.model_class.table_name()}
            WHERE id = ?
        """

        with self.db.cursor() as cur:
            cur.execute(sql, (item_id,))
            row = cur.fetchone()

        return self._row_to_model(row) if row else None

    def get_all(self) -> list[T]:
        """Get all items."""
        sql = f"SELECT * FROM {self.model_class.table_name()}"

        with self.db.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        return [self._row_to_model(row) for row in rows]

    def update(self, item: T) -> T | None:
        """Update an existing item."""
        if item.id is None:
            return None

        field_names = self.model_class.field_names()
        set_clause = ", ".join(f"{f} = ?" for f in field_names)

        sql = f"""
            UPDATE {self.model_class.table_name()}
            SET {set_clause}
            WHERE id = ?
        """

        with self.db.cursor() as cur:
            cur.execute(sql, (*item.values(), item.id))
            if cur.rowcount == 0:
                return None

        return item

    def delete(self, item_id: int) -> bool:
        """Delete item by id."""
        sql = f"""
            DELETE FROM {self.model_class.table_name()}
            WHERE id = ?
        """

        with self.db.cursor() as cur:
            cur.execute(sql, (item_id,))
            return cur.rowcount > 0

    def find_by(self, **kwargs: Any) -> list[T]:
        """Find items by field values."""
        conditions = " AND ".join(f"{k} = ?" for k in kwargs)
        sql = f"""
            SELECT * FROM {self.model_class.table_name()}
            WHERE {conditions}
        """

        with self.db.cursor() as cur:
            cur.execute(sql, tuple(kwargs.values()))
            rows = cur.fetchall()

        return [self._row_to_model(row) for row in rows]

    def count(self) -> int:
        """Count all items."""
        sql = f"SELECT COUNT(*) FROM {self.model_class.table_name()}"

        with self.db.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]

    def exists(self, item_id: int) -> bool:
        """Check if item exists."""
        sql = f"""
            SELECT 1 FROM {self.model_class.table_name()}
            WHERE id = ? LIMIT 1
        """

        with self.db.cursor() as cur:
            cur.execute(sql, (item_id,))
            return cur.fetchone() is not None
