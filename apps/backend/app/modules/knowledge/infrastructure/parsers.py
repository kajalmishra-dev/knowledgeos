from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.core.exceptions import AppError


class ParseError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


def parse_document(*, data: bytes, source_type: str, filename: str) -> str:
    if source_type == "pdf":
        return _parse_pdf(data, filename)
    if source_type == "docx":
        return _parse_docx(data, filename)
    if source_type in {"markdown", "text"}:
        return _parse_text(data, filename)
    raise ParseError(f"Unsupported source type '{source_type}'.")


def _parse_pdf(data: bytes, filename: str) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ParseError(f"Could not read PDF '{filename}'.") from exc

    if getattr(reader, "is_encrypted", False):
        raise ParseError(f"Encrypted PDFs are not supported ({filename}).")

    pages: list[str] = []
    try:
        for page in reader.pages:
            pages.append(page.extract_text() or "")
    except Exception as exc:
        raise ParseError(f"Could not extract text from PDF '{filename}'.") from exc
    return "\n\n".join(part.strip() for part in pages if part and part.strip())


def _parse_docx(data: bytes, filename: str) -> str:
    try:
        from docx import Document as DocxDocument
    except ImportError as exc:
        raise ParseError("DOCX support is not installed.") from exc

    try:
        document = DocxDocument(BytesIO(data))
    except Exception as exc:
        raise ParseError(f"Could not read DOCX '{filename}'.") from exc
    return "\n".join(
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    )


def _parse_text(data: bytes, filename: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError(f"File '{filename}' is not valid UTF-8 text.") from exc
