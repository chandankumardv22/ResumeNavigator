"""Backward-compatible facade → services.role_classifier (TF-IDF + Logistic Regression). """
from __future__ import annotations

from typing import Any

try:
    from services.role_classifier import (
        predict_role as _predict_role,
        train_and_save,
        classifier_status,
        MODEL_PATH,
        VECTORIZER_PATH,
    )
except Exception:  # pragma: no cover
    _predict_role = None
    train_and_save = None  # type: ignore
    classifier_status = None  # type: ignore
    MODEL_PATH = None
    VECTORIZER_PATH = None


def predict_job_role(resume_text: str, matched_skills: list[str] | None = None) -> dict[str, Any]:
    if _predict_role is None:
        return {"predicted_role": None, "confidence": 0.0, "available": False, "algorithm": "TF-IDF + Logistic Regression"}
    result = _predict_role(resume_text, matched_skills)
    # Legacy UI expected confidence as 0-100 in some places
    conf = float(result.get("confidence") or 0)
    return {
        **result,
        "confidence": round(conf * 100, 1) if conf <= 1 else conf,
        "top_roles": [
            {"role": a.get("role"), "confidence": round(float(a.get("confidence") or 0) * 100, 1)}
            for a in (result.get("alternative_roles") or [])
        ],
    }


def role_predictor_status() -> dict[str, Any]:
    if classifier_status is None:
        return {"available": False, "algorithm": "TF-IDF + Logistic Regression"}
    return classifier_status()
