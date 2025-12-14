"""
Example models for the database.
"""

from dataclasses import dataclass

from xiaozhi_mcp.database import BaseModel


@dataclass
class User(BaseModel):
    """User model example."""

    name: str = ""
    email: str = ""
    age: int = 0


@dataclass
class Task(BaseModel):
    """Task model example."""

    title: str = ""
    description: str = ""
    completed: bool = False
    user_id: int = 0


@dataclass
class Note(BaseModel):
    """Note model for storing notes."""

    title: str = ""
    content: str = ""
    created_at: str = ""
    updated_at: str = ""
    tags: str = ""  # comma-separated tags
