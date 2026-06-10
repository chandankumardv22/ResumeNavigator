from __future__ import annotations

import json
import os
import re
import shutil
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from pathlib import Path
from pdf_parser import extract_pdf_text
from pydantic import BaseModel, Field

from skills import (
    DOMAIN_PROFILES,
    _NON_RESUME_SIGNALS,
    _RESUME_SIGNALS,
    compute_missing_skills,
    detect_domain,
    extract_professional_skills,
    infer_roles_from_skills,
    merge_recommended_roles,
    sanitize_skills,
)

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "jsearch.p.rapidapi.com").strip()
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "").strip()
JOBS_PER_ROLE = 4
JOB_API_TIMEOUT = 30
MAX_JOB_ROLES = 5
INVALID_PDF_TEXT_ERROR = (
    "Unable to read text from this PDF. It may be scanned or image-only. "
    "Please upload a text-based PDF exported from Word, Google Docs, or a resume builder."
)
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

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]

INVALID_RESUME_ERROR = "Invalid document type. Please upload a valid resume."

app = FastAPI(title="PathFinder API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
    }


def jobs_provider_status() -> dict[str, Any]:
    has_jsearch = _is_real_key(RAPIDAPI_KEY)
    has_adzuna = _is_real_key(ADZUNA_APP_ID) and _is_real_key(ADZUNA_APP_KEY)
    return {
        "jsearch_configured": has_jsearch,
        "adzuna_configured": has_adzuna,
        "any_provider": has_jsearch or has_adzuna,
    }


def fetch_jsearch_jobs(role_category: str, limit: int = JOBS_PER_ROLE) -> list[dict[str, Any]]:
    if not _is_real_key(RAPIDAPI_KEY):
        return []
    query = f"{role_category} in India"
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
            loc = ", ".join(x for x in [city, country] if x) or "India"
            out.append(
                _job_record(
                    role_category=role_category,
                    company_name=j.get("employer_name") or "Hiring Company",
                    job_title=j.get("job_title") or role_category,
                    location=loc,
                    redirect_url=j.get("job_apply_link") or j.get("job_google_link") or "#",
                    employment_type=j.get("job_employment_type") or "Full-time",
                )
            )
    except Exception as exc:
        _log(f"[JSearch] {type(exc).__name__}: {exc!r}")
    return out[:limit]


