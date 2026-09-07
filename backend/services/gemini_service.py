"""
Gemini 2.5 Flash intelligence layer (Technology #5)

Receives STRUCTURED outputs from NLP / TF-IDF+LR / Sentence-Transformers.
Does NOT replace those models — validates roles, interprets gaps, builds roadmaps.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND / ".env")

GEMINI_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "resume_valid": {"type": "boolean"},
        "predicted_role": {"type": "string"},
        "realistic_role": {"type": "string"},
        "ats_score": {"type": "integer"},
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "matched_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "skill_gap_analysis": {"type": "array", "items": {"type": "string"}},
        "resume_improvements": {"type": "array", "items": {"type": "string"}},
        "recommended_skills": {"type": "array", "items": {"type": "string"}},
        "learning_roadmap": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "phase": {"type": "integer"},
                    "title": {"type": "string"},
                    "duration": {"type": "string"},
                    "skills": {"type": "array", "items": {"type": "string"}},
                    "projects": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["phase", "title", "duration", "skills", "projects"],
            },
        },
        "career_milestones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "milestone": {"type": "string"},
                    "target": {"type": "string"},
                    "skills_required": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["milestone", "target", "skills_required"],
            },
        },
    },
    "required": [
        "resume_valid", "predicted_role", "realistic_role", "ats_score", "summary",
        "strengths", "weaknesses", "matched_skills", "missing_skills",
        "skill_gap_analysis", "resume_improvements", "recommended_skills",
        "learning_roadmap", "career_milestones",
    ],
}


def _client():
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    placeholders = {"", "your_gemini_api_key", "changeme"}
    if key.lower() in placeholders:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception:
        return None


def gemini_available() -> bool:
    return _client() is not None


def _heuristic_intelligence(
    resume: dict[str, Any],
    role_prediction: dict[str, Any],
    semantic: dict[str, Any],
    ats: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic fallback when Gemini key is missing — still structured, not random."""
    ml_role = role_prediction.get("predicted_role") or "Software Developer"
    years = int(resume.get("total_experience") or 0)
    if years <= 0:
        realistic = f"Entry-Level {ml_role}" if not ml_role.lower().startswith(("entry", "junior", "intern")) else ml_role
        if "senior" in ml_role.lower():
            realistic = ml_role.replace("Senior", "Entry-Level").replace("senior", "entry-level")
    elif years < 2:
        realistic = f"Junior {ml_role}" if "junior" not in ml_role.lower() else ml_role
    else:
        realistic = ml_role

    matched = semantic.get("matched_skills") or (resume.get("skills") or [])[:6]
    missing = semantic.get("missing_skills") or []
    score = int(ats.get("ats_score") or 0)

    roadmap = [
        {
            "phase": 1,
            "title": "Strengthen core skills",
            "duration": "30 days",
            "skills": missing[:3] or (resume.get("skills") or [])[:3],
            "projects": [f"Build a small portfolio project aligned to {realistic}"],
        },
        {
            "phase": 2,
            "title": "Demonstrate applied ability",
            "duration": "30-60 days",
            "skills": missing[3:6] or matched[:3],
            "projects": ["Document measurable outcomes on GitHub or a case study"],
        },
        {
            "phase": 3,
            "title": "Interview & applications",
            "duration": "60-90 days",
            "skills": matched[:4],
            "projects": [f"Apply to {realistic} roles with a tailored resume"],
        },
    ]
    return {
        "resume_valid": True,
        "predicted_role": ml_role,
        "realistic_role": realistic,
        "ats_score": score,
        "summary": (
            f"Based on parsed evidence ({years}y experience, {len(resume.get('skills') or [])} skills), "
            f"the TF-IDF/LR model suggests {ml_role}. A realistic target is {realistic}."
        ),
        "strengths": matched[:5] or ["Foundational skills detected on resume"],
        "weaknesses": missing[:5] or ["Add quantified impact bullets"],
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_gap_analysis": [
            f"Prioritize learning {s} to improve fit for {realistic}" for s in missing[:5]
        ] or ["Continue deepening matched skills with projects"],
        "resume_improvements": [
            "Add measurable outcomes (%, time saved, users impacted)",
            "Ensure skills section mirrors target job keywords",
            "Keep experience bullets action-verb led",
        ],
        "recommended_skills": missing[:6],
        "learning_roadmap": roadmap,
        "career_milestones": [
            {"milestone": "Portfolio ready", "target": "30 days", "skills_required": matched[:3] or missing[:2]},
            {"milestone": "First interviews", "target": "60 days", "skills_required": (matched + missing)[:4]},
            {"milestone": f"Land {realistic} role", "target": "90 days", "skills_required": missing[:3] or matched[:3]},
        ],
        "provider": "heuristic_fallback",
        "note": "Gemini API key not configured — used structured heuristic intelligence. Set GEMINI_API_KEY for full Gemini analysis.",
    }


