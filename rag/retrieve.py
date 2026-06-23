"""Query-time retrieval over a per-course RAG index.

Loads the course's numpy index (cached in-process), embeds the student query,
and returns the most relevant chunks under a character budget. ``format_context``
renders them into the block that tutor_bridge injects on the latest student turn.
"""

from __future__ import annotations

from rag.chunking import Chunk
from rag.embeddings import embed_query
from rag.store import NumpyVectorStore

# Per-course store cache so we load each index from disk only once per process.
_STORE_CACHE: dict[str, NumpyVectorStore | None] = {}


def _get_store(course: str) -> NumpyVectorStore | None:
    if course not in _STORE_CACHE:
        _STORE_CACHE[course] = NumpyVectorStore.load(course)
    return _STORE_CACHE[course]


def has_index(course: str) -> bool:
    """True if a built RAG index exists for *course*."""
    return _get_store(course) is not None


def retrieve(course: str, query: str, *, k: int = 6, max_chars: int = 12000) -> list[Chunk]:
    """Return up to *k* relevant chunks for *query*, capped at *max_chars* total.

    Returns ``[]`` when there's no index or the query is empty — callers fall
    back to their non-RAG context path.
    """
    store = _get_store(course)
    if store is None or not query.strip():
        return []
    hits = store.search(embed_query(query), k)
    out: list[Chunk] = []
    total = 0
    for chunk, _score in hits:
        if out and total + len(chunk.text) > max_chars:
            break
        out.append(chunk)
        total += len(chunk.text)
    return out


def format_context(chunks: list[Chunk]) -> str:
    """Render retrieved chunks into a labeled 'Relevant course material' block."""
    if not chunks:
        return ""
    blocks = [f"[{c.source}]\n{c.text}" for c in chunks]
    return "Relevant course material (retrieved):\n\n" + "\n\n".join(blocks)
