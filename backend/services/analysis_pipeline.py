"""
Complete Smart Resume Analyzer pipeline orchestrator.

UPLOAD → NLP parse → TF-IDF+LR → Sentence Transformers + Cosine → ATS → Gemini
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.resume_parser import parse_resume_file, parse_resume_structured
from services.role_classifier import predict_role
from services.similarity_engine import semantic_job_analysis
from services.ats_engine import compute_ats_breakdown
from services.gemini_service import run_gemini_intelligence

try:
    from skills import extract_professional_skills, detect_domain
except ImportError:
    extract_professional_skills = None  # type: ignore
    detect_domain = None  # type: ignore


def _job_skills_from_text(job_description: str) -> list[str]:
    if not job_description or not extract_professional_skills:
        return []
    domain = detect_domain(job_description) if detect_domain else "General / Fresher"
    return extract_professional_skills(job_description, domain)[:30]


def _default_jd_from_role(role: str, skills: list[str]) -> str:
    """Synthetic JD for semantic scoring when user did not paste a job description."""
    skill_line = ", ".join(skills[:12]) or "relevant technical skills"
    return (
        f"We are hiring a {role}. Required skills: {skill_line}. "
        f"Responsibilities include delivering projects aligned to the {role} role, "
        f"collaborating with teams, and demonstrating proficiency in {skill_line}."
    )


def run_full_analysis(
    file_path: str | None = None,
    resume_text: str | None = None,
    job_description: str | None = None,
) -> dict[str, Any]:
    # 1) NLP structured parsing
    if file_path:
        resume = parse_resume_file(file_path)
    elif resume_text:
        resume = parse_resume_structured(resume_text)
        resume["raw_text"] = resume_text
    else:
        raise ValueError("Provide a resume file path or resume text.")

    text = resume.get("raw_text") or resume_text or ""
    skills = resume.get("skills") or []

    # 2-3) TF-IDF + Logistic Regression FALLBACK role prediction
    role_prediction = predict_role(text, skills)
    predicted = role_prediction.get("predicted_role") or "Software Developer"

    # 4) Sentence Transformers + Cosine Similarity
    jd = (job_description or "").strip()
    jd_provided = bool(jd)
    if not jd:
        jd = _default_jd_from_role(predicted, skills)
    job_skills = _job_skills_from_text(jd) if jd_provided else list(skills[:8])
    # When no JD, still run embedding cosine vs role-targeted JD for a real score
    semantic = semantic_job_analysis(text, jd, skills, job_skills)
    semantic["job_description_provided"] = jd_provided

    # 5) Deterministic ATS
    ats = compute_ats_breakdown(resume, role_prediction, semantic, job_description)

    # 6) Gemini intelligence (structured inputs only)
    ai = run_gemini_intelligence(resume, role_prediction, semantic, ats, job_description if jd_provided else None)

    # Final role: Gemini realistic_role preferred for display; ML role kept separately
    return {
        "resume": {k: v for k, v in resume.items() if k != "raw_text"},
        "resume_text": text,
        "role_prediction": role_prediction,
        "semantic_analysis": semantic,
        "ats_analysis": ats,
        "ai_analysis": ai,
        "predicted_role": role_prediction.get("predicted_role"),
        "realistic_role": ai.get("realistic_role") or role_prediction.get("predicted_role"),
        "ats_score": ats.get("ats_score"),
        "algorithms": {
            "nlp": True,
            "tfidf": True,
            "logistic_regression": bool(role_prediction.get("available")),
            "sentence_transformers_cosine": bool(semantic.get("available")),
            "gemini": ai.get("provider") == "gemini-2.5-flash",
        },
    }
