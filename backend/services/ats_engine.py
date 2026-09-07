"""
Domain-aware ATS scoring engine.

Combines measurable signals (skills, keywords, experience, education, projects,
completeness, semantic similarity, role alignment). Does NOT use random scores.
"""
from __future__ import annotations

import re
from typing import Any


def _clamp(n: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def compute_ats_breakdown(
    resume: dict[str, Any],
    role_prediction: dict[str, Any],
    semantic: dict[str, Any],
    job_description: str | None = None,
) -> dict[str, Any]:
    skills = resume.get("skills") or []
    matched = semantic.get("matched_skills") or skills[:8]
    missing = semantic.get("missing_skills") or []
    semantic_score = float(semantic.get("semantic_match_score") or 0)

    # Skills coverage
    denom = max(1, len(matched) + len(missing))
    skills_score = 100 * len(matched) / denom if (matched or missing) else min(70, 15 * len(skills))

    # Keyword relevance from role prediction confidence + skill density
    conf = float(role_prediction.get("confidence") or 0)
    if conf > 1:
        conf = conf / 100.0
    keywords_score = 40 + conf * 50 + min(10, len(skills))

    # Experience
    years = int(resume.get("total_experience") or 0)
    exp_entries = resume.get("experience") or []
    experience_score = min(100, years * 12 + len(exp_entries) * 8 + (15 if years == 0 and not exp_entries else 0))
    if years == 0 and not exp_entries:
        experience_score = 35  # fresher baseline — not zero

    # Education
    education = resume.get("education") or []
    degrees = resume.get("degrees") or []
    education_score = min(100, 40 + len(degrees) * 20 + len(education) * 10)

    # Projects
    projects = resume.get("projects") or []
    projects_score = min(100, 25 + len(projects) * 18)

    # Completeness of parsed fields
    fields = [
        resume.get("name"), resume.get("email"), resume.get("phone"),
        skills, education or degrees, projects, exp_entries or years,
        resume.get("certifications"),
    ]
    filled = sum(1 for f in fields if f)
    completeness_score = 100 * filled / len(fields)

    # Semantic match component
    semantic_component = semantic_score if semantic.get("available") else max(40, skills_score * 0.7)

    # Role alignment from LR confidence
    role_alignment = conf * 100

    # Weighted overall (deterministic)
    weights = {
        "skills": 0.22,
        "keywords": 0.12,
        "experience": 0.15,
        "education": 0.10,
        "projects": 0.12,
        "semantic_match": 0.18,
        "completeness": 0.11,
    }
    breakdown = {
        "skills": _clamp(skills_score),
        "keywords": _clamp(keywords_score),
        "experience": _clamp(experience_score),
        "education": _clamp(education_score),
        "projects": _clamp(projects_score),
        "semantic_match": _clamp(semantic_component),
        "completeness": _clamp(completeness_score),
    }
    # Optional role_alignment baked into keywords already; expose separately
    overall = sum(breakdown[k] * weights[k] for k in weights)
    # Slight boost when role confidence is high
    overall = overall * 0.92 + role_alignment * 0.08

    return {
        "ats_score": _clamp(overall),
        "score_breakdown": breakdown,
        "role_alignment": _clamp(role_alignment),
        "weights": {k: int(v * 100) for k, v in weights.items()},
        "method": "deterministic weighted ATS (skills, keywords, experience, education, projects, semantic, completeness)",
    }