def fetch_adzuna_jobs(role_category: str, limit: int = JOBS_PER_ROLE) -> list[dict[str, Any]]:
    if not (_is_real_key(ADZUNA_APP_ID) and _is_real_key(ADZUNA_APP_KEY)):
        return []
    out: list[dict[str, Any]] = []
    try:
        r = requests.get(
            "https://api.adzuna.com/v1/api/jobs/in/search/1",
            params={
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "what": role_category,
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
            loc = loc_obj.get("display_name") or "India"
            out.append(
                _job_record(
                    role_category=role_category,
                    company_name=company,
                    job_title=j.get("title") or role_category,
                    location=loc,
                    redirect_url=j.get("redirect_url") or "#",
                    employment_type=j.get("contract_type") or "Full-time",
                )
            )
    except Exception as exc:
        _log(f"[Adzuna] {type(exc).__name__}: {exc!r}")
    return out[:limit]


def fetch_india_jobs_for_role(role_category: str, limit: int = JOBS_PER_ROLE) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(fetch_jsearch_jobs, role_category, limit),
            pool.submit(fetch_adzuna_jobs, role_category, limit),
        ]
        for future in as_completed(futures):
            for job in future.result():
                url = job.get("redirect_url") or ""
                if url in seen or url == "#":
                    continue
                seen.add(url)
                merged.append(job)
                if len(merged) >= limit:
                    return merged[:limit]
    return merged[:limit]


def fetch_jobs_for_roles(
    roles: list[str],
    per_role_limit: int = JOBS_PER_ROLE,
) -> dict[str, list[dict[str, Any]]]:
    role_names = [str(role).strip() for role in roles if str(role).strip()][:MAX_JOB_ROLES]
    if not role_names:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=min(len(role_names), 5)) as pool:
        futures = {
            pool.submit(fetch_india_jobs_for_role, role_name, per_role_limit): role_name
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
    predicted_role = role_scores[0][0]
    domain_roles = [r for r, _ in role_scores[:5]]
    skill_roles = infer_roles_from_skills(matched, domain)
    recommended_roles = merge_recommended_roles(
        [predicted_role] + domain_roles,
        skill_roles,
        limit=6,
    )

    skill_pool = list(profile["skill_pool"])
    coverage = len(matched) / max(1, len(skill_pool))
    ats_score = int(max(30, min(92, round(38 + coverage * 52))))

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
    return _build_domain_analysis(text)


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

    return {
        "candidate_name": probable_name,
        "candidate_email": email,
        "candidate_phone": phone,
        "candidate_college": college,
    }


def _build_jobs_payload(recommended_roles: list[str]) -> dict[str, Any]:
    jobs_by_role = fetch_jobs_for_roles(recommended_roles, JOBS_PER_ROLE)
    total = sum(len(v) for v in jobs_by_role.values())
    provider = jobs_provider_status()
    message = None
    if not provider["any_provider"]:
        message = "Live job listings are temporarily unavailable. Please try again shortly."
    elif total == 0:
        message = "No active India listings found for your roles right now. Try again shortly."
    return {
        "jobs_by_role": jobs_by_role,
        "jobs": jobs_by_role.get(recommended_roles[0], []) if recommended_roles else [],
        "jobs_count": total,
        "jobs_provider": provider,
        "jobs_message": message,
    }


@app.get("/")
def root():
    return {
        "service": "PathFinder",
        "health": "/health",
        "analyze": "POST /analyze",
        "fetch_jobs": "POST /api/fetch-jobs",
    }


@app.get("/health")
def health():
    return {"status": "ok", "jobs_provider": jobs_provider_status()}


@app.get("/analyze")
def analyze_get_info():
    return {"detail": "Use POST with multipart form field 'file' (PDF).", "field": "file"}


@app.get("/api/analyze")
def analyze_get_info_compat():
    return analyze_get_info()


@app.post("/api/fetch-jobs")
def api_fetch_jobs(body: FetchJobsRequest):
    roles = [str(r).strip() for r in (body.recommended_roles or []) if str(r).strip()][:5]
    if not roles:
        raise HTTPException(status_code=400, detail="recommended_roles must be a non-empty list.")
    payload = _build_jobs_payload(roles)
    return {"recommended_roles": roles, **payload}


async def _analyze_impl(file: UploadFile) -> dict[str, Any]:
    fname = (file.filename or "").lower()
    if not fname.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")
    internal = f"{uuid.uuid4().hex}.pdf"
    path = os.path.join(UPLOAD_DIR, internal)
    try:
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            text = _normalize_resume_text(extract_pdf_text(path))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF read error: {type(e).__name__}")
        if not text:
            return JSONResponse(status_code=422, content={"error": INVALID_PDF_TEXT_ERROR})

        ai = analyze_resume(text)
        if ai.get("error"):
            return JSONResponse(
                status_code=422,
                content={"error": ai["error"]},
            )

        role = str(ai.get("predicted_role") or "Graduate Trainee").strip()
        details = _extract_candidate_details(text)
        domain = str(ai.get("detected_domain") or detect_domain(text)).strip()
        matched = sanitize_skills(
            [str(s).strip() for s in (ai.get("matched_skills") or []) if s],
            details,
        )
        if not matched:
            matched = sanitize_skills(extract_professional_skills(text, domain), details)
        skill_roles = infer_roles_from_skills(matched, domain)
        recommended_roles = merge_recommended_roles(
            [role] + [str(x).strip() for x in (ai.get("recommended_roles") or []) if str(x).strip()],
            skill_roles,
            limit=6,
        )
        if not recommended_roles:
            recommended_roles = [role]

        try:
            ats = int(ai.get("ats_score", 0))
        except (TypeError, ValueError):
            ats = 50
        ats = max(0, min(100, ats))

        missing = sanitize_skills(
            [str(s).strip() for s in (ai.get("missing_skills") or []) if s],
            details,
        )
        if not missing:
            missing = compute_missing_skills(matched, domain)
        jobs_payload = _build_jobs_payload(recommended_roles)

        return {
            "ats_score": ats,
            "predicted_role": role,
            "recommended_roles": recommended_roles,
            "matched_skills": matched,
            "missing_skills": missing,
            "detected_domain": domain,
            "learning_roadmap": ai.get("learning_roadmap") or [],
            "custom_suggestion": str(ai.get("custom_suggestion") or "").strip(),
            "career_suggestions": str(ai.get("career_suggestions") or ai.get("custom_suggestion") or "").strip(),
            "keywords": matched[:15],
            "candidate_metadata": details,
            "candidate_name": details.get("candidate_name", "Not found"),
            "candidate_email": details.get("candidate_email", "Not found"),
            "candidate_phone": details.get("candidate_phone", "Not found"),
            "candidate_college": details.get("candidate_college", "Not found"),
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
async def analyze(file: UploadFile = File(..., description="PDF resume")):
    return await _analyze_impl(file)


@app.post("/api/analyze")
async def analyze_compat(file: UploadFile = File(..., description="PDF resume")):
    return await _analyze_impl(file)


_provider = jobs_provider_status()
if not _provider["any_provider"]:
    _log(
        "[jobs] No RAPIDAPI_KEY or ADZUNA_APP_ID/KEY in backend/.env — "
        "live India job cards will stay empty until configured."
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
