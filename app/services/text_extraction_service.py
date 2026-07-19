from io import BytesIO
from pathlib import Path


SUPPORTED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/x-markdown": "md",
}

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
}


class TextExtractionError(Exception):
    pass


def detect_document_type(filename: str, content_type: str | None) -> str:
    normalized_content_type = (content_type or "").split(";")[0].lower()
    if normalized_content_type in SUPPORTED_CONTENT_TYPES:
        return SUPPORTED_CONTENT_TYPES[normalized_content_type]

    suffix = Path(filename).suffix.lower()
    if suffix in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[suffix]

    raise TextExtractionError("Unsupported document type")


def extract_text(
    file_bytes: bytes,
    filename: str,
    content_type: str | None,
) -> tuple[str, dict]:
    document_type = detect_document_type(filename, content_type)

    if document_type == "pdf":
        return _extract_pdf_text(file_bytes)

    if document_type == "docx":
        return _extract_docx_text(file_bytes)

    return _extract_plain_text(file_bytes, document_type)


def _extract_pdf_text(file_bytes: bytes) -> tuple[str, dict]:
    try:
        import fitz
    except ImportError as exc:
        raise TextExtractionError("PDF parsing dependency is not installed") from exc

    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as document:
            pages = [page.get_text().strip() for page in document]
            text = "\n\n".join(page for page in pages if page)
            metadata = {
                "document_type": "pdf",
                "page_count": document.page_count,
                "title": document.metadata.get("title") or None,
                "author": document.metadata.get("author") or None,
            }
    except Exception as exc:
        raise TextExtractionError("Failed to parse PDF") from exc

    return text, metadata


def _extract_docx_text(file_bytes: bytes) -> tuple[str, dict]:
    try:
        from docx import Document as DocxDocument
    except ImportError as exc:
        raise TextExtractionError("DOCX parsing dependency is not installed") from exc

    try:
        document = DocxDocument(BytesIO(file_bytes))
        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
    except Exception as exc:
        raise TextExtractionError("Failed to parse DOCX") from exc

    return "\n\n".join(paragraphs), {
        "document_type": "docx",
        "paragraph_count": len(paragraphs),
    }


def _extract_plain_text(
    file_bytes: bytes,
    document_type: str,
) -> tuple[str, dict]:
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TextExtractionError("Text file must be UTF-8 encoded") from exc

    return text, {
        "document_type": document_type,
        "line_count": len(text.splitlines()),
    }