def run_gemini_intelligence(
    resume: dict[str, Any],
    role_prediction: dict[str, Any],
    semantic: dict[str, Any],
    ats: dict[str, Any],
    job_description: str | None = None,
) -> dict[str, Any]:
    client = _client()
    if client is None:
        return _heuristic_intelligence(resume, role_prediction, semantic, ats)

    from google.genai import types

    payload = {
        "parsed_resume": {
            "name": resume.get("name"),
            "email": resume.get("email"),
            "skills": resume.get("skills"),
            "programming_languages": resume.get("programming_languages"),
            "tools_technologies": resume.get("tools_technologies"),
            "education": resume.get("education"),
            "degrees": resume.get("degrees"),
            "certifications": resume.get("certifications"),
            "projects": resume.get("projects"),
            "experience": resume.get("experience"),
            "total_experience": resume.get("total_experience"),
            "detected_domain": resume.get("detected_domain"),
        },
        "tfidf_logistic_regression_prediction": role_prediction,
        "semantic_analysis": {
            "semantic_match_score": semantic.get("semantic_match_score"),
            "matched_skills": semantic.get("matched_skills"),
            "missing_skills": semantic.get("missing_skills"),
            "cosine_similarity": semantic.get("cosine_similarity"),
        },
        "deterministic_ats": ats,
        "job_description": (job_description or "")[:4000],
    }

    prompt = f"""You are ResumeNavigator's advanced intelligence layer (Gemini 2.5 Flash).
Other models already ran:
  1) NLP structured parsing
  2) TF-IDF + Logistic Regression role prediction (FALLBACK classifier)
  3) Sentence Transformers + Cosine Similarity semantic match

Your job is NOT to replace them. You must:
- Validate whether the resume is legitimate
- Interpret whether the ML-predicted role is REALISTIC given experience level
  (e.g. student / 0 years → Entry-Level or Junior, NEVER Senior)
- Refine ATS narrative using the deterministic score as an anchor (±8 points max)
- Explain skill gaps, resume improvements, learning roadmap, career milestones

Return ONLY JSON matching the schema.

STRUCTURED INPUT:
{json.dumps(payload, ensure_ascii=False)[:12000]}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=GEMINI_SCHEMA,
                temperature=0.2,
            ),
        )
        data = json.loads(response.text)
        data["provider"] = "gemini-2.5-flash"
        # Anchor ATS to deterministic score if Gemini drifts wildly
        det = int(ats.get("ats_score") or 0)
        try:
            g = int(data.get("ats_score") or det)
            if abs(g - det) > 8:
                data["ats_score"] = det
                data["ats_note"] = "Anchored to deterministic ATS (±8 cap from Gemini suggestion)."
            else:
                data["ats_score"] = g
        except (TypeError, ValueError):
            data["ats_score"] = det
        return data
    except Exception as exc:
        fallback = _heuristic_intelligence(resume, role_prediction, semantic, ats)
        fallback["error"] = f"Gemini error: {type(exc).__name__}: {exc}"
        fallback["provider"] = "heuristic_after_gemini_error"
        return fallback
