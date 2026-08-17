from __future__ import annotations

import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


def _tokens(text: str) -> list[str]:
    words = [word for word in _TOKEN_RE.findall(text.lower()) if word not in _STOPWORDS]
    grams: list[str] = []
    for word in words:
        if len(word) >= 3:
            grams.extend(word[i : i + 3] for i in range(len(word) - 2))
    return words + grams


class LocalEmbeddingProvider:
    """Deterministic hashing embeddings so the system runs without an API key.

    This is not a substitute for a neural embedding model. Overlapping tokens
    produce closer vectors, which is enough for demos and tests. Set
    EMBEDDING_PROVIDER=openai for production-quality retrieval.
    """

    name = "local"

    def __init__(self, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive.")
        self._dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, 32, 4):
                bucket = int.from_bytes(digest[offset : offset + 4], "big") % self._dimensions
                sign = 1.0 if digest[offset] % 2 == 0 else -1.0
                vector[bucket] += sign
        return _l2_normalize(vector)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
