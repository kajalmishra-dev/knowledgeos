"""Offline retrieval-quality check for the default local embedding provider.

This is not a substitute for a labeled IR benchmark. It verifies that overlapping
factual phrases rank above unrelated jargon when using the hashing embedder.
"""

from __future__ import annotations

import pytest

from app.infrastructure.ai.embeddings.local import LocalEmbeddingProvider

CORPUS = {
    "france": "Paris is the capital of France and sits on the River Seine.",
    "germany": "Berlin is the capital of Germany and was divided during the Cold War.",
    "rag": "KnowledgeOS chunks documents, stores embeddings in pgvector, and cites sources.",
    "storage": "Original files are written to MinIO object storage before ingestion starts.",
}

QUERIES = [
    ("What is the capital of France?", "france"),
    ("capital of Germany", "germany"),
    ("Where are original files stored?", "storage"),
    ("How does KnowledgeOS cite sources?", "rag"),
]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


@pytest.mark.asyncio
async def test_local_retrieval_recall_at_1() -> None:
    provider = LocalEmbeddingProvider(256)
    doc_ids = list(CORPUS)
    doc_vectors = await provider.embed([CORPUS[doc_id] for doc_id in doc_ids])
    hits = 0
    for query, relevant in QUERIES:
        query_vector = (await provider.embed([query]))[0]
        ranked = sorted(
            zip(doc_ids, doc_vectors, strict=True),
            key=lambda item: _cosine(query_vector, item[1]),
            reverse=True,
        )
        if ranked[0][0] == relevant:
            hits += 1
    recall = hits / len(QUERIES)
    assert recall >= 0.75, f"recall@1={recall:.2f} hits={hits}/{len(QUERIES)}"
