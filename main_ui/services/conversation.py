"""Conversation persistence helpers.

The one place that creates / resolves / appends to `Conversation` and
`Message` rows. Route handlers call these helpers; they never construct DB
models inline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from main_ui.db.models import Conversation, Message


class WrongSessionError(Exception):
    """Raised when a request supplies a conversation_id that isn't owned by
    the current session_id (or doesn't exist at all)."""


def find_or_create_conversation(
    db: Session,
    *,
    session_id: str,
    conversation_id: UUID | None,
    course: str,
    exercise_number: str,
    tutor_prompt: str,
    email: str | None = None,
) -> Conversation:
    """Resolve to an existing conversation or insert a new one.

    Raises:
        WrongSessionError: if `conversation_id` was provided but either
            doesn't exist or belongs to a different session.
    """
    if conversation_id is not None:
        existing = db.get(Conversation, conversation_id)
        if existing is None or existing.session_id != session_id:
            raise WrongSessionError()
        return existing

    convo = Conversation(
        session_id=session_id,
        email=email,
        course=course,
        exercise_number=exercise_number,
        tutor_prompt=tutor_prompt,
    )
    db.add(convo)
    db.flush()  # populate convo.id before the caller uses it
    return convo


def append_exchange(
    db: Session,
    *,
    conversation: Conversation,
    student_text: str,
    tutor_text: str,
    pedagogical_reasoning: str | None,
) -> tuple[Message, Message]:
    """Insert the student/tutor message pair for the next turn.

    Both messages share a single turn number (1-indexed). Bumps
    `conversation.last_active_at`.
    """
    next_turn = _next_turn_number(db, conversation)

    student_msg = Message(
        conversation_id=conversation.id,
        turn=next_turn,
        role="student",
        content=student_text,
    )
    tutor_msg = Message(
        conversation_id=conversation.id,
        turn=next_turn,
        role="tutor",
        content=tutor_text,
        pedagogical_reasoning=pedagogical_reasoning,
    )
    db.add(student_msg)
    db.add(tutor_msg)
    conversation.last_active_at = datetime.now(timezone.utc)
    db.flush()
    return student_msg, tutor_msg


def get_history_for_tutor(db: Session, conversation: Conversation) -> list[dict]:
    """Return prior messages as [{role, content}, ...] in chronological order.

    Shape matches what `tutor_bridge.get_tutor_reply` expects, so callers can
    pass the result straight through.
    """
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.turn, Message.id)
    )
    return [
        {"role": m.role, "content": m.content}
        for m in db.execute(stmt).scalars().all()
    ]


def count_student_messages(db: Session, conversation: Conversation) -> int:
    """Number of student-role messages in this conversation.

    Step 7's email modal triggers when this reaches 3.
    """
    stmt = (
        select(func.count(Message.id))
        .where(Message.conversation_id == conversation.id)
        .where(Message.role == "student")
    )
    return int(db.execute(stmt).scalar_one())


def backfill_email_for_session(
    db: Session, session_id: str, email: str
) -> int:
    """Set `email` on every Conversation row for this session that doesn't
    already have one. Returns the number of rows touched.

    Used by Step 7's email modal to retroactively link anonymous
    conversations to a student once they provide their email.
    """
    stmt = (
        update(Conversation)
        .where(Conversation.session_id == session_id)
        .where(Conversation.email.is_(None))
        .values(email=email)
        .execution_options(synchronize_session="fetch")
    )
    result = db.execute(stmt)
    db.flush()
    return int(result.rowcount or 0)


def _next_turn_number(db: Session, conversation: Conversation) -> int:
    stmt = select(func.max(Message.turn)).where(
        Message.conversation_id == conversation.id
    )
    current_max = db.execute(stmt).scalar_one()
    return (current_max or 0) + 1
