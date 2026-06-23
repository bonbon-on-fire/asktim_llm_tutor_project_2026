"""Retrieval-Augmented Generation over course materials.

Phase 11 (see root ``PLANNING.md``). Ingests course-level material — course
description, syllabus, lectures, readings — from either the local curriculum
files or the course's OCW site (toggle), embeds it into a per-course numpy
vector index under ``curriculum/<course>/rag_index/``, and retrieves only the
top-k chunks relevant to a student turn at tutor-call time. The exercise prompt
and figures are deliberately NOT ingested — they stay local/always-in-context.

Public API:
    from rag import retrieve, format_context, has_index
"""

from __future__ import annotations

from rag.chunking import Chunk
from rag.retrieve import format_context, has_index, retrieve

__all__ = ["Chunk", "retrieve", "format_context", "has_index"]
