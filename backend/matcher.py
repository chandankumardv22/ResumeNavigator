"""Legacy compatibility facade for semantic matching + role prediction.

Prefer ``nlp_engine`` (Sentence Transformers + Cosine Similarity) and
``role_predictor`` (TF-IDF + Logistic Regression) — this module keeps older
imports working without forcing heavy models to load at import time.
"""
from __future__ import annotations

from typing import Any


def calculate_similarity(resume_text: str, job_description: str) -> float:
    try:
        from nlp_engine import _cosine, _embed_texts, _get_embed_model
    except Exception:
        return 0.0
    model = _get_embed_model()
    if model is None:
        return 0.0
    vectors = _embed_texts([resume_text or "", job_description or ""])
    if vectors is None or len(vectors) < 2:
        return 0.0
    return round(float(_cosine(vectors[0], vectors[1])) * 100, 2)


def skill_gap_analysis(resume_text: str, job_description: str) -> dict[str, Any]:
    try:
        from skills import detect_domain, extract_professional_skills, sanitize_skills
        from nlp_engine import semantic_match_skills
    except Exception:
        return {"matched_skills": [], "missing_skills": [], "skill_match_scores": {}}

    domain = detect_domain(job_description or resume_text or "")
    jd_skills = sanitize_skills(extract_professional_skills(job_description or "", domain), {})
    report = semantic_match_skills(resume_text or "", jd_skills)
    matched = [m["skill"] for m in report.get("matched", [])]
    missing = [m["skill"] for m in report.get("missing", [])]
    scores = {
        m["skill"]: round(float(m.get("confidence") or 0) * 100, 2)
        for m in report.get("matched", [])
    }
    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_match_scores": scores,
    }


def generate_learning_roadmap(missing_skills):
    roadmap = []
    for skill in missing_skills or []:
        skill_lower = str(skill).lower()
        if "python" in skill_lower:
            roadmap.append("Complete advanced Python (OOP, DSA)")
        elif "react" in skill_lower:
            roadmap.append("Build 2 React projects with API integration")
        elif "aws" in skill_lower:
            roadmap.append("Complete AWS Cloud Practitioner course")
        elif "docker" in skill_lower:
            roadmap.append("Learn Docker & containerize a project")
        elif "sql" in skill_lower:
            roadmap.append("Practice SQL joins & database design")
        elif "machine learning" in skill_lower:
            roadmap.append("Build 3 ML projects (Regression, Classification, NLP)")
        elif "data analysis" in skill_lower:
            roadmap.append("Learn Pandas, NumPy & create analysis dashboards")
        else:
            roadmap.append(f"Improve knowledge in {skill}")
    return roadmap


def weighted_skill_match(resume_skills, job_description):
    skill_weights = {
        "machine learning": 2.0,
        "deep learning": 2.0,
        "python": 1.5,
        "aws": 1.3,
        "docker": 1.2,
        "react": 1.0,
        "node": 1.0,
        "mongodb": 1.0,
        "sql": 1.2,
        "data analysis": 1.4,
    }
    jd_lower = (job_description or "").lower()
    resume_lower = [str(skill).lower() for skill in (resume_skills or [])]
    total_weight = 0.0
    matched_weight = 0.0
    matched_skills = []
    for skill, weight in skill_weights.items():
        if skill in jd_lower:
            total_weight += weight
            if skill in resume_lower:
                matched_weight += weight
                matched_skills.append(skill)
    if total_weight == 0:
        return 0, []
    return round((matched_weight / total_weight) * 100, 2), matched_skills


def predict_job_role(resume_text: str):
    try:
        from role_predictor import predict_job_role as _predict
    except Exception:
        return "Model Not Trained"
    result = _predict(resume_text or "")
    return result.get("predicted_role") or "Model Not Trained"
