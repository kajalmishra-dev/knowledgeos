from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.modules.knowledge.infrastructure.parsers import ParseError, parse_document


def test_parse_markdown() -> None:
    text = parse_document(data=b"# Title\nHello", source_type="markdown", filename="note.md")
    assert "Hello" in text


def test_parse_invalid_utf8() -> None:
    with pytest.raises(ParseError):
        parse_document(data=b"\xff\xfe\x00", source_type="text", filename="note.txt")


def test_parse_unsupported_type() -> None:
    with pytest.raises(ParseError):
        parse_document(data=b"x", source_type="mp3", filename="a.mp3")


def test_parse_pdf_does_not_crash() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    data = buffer.getvalue()
    assert data[:4] == b"%PDF"
    try:
        parse_document(data=data, source_type="pdf", filename="blank.pdf")
    except ParseError:
        pass


def test_parse_docx() -> None:
    from docx import Document as DocxDocument

    document = DocxDocument()
    document.add_paragraph("Paris is the capital of France.")
    buffer = BytesIO()
    document.save(buffer)
    text = parse_document(data=buffer.getvalue(), source_type="docx", filename="notes.docx")
    assert "Paris" in text
