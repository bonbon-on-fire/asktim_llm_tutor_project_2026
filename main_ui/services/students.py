"""Student identity (username + password) helpers.

Not a real auth system — just enough to stop someone who knows another
student's username from claiming their chat history on a different browser.
The browser cookie (`tutor_username`) remains the day-to-day session-identity
carrier; the password is checked exactly once, when a username is first
linked to a session.
"""

from __future__ import annotations

import bcrypt
from sqlalchemy.orm import Session

from main_ui.db.models import Student


MIN_PASSWORD_LENGTH = 6


class WeakPasswordError(Exception):
    """Raised when a chosen password fails the minimum-length rule."""


def get_student(db: Session, username: str) -> Student | None:
    """Return the Student row for the given username, or None if absent."""
    return db.get(Student, username)


def create_student(db: Session, *, username: str, password: str) -> Student:
    """Insert a new students row with the password hashed via bcrypt.

    Raises:
        WeakPasswordError: if ``password`` is shorter than the minimum.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    student = Student(username=username, password_hash=hashed)
    db.add(student)
    db.flush()
    return student


def verify_password(student: Student, password: str) -> bool:
    """Constant-time check that ``password`` matches the stored hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), student.password_hash.encode("ascii")
        )
    except (ValueError, TypeError):
        return False
