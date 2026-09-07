# Copyright (c) 2026 chandankumardv22
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (OSError, ValueError, AttributeError):
        pass


def _log(msg: object) -> None:
    try:
        line = f"{msg}\n".encode("utf-8", errors="replace")
        sys.stderr.buffer.write(line)
        sys.stderr.buffer.flush()
    except Exception:
        pass


import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from pathlib import Path
from pydantic import BaseModel, Field

# Support both `uvicorn backend.main:app` (package mode) and the existing
# quick-start launcher, which runs `uvicorn main:app` from backend/.
try:
    from .pdf_parser import extract_pdf_text
    from .skills import (
        DOMAIN_PROFILES, _NON_RESUME_SIGNALS, _RESUME_SIGNALS,
        analyze_for_target_role, compute_missing_skills, detect_domain,
        extract_professional_skills, infer_roles_from_skills,
        merge_recommended_roles, sanitize_skills,
    )
except ImportError:  # pragma: no cover - used only when launched from backend/
    from pdf_parser import extract_pdf_text
    from skills import (
        DOMAIN_PROFILES, _NON_RESUME_SIGNALS, _RESUME_SIGNALS,
        analyze_for_target_role, compute_missing_skills, detect_domain,
        extract_professional_skills, infer_roles_from_skills,
        merge_recommended_roles, sanitize_skills,
    )

try:
    try:
        from .resume_nlp import extract_resume_text, nlp_parse_resume
        from .role_predictor import predict_job_role, role_predictor_status
    except ImportError:
        from resume_nlp import extract_resume_text, nlp_parse_resume
        from role_predictor import predict_job_role, role_predictor_status
except Exception as _algo_exc:  # pragma: no cover
    _log(f"[algorithms] resume_nlp/role_predictor unavailable: {_algo_exc!r}")

    def extract_resume_text(path: str) -> str:
        return extract_pdf_text(path)

    def nlp_parse_resume(text: str, domain: str | None = None) -> dict[str, Any]:
        return {
            "cleaned_text": text,
            "skills": [],
            "academic_degrees": [],
            "years_of_experience": 0,
            "detected_domain": domain or "General / Fresher",
            "algorithm": "Natural Language Processing (rules + regex)",
        }

    def predict_job_role(resume_text: str, matched_skills: list[str] | None = None) -> dict[str, Any]:
        return {"predicted_role": None, "confidence": 0.0, "available": False, "algorithm": "TF-IDF + Logistic Regression"}

    def role_predictor_status() -> dict[str, Any]:
        return {"available": False, "algorithm": "TF-IDF + Logistic Regression"}

# The NLP engine is optional and may pull in heavy libraries. It must NEVER be
# able to prevent the API from starting, so any failure here falls back to
# lightweight scoring instead of crashing the process.
try:
    try:
        from .nlp_engine import (
            compute_ats, engine_capabilities, extract_semantic_skills,
            semantic_match_skills,
        )
    except ImportError:
        from nlp_engine import (
            compute_ats, engine_capabilities, extract_semantic_skills,
            semantic_match_skills,
        )
except Exception as _nlp_exc:  # pragma: no cover - defensive
    _log(f"[nlp] engine unavailable ({type(_nlp_exc).__name__}: {_nlp_exc!r}); using lightweight fallback.")

    def engine_capabilities() -> dict[str, Any]:
        return {
            "embeddings": False, "embedding_model": "n/a", "spacy_ner": False,
            "tfidf": False, "bm25": False, "fuzzy": False, "readability": False,
            "note": "NLP engine failed to load; using ontology fallback.",
        }

    def extract_semantic_skills(text: str, domain: str, limit: int = 30) -> list[str]:
        return extract_professional_skills(text, domain)[:limit]

    def semantic_match_skills(resume_text: str, required_skills, threshold=None) -> dict[str, Any]:
        lower = (resume_text or "").lower()
        matched, missing = [], []
        for s in required_skills:
            s = str(s).strip()
            if s and s.lower() in lower:
                matched.append({"skill": s, "method": "exact", "confidence": 0.9, "evidence": f"'{s}' found in resume"})
            elif s:
                missing.append({"skill": s, "confidence": 0.0})
        return {"matched": matched, "missing": missing}

    def compute_ats(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        # Signals _build_scorecard to use its own minimal deterministic fallback.
        raise RuntimeError("nlp_engine unavailable")

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "jsearch.p.rapidapi.com").strip()
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "").strip()
JOBS_PER_ROLE = 20
JOB_API_TIMEOUT = 5
MAX_JOB_ROLES = 5
INVALID_PDF_TEXT_ERROR = (
    "Unable to read text from this resume. It may be scanned or image-only. "
    "Please upload a text-based PDF or Word (.docx) exported from Word, Google Docs, or a resume builder."
)
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx"}
_PLACEHOLDER_KEYS = {
    "your_gemini_api_key",
    "your_rapidapi_key",
    "your_adzuna_app_id",
    "your_adzuna_app_key",
}


def _is_real_key(value: str | None) -> bool:
    key = (value or "").strip()
    if len(key) < 12:
        return False
    return key.lower() not in _PLACEHOLDER_KEYS and not key.lower().startswith("your_")


_genai_client = (
    genai.Client(api_key=GEMINI_API_KEY.strip())
    if _is_real_key(GEMINI_API_KEY)
    else None
)
if _genai_client is None:
    _log("[gemini] GEMINI_API_KEY missing or invalid. Gemini functionality disabled.")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]

# Also accept the frontend when it is served from any LAN IP / hostname on a
# common dev port (e.g. http://10.196.2.110:3000 when testing across devices).
# The app uses no cookies/session auth, so echoing the specific origin here is
# safe. Using a regex (not "*") keeps allow_credentials working.
ALLOWED_ORIGIN_REGEX = r"https?://[A-Za-z0-9.\-]+(:(3000|3001|3002))?$"

INVALID_RESUME_ERROR = "Invalid document type. Please upload a valid resume."

app = FastAPI(title="PathFinder API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ATS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_valid_resume": {"type": "boolean"},
        "error": {"type": "string"},
        "detected_domain": {"type": "string"},
        "ats_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "predicted_role": {"type": "string"},
        "recommended_roles": {"type": "array", "items": {"type": "string"}},
        "matched_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "learning_roadmap": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "integer"},
                    "title": {"type": "string"},
                    "focus": {"type": "string"},
                    "project_idea": {"type": "string"},
                },
                "required": ["step", "title", "focus", "project_idea"],
            },
        },
        "custom_suggestion": {"type": "string"},
        "career_suggestions": {"type": "string"},
    },
    "required": ["is_valid_resume"],
}

class FetchJobsRequest(BaseModel):
    recommended_roles: list[str] = Field(default_factory=list)
    matched_skills: list[str] | None = Field(default=None)
    jobs_per_role: int = Field(default=JOBS_PER_ROLE)
    candidate_location: str | None = Field(default=None, max_length=120)


class ApplyJobRequest(BaseModel):
    """Record that the candidate started an application for a skill-matched opening."""
    job_title: str = Field(min_length=1, max_length=200)
    company_name: str = Field(default="Hiring Company", max_length=200)
    redirect_url: str = Field(min_length=5, max_length=2000)
    role_category: str | None = Field(default=None, max_length=120)
    skill_match_pct: int | None = Field(default=None, ge=0, le=100)
    matched_skills: list[str] | None = Field(default=None)
    candidate_name: str | None = Field(default=None, max_length=120)
    candidate_email: str | None = Field(default=None, max_length=200)

class ResumeTextRequest(BaseModel):
    """Used by interactive intelligence tools after a resume has been parsed."""
    resume_text: str = Field(min_length=35, max_length=50000)
    target_role: str | None = Field(default=None, max_length=120)


class RoleAnalysisRequest(BaseModel):
    """Used by the Role Explorer to analyze resume skills against a target role."""
    resume_text: str = Field(min_length=35, max_length=50000)
    target_role: str = Field(min_length=1, max_length=120)


class JobMatchRequest(ResumeTextRequest):
    job_description: str = Field(min_length=35, max_length=50000)


def _normalize_resume_text(text: str) -> str:
    if not text:
        return ""
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace").strip()


def _job_record(
    role_category: str,
    company_name: str,
    job_title: str,
    location: str,
    redirect_url: str,
    employment_type: str = "Full-time",
    source: str = "Job provider",
    tags: list[str] | None = None,
    description: str = "",
) -> dict[str, Any]:
    url = redirect_url or "#"
    return {
        "role_category": role_category,
        "company_name": company_name,
        "job_title": job_title,
        "location": location,
        "redirect_url": url,
        "employer_name": company_name,
        "job_apply_link": url,
        "job_employment_type": employment_type,
        "source": source,
        "tags": [str(t).strip() for t in (tags or []) if str(t).strip()][:12],
        "description": (description or "")[:600],
        "skill_match_pct": 0,
        "matched_skills": [],
    }


