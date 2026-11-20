import io
import pathlib

from docx import Document
from pypdf import PdfReader

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


def extract_text(name: str, data: bytes) -> str:
    """Return plain text from PDF/DOCX/TXT bytes. Returns '' if unreadable (e.g. scanned PDF)."""
    ext = pathlib.Path(name).suffix.lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        if ext == ".docx":
            return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""
