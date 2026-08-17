"""Shared constants that must stay in sync with the database schema."""

# pgvector column size for document_chunks.embedding.
# Changing this requires a new Alembic migration.
EMBEDDING_DIMENSIONS = 1536