def _score_job_against_skills(job: dict[str, Any], skills: list[str] | None) -> dict[str, Any]:
    """Rank a listing by overlap between the candidate's matched skills and the job text."""
    skill_list = [str(s).strip() for s in (skills or []) if str(s).strip()]
    if not skill_list:
        job["skill_match_pct"] = 50
        job["matched_skills"] = []
        return job

    haystack = " ".join(
        [
            str(job.get("job_title") or ""),
            str(job.get("company_name") or ""),
            str(job.get("role_category") or ""),
            str(job.get("description") or ""),
            " ".join(job.get("tags") or []),
            str(job.get("source") or ""),
        ]
    ).lower()

    hits: list[str] = []
    for skill in skill_list:
        token = skill.lower().strip()
        if len(token) < 2:
            continue
        # Prefer whole-token / phrase hits so short skills (e.g. "C") don't false-positive.
        if token in haystack or all(part in haystack for part in token.replace("/", " ").split() if len(part) > 1):
            hits.append(skill)

    denom = min(8, max(len(skill_list), 1))
    pct = int(round(100 * min(len(hits), denom) / denom))
    if hits and pct < 35:
        pct = 35
    job["skill_match_pct"] = pct
    job["matched_skills"] = hits[:8]
    return job


def _annotate_and_rank_jobs(
    jobs: list[dict[str, Any]],
    skills: list[str] | None,
) -> list[dict[str, Any]]:
    ranked = [_score_job_against_skills(dict(job), skills) for job in jobs]
    # Real listings first, then portal searches; within each group, highest skill match.
    ranked.sort(
        key=lambda j: (
            0 if str(j.get("job_employment_type") or "").lower() != "search" else 1,
            -int(j.get("skill_match_pct") or 0),
            str(j.get("job_title") or "").lower(),
        )
    )
    return ranked


def _is_direct_apply_job(job: dict[str, Any]) -> bool:
    """Only keep listings with a real http(s) apply link (not portal search cards)."""
    url = str(job.get("redirect_url") or job.get("job_apply_link") or "").strip()
    if not url.startswith(("http://", "https://")):
        return False
    employment = str(job.get("job_employment_type") or "").lower()
    source = str(job.get("source") or "").lower()
    if employment == "search" or source.endswith("search"):
        return False
    return True


# Canonical Indian cities -> aliases used on resumes and job boards.
_CITY_ALIASES: dict[str, tuple[str, ...]] = {
    "Bengaluru": ("bengaluru", "bangalore", "blr", "bengalooru"),
    "Mumbai": ("mumbai", "bombay", "navi mumbai", "thane", "navi-mumbai"),
    "Delhi": ("delhi", "new delhi", "ncr", "delhi ncr"),
    "Gurugram": ("gurugram", "gurgaon"),
    "Noida": ("noida", "greater noida"),
    "Hyderabad": ("hyderabad", "secunderabad", "cyberabad"),
    "Chennai": ("chennai", "madras"),
    "Pune": ("pune", "pimpri", "chinchwad"),
    "Kolkata": ("kolkata", "calcutta", "howrah"),
    "Ahmedabad": ("ahmedabad", "amdavad"),
    "Jaipur": ("jaipur",),
    "Kochi": ("kochi", "cochin", "ernakulam"),
    "Chandigarh": ("chandigarh", "mohali", "panchkula"),
    "Indore": ("indore",),
    "Coimbatore": ("coimbatore",),
    "Thiruvananthapuram": ("thiruvananthapuram", "trivandrum"),
    "Lucknow": ("lucknow",),
    "Bhopal": ("bhopal",),
    "Nagpur": ("nagpur",),
    "Surat": ("surat",),
    "Vadodara": ("vadodara", "baroda"),
    "Mysuru": ("mysuru", "mysore"),
    "Visakhapatnam": ("visakhapatnam", "vizag"),
    "Bhubaneswar": ("bhubaneswar", "bhubaneshwar"),
    "Patna": ("patna",),
    "Ranchi": ("ranchi",),
    "Guwahati": ("guwahati",),
    "Dehradun": ("dehradun", "dehra dun"),
}


def _resolve_location_profile(location_hint: str | None) -> dict[str, Any] | None:
    """Normalize a free-text location into a city profile with match aliases."""
    if not location_hint:
        return None
    raw = str(location_hint).strip()
    if not raw or raw.lower() in {"not found", "n/a", "na", "india"}:
        return None
    lower = raw.lower()
    for canonical, aliases in _CITY_ALIASES.items():
        if any(alias in lower for alias in aliases) or canonical.lower() in lower:
            return {
                "city": canonical,
                "display": canonical,
                "aliases": tuple(dict.fromkeys((canonical.lower(),) + aliases)),
                "country": "India",
                "query": f"{canonical}, India",
            }
    first = re.split(r"[,|/]|-", raw)[0].strip()
    if 2 <= len(first) <= 40 and re.match(r"^[A-Za-z][A-Za-z .'-]+$", first):
        return {
            "city": first.title(),
            "display": first.title(),
            "aliases": (first.lower(),),
            "country": "India",
            "query": f"{first.title()}, India",
        }
    return None


def _extract_candidate_location(resume_text: str) -> dict[str, Any] | None:
    """Pull the candidate's city/address from resume contact lines."""
    text = resume_text or ""
    lower = text.lower()

    for canonical, aliases in _CITY_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                return _resolve_location_profile(canonical)

    for ln in text.splitlines():
        line = ln.strip()
        if not line:
            continue
        m = re.match(r"(?i)^(?:location|address|city|based in|residing in)\s*[:\-]\s*(.+)$", line)
        if m:
            profile = _resolve_location_profile(m.group(1))
            if profile:
                return profile
        if _looks_like_location(line):
            profile = _resolve_location_profile(line)
            if profile:
                return profile
    return None


def _job_matches_candidate_location(job: dict[str, Any], location: dict[str, Any] | None) -> bool:
    """True when the listing is in the candidate's city (or that metro area)."""
    loc = str(job.get("location") or "").lower()
    if not location:
        # No city on resume — keep only clearly India-based roles (not global remote).
        rank = _india_location_rank(loc)
        return rank == 0

    if not loc:
        return False
    aliases = location.get("aliases") or ()
    if any(alias and alias in loc for alias in aliases):
        return True
    hay = " ".join(
        [
            str(job.get("job_title") or ""),
            str(job.get("description") or ""),
            " ".join(job.get("tags") or []),
        ]
    ).lower()
    return any(alias and alias in hay for alias in aliases)


def jobs_provider_status() -> dict[str, Any]:
    has_jsearch = _is_real_key(RAPIDAPI_KEY)
    has_adzuna = _is_real_key(ADZUNA_APP_ID) and _is_real_key(ADZUNA_APP_KEY)
    return {
        "jsearch_configured": has_jsearch,
        "adzuna_configured": has_adzuna,
        # Free, no-key providers (Remotive / Arbeitnow / RemoteOK) and a guaranteed
        # search-portal fallback keep listings available even without any API key.
        "free_providers": True,
        "keyed_providers": has_jsearch or has_adzuna,
        "any_provider": True,
    }


def fetch_jsearch_jobs(
    role_category: str,
    skills: list[str] | None = None,
    limit: int = JOBS_PER_ROLE,
    location: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not _is_real_key(RAPIDAPI_KEY):
        return []
    skill_query = " ".join((skills or [])[:4])
    place = (location or {}).get("query") or "India"
    query = f"{role_category} {skill_query} in {place}".strip()
    out: list[dict[str, Any]] = []
    try:
        r = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": RAPIDAPI_HOST,
            },
            params={
                "query": query,
                "page": "1",
                "num_pages": "1",
                "country": "in",
            },
            timeout=JOB_API_TIMEOUT,
        )
        r.raise_for_status()
        for j in (r.json().get("data") or []):
            if len(out) >= limit:
                break
            city = j.get("job_city") or ""
            country = j.get("job_country") or "India"
            loc = ", ".join(x for x in [city, country] if x) or place
            apply_url = j.get("job_apply_link") or j.get("job_google_link") or "#"
            out.append(
                _job_record(
                    role_category=role_category,
                    company_name=j.get("employer_name") or "Hiring Company",
                    job_title=j.get("job_title") or role_category,
                    location=loc,
                    redirect_url=apply_url,
                    employment_type=j.get("job_employment_type") or "Full-time",
                    source="JSearch",
                    tags=[str(x) for x in (j.get("job_required_skills") or []) if x][:12],
                    description=str(j.get("job_description") or "")[:600],
                )
            )
    except Exception as exc:
        _log(f"[JSearch] {type(exc).__name__}: {exc!r}")
    return out[:limit]


