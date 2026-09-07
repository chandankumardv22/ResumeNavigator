"""NLP resume parsing — PDF / DOCX text extraction and rule-based field extraction.

Algorithm stack #1 (Natural Language Processing):
  * Extract unstructured text from uploaded PDF and Word (.docx) resumes
  * Clean / normalize text
  * Extract skills, academic degrees, and years of experience via custom rules + regex
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pdf_parser import extract_pdf_text

Document = None
try:
    import importlib
    _docx = importlib.import_module("docx")
    Document = getattr(_docx, "Document")
except Exception:
    Document = None

try:
    from skills import detect_degrees, extract_professional_skills, detect_domain
except ImportError:  # pragma: no cover
    detect_degrees = None  # type: ignore
    extract_professional_skills = None  # type: ignore
    detect_domain = None  # type: ignore


def clean_resume_text(text: str) -> str:
    """Clean extracted resume text for downstream NLP / ML stages."""
    if not text:
        return ""
    cleaned = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    cleaned = cleaned.replace("\x00", " ")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[^\S\n]+", " ", cleaned)
    return cleaned.strip()


def extract_docx_text(path: str) -> str:
    if Document is None:
        raise RuntimeError("python-docx is not installed; cannot parse .docx resumes.")
    doc = Document(path)
    parts = [para.text for para in doc.paragraphs if para.text and para.text.strip()]
    # Also pull simple table cells (common in Word resume templates).
    for table in getattr(doc, "tables", []) or []:
        for row in table.rows:
            for cell in row.cells:
                cell_text = (cell.text or "").strip()
                if cell_text:
                    parts.append(cell_text)
    return clean_resume_text("\n".join(parts))


def extract_resume_text(path: str) -> str:
    """Extract and clean text from a PDF or DOCX resume path."""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return clean_resume_text(extract_pdf_text(path))
    if suffix in {".docx", ".doc"}:
        if suffix == ".doc":
            raise ValueError("Legacy .doc is not supported. Please upload PDF or .docx.")
        return extract_docx_text(path)
    raise ValueError(f"Unsupported resume format: {suffix or 'unknown'}")


_EXPERIENCE_PATTERNS = (
    re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs)\s*(?:of\s+)?(?:experience|exp\.?)?", re.I),
    re.compile(r"(?:experience|exp\.?)\s*(?:of\s*)?(\d+)\s*\+?\s*(?:years?|yrs)", re.I),
    re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs)\s*(?:in|as)\b", re.I),
)


def extract_years_of_experience(text: str) -> int:
    """Extract total years of work experience using regex pattern matching."""
    years: list[int] = []
    for pattern in _EXPERIENCE_PATTERNS:
        for match in pattern.finditer(text or ""):
            try:
                years.append(int(match.group(1)))
            except (TypeError, ValueError, IndexError):
                continue
    if not years:
        return 0
    # Cap absurd OCR/noise values.
    return min(max(years), 40)


def extract_academic_degrees(text: str) -> list[str]:
    """Extract academic degrees via the shared degree rule engine."""
    lower = (text or "").lower()
    if detect_degrees is not None:
        return detect_degrees(lower)
    # Minimal fallback if skills.py is unavailable.
    simple = ["b.tech", "b.e", "m.tech", "mba", "b.sc", "m.sc", "mca", "bca", "phd", "diploma"]
    return [d for d in simple if d in lower]


def nlp_parse_resume(text: str, domain: str | None = None) -> dict[str, Any]:
    """Run the NLP parsing phase over already-extracted resume text."""
    cleaned = clean_resume_text(text)
    resolved_domain = domain
    if not resolved_domain and detect_domain is not None:
        resolved_domain = detect_domain(cleaned)
    resolved_domain = resolved_domain or "General / Fresher"

    skills: list[str] = []
    if extract_professional_skills is not None:
        skills = extract_professional_skills(cleaned, resolved_domain)

    degrees = extract_academic_degrees(cleaned)
    years = extract_years_of_experience(cleaned)
    return {
        "cleaned_text": cleaned,
        "skills": skills,
        "academic_degrees": degrees,
        "years_of_experience": years,
        "detected_domain": resolved_domain,
        "algorithm": "Natural Language Processing (rules + regex)",
    }
