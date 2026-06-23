"""Sentence-aware chunking of source documents into retrievable pieces.

Splits text on paragraph then sentence boundaries and greedily packs sentences
into ~``target_chars`` chunks with a trailing ``overlap_chars`` carry-over so a
fact that straddles a boundary still appears whole in one chunk. Character-based
sizing keeps this dependency-free; ~2400 chars ≈ ~600 tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Sentence boundary: end punctuation followed by whitespace.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
# Blank-line paragraph boundary.
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


@dataclass
class Chunk:
    """One retrievable piece of a source document."""

    text: str
    source: str  # label, e.g. "local:lecture_08_01_..." or "ocw:pages/syllabus"
    course: str
    index: int  # position of this chunk within its source


def _sentences(text: str) -> list[str]:
    """Split *text* into sentences, respecting paragraph boundaries first."""
    out: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT.split(text.strip()):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for sentence in _SENTENCE_SPLIT.split(paragraph):
            sentence = sentence.strip()
            if sentence:
                out.append(sentence)
    return out


def chunk_document(
    text: str,
    source: str,
    course: str,
    *,
    target_chars: int = 2400,
    overlap_chars: int = 300,
) -> list[Chunk]:
    """Chunk one document into overlapping, sentence-aligned :class:`Chunk`s."""
    sentences = _sentences(text)
    if not sentences:
        return []

    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0
    idx = 0

    for sentence in sentences:
        # Flush when adding this sentence would overflow the target (but keep at
        # least one sentence per chunk, so an over-long sentence stands alone).
        if current and current_len + len(sentence) + 1 > target_chars:
            chunks.append(
                Chunk(text=" ".join(current).strip(), source=source, course=course, index=idx)
            )
            idx += 1
            # Carry a tail of sentences (up to overlap_chars) into the next chunk.
            carry: list[str] = []
            carry_len = 0
            for prev in reversed(current):
                if carry_len + len(prev) + 1 > overlap_chars:
                    break
                carry.insert(0, prev)
                carry_len += len(prev) + 1
            current = carry
            current_len = sum(len(s) + 1 for s in current)

        current.append(sentence)
        current_len += len(sentence) + 1

    if current:
        chunks.append(
            Chunk(text=" ".join(current).strip(), source=source, course=course, index=idx)
        )
    return chunks