def fetch_adzuna_jobs(
    role_category: str,
    skills: list[str] | None = None,
    limit: int = JOBS_PER_ROLE,
    location: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not (_is_real_key(ADZUNA_APP_ID) and _is_real_key(ADZUNA_APP_KEY)):
        return []
    out: list[dict[str, Any]] = []
    where = (location or {}).get("city") or "India"
    try:
        r = requests.get(
            "https://api.adzuna.com/v1/api/jobs/in/search/1",
            params={
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "what": f"{role_category} {' '.join((skills or [])[:4])}",
                "where": where,
                "results_per_page": limit,
            },
            timeout=JOB_API_TIMEOUT,
        )
        r.raise_for_status()
        for j in (r.json().get("results") or []):
            if len(out) >= limit:
                break
            company = (j.get("company") or {}).get("display_name") or "Hiring Company"
            loc_obj = j.get("location") or {}
            loc = loc_obj.get("display_name") or where
            out.append(
                _job_record(
                    role_category=role_category,
                    company_name=company,
                    job_title=j.get("title") or role_category,
                    location=loc,
                    redirect_url=j.get("redirect_url") or "#",
                    employment_type=j.get("contract_type") or "Full-time",
                    source="Adzuna",
                    description=str(j.get("description") or "")[:600],
                )
            )
    except Exception as exc:
        _log(f"[Adzuna] {type(exc).__name__}: {exc!r}")
    return out[:limit]


# ---------------------------------------------------------------------------
# Free, no-key job providers. These require NO API key so live openings are
# available out of the box. They are remote/global-friendly boards; the keyed
# providers above give India-specific results when configured.
# ---------------------------------------------------------------------------
_FREE_HTTP_HEADERS = {"User-Agent": "ResumeNavigator/1.0 (+job-aggregator)", "Accept": "application/json"}


def fetch_remotive_jobs(role_category: str, skills: list[str] | None = None, limit: int = JOBS_PER_ROLE, location: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    skill_query = " ".join((skills or [])[:3])
    place = (location or {}).get("city") or ""
    search = f"{role_category} {skill_query} {place}".strip()
    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": search or role_category, "limit": max(limit, 20)},
            headers=_FREE_HTTP_HEADERS,
            timeout=JOB_API_TIMEOUT,
        )
        r.raise_for_status()
        for j in (r.json().get("jobs") or []):
            if len(out) >= limit:
                break
            tags = list(j.get("tags") or [])
            out.append(
                _job_record(
                    role_category=role_category,
                    company_name=j.get("company_name") or "Hiring Company",
                    job_title=j.get("title") or role_category,
                    location=j.get("candidate_required_location") or "Remote",
                    redirect_url=j.get("url") or "#",
                    employment_type=(j.get("job_type") or "Full-time").replace("_", " ").title(),
                    source="Remotive",
                    tags=tags,
                    description=str(j.get("description") or "")[:600],
                )
            )
    except Exception as exc:
        _log(f"[Remotive] {type(exc).__name__}: {exc!r}")
    return out[:limit]


def fetch_arbeitnow_jobs(role_category: str, skills: list[str] | None = None, limit: int = JOBS_PER_ROLE, location: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    terms = [role_category.lower()] + [s.lower() for s in (skills or [])[:3]]
    if location and location.get("aliases"):
        terms.extend(list(location["aliases"])[:3])
    try:
        r = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            headers=_FREE_HTTP_HEADERS,
            timeout=JOB_API_TIMEOUT,
        )
        r.raise_for_status()
        for j in (r.json().get("data") or []):
            if len(out) >= limit:
                break
            haystack = f"{j.get('title', '')} {' '.join(j.get('tags') or [])} {j.get('location', '')}".lower()
            if not any(t and t in haystack for t in terms):
                continue
            loc = j.get("location") or ("Remote" if j.get("remote") else "On-site")
            out.append(
                _job_record(
                    role_category=role_category,
                    company_name=j.get("company_name") or "Hiring Company",
                    job_title=j.get("title") or role_category,
                    location=loc,
                    redirect_url=j.get("url") or "#",
                    employment_type=", ".join(j.get("job_types") or []).title() or "Full-time",
                    source="Arbeitnow",
                    tags=list(j.get("tags") or []),
                    description=str(j.get("description") or "")[:600],
                )
            )
    except Exception as exc:
        _log(f"[Arbeitnow] {type(exc).__name__}: {exc!r}")
    return out[:limit]


def fetch_remoteok_jobs(role_category: str, skills: list[str] | None = None, limit: int = JOBS_PER_ROLE, location: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    terms = [role_category.lower()] + [s.lower() for s in (skills or [])[:3]]
    if location and location.get("aliases"):
        terms.extend(list(location["aliases"])[:3])
    try:
        r = requests.get("https://remoteok.com/api", headers=_FREE_HTTP_HEADERS, timeout=JOB_API_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        rows = data[1:] if isinstance(data, list) else []
        for j in rows:
            if len(out) >= limit:
                break
            if not isinstance(j, dict):
                continue
            haystack = f"{j.get('position', '')} {' '.join(j.get('tags') or [])} {j.get('location', '')}".lower()
            if not any(t and t in haystack for t in terms):
                continue
            out.append(
                _job_record(
                    role_category=role_category,
                    company_name=j.get("company") or "Hiring Company",
                    job_title=j.get("position") or role_category,
                    location=j.get("location") or "Remote",
                    redirect_url=j.get("url") or j.get("apply_url") or "#",
                    employment_type="Remote",
                    source="RemoteOK",
                    tags=list(j.get("tags") or []),
                    description=str(j.get("description") or "")[:600],
                )
            )
    except Exception as exc:
        _log(f"[RemoteOK] {type(exc).__name__}: {exc!r}")
    return out[:limit]


def build_search_fallback_jobs(
    role_category: str,
    skills: list[str] | None = None,
    location: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Location-scoped portal searches — used only as a last-resort browse aid.

    These are NOT treated as direct-apply openings in the main feed.
    """
    top_skills = [s for s in (skills or []) if s][:3]
    place = (location or {}).get("query") or (location or {}).get("city") or "India"
    query = " ".join([role_category] + top_skills).strip()
    q = urllib.parse.quote_plus(query)
    place_q = urllib.parse.quote_plus(place)
    slug = urllib.parse.quote(query.lower().replace(" ", "-"))
    city_slug = urllib.parse.quote(str((location or {}).get("city") or "india").lower().replace(" ", "-"))
    portals = [
        ("LinkedIn", f"https://www.linkedin.com/jobs/search/?keywords={q}&location={place_q}"),
        ("Naukri", f"https://www.naukri.com/{slug}-jobs-in-{city_slug}"),
        ("Indeed", f"https://in.indeed.com/jobs?q={q}&l={place_q}"),
        ("Foundit", f"https://www.foundit.in/srp/results?query={q}&locations={place_q}"),
        ("Google Jobs", f"https://www.google.com/search?q={q}+jobs+in+{place_q}&ibp=htl;jobs"),
    ]
    return [
        _job_record(
            role_category=role_category,
            company_name=name,
            job_title=f"{role_category} openings",
            location=place,
            redirect_url=url,
            employment_type="Search",
            source=f"{name} search",
        )
        for name, url in portals
    ]


_INDIA_LOCATION_TOKENS = (
    "india", "bengaluru", "bangalore", "mumbai", "delhi", "chennai", "hyderabad",
    "pune", "kolkata", "noida", "gurugram", "gurgaon", "ahmedabad", "jaipur",
    "kochi", "chandigarh", "indore", "coimbatore", "thiruvananthapuram", "remote, in",
)
_REMOTE_WORLDWIDE_TOKENS = (
    "worldwide", "anywhere", "global", "remote - global", "remote", "work from home",
    "wfh", "distributed", "utc", "timezone",
)
_FOREIGN_ONLY_TOKENS = (
    "usa only", "us only", "united states only", "uk only", "europe only",
    "eu only", "canada only", "australia only", "germany only", "visa sponsorship required",
)


def _india_location_rank(location: str) -> int | None:
    """Rank a job's location for India relevance.

    Returns 0 for India-based, 1 for worldwide-remote (an Indian can apply), or
    None when the listing is clearly restricted to another country/region.
    """
    loc = (location or "").lower().strip()
    if not loc:
        return 1  # unknown remote board location — treat as globally applicable
    if any(tok in loc for tok in _FOREIGN_ONLY_TOKENS):
        return None
    if any(tok in loc for tok in _INDIA_LOCATION_TOKENS):
        return 0
    if any(tok in loc for tok in _REMOTE_WORLDWIDE_TOKENS):
        return 1
    # Single country labels without India — skip; multi-region / vague keep as remote-eligible.
    if re.search(r"\b(usa|united states|uk|united kingdom|germany|france|canada|australia|europe|eu)\b", loc):
        if "india" not in loc and "asia" not in loc:
            return None
    return 1


def fetch_india_jobs_for_role(
    role_category: str,
    skills: list[str] | None = None,
    limit: int = JOBS_PER_ROLE,
    location: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    india_jobs: list[dict[str, Any]] = []
    # Keyed providers already query the candidate city when provided.
    providers = [
        (fetch_jsearch_jobs, True),
        (fetch_adzuna_jobs, True),
        (fetch_remotive_jobs, False),
        (fetch_arbeitnow_jobs, False),
        (fetch_remoteok_jobs, False),
    ]
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        futures = {
            pool.submit(fn, role_category, skills, limit, location): scoped
            for fn, scoped in providers
        }
        for future in as_completed(futures):
            try:
                results = future.result()
            except Exception as exc:
                _log(f"[jobs] provider error: {exc!r}")
                results = []
            for job in results:
                url = job.get("redirect_url") or ""
                if url in seen or url == "#" or not _is_direct_apply_job(job):
                    continue
                if not _job_matches_candidate_location(job, location):
                    continue
                seen.add(url)
                india_jobs.append(job)

    # Direct-apply only — never inject portal "Search" cards into the apply feed.
    return _annotate_and_rank_jobs(india_jobs, skills)[:limit]


def fetch_jobs_for_roles(
    roles: list[str],
    skills: list[str] | None = None,
    per_role_limit: int = JOBS_PER_ROLE,
    location: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    role_names = [str(role).strip() for role in roles if str(role).strip()][:MAX_JOB_ROLES]
    if not role_names:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=min(len(role_names), 5)) as pool:
        futures = {
            pool.submit(fetch_india_jobs_for_role, role_name, skills, per_role_limit, location): role_name
            for role_name in role_names
        }
        for future in as_completed(futures):
            role_name = futures[future]
            grouped[role_name] = future.result()
        return grouped


def _heuristic_is_resume(text: str) -> bool:
    normalized = _normalize_resume_text(text)
    if len(normalized) < 35:
        return False
    lower = normalized.lower()
    non_resume_hits = sum(1 for sig in _NON_RESUME_SIGNALS if sig in lower)
    resume_hits = sum(1 for sig in _RESUME_SIGNALS if sig in lower)
    if non_resume_hits >= 2 and resume_hits < 1:
        return False
    has_contact = bool(
        re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalized)
        or re.search(r"(?:\+91[\-\s]?)?[6-9]\d{9}", normalized)
    )
    has_experience_block = any(
        k in lower
        for k in ("experience", "education", "skills", "project", "internship", "work", "employment", "responsibilities")
    )
    has_company_marker = any(
        marker in lower
        for marker in (" pvt", " ltd", " limited", " technologies", " solutions", " infotech", " services")
    )
    has_work_timeline = bool(
        re.search(r"\b(19|20)\d{2}\s*[-–—to]{1,3}\s*((19|20)\d{2}|present|current)\b", lower)
    )
    if has_contact and (has_experience_block or has_company_marker or has_work_timeline):
        return True
    if resume_hits >= 2:
        return True
    if len(normalized) >= 80 and (resume_hits >= 1 or has_experience_block):
        return True
    return False


def _build_scorecard(
    resume_text: str,
    matched_skills: list[str],
    missing_skills: list[str],
    domain: str,
    job_description: str | None = None,
) -> dict[str, Any]:
    """Return an explainable, multi-signal ATS scorecard via the NLP engine.

    Delegates to ``nlp_engine.compute_ats`` which blends semantic skill matching
    (embeddings + ontology + fuzzy), spaCy/regex structure detection, readability
    and grammar analysis into a weighted score. Everything degrades gracefully
    when the ML stack is not installed, so the endpoint never fails on scoring.
    """
    profile = DOMAIN_PROFILES.get(domain, {})
    required = list(profile.get("skill_pool", []))
    # Ensure the resume's own detected skills are represented in the target set
    for skill in matched_skills:
        if skill.lower() not in {r.lower() for r in required}:
            required.append(skill)
    try:
        return compute_ats(resume_text, domain, matched_skills, required, job_description)
    except Exception as exc:  # pragma: no cover - defensive last resort
        _log(f"[scorecard] engine failed, using minimal fallback: {exc!r}")
        cov = min(1.0, len(matched_skills) / max(5, min(12, len(required))))
        overall = round(40 + cov * 45)
        return {
            "overall": max(0, min(100, overall)),
            "sections": {"Skill Match": round(20 + cov * 80), "Resume Structure": 60,
                          "Experience": 55, "Projects": 55, "Education": 60,
                          "Formatting": 65, "Achievements": 50, "Grammar": 70},
            "weights": {},
            "confidence": {"value": 40, "basis": "Minimal fallback scorer."},
            "recruiter_readiness": overall, "interview_probability": max(5, overall - 15),
            "hiring_confidence": max(5, overall - 25),
            "evidence": [f"{len(matched_skills)} skills matched to the {domain} profile."],
            "weak_areas": [], "features": {}, "semantic_missing_skills": missing_skills[:8],
            "engine": engine_capabilities(),
        }


def _extract_resume_sections(resume_text: str) -> dict[str, str]:
    """Split common resume sections without assuming a rigid template."""
    aliases = {
        "summary": ("summary", "profile", "objective", "about me"),
        "experience": ("experience", "work history", "employment", "internship"),
        "education": ("education", "academic background", "qualification"),
        "skills": ("skills", "technical skills", "core competencies"),
        "projects": ("projects", "academic projects", "personal projects"),
        "achievements": ("achievements", "awards", "certifications", "certificates"),
    }
    result = {name: "" for name in aliases}
    current: str | None = None
    for line in resume_text.splitlines():
        clean = line.strip()
        compact = clean.lower().rstrip(":")
        found = next((name for name, names in aliases.items() if compact in names), None)
        if found:
            current = found
        elif current and clean:
            result[current] += ("\n" if result[current] else "") + clean
    return result


def _build_career_intelligence(
    resume_text: str, matched: list[str], missing: list[str], domain: str, scorecard: dict[str, Any]
) -> dict[str, Any]:
    """Create UI-ready intelligence from measured document signals.

    Labels deliberately describe readiness/attention rather than claiming to predict a
    particular hiring decision. Hiring outcomes require data the resume cannot provide.
    """
    sections = _extract_resume_sections(resume_text)
    score_sections = scorecard.get("sections", {})
    features = scorecard.get("features", {})
    readability_score = (features.get("readability") or {}).get("score", score_sections.get("Grammar", 60))
    attention = []
    section_score_key = {"summary": "Resume Structure", "experience": "Experience", "education": "Education", "skills": "Skill Match", "projects": "Projects", "achievements": "Achievements"}
    for name, content in sections.items():
        if not content:
            status, reason = "low", "No clearly labeled section was detected."
        else:
            value = score_sections.get(section_score_key[name], 0)
            status = "high" if value >= 70 else "medium" if value >= 45 else "low"
            reason = f"{len(content.split())} extractable words; {section_score_key[name].lower()} signal is {value}/100."
        attention.append({"section": name.title(), "attention": status, "reason": reason})

    lower = resume_text.lower()
    years = sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", lower)))
    timeline = []
    for year in years[:12]:
        context = next((line.strip() for line in resume_text.splitlines() if year in line), year)
        timeline.append({"year": year, "event": context[:180]})
    action_count = len(re.findall(r"\b(built|led|created|delivered|improved|designed|developed|managed|launched|optimized|implemented|automated|analyzed)\b", lower))
    quantified = len(re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:%|x|users|customers|projects|days|hours|lakhs|crore)\b", lower))
    question_skills = matched[:5] or missing[:3]
    interview = [{"type": "Technical", "question": f"Walk me through a project where you used {skill}.", "why": "This skill was detected in the resume."} for skill in question_skills]
    interview += [
        {"type": "Behavioral", "question": "Tell me about an outcome you improved and how you measured it.", "why": "Recruiters look for measurable ownership."},
        {"type": "HR", "question": "Why is this target role the right next step for you?", "why": "Tests the clarity of your career narrative."},
    ]
    readiness = scorecard.get("overall", 0)
    return {
        "recruiter_simulation": {
            "first_ten_second_read": "clear" if readiness >= 70 else "mixed" if readiness >= 50 else "unclear",
            "summary": f"The first scan finds {len(matched)} relevant skills, {action_count} action verbs, and {quantified} quantified outcomes.",
            "attention_map": attention,
        },
        "resume_heatmap": attention,
        "career_dna": {
            "best_domains": [domain],
            "leadership_signal": min(100, 25 + action_count * 5),
            "innovation_signal": min(100, 20 + (18 if sections["projects"] else 0) + action_count * 3),
            "communication_signal": readability_score,
            "learning_signal": min(100, 25 + len(matched) * 5 + (15 if sections["achievements"] else 0)),
            "note": "Signals are based on written evidence in this resume, not personality inference.",
        },
        "interview_predictor": interview,
        "resume_timeline": timeline,
        "confidence_meter": {
            "readiness_score": readiness,
            "label": "Application readiness—not a selection or offer probability.",
            "next_action": "Address the highest-value skill gaps and add measurable outcomes before applying." if missing else "Tailor the resume to each job description before applying.",
        },
    }


def _analyze_text_intelligence(resume_text: str) -> dict[str, Any]:
    text = _normalize_resume_text(resume_text)
    if not _heuristic_is_resume(text):
        raise HTTPException(status_code=422, detail=INVALID_RESUME_ERROR)
    domain = detect_domain(text)
    metadata = _extract_candidate_details(text)
    matched = sanitize_skills(extract_professional_skills(text, domain), metadata)
    missing = compute_missing_skills(matched, domain)
    scorecard = _build_scorecard(text, matched, missing, domain)
    return {"domain": domain, "matched_skills": matched, "missing_skills": missing, "scorecard": scorecard, "intelligence": _build_career_intelligence(text, matched, missing, domain, scorecard)}


def _build_domain_analysis(resume_text: str) -> dict[str, Any]:
    if not _heuristic_is_resume(resume_text):
        return {"error": INVALID_RESUME_ERROR}

    text = _normalize_resume_text(resume_text)
    lower = text.lower()
    domain = detect_domain(text)
    profile = DOMAIN_PROFILES[domain]
    roles = list(profile["roles"])
    metadata = _extract_candidate_details(text)
    matched = sanitize_skills(extract_professional_skills(text, domain), metadata)
    if not matched:
        edu_hits = [
            w for w in ("b.com", "b.a", "b.tech", "b.e", "mba", "b.sc", "diploma", "graduate", "internship")
            if w in lower
        ]
        matched = sanitize_skills(edu_hits[:4] if edu_hits else [f"{domain.split('/')[0].strip()} competency"], metadata)
    missing = compute_missing_skills(matched, domain)

    role_scores: list[tuple[str, int]] = []
    for role in roles:
        role_tokens = [t for t in re.findall(r"[a-z]+", role.lower()) if len(t) > 3]
        score = sum(1 for t in role_tokens if t in lower) + len(matched)
        role_scores.append((role, score))
    role_scores.sort(key=lambda item: item[1], reverse=True)

    # Fallback role prediction: TF-IDF feature vectors + Logistic Regression classifier.
    ml_role = predict_job_role(text, matched)
    if ml_role.get("available") and ml_role.get("predicted_role"):
        predicted_role = str(ml_role["predicted_role"])
    else:
        predicted_role = role_scores[0][0]
    domain_roles = [r for r, _ in role_scores[:5]]
    skill_roles = infer_roles_from_skills(matched, domain)
    recommended_roles = merge_recommended_roles(
        [predicted_role] + ([ml_role["predicted_role"]] if ml_role.get("predicted_role") else []) + domain_roles,
        skill_roles,
        limit=6,
    )

    scorecard = _build_scorecard(text, matched, missing, domain)
    ats_score = scorecard["overall"]

    if domain == "General / Fresher" or any(k in lower for k in ("fresher", "intern", "trainee", "graduate")):
        roadmap = [
            {
                "step": 1,
                "title": "Build employability foundations",
                "focus": f"Strengthen {', '.join(missing[:3]) or 'core workplace skills'} through short courses.",
                "project_idea": "Complete a domain-relevant internship or volunteer project and document outcomes.",
            },
            {
                "step": 2,
                "title": "Create a targeted entry-level profile",
                "focus": f"Tailor your resume for {predicted_role} roles with measurable bullet points.",
                "project_idea": "Add one portfolio artifact (report, case study, or practical assignment).",
            },
            {
                "step": 3,
                "title": "Start structured job applications",
                "focus": "Apply to trainee and associate roles aligned with your education background.",
                "project_idea": "Prepare a 60-second self-introduction and common HR interview answers.",
            },
        ]
        suggestion = (
            f"As a fresher in the {domain} space, you can credibly target {predicted_role}. "
            f"Highlight {', '.join(matched[:4]) or 'your academic strengths'} and close gaps in "
            f"{', '.join(missing[:3]) or 'workplace readiness'} through practical projects before campus or off-campus drives."
        )
    else:
        roadmap = [
            {
                "step": 1,
                "title": f"Strengthen {domain} fundamentals",
                "focus": f"Prioritize {', '.join(missing[:3]) or 'role-specific competencies'} from the uploaded resume context.",
                "project_idea": f"Deliver one measurable outcome linked to {predicted_role}.",
            },
            {
                "step": 2,
                "title": "Align resume with market demand",
                "focus": "Rewrite experience bullets using action verbs and quantified results.",
                "project_idea": "Map your background to 10 live India job descriptions in your domain.",
            },
            {
                "step": 3,
                "title": "Prepare for domain interviews",
                "focus": f"Practice role-specific scenarios for {', '.join(recommended_roles[:2])}.",
                "project_idea": "Build a one-page career transition plan for the next 90 days.",
            },
        ]
        suggestion = (
            f"Based on your {domain} background, {predicted_role} is a realistic next step. "
            f"Your resume shows strengths in {', '.join(matched[:4]) or 'foundational skills'}; "
            f"focus on {', '.join(missing[:3]) or 'high-impact skill gaps'} to improve ATS visibility."
        )

    career_suggestions = (
        f"{suggestion} Recommended transition path: "
        f"{' → '.join(recommended_roles[:3])}."
    )

    return {
        "is_valid_resume": True,
        "detected_domain": domain,
        "ats_score": ats_score,
        "predicted_role": predicted_role,
        "recommended_roles": recommended_roles,
        "matched_skills": matched,
        "missing_skills": missing,
        "learning_roadmap": roadmap,
        "custom_suggestion": suggestion,
        "career_suggestions": career_suggestions,
        "scorecard": scorecard,
    }


def _normalize_ai_payload(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw.get("is_valid_resume", False):
        return {"error": raw.get("error") or INVALID_RESUME_ERROR}

    career = str(
        raw.get("career_suggestions") or raw.get("custom_suggestion") or ""
    ).strip()
    custom = str(raw.get("custom_suggestion") or career).strip()

    return {
        "is_valid_resume": True,
        "detected_domain": str(raw.get("detected_domain") or "General").strip(),
        "ats_score": raw.get("ats_score", 0),
        "predicted_role": str(raw.get("predicted_role") or "").strip(),
        "recommended_roles": raw.get("recommended_roles") or [],
        "matched_skills": raw.get("matched_skills") or [],
        "missing_skills": raw.get("missing_skills") or [],
        "learning_roadmap": raw.get("learning_roadmap") or [],
        "custom_suggestion": custom,
        "career_suggestions": career or custom,
    }


def analyze_resume_with_gemini(resume_text: str) -> dict[str, Any]:
    if _genai_client is None:
        raise RuntimeError("GEMINI_API_KEY missing")
    truncated = _normalize_resume_text(resume_text)[:12000]
    prompt = f"""
You are PathFinder, an expert career counselor for Indian job seekers.

STEP 1 STRICT DOCUMENT VALIDATION:
Determine if the extracted text is an authentic resume or CV.
If it is NOT a resume (text snippet, textbook page, study note, assignment, image log, article),
set is_valid_resume to false and error to exactly:
"Invalid document type. Please upload a valid resume."
Bypass all scoring when invalid.

STEP 2 ONLY WHEN is_valid_resume IS TRUE:
Analyze the ACTUAL unique content of this resume. Never reuse generic or identical evaluations across documents.
Personalize every field from the extracted text only.

Domain detection must include: Information Technology, Network Engineering, Commerce, Healthcare,
Education, Management, Marketing, Arts, Administration, Core Engineering, and Fresher profiles.
If the candidate has zero IT skills, do NOT assign software developer roles.
Generate realistic non-IT or fresher roadmaps aligned to their true industry.

Skill extraction rules:
- NEVER place names, phone numbers, email addresses, or contact metadata inside matched_skills.
- matched_skills must contain only professional competencies, tools, frameworks, certifications, and domain terms.
- Infer skills from experience and employment sections even when the resume lacks a formal skills block.
- Recognize AWS and cloud skills: EC2, S3, Lambda, VPC, IAM, CloudFormation, EKS, Terraform, Kubernetes, Docker, Azure, GCP.
- Recognize network skills such as Cisco, Routing, TCP/IP, Wireshark, BGP, OSPF, VLAN, Firewall.
- Recognize non-IT skills such as Financial Analysis, Marketing, Operations, Customer Relations, Tally, GST.
- recommended_roles must include every major role that matches the extracted skill set (up to 6 roles).

Output when valid:
1) detected_domain
2) predicted_role from actual background
3) recommended_roles ranked 3-5 by fit
4) ats_score integer 0-100 unique to this resume
5) matched_skills and missing_skills never empty and never containing PII
6) learning_roadmap with 3 sequential steps and project_idea
7) custom_suggestion personalized paragraph
8) career_suggestions transition paragraph

