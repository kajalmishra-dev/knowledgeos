# Ingestion pipeline

KnowledgeOS stores uploaded files in MinIO.

The worker parses PDF, Markdown, TXT, and DOCX files, chunks the text, generates
embeddings, and writes vectors into PostgreSQL with pgvector.
