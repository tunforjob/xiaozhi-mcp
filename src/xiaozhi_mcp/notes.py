"""
Notes repository with extended functionality.
"""

from datetime import datetime

from xiaozhi_mcp.database import Database, SQLiteCRUD
from xiaozhi_mcp.models import Note


class NotesRepository(SQLiteCRUD[Note]):
    """Repository for managing notes with additional methods."""

    def __init__(self, db: Database) -> None:
        super().__init__(db, Note)

    def create_note(self, title: str, content: str, tags: list[str] | None = None) -> Note:
        """Create a new note with automatic timestamps."""
        now = datetime.now().isoformat()
        note = Note(
            title=title,
            content=content,
            created_at=now,
            updated_at=now,
            tags=",".join(tags) if tags else "",
        )
        return self.create(note)

    def update_note(self, note: Note) -> Note | None:
        """Update note with automatic updated_at timestamp."""
        note.updated_at = datetime.now().isoformat()
        return self.update(note)

    def find_by_title(self, title: str) -> list[Note]:
        """Find notes by exact title match."""
        return self.find_by(title=title)

    def search_by_title(self, query: str) -> list[Note]:
        """Search notes by title (partial match)."""
        sql = f"""
            SELECT * FROM {self.model_class.table_name()}
            WHERE title LIKE ?
        """
        with self.db.cursor() as cur:
            cur.execute(sql, (f"%{query}%",))
            rows = cur.fetchall()
        return [self._row_to_model(row) for row in rows]

    def search_by_content(self, query: str) -> list[Note]:
        """Search notes by content (partial match)."""
        sql = f"""
            SELECT * FROM {self.model_class.table_name()}
            WHERE content LIKE ?
        """
        with self.db.cursor() as cur:
            cur.execute(sql, (f"%{query}%",))
            rows = cur.fetchall()
        return [self._row_to_model(row) for row in rows]

    def search(self, query: str) -> list[Note]:
        """Search notes by title or content."""
        sql = f"""
            SELECT * FROM {self.model_class.table_name()}
            WHERE title LIKE ? OR content LIKE ?
        """
        pattern = f"%{query}%"
        with self.db.cursor() as cur:
            cur.execute(sql, (pattern, pattern))
            rows = cur.fetchall()
        return [self._row_to_model(row) for row in rows]

    def find_by_tag(self, tag: str) -> list[Note]:
        """Find notes containing a specific tag."""
        sql = f"""
            SELECT * FROM {self.model_class.table_name()}
            WHERE tags LIKE ?
        """
        with self.db.cursor() as cur:
            cur.execute(sql, (f"%{tag}%",))
            rows = cur.fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_recent(self, limit: int = 10) -> list[Note]:
        """Get most recently updated notes."""
        sql = f"""
            SELECT * FROM {self.model_class.table_name()}
            ORDER BY updated_at DESC
            LIMIT ?
        """
        with self.db.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_tags(self, note: Note) -> list[str]:
        """Get list of tags from a note."""
        if not note.tags:
            return []
        return [t.strip() for t in note.tags.split(",") if t.strip()]

    def add_tag(self, note: Note, tag: str) -> Note | None:
        """Add a tag to a note."""
        tags = self.get_tags(note)
        if tag not in tags:
            tags.append(tag)
            note.tags = ",".join(tags)
            return self.update_note(note)
        return note

    def remove_tag(self, note: Note, tag: str) -> Note | None:
        """Remove a tag from a note."""
        tags = self.get_tags(note)
        if tag in tags:
            tags.remove(tag)
            note.tags = ",".join(tags)
            return self.update_note(note)
        return note
