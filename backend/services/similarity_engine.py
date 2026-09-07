"""
Sentence Transformers + Cosine Similarity (Technologies #4)

- Encode full resume → dense embedding
- Encode job description → dense embedding
- Cosine similarity → semantic_match_score
- Skill-gap analysis from matched/missing skills
"""
from __future__ import annotations

import os
import threading
from typing import Any

_lock = threading.Lock()
_model = None
_model_name: str | None = None

DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _embeddings_enabled() -> bool:
    flag = os.getenv("ENABLE_EMBEDDINGS", "true").strip().lower()
    return flag in ("1", "true", "yes", "on")


def get_sentence_transformer():
    """Lazy-load SentenceTransformer (all-MiniLM-L6-v2 by default)."""
    global _model, _model_name
    if not _embeddings_enabled():
        return None
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from sentence_transformers import SentenceTransformer
            for name in (DEFAULT_MODEL, "sentence-transformers/all-MiniLM-L6-v2"):
                try:
                    _model = SentenceTransformer(name)
                    _model_name = name
                    return _model
                except Exception:
                    continue
        except Exception:
            return None
    return None


def _cosine_similarity(a, b) -> float:
    """Mathematical cosine similarity between two vectors."""
    import numpy as np

    va = np.asarray(a, dtype=float).ravel()
    vb = np.asarray(b, dtype=float).ravel()
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def embed_text(text: str):
    model = get_sentence_transformer()
    if model is None or not (text or "").strip():
        return None
    return model.encode(text, normalize_embeddings=True)


def cosine_match_score(resume_text: str, job_description: str) -> dict[str, Any]:
    """
    Embed resume + JD with Sentence Transformers, compute cosine similarity.
    Score is 0-100.
    """
    model = get_sentence_transformer()
    if model is None:
        return {
            "semantic_match_score": 0,
            "available": False,
            "method": "unavailable",
            "model": None,
            "error": "Sentence Transformers not available. pip install -r requirements-ml.txt and set ENABLE_EMBEDDINGS=true",
        }

    resume_emb = embed_text(resume_text or "")
    job_emb = embed_text(job_description or "")
    if resume_emb is None or job_emb is None:
        return {
            "semantic_match_score": 0,
            "available": False,
            "method": "encode_failed",
            "model": _model_name,
        }

    sim = _cosine_similarity(resume_emb, job_emb)
    # Cosine on normalized embeddings is typically [-1,1]; clamp to [0,1] for scores
    sim01 = max(0.0, min(1.0, (sim + 1) / 2 if sim < 0 else sim))
    # Prefer direct cosine when embeddings are L2-normalized (dot product ≈ cosine in [0,1] for similar docs)
    if sim >= 0:
        sim01 = max(0.0, min(1.0, sim))

    return {
        "semantic_match_score": int(round(sim01 * 100)),
        "cosine_similarity": round(float(sim), 6),
        "available": True,
        "method": "sentence_transformers_cosine",
        "model": _model_name or DEFAULT_MODEL,
        "algorithm": "Sentence Transformers + Cosine Similarity",
    }


def skill_gap_analysis(
    resume_skills: list[str],
    job_skills: list[str],
    resume_text: str = "",
    job_description: str = "",
) -> dict[str, Any]:
    """Skill-gap analysis with optional embedding-assisted matching."""
    rset = {s.lower().strip(): s for s in (resume_skills or []) if s}
    jset = {s.lower().strip(): s for s in (job_skills or []) if s}

    matched_keys = set(rset) & set(jset)
    missing_keys = set(jset) - set(rset)
    additional_keys = set(rset) - set(jset)

    # Soft semantic matches for near-synonyms when embeddings available
    soft_matched: list[str] = []
    model = get_sentence_transformer()
    if model is not None and missing_keys and resume_text:
        resume_emb = embed_text(resume_text[:4000])
        still_missing = []
        for key in list(missing_keys):
            skill_emb = embed_text(jset[key])
            if resume_emb is not None and skill_emb is not None:
                sim = _cosine_similarity(resume_emb, skill_emb)
                if sim >= 0.55:
                    soft_matched.append(jset[key])
                    matched_keys.add(key)
                    continue
            still_missing.append(key)
        missing_keys = set(still_missing)

    matched = [jset[k] if k in jset else rset[k] for k in matched_keys]
    missing = [jset[k] for k in missing_keys]
    additional = [rset[k] for k in additional_keys]
    skill_gap = [
        {"skill": s, "status": "missing", "recommendation": f"Learn and demonstrate {s} in a project or coursework."}
        for s in missing[:15]
    ]

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "additional_skills": additional,
        "skill_gap": skill_gap,
        "soft_semantic_matches": soft_matched,
    }


def semantic_job_analysis(
    resume_text: str,
    job_description: str,
    resume_skills: list[str] | None = None,
    job_skills: list[str] | None = None,
) -> dict[str, Any]:
    """Complete semantic matching package for a resume vs job description."""
    score_block = cosine_match_score(resume_text, job_description or resume_text)
    # If no JD provided, compare resume to itself as baseline calibration — callers should pass JD
    gap = skill_gap_analysis(resume_skills or [], job_skills or [], resume_text, job_description or "")
    return {
        "semantic_match_score": score_block.get("semantic_match_score", 0),
        "cosine_similarity": score_block.get("cosine_similarity"),
        "matched_skills": gap["matched_skills"],
        "missing_skills": gap["missing_skills"],
        "additional_skills": gap["additional_skills"],
        "skill_gap": gap["skill_gap"],
        "available": score_block.get("available", False),
        "model": score_block.get("model"),
        "algorithm": "Sentence Transformers + Cosine Similarity",
        "error": score_block.get("error"),
    }


def embedding_status() -> dict[str, Any]:
    model = get_sentence_transformer()
    return {
        "available": model is not None,
        "enabled": _embeddings_enabled(),
        "model": _model_name or DEFAULT_MODEL,
        "algorithm": "Sentence Transformers + Cosine Similarity",
    }
