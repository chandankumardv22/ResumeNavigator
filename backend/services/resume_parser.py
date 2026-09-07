"""
NLP Resume Parser (Technology #1)

Extracts structured information from PDF/DOCX resumes using:
  - Text extraction (pdfminer / pypdf / python-docx)
  - Text cleaning & normalization
  - Section-aware NLP heuristics
  - Regular expressions for contact fields
  - Lexicon / ontology matching for skills (via skills.py)

Produces a structured resume JSON — not Gemini, not TF-IDF.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from resume_nlp import clean_resume_text, extract_resume_text, extract_years_of_experience
from skills import detect_degrees, detect_domain, extract_professional_skills, DOMAIN_PROFILES  # noqa: F401


# ---------------------------------------------------------------------------
# Lexicons (NLP / rule-based — complement regex)
# ---------------------------------------------------------------------------
PROGRAMMING_LANGUAGES = {
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang",
    "rust", "kotlin", "swift", "ruby", "php", "scala", "r", "matlab", "perl", "dart",
    "html", "css", "sql", "bash", "shell", "powershell",
}

TOOLS_TECH = {
    "react", "angular", "vue", "node", "nodejs", "express", "django", "flask", "fastapi",
    "spring", "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "jenkins",
    "git", "github", "gitlab", "linux", "mongodb", "postgresql", "mysql", "redis",
    "elasticsearch", "kafka", "spark", "hadoop", "tensorflow", "pytorch", "keras",
    "scikit-learn", "pandas", "numpy", "tableau", "power bi", "excel", "figma",
    "jira", "ansible", "nginx", "graphql", "rest", "api", "ci/cd", "mlops",
}

CERT_MARKERS = (
    "certified", "certification", "certificate", "aws certified", "azure certified",
    "google cloud", "coursera", "udemy", "nptel", "compTIA", "pmp", "scrum",
)

SECTION_HEADERS = {
    "experience": ("experience", "work experience", "employment", "professional experience", "work history", "internship"),
    "education": ("education", "academic", "qualification", "academics"),
    "skills": ("skills", "technical skills", "core competencies", "technologies"),
    "projects": ("projects", "project work", "academic projects", "personal projects", "key projects"),
    "certifications": ("certifications", "certificates", "licenses", "achievements"),
    "summary": ("summary", "objective", "profile", "about me"),
}


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _looks_like_name(line: str) -> bool:
    if not line or len(line) > 55 or "@" in line or re.search(r"\d{5,}", line):
        return False
    lower = line.lower()
    if any(h in lower for headers in SECTION_HEADERS.values() for h in headers):
        return False
    if any(w in lower for w in ("university", "college", "institute", "resume", "curriculum")):
        return False
    words = line.split()
    if not (1 <= len(words) <= 5):
        return False
    if not all(re.match(r"^[A-Za-z][A-Za-z.'-]*$", w) for w in words):
        return False
    titled = sum(1 for w in words if w[0].isupper())
    return titled >= max(1, len(words) - 1)


def extract_name(text: str) -> str:
    for ln in _lines(text)[:12]:
        if _looks_like_name(ln):
            return ln
    email = extract_email(text)
    if email and "@" in email:
        local = re.sub(r"[._+\-0-9]+", " ", email.split("@")[0]).strip()
        parts = [p.capitalize() for p in local.split() if len(p) > 1]
        if parts:
            return " ".join(parts[:3])
    return ""


def extract_email(text: str) -> str:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    return m.group(0) if m else ""


def extract_phone(text: str) -> str:
    m = re.search(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,5}[\s\-]?\d{4,6}", text or "")
    if not m:
        m = re.search(r"(?:\+91[\-\s]?)?[6-9]\d{9}", text or "")
    return m.group(0).strip() if m else ""


def _split_sections(text: str) -> dict[str, str]:
    """Section-aware split using header lexicon (NLP heuristic, not pure regex)."""
    lines = _lines(text)
    sections: dict[str, list[str]] = {k: [] for k in SECTION_HEADERS}
    current = "summary"
    for ln in lines:
        lower = ln.lower().strip(" :|-")
        matched_section = None
        for key, headers in SECTION_HEADERS.items():
            if any(lower == h or lower.startswith(h + " ") or lower.endswith(h) for h in headers):
                if len(lower) < 48:
                    matched_section = key
                    break
        if matched_section:
            current = matched_section
            continue
        if current in sections:
            sections[current].append(ln)
    return {k: "\n".join(v) for k, v in sections.items()}


def _extract_education_entries(edu_text: str, full_text: str) -> list[dict[str, Any]]:
    degrees = detect_degrees((full_text or "").lower()) if detect_degrees else []
    entries: list[dict[str, Any]] = []
    for ln in _lines(edu_text)[:20]:
        lower = ln.lower()
        if any(k in lower for k in ("university", "college", "institute", "school", "b.tech", "b.e", "m.tech", "mba", "b.sc", "degree")):
            entries.append({"raw": ln})
    if not entries and degrees:
        entries = [{"degree": d} for d in degrees]
    elif degrees:
        for i, d in enumerate(degrees):
            if i < len(entries):
                entries[i]["degree"] = d
            else:
                entries.append({"degree": d})
    return entries


def _extract_certifications(text: str, cert_section: str) -> list[str]:
    found: list[str] = []
    blob = cert_section or text or ""
    for ln in _lines(blob):
        lower = ln.lower()
        if any(m in lower for m in CERT_MARKERS) or "certif" in lower:
            found.append(ln[:160])
    # Deduplicate
    out, seen = [], set()
    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out[:12]


def _extract_projects(proj_section: str, full_text: str) -> list[dict[str, str]]:
    projects: list[dict[str, str]] = []
    source = proj_section or ""
    if not source:
        # Fallback: lines after a "Projects" header already handled; scan bullets with tech verbs
        return projects
    for ln in _lines(source):
        if len(ln) < 8:
            continue
        if re.match(r"^[\-\*\u2022\d\.\)\(]+", ln) or ln[0].isupper():
            projects.append({"title": ln[:120], "description": ln})
    return projects[:10]


def _extract_experience_entries(exp_section: str) -> list[dict[str, Any]]:
    """Parse job titles / companies from experience section with NLP heuristics."""
    entries: list[dict[str, Any]] = []
    title_hints = (
        "engineer", "developer", "analyst", "intern", "manager", "consultant",
        "scientist", "architect", "lead", "associate", "trainee", "specialist",
    )
    company_hints = ("pvt", "ltd", "limited", "inc", "technologies", "solutions", "systems", "labs", "corp")
    for ln in _lines(exp_section):
        lower = ln.lower()
        is_title = any(h in lower for h in title_hints)
        is_company = any(h in lower for h in company_hints)
        date_m = re.search(
            r"((?:19|20)\d{2})\s*[-–—to]{1,3}\s*((?:19|20)\d{2}|present|current)",
            lower,
        )
        if is_title or is_company or date_m:
            entry: dict[str, Any] = {"raw": ln}
            if is_title:
                entry["job_title"] = ln.split("|")[0].split(",")[0].strip()[:80]
            if is_company:
                entry["company"] = ln[:100]
            if date_m:
                entry["duration"] = date_m.group(0)
            entries.append(entry)
    return entries[:15]


def _classify_skills(skills: list[str]) -> tuple[list[str], list[str], list[str]]:
    programming, tools, other = [], [], []
    for s in skills:
        key = s.lower().strip()
        if key in PROGRAMMING_LANGUAGES or any(p == key for p in PROGRAMMING_LANGUAGES):
            programming.append(s)
        elif key in TOOLS_TECH or any(t in key for t in TOOLS_TECH):
            tools.append(s)
        else:
            other.append(s)
    return programming, tools, other


def parse_resume_structured(text: str) -> dict[str, Any]:
    """
    Full NLP structured parse → canonical resume JSON.
    Uses section detection + lexicons + regex (not Gemini / not TF-IDF).
    """
    cleaned = clean_resume_text(text)
    domain = detect_domain(cleaned) if detect_domain else "General / Fresher"
    sections = _split_sections(cleaned)

    skills = []
    if extract_professional_skills:
        skills = extract_professional_skills(cleaned, domain)
    # Augment from skills section tokens
    for token in re.findall(r"[A-Za-z][A-Za-z0-9+.#\-]{1,24}", sections.get("skills", "")):
        if token.lower() in PROGRAMMING_LANGUAGES or token.lower() in TOOLS_TECH:
            if token not in skills:
                skills.append(token)

    programming, tools, other_skills = _classify_skills(skills)
    education = _extract_education_entries(sections.get("education", ""), cleaned)
    degrees = detect_degrees(cleaned.lower()) if detect_degrees else []
    certifications = _extract_certifications(cleaned, sections.get("certifications", ""))
    projects = _extract_projects(sections.get("projects", ""), cleaned)
    experience = _extract_experience_entries(sections.get("experience", ""))
    total_experience = extract_years_of_experience(cleaned)

    job_titles = [e.get("job_title") for e in experience if e.get("job_title")]
    companies = [e.get("company") for e in experience if e.get("company")]

    return {
        "name": extract_name(cleaned),
        "email": extract_email(cleaned),
        "phone": extract_phone(cleaned),
        "skills": skills[:40],
        "programming_languages": programming[:20],
        "tools_technologies": tools[:25],
        "other_skills": other_skills[:20],
        "education": education,
        "degrees": degrees,
        "certifications": certifications,
        "projects": projects,
        "experience": experience,
        "job_titles": job_titles[:10],
        "companies": companies[:10],
        "total_experience": total_experience,
        "detected_domain": domain,
        "raw_text_preview": cleaned[:1500],
        "sections_found": [k for k, v in sections.items() if v.strip()],
        "algorithm": "Natural Language Processing (section heuristics + lexicon + regex)",
    }


def parse_resume_file(path: str) -> dict[str, Any]:
    text = extract_resume_text(path)
    if not text or len(text.strip()) < 35:
        raise ValueError("Unable to extract usable text from the resume. Upload a text-based PDF or DOCX.")
    parsed = parse_resume_structured(text)
    parsed["raw_text"] = text
    return parsed
