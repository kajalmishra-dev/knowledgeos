from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"[ \t]+")


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph then sentence breaks.

    Defaults used in production: chunk_size=800, overlap=150. Overlap preserves
    sentences that would otherwise be cut at a window boundary, which improves
    embedding quality for short factual passages.
    """
    normalized = _normalize(text)
    if not normalized:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            end = _choose_break(normalized, start, end)
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _choose_break(text: str, start: int, end: int) -> int:
    window = text[start:end]
    for separator in ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "):
        index = window.rfind(separator)
        if index >= int(len(window) * 0.4):
            return start + index + len(separator)
    return end
