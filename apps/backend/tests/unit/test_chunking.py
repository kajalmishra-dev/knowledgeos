from app.modules.knowledge.application.chunking import chunk_text


def test_short_text_is_single_chunk() -> None:
    assert chunk_text("hello world", chunk_size=800, overlap=150) == ["hello world"]


def test_chunking_splits_and_overlaps() -> None:
    text = ("alpha " * 40 + "\n\n" + "bravo " * 40).strip()
    chunks = chunk_text(text, chunk_size=80, overlap=20)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("   \n\n  ", chunk_size=800, overlap=150) == []
