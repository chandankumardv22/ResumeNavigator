from __future__ import annotations

import re

from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdfminer.layout import LAParams

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def _normalize(text: str) -> str:
    if not text:
        return ""
    cleaned = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_pdfminer(path: str, laparams: LAParams | None = None) -> str:
    try:
        if laparams:
            return pdfminer_extract_text(path, laparams=laparams) or ""
        return pdfminer_extract_text(path) or ""
    except Exception:
        return ""


def _extract_pypdf(path: str) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(path)
        chunks: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                chunks.append(page_text)
        return "\n".join(chunks)
    except Exception:
        return ""


def extract_pdf_text(path: str) -> str:
    candidates = [
        _extract_pdfminer(path),
        _extract_pdfminer(path, LAParams(all_texts=True, line_margin=0.12, word_margin=0.08)),
        _extract_pypdf(path),
    ]
    best = ""
    for raw in candidates:
        normalized = _normalize(raw)
        if len(normalized) > len(best):
            best = normalized
    return best