Return ONLY valid JSON.

--- EXTRACTED TEXT ---
{truncated}
--- END ---
"""
    try:
        response = _genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=ATS_JSON_SCHEMA,
                temperature=0.2,
            ),
        )
        return _normalize_ai_payload(json.loads(response.text))
    except HTTPException:
        raise
    except Exception as e:
        _log(f"[Gemini] {type(e).__name__}: {e!r}")
        safe_detail = str(e).encode("ascii", "backslashreplace").decode("ascii")
        raise HTTPException(status_code=502, detail=f"Gemini analysis failed: {safe_detail[:500]}")


def analyze_resume(text: str) -> dict[str, Any]:
    if _genai_client is not None:
        try:
            return analyze_resume_with_gemini(text)
        except HTTPException:
            raise
        except Exception as exc:
            _log(f"[analyze] Gemini unavailable, using heuristic analyzer: {exc!r}")
    result = _build_domain_analysis(text)
    if isinstance(result, dict) and "error" not in result:
        result["_heuristic"] = True
        # Attach TF-IDF + LR prediction metadata for the analyze response.
        result["ml_role_prediction"] = predict_job_role(
            text,
            result.get("matched_skills") or [],
        )
    return result


_LOCATION_MARKERS = (
    "india", "bengaluru", "bangalore", "mumbai", "delhi", "chennai", "hyderabad",
    "pune", "kolkata", "noida", "gurugram", "gurgaon", "address", "street", "road",
    "pincode", "pin code", "karnataka", "maharashtra", "tamil nadu", "telangana",
    "andhra", "kerala", "gujarat", "rajasthan", "uttar pradesh", "west bengal",
)

_SECTION_HEADERS = (
    "experience", "education", "skills", "summary", "objective", "projects",
    "certifications", "contact", "profile", "resume", "curriculum vitae",
    "work history", "technical skills", "personal details", "professional",
    "employment", "achievements", "hobbies", "references", "declaration",
)


def _looks_like_location(line: str) -> bool:
    lower = line.lower().strip()
    if any(marker in lower for marker in _LOCATION_MARKERS):
        return True
    if re.search(r"\b\d{5,6}\b", line):
        return True
    if "," in line:
        parts = [p.strip().lower() for p in line.split(",") if p.strip()]
        if len(parts) >= 2 and any("india" in p or p in ("in", "ind") for p in parts):
            return True
        if len(parts) >= 2 and all(len(p) < 30 for p in parts):
            geo_words = ("city", "state", "district", "taluk", "region")
            if any(any(g in p for g in geo_words) for p in parts):
                return True
    return False


def _looks_like_person_name(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned or len(cleaned) > 55:
        return False
    if "@" in cleaned or re.search(r"\d", cleaned):
        return False
    lower = cleaned.lower()
    if any(header in lower for header in _SECTION_HEADERS):
        return False
    if _looks_like_location(cleaned):
        return False
    if any(w in lower for w in ("college", "university", "institute", "school", "ltd", "pvt", "inc")):
        return False
    words = cleaned.split()
    if len(words) < 1 or len(words) > 5:
        return False
    if not all(re.match(r"^[A-Za-z][A-Za-z.'-]*$", word) for word in words):
        return False
    titled = sum(1 for word in words if word[0].isupper())
    if len(words) >= 2 and titled < max(1, len(words) - 1):
        return False
    return True


def _name_from_email(email: str) -> str | None:
    if not email or email.lower() == "not found":
        return None
    local = email.split("@")[0].lower()
    local = re.sub(r"\d+", " ", local)
    local = re.sub(r"(edu|gmail|yahoo|hotmail|outlook|mail|co|in)\b", "", local)
    local = re.sub(r"[._+\-]+", " ", local).strip()
    if len(local) < 2:
        return None
    parts = [p.capitalize() for p in local.split() if len(p) >= 2]
    if parts:
        return " ".join(parts[:4])
    return local.capitalize()


def _extract_candidate_details(resume_text: str) -> dict[str, str]:
    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)
    phone_match = re.search(r"(?:\+91[\-\s]?)?[6-9]\d{9}", resume_text)
    email = email_match.group(0) if email_match else "Not found"
    phone = phone_match.group(0) if phone_match else "Not found"
    probable_name = "Not found"
    college = "Not found"

    for ln in lines[:15]:
        if _looks_like_person_name(ln):
            probable_name = ln
            break

    if probable_name == "Not found":
        email_name = _name_from_email(email)
        if email_name:
            probable_name = email_name

    for ln in lines:
        lower = ln.lower()
        if any(k in lower for k in ("college", "university", "institute", "school of")):
            college = ln
            break

    location_profile = _extract_candidate_location(resume_text)
    return {
        "candidate_name": probable_name,
        "candidate_email": email,
        "candidate_phone": phone,
        "candidate_college": college,
        "candidate_location": (location_profile or {}).get("display") or "Not found",
        "candidate_location_query": (location_profile or {}).get("query") or "",
    }


def _build_jobs_payload(
    recommended_roles: list[str],
    matched_skills: list[str] | None = None,
    jobs_per_role: int = JOBS_PER_ROLE,
    candidate_location: str | dict[str, Any] | None = None,
    resume_text: str | None = None,
) -> dict[str, Any]:
    skills = [str(skill).strip() for skill in (matched_skills or []) if str(skill).strip()]
    if isinstance(candidate_location, dict):
        location = candidate_location
    else:
        location = _resolve_location_profile(candidate_location) if candidate_location else None
    if location is None and resume_text:
        location = _extract_candidate_location(resume_text)

    jobs_by_role = fetch_jobs_for_roles(recommended_roles, skills, jobs_per_role, location)
    total = sum(len(v) for v in jobs_by_role.values())
    provider = jobs_provider_status()
    city = (location or {}).get("display")
    portal_searches = []
    if recommended_roles:
        portal_searches = build_search_fallback_jobs(recommended_roles[0], skills, location)

    if total == 0:
        if city:
            message = (
                f"No direct-apply openings found in {city} for your matched skills right now. "
                f"Use the location-scoped portal links below, or add a JSearch/Adzuna key in backend/.env."
            )
        else:
            message = (
                "No city/address was detected on your resume, and no India direct-apply listings matched. "
                "Add a city (e.g. Bengaluru, Mumbai) to your resume contact section and re-analyze."
            )
    elif city:
        message = (
            f"Showing only direct-apply openings in {city} (from your resume address), "
            "ranked by overlap with your matched skills. Apply Now opens the employer application page."
        )
    else:
        message = (
            "Showing India-based direct-apply openings ranked by your matched skills. "
            "Add a city to your resume to narrow results to your address."
        )

    return {
        "jobs_by_role": jobs_by_role,
        "jobs": jobs_by_role.get(recommended_roles[0], []) if recommended_roles else [],
        "jobs_count": total,
        "jobs_provider": provider,
        "jobs_message": message,
        "job_search_skills": skills,
        "candidate_location": city or "Not found",
        "portal_searches": portal_searches,
    }


@app.get("/")
def root():
    return {
        "service": "PathFinder",
        "health": "/health",
        "analyze": "POST /analyze",
        "fetch_jobs": "POST /api/fetch-jobs",
        "algorithms": "GET /api/algorithms",
    }


@app.get("/api/algorithms")
def api_algorithms():
    """Document the academic algorithm stack and live availability."""
    caps = engine_capabilities()
    ml = role_predictor_status()
    return {
        "algorithms": [
            {
                "id": "nlp",
                "name": "Natural Language Processing (NLP)",
                "phase": "Parsing",
                "used": True,
                "modules": ["resume_nlp.py", "pdf_parser.py", "skills.py"],
                "description": (
                    "Extracts unstructured text from PDF and Word (.docx) resumes, cleans it, "
                    "and extracts skills, academic degrees, and years of experience via rules and regex."
                ),
            },
            {
                "id": "tfidf",
                "name": "TF-IDF (Term Frequency–Inverse Document Frequency)",
                "phase": "Feature extraction",
                "used": bool(ml.get("available")),
                "modules": ["role_predictor.py", "nlp_engine.py"],
                "description": (
                    "Converts resume skills and phrases into numerical feature vectors for ML classification "
                    "and document relevance scoring."
                ),
            },
            {
                "id": "logistic_regression",
                "name": "Logistic Regression",
                "phase": "Role classification",
                "used": bool(ml.get("available")),
                "modules": ["role_predictor.py", "role_model.pkl"],
                "description": (
                    "Classifies the resume to predict the applicant's target career role "
                    "(e.g. Machine Learning Engineer, Data Analyst, Full Stack Developer, DevOps Engineer)."
                ),
                "classes": ml.get("classes") or [],
            },
            {
                "id": "sentence_transformers_cosine",
                "name": "Sentence Transformers & Cosine Similarity",
                "phase": "Semantic matching",
                "used": bool(caps.get("embeddings")),
                "modules": ["nlp_engine.py"],
                "description": (
                    "Encodes resumes and job descriptions into dense embeddings and computes cosine similarity "
                    "for precise match scores and skill-gap analysis."
                ),
                "embedding_model": caps.get("embedding_model"),
            },
            {
                "id": "gemini_llm",
                "name": "Generative Artificial Intelligence (Gemini LLM)",
                "phase": "Intelligence & roadmap",
                "used": _genai_client is not None,
                "modules": ["main.py"],
                "model": "gemini-2.5-flash",
                "description": (
                    "Validates uploads, produces domain-aware ATS narrative and role realism checks, "
                    "and generates personalized milestone roadmaps as structured JSON."
                ),
            },
        ],
        "docs": "See ALGORITHMS.md in the project root.",
    }


@app.get("/health")
def health():
    caps = engine_capabilities()
    ml = role_predictor_status()
    return {
        "status": "ok",
        "jobs_provider": jobs_provider_status(),
        "nlp_engine": caps,
        "gemini_enabled": _genai_client is not None,
        "role_predictor": ml,
        "algorithms": {
            "nlp_parsing": True,
            "tfidf": bool(ml.get("available")),
            "logistic_regression": bool(ml.get("available")),
            "sentence_transformers_cosine": bool(caps.get("embeddings")),
            "gemini_llm": _genai_client is not None,
        },
    }


@app.get("/analyze")
def analyze_get_info():
    return {
        "detail": "Use POST with multipart form field 'file' (PDF or DOCX).",
        "field": "file",
        "accepted": sorted(SUPPORTED_RESUME_EXTENSIONS),
    }


@app.get("/api/analyze")
def analyze_get_info_compat():
    return analyze_get_info()


@app.post("/api/fetch-jobs")
def api_fetch_jobs(body: FetchJobsRequest):
    roles = [str(r).strip() for r in (body.recommended_roles or []) if str(r).strip()][:5]
    if not roles:
        raise HTTPException(status_code=400, detail="recommended_roles must be a non-empty list.")
    payload = _build_jobs_payload(
        roles,
        body.matched_skills,
        body.jobs_per_role,
        candidate_location=body.candidate_location,
    )
    return {"recommended_roles": roles, **payload}


# In-memory application log for the session (also written when Mongo is available).
_APPLICATIONS: list[dict[str, Any]] = []


@app.post("/api/apply")
def api_apply_job(body: ApplyJobRequest):
    """Mark that the user is applying to a skill-matched opening (opens external apply URL)."""
    url = (body.redirect_url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="redirect_url must be an http(s) apply link.")
    record = {
        "id": uuid.uuid4().hex,
        "job_title": body.job_title.strip(),
        "company_name": (body.company_name or "Hiring Company").strip(),
        "redirect_url": url,
        "role_category": (body.role_category or "").strip() or None,
        "skill_match_pct": body.skill_match_pct,
        "matched_skills": [str(s).strip() for s in (body.matched_skills or []) if str(s).strip()][:12],
        "candidate_name": (body.candidate_name or "").strip() or None,
        "candidate_email": (body.candidate_email or "").strip() or None,
        "status": "applied",
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    _APPLICATIONS.append(record)
    try:
        from database import save_candidate  # type: ignore
        save_candidate({"type": "job_application", **record})
    except Exception:
        pass
    return {"ok": True, "application": record, "message": "Application started — complete it on the employer portal."}


@app.get("/api/applications")
def api_list_applications():
    return {"applications": list(reversed(_APPLICATIONS[-50:])), "count": len(_APPLICATIONS)}


@app.post("/api/intelligence")
def career_intelligence(body: ResumeTextRequest):
    """Return recruiter simulation, heatmap, career DNA, interview prompts and timeline."""
    return _analyze_text_intelligence(body.resume_text)


@app.post("/api/role-analysis")
def role_analysis(body: RoleAnalysisRequest):
    """Analyze resume skills against a user-specified target role and surface openings."""
    text = _normalize_resume_text(body.resume_text)
    if not _heuristic_is_resume(text):
        raise HTTPException(status_code=422, detail=INVALID_RESUME_ERROR)
    domain = detect_domain(text)
    metadata = _extract_candidate_details(text)
    matched = sanitize_skills(extract_professional_skills(text, domain), metadata)
    result = analyze_for_target_role(matched, body.target_role)
    # Pull live openings for the explored role using skills the candidate already has.
    role_name = str(result.get("matched_role") or body.target_role).strip()
    have = result.get("skills_you_have") or matched
    jobs_payload = _build_jobs_payload(
        [role_name],
        have,
        jobs_per_role=min(12, JOBS_PER_ROLE),
        resume_text=text,
        candidate_location=metadata.get("candidate_location"),
    )
    result.update(jobs_payload)
    return result


@app.post("/api/job-match")
def job_match(body: JobMatchRequest):
    """Explain a resume-to-job match using normalized skills and document evidence."""
    text = _normalize_resume_text(body.resume_text)
    if not _heuristic_is_resume(text):
        raise HTTPException(status_code=422, detail=INVALID_RESUME_ERROR)
    jd = _normalize_resume_text(body.job_description)
    domain = detect_domain(text)
    jd_domain = detect_domain(jd)
    jd_skills = sanitize_skills(extract_professional_skills(jd, jd_domain), {})
    # Score the resume against the job description directly (semantic).
    matched = sanitize_skills(extract_professional_skills(text, domain), {})
    missing = compute_missing_skills(matched, domain)
    scorecard = _build_scorecard(text, matched, missing, domain, job_description=jd)
    report = semantic_match_skills(text, jd_skills)
    matched_jd = [m["skill"] for m in report["matched"]]
    missing_jd = [m["skill"] for m in report["missing"]]
    jd_rel = scorecard.get("jd_relevance")
    return {
        "target_role": body.target_role or "Target role",
        "match_score": scorecard["sections"].get("Skill Match", scorecard["overall"]),
        "overall_ats": scorecard["overall"],
        "confidence": scorecard.get("confidence"),
        "jd_relevance_pct": round((jd_rel or 0) * 100) if jd_rel is not None else None,
        "score_explanation": [
            f"{len(matched_jd)} of {len(jd_skills)} job-description skills are evidenced in the resume (semantic + ontology matching).",
            f"Resume domain: {domain}; job-description domain: {jd_domain}.",
            (f"Overall resume/JD semantic relevance: {round((jd_rel or 0)*100)}%." if jd_rel is not None else
             "Semantic embeddings unavailable — using ontology + keyword relevance."),
        ] + scorecard.get("evidence", [])[:2],
        "matched_skills": matched_jd,
        "missing_skills": missing_jd,
        "matched_skill_details": report["matched"],
        "resume_scorecard": scorecard,
    }


async def _analyze_impl(file: UploadFile, job_description: str | None = None) -> dict[str, Any]:
    fname = (file.filename or "").lower()
    suffix = Path(fname).suffix.lower()
    if suffix not in SUPPORTED_RESUME_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Word (.docx) resumes are supported.",
        )
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume file too large (max 8 MB).")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    internal = f"{uuid.uuid4().hex}{suffix}"
    path = os.path.join(UPLOAD_DIR, internal)
    try:
        with open(path, "wb") as buffer:
            buffer.write(content)

        try:
            from services.analysis_pipeline import run_full_analysis
            pipeline = run_full_analysis(file_path=path, job_description=job_description)
        except ValueError as ve:
            return JSONResponse(status_code=422, content={"error": str(ve)})
        except Exception as e:
            _log(f"[pipeline] {type(e).__name__}: {e!r}")
            raise HTTPException(
                status_code=500,
                detail=f"Analysis pipeline failed: {type(e).__name__}: {e}",
            ) from e

        resume = pipeline.get("resume") or {}
        role_prediction = pipeline.get("role_prediction") or {}
        semantic = pipeline.get("semantic_analysis") or {}
        ats_analysis = pipeline.get("ats_analysis") or {}
        ai = pipeline.get("ai_analysis") or {}
        text = pipeline.get("resume_text") or ""

        matched = list(semantic.get("matched_skills") or resume.get("skills") or [])[:24]
        missing = list(semantic.get("missing_skills") or ai.get("missing_skills") or [])[:16]
        role = str(pipeline.get("realistic_role") or pipeline.get("predicted_role") or "Graduate Trainee")
        ml_role_name = str(role_prediction.get("predicted_role") or role)
        recommended_roles = merge_recommended_roles(
            [role, ml_role_name]
            + [a.get("role") for a in (role_prediction.get("alternative_roles") or []) if a.get("role")],
            infer_roles_from_skills(matched, resume.get("detected_domain") or detect_domain(text)),
            limit=6,
        )

        domain = str(resume.get("detected_domain") or detect_domain(text))
        scorecard = _build_scorecard(text, matched, missing, domain)
        ats = int(ats_analysis.get("ats_score") or scorecard.get("overall") or 0)
        scorecard["overall"] = ats
        scorecard["pipeline_breakdown"] = ats_analysis.get("score_breakdown")

        loc_details = _extract_candidate_details(text)
        details = {
            "candidate_name": resume.get("name") or "Not found",
            "candidate_email": resume.get("email") or "Not found",
            "candidate_phone": resume.get("phone") or "Not found",
            "candidate_college": "Not found",
            "candidate_location": loc_details.get("candidate_location", "Not found"),
        }
        for edu in resume.get("education") or []:
            if isinstance(edu, dict) and edu.get("raw"):
                details["candidate_college"] = edu["raw"]
                break

        intelligence = _build_career_intelligence(text, matched, missing, domain, scorecard)
        jobs_payload = _build_jobs_payload(
            recommended_roles,
            matched,
            resume_text=text,
            candidate_location=details.get("candidate_location"),
        )

        learning_roadmap = ai.get("learning_roadmap") or []
        if learning_roadmap and "step" not in (learning_roadmap[0] or {}):
            learning_roadmap = [
                {
                    "step": item.get("phase", i + 1),
                    "title": item.get("title", f"Phase {i + 1}"),
                    "focus": ", ".join(item.get("skills") or []) or item.get("duration", ""),
                    "project_idea": "; ".join(item.get("projects") or []) or item.get("duration", ""),
                }
                for i, item in enumerate(learning_roadmap)
            ]

        conf = float(role_prediction.get("confidence") or 0)
        conf_pct = round(conf * 100, 1) if conf <= 1 else round(conf, 1)

        algorithms_used = {
            "nlp_parsing": {
                "name": "Natural Language Processing (NLP)",
                "used": True,
                "details": "Structured PDF/DOCX parse → name, contact, skills, education, experience, projects",
            },
            "tfidf": {
                "name": "TF-IDF (Term Frequency–Inverse Document Frequency)",
                "used": True,
                "details": "Feature extraction for fallback role classification",
            },
            "logistic_regression": {
                "name": "Logistic Regression",
                "used": bool(role_prediction.get("available")),
                "details": "Fallback career-role classifier on TF-IDF features",
                "predicted_role": role_prediction.get("predicted_role"),
                "confidence": role_prediction.get("confidence"),
            },
            "sentence_transformers_cosine": {
                "name": "Sentence Transformers & Cosine Similarity",
                "used": bool(semantic.get("available")),
                "details": "Dense embeddings + mathematical cosine similarity for job match / skill gap",
                "semantic_match_score": semantic.get("semantic_match_score"),
                "model": semantic.get("model"),
            },
            "gemini_llm": {
                "name": "Generative AI (Gemini LLM)",
                "used": ai.get("provider") == "gemini-2.5-flash",
                "model": "gemini-2.5-flash",
                "details": "Validation, realistic role, roadmap, milestones (does not replace ML pipeline)",
            },
        }

        return {
            "resume": resume,
            "role_prediction": role_prediction,
            "semantic_analysis": semantic,
            "ats_analysis": ats_analysis,
            "ai_analysis": ai,
            "ats_score": ats,
            "predicted_role": ml_role_name,
            "realistic_role": role,
            "role_prediction_source": "tfidf_logistic_regression",
            "ml_role_prediction": {
                "predicted_role": role_prediction.get("predicted_role"),
                "confidence": conf_pct,
                "top_roles": [
                    {
                        "role": a.get("role"),
                        "confidence": round(float(a.get("confidence") or 0) * 100, 1)
                        if float(a.get("confidence") or 0) <= 1
                        else round(float(a.get("confidence") or 0), 1),
                    }
                    for a in (role_prediction.get("alternative_roles") or [])
                ],
                "available": role_prediction.get("available"),
                "algorithm": role_prediction.get("algorithm"),
            },
            "recommended_roles": recommended_roles,
            "matched_skills": matched,
            "missing_skills": missing,
            "detected_domain": domain,
            "learning_roadmap": learning_roadmap,
            "career_milestones": ai.get("career_milestones") or [],
            "custom_suggestion": str(ai.get("summary") or "").strip(),
            "career_suggestions": str(ai.get("summary") or "").strip(),
            "strengths": ai.get("strengths") or [],
            "weaknesses": ai.get("weaknesses") or [],
            "resume_improvements": ai.get("resume_improvements") or [],
            "semantic_match_score": semantic.get("semantic_match_score"),
            "resume_text": text,
            "keywords": matched[:15],
            "candidate_metadata": details,
            "candidate_name": details.get("candidate_name", "Not found"),
            "candidate_email": details.get("candidate_email", "Not found"),
            "candidate_phone": details.get("candidate_phone", "Not found"),
            "candidate_college": details.get("candidate_college", "Not found"),
            "candidate_location": details.get("candidate_location", "Not found"),
            "academic_degrees": resume.get("degrees") or [],
            "years_of_experience": resume.get("total_experience") or 0,
            "scorecard": scorecard,
            "career_intelligence": intelligence,
            "algorithms_used": algorithms_used,
            **jobs_payload,
        }
    except HTTPException:
        raise
    except Exception as e:
        _log(f"[analyze] {type(e).__name__}: {e!r}")
        safe_detail = str(e).encode("ascii", "backslashreplace").decode("ascii")
        raise HTTPException(
            status_code=500,
            detail=safe_detail[:800] if safe_detail else f"Analysis failed: {type(e).__name__}",
        )
    finally:
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(..., description="PDF or DOCX resume"),
    job_description: str | None = Form(default=None),
):
    return await _analyze_impl(file, job_description)


@app.post("/api/analyze")
async def analyze_compat(
    file: UploadFile = File(..., description="PDF or DOCX resume"),
    job_description: str | None = Form(default=None),
):
    return await _analyze_impl(file, job_description)


@app.post("/api/analyze-resume")
async def api_analyze_resume(
    file: UploadFile = File(..., description="PDF or DOCX resume"),
    job_description: str | None = Form(default=None),
):
    """Canonical Smart Resume Analyzer endpoint (full 5-technology pipeline)."""
    return await _analyze_impl(file, job_description)


class PredictRoleBody(BaseModel):
    resume_text: str = Field(min_length=20, max_length=50000)
    skills: list[str] | None = None


class MatchJobBody(BaseModel):
    resume_text: str = Field(min_length=20, max_length=50000)
    job_description: str = Field(min_length=20, max_length=50000)
    resume_skills: list[str] | None = None
    job_skills: list[str] | None = None


class SkillsBody(BaseModel):
    resume_text: str = Field(min_length=20, max_length=50000)
    job_description: str | None = None


class RoadmapBody(BaseModel):
    resume: dict[str, Any] = Field(default_factory=dict)
    role_prediction: dict[str, Any] = Field(default_factory=dict)
    semantic_analysis: dict[str, Any] = Field(default_factory=dict)
    ats_analysis: dict[str, Any] = Field(default_factory=dict)
    job_description: str | None = None


@app.post("/api/predict-role")
def api_predict_role(body: PredictRoleBody):
    """TF-IDF + Logistic Regression fallback role prediction."""
    try:
        from services.role_classifier import predict_role
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Classifier import failed: {exc}")
    return predict_role(body.resume_text, body.skills)


@app.post("/api/match-job")
def api_match_job(body: MatchJobBody):
    """Sentence Transformers + Cosine Similarity resume/JD matching."""
    try:
        from services.similarity_engine import semantic_job_analysis
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Similarity engine import failed: {exc}")
    return semantic_job_analysis(
        body.resume_text,
        body.job_description,
        body.resume_skills,
        body.job_skills,
    )


@app.post("/api/analyze-skills")
def api_analyze_skills(body: SkillsBody):
    """NLP skill extraction + optional semantic gap vs a job description."""
    try:
        from services.resume_parser import parse_resume_structured
        from services.similarity_engine import skill_gap_analysis
        from skills import extract_professional_skills, detect_domain
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    parsed = parse_resume_structured(body.resume_text)
    job_skills = []
    if body.job_description:
        domain = detect_domain(body.job_description)
        job_skills = extract_professional_skills(body.job_description, domain)
    gap = skill_gap_analysis(parsed.get("skills") or [], job_skills, body.resume_text, body.job_description or "")
    return {"resume_skills": parsed.get("skills"), "job_skills": job_skills, **gap}


@app.post("/api/generate-roadmap")
def api_generate_roadmap(body: RoadmapBody):
    """Gemini (or heuristic) roadmap / milestones from structured pipeline outputs."""
    try:
        from services.gemini_service import run_gemini_intelligence
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return run_gemini_intelligence(
        body.resume,
        body.role_prediction,
        body.semantic_analysis,
        body.ats_analysis,
        body.job_description,
    )


_provider = jobs_provider_status()
if not _provider["any_provider"]:
    _log(
        "[jobs] No RAPIDAPI_KEY or ADZUNA_APP_ID/KEY in backend/.env — "
        "live India job cards will stay empty until configured."
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
