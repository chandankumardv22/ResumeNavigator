"""Enterprise-grade NLP / ML engine for ResumeNavigator.

This module upgrades the platform from keyword counting to a multi-signal,
semantic, explainable ATS engine. Every heavy dependency is OPTIONAL and loaded
lazily behind a capability flag, so the API keeps running (falling back to the
deterministic ontology/regex layer) even on a machine where the ML stack is not
installed. Install the extras from ``requirements.txt`` to unlock:

    * sentence-transformers  -> true embedding-based semantic skill matching
    * spaCy (en_core_web_sm) -> NER + dependency-parsed action/impact detection
    * scikit-learn           -> TF-IDF keyword importance
    * rank-bm25              -> BM25 resume<->JD relevance
    * rapidfuzz              -> fuzzy skill / role normalisation
    * textstat               -> Flesch / Flesch-Kincaid readability
    * language-tool-python   -> grammar & spelling (needs Java; optional)

The scoring engine implements the weighted rubric requested by the product:

    Resume Structure 15 | Skill Match 25 | Experience 20 | Projects 15
    Education 10 | Formatting 5 | Achievements 5 | Grammar 5

and derives Confidence, Recruiter Readiness, Interview Probability and Hiring
Confidence from the sub-signals, each with human-readable explanations.
"""

from __future__ import annotations

import os
import re
import sys
import threading
from functools import lru_cache
from typing import Any

try:  # Package vs. flat launch (matches main.py's dual-import strategy)
    from .skills import (
        CERTIFICATION_PROVIDERS, DOMAIN_PROFILES, SKILL_ONTOLOGY,
        STRONG_ACTION_VERBS, WEAK_VERBS, build_skill_vocabulary,
        detect_certifications, detect_degrees, detect_resume_sections,
        detect_soft_skills, expand_skill_terms,
    )
except ImportError:  # pragma: no cover
    from skills import (
        CERTIFICATION_PROVIDERS, DOMAIN_PROFILES, SKILL_ONTOLOGY,
        STRONG_ACTION_VERBS, WEAK_VERBS, build_skill_vocabulary,
        detect_certifications, detect_degrees, detect_resume_sections,
        detect_soft_skills, expand_skill_terms,
    )


def _log(msg: object) -> None:
    try:
        sys.stderr.write(f"[nlp] {msg}\n")
        sys.stderr.flush()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Optional capability probing (import errors are expected and handled)
# ---------------------------------------------------------------------------
_EMBED_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
_EMBED_FALLBACK = "sentence-transformers/all-MiniLM-L6-v2"
# Embeddings are OFF by default so the first /analyze never blocks on a large
# model download. Set ENABLE_EMBEDDINGS=true in backend/.env to turn them on.
_ENABLE_EMBEDDINGS = os.getenv("ENABLE_EMBEDDINGS", "true").strip().lower() in ("1", "true", "yes", "on")

_HAS_ST = False
_HAS_NUMPY = False
_HAS_SPACY = False
_HAS_SKLEARN = False
_HAS_BM25 = False
_HAS_RAPIDFUZZ = False
_HAS_TEXTSTAT = False

try:
    import numpy as _np  # noqa: N812
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    _np = None

try:
    from sentence_transformers import SentenceTransformer  # noqa: F401
    _HAS_ST = True
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

try:
    import spacy  # noqa: F401
    _HAS_SPACY = True
except Exception:  # pragma: no cover
    spacy = None  # type: ignore

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
    _HAS_SKLEARN = True
except Exception:  # pragma: no cover
    TfidfVectorizer = None  # type: ignore

try:
    from rank_bm25 import BM25Okapi  # noqa: F401
    _HAS_BM25 = True
except Exception:  # pragma: no cover
    BM25Okapi = None  # type: ignore

try:
    from rapidfuzz import fuzz as _rf_fuzz
    _HAS_RAPIDFUZZ = True
except Exception:  # pragma: no cover
    _rf_fuzz = None

try:
    import textstat as _textstat
    _HAS_TEXTSTAT = True
except Exception:  # pragma: no cover
    _textstat = None


# ---------------------------------------------------------------------------
# Lazy model singletons (thread-safe; first request pays the load cost)
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_embed_model = None
_embed_model_loaded_name: str | None = None
_spacy_nlp = None
_spacy_tried = False


def _get_embed_model():
    """Load the sentence-transformer once. Prefer mpnet, fall back to MiniLM."""
    global _embed_model, _embed_model_loaded_name
    if not (_HAS_ST and _HAS_NUMPY and _ENABLE_EMBEDDINGS):
        return None
    if _embed_model is not None:
        return _embed_model
    with _model_lock:
        if _embed_model is not None:
            return _embed_model
        for name in (_EMBED_MODEL_NAME, _EMBED_FALLBACK):
            try:
                _log(f"loading embedding model: {name}")
                _embed_model = SentenceTransformer(name)
                _embed_model_loaded_name = name
                _log(f"embedding model ready: {name}")
                return _embed_model
            except Exception as exc:  # pragma: no cover
                _log(f"failed to load {name}: {exc!r}")
        return None


def _get_spacy():
    global _spacy_nlp, _spacy_tried
    if not _HAS_SPACY:
        return None
    if _spacy_nlp is not None or _spacy_tried:
        return _spacy_nlp
    with _model_lock:
        if _spacy_tried:
            return _spacy_nlp
        _spacy_tried = True
        for name in ("en_core_web_sm", "en_core_web_md"):
            try:
                _spacy_nlp = spacy.load(name, disable=["lemmatizer"])
                _log(f"spaCy model ready: {name}")
                return _spacy_nlp
            except Exception:
                continue
        try:  # blank pipeline still gives us the sentence splitter
            _spacy_nlp = spacy.blank("en")
            _spacy_nlp.add_pipe("sentencizer")
            _log("spaCy blank pipeline (no NER model installed)")
        except Exception as exc:  # pragma: no cover
            _log(f"spaCy unavailable: {exc!r}")
            _spacy_nlp = None
        return _spacy_nlp


def engine_capabilities() -> dict[str, bool]:
    return {
        "embeddings": bool(_HAS_ST and _HAS_NUMPY and _ENABLE_EMBEDDINGS),
        "embeddings_installed": bool(_HAS_ST and _HAS_NUMPY),
        "embedding_model": _embed_model_loaded_name or _EMBED_MODEL_NAME,
        "spacy_ner": _HAS_SPACY,
        "tfidf": _HAS_SKLEARN,
        "bm25": _HAS_BM25,
        "fuzzy": _HAS_RAPIDFUZZ,
        "readability": _HAS_TEXTSTAT,
    }


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------
@lru_cache(maxsize=2048)
def _embed_cached(text: str):
    model = _get_embed_model()
    if model is None:
        return None
    try:
        vec = model.encode(text, normalize_embeddings=True)
        return vec
    except Exception as exc:  # pragma: no cover
        _log(f"encode failed: {exc!r}")
        return None


def _cosine(a, b) -> float:
    if a is None or b is None or not _HAS_NUMPY:
        return 0.0
    try:
        return float(_np.dot(a, b))  # vectors are already normalised
    except Exception:
        return 0.0


def semantic_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity in [0, 1]; 0.0 when embeddings are unavailable."""
    va, vb = _embed_cached(text_a[:2000]), _embed_cached(text_b[:2000])
    if va is None or vb is None:
        return 0.0
    return max(0.0, min(1.0, _cosine(va, vb)))


# ---------------------------------------------------------------------------
# Semantic skill matching
# ---------------------------------------------------------------------------
_SIM_THRESHOLD = float(os.getenv("SKILL_SIM_THRESHOLD", "0.55"))


def semantic_match_skills(
    resume_text: str, required_skills: list[str], threshold: float | None = None
) -> dict[str, Any]:
    """Decide which required skills the resume satisfies, semantically.

    Three layers, best-available first:
      1. Ontology expansion  (Flask/Pandas -> python, deterministic)
      2. Fuzzy string match  (rapidfuzz, catches typos/variants)
      3. Embedding cosine     (true semantic relatedness)

    Returns matched / missing lists plus per-skill evidence & confidence.
    """
    threshold = _SIM_THRESHOLD if threshold is None else threshold
    lower = resume_text.lower()
    implied = expand_skill_terms(lower)  # canonical skills implied by concrete terms
    resume_vec = _embed_cached(resume_text[:2000])

    matched: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for skill in required_skills:
        s = str(skill).strip()
        if not s:
            continue
        sl = s.lower()
        method = None
        confidence = 0.0
        evidence = ""

        # 1. exact / substring
        if sl in lower:
            method, confidence, evidence = "exact", 0.99, f"'{s}' appears directly in the resume"
        # 2. ontology (semantic-by-knowledge-graph)
        elif sl in implied or any(a in lower for a in SKILL_ONTOLOGY.get(sl, [])):
            related = [a for a in SKILL_ONTOLOGY.get(sl, []) if a in lower]
            method = "ontology"
            confidence = 0.85
            evidence = (
                f"related tools imply '{s}': {', '.join(related[:3])}"
                if related else f"'{s}' inferred from related competencies"
            )
        # 3. fuzzy
        elif _HAS_RAPIDFUZZ and _best_fuzzy(sl, lower) >= 88:
            method = "fuzzy"
            confidence = 0.7
            evidence = f"close textual variant of '{s}' detected"
        else:
            # 4. embeddings against the whole resume
            sim = 0.0
            if resume_vec is not None:
                sv = _embed_cached(s)
                sim = _cosine(resume_vec, sv) if sv is not None else 0.0
            if sim >= threshold:
                method = "semantic"
                confidence = round(min(0.95, 0.5 + sim / 2), 2)
                evidence = f"semantically related content found (similarity {sim:.2f})"

        if method:
            matched.append({"skill": s, "method": method, "confidence": confidence, "evidence": evidence})
        else:
            missing.append({"skill": s, "confidence": 0.0})

    return {"matched": matched, "missing": missing}


def _best_fuzzy(needle: str, haystack: str) -> float:
    if not _HAS_RAPIDFUZZ:
        return 0.0
    try:
        return float(_rf_fuzz.partial_ratio(needle, haystack))
    except Exception:
        return 0.0


def extract_semantic_skills(resume_text: str, domain: str, limit: int = 30) -> list[str]:
    """Skills present in the resume, expanded with ontology-implied competencies."""
    lower = resume_text.lower()
    vocab = build_skill_vocabulary(domain)
    found: list[str] = []
    seen: set[str] = set()
    for skill in vocab:
        sl = skill.lower()
        if sl in seen:
            continue
        if sl in lower or any(a in lower for a in SKILL_ONTOLOGY.get(sl, [])):
            seen.add(sl)
            found.append(skill)
    for canonical in expand_skill_terms(lower):
        if canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
        if len(found) >= limit:
            break
    return found[:limit]


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
_QUANT_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:%|x|k|m|bn|users|customers|clients|projects|days|"
    r"hours|lakhs?|crores?|million|billion|revenue|cost|reduction|increase|"
    r"f1|accuracy|precision|recall)\b",
    re.IGNORECASE,
)
_YEAR_RANGE_RE = re.compile(r"\b(19|20)\d{2}\s*[-–—to]{1,3}\s*((19|20)\d{2}|present|current)\b", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\-\s]?)?\d{10}")
_LINKEDIN_RE = re.compile(r"linkedin\.com/\S+", re.IGNORECASE)
_GITHUB_RE = re.compile(r"github\.com/\S+", re.IGNORECASE)
_PORTFOLIO_RE = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{1,}", text.lower())


def detect_action_verbs(text_lower: str) -> dict[str, Any]:
    strong = sorted({v for v in STRONG_ACTION_VERBS if re.search(r"\b" + re.escape(v) + r"\b", text_lower)})
    weak = sorted({v for v in WEAK_VERBS if re.search(r"\b" + re.escape(v) + r"\b", text_lower)})
    return {"strong": strong, "weak": weak, "strong_count": len(strong), "weak_count": len(weak)}


def detect_achievements(text: str) -> list[str]:
    achievements: list[str] = []
    for line in text.splitlines():
        clean = line.strip()
        if len(clean) < 8:
            continue
        if _QUANT_RE.search(clean):
            achievements.append(clean[:200])
    # dedupe preserving order
    out, seen = [], set()
    for a in achievements:
        k = a.lower()
        if k not in seen:
            seen.add(k)
            out.append(a)
    return out[:12]


def years_of_experience(text: str) -> float:
    """Best-effort estimate combining explicit statements and year ranges."""
    lower = text.lower()
    explicit = re.findall(r"(\d+(?:\.\d+)?)\+?\s*years?", lower)
    best_explicit = max((float(x) for x in explicit), default=0.0)
    span = 0.0
    for m in _YEAR_RANGE_RE.finditer(lower):
        start = int(m.group(0)[:4])
        end_raw = m.group(2)
        end = 2026 if end_raw in ("present", "current") else int(end_raw[:4])
        span = max(span, end - start)
    return round(max(best_explicit, float(span)), 1)


def readability_metrics(text: str) -> dict[str, Any]:
    """Flesch Reading Ease / Flesch-Kincaid + passive & repetition heuristics."""
    words = re.findall(r"\w+", text)
    sentences = [s for s in re.split(r"[.!?\n]+", text) if s.strip()]
    avg_sentence = len(words) / max(1, len(sentences))
    passive = len(re.findall(r"\b(?:was|were|been|being|is|are)\s+\w+(?:ed|en)\b", text.lower()))
    counts: dict[str, int] = {}
    for w in (w.lower() for w in words if len(w) > 5):
        counts[w] = counts.get(w, 0) + 1
    repeated = sum(1 for c in counts.values() if c >= 5)

    if _HAS_TEXTSTAT and len(words) > 30:
        try:
            flesch = float(_textstat.flesch_reading_ease(text))
            fk = float(_textstat.flesch_kincaid_grade(text))
        except Exception:
            flesch, fk = _fallback_flesch(words, sentences), avg_sentence / 2
    else:
        flesch, fk = _fallback_flesch(words, sentences), avg_sentence / 2

    score = max(0, min(100, round(flesch)))
    return {
        "flesch_reading_ease": round(flesch, 1),
        "flesch_kincaid_grade": round(fk, 1),
        "avg_sentence_length": round(avg_sentence, 1),
        "passive_voice_count": passive,
        "repeated_words": repeated,
        "score": score,
    }


def _fallback_flesch(words: list[str], sentences: list[str]) -> float:
    if not words or not sentences:
        return 50.0
    syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)
    asw = syllables / len(words)
    return 206.835 - 1.015 * asl - 84.6 * asw


def _count_syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def grammar_metrics(text: str) -> dict[str, Any]:
    """Lightweight grammar/spelling signal (no Java dependency required).

    If ``language_tool_python`` is installed it is used for a precise count;
    otherwise we approximate with common resume-writing issues.
    """
    issues: list[str] = []
    lower = text.lower()
    # First-person pronouns are discouraged on resumes
    fp = len(re.findall(r"\b(i|me|my|myself)\b", lower))
    if fp > 3:
        issues.append(f"{fp} first-person pronouns (prefer implied subject)")
    # Double spaces / spacing before punctuation
    if re.search(r"\s{2,}\S", text):
        issues.append("inconsistent spacing detected")
    if re.search(r"\s[,.;:]", text):
        issues.append("space before punctuation")
    # Missing capitalization at bullet starts
    lowered_bullets = sum(
        1 for ln in text.splitlines()
        if re.match(r"^\s*[-•*]\s+[a-z]", ln)
    )
    if lowered_bullets > 2:
        issues.append(f"{lowered_bullets} bullet points start lowercase")

    tool_issue_count = None
    try:  # optional precise checker
        import language_tool_python  # type: ignore
        tool = _get_language_tool(language_tool_python)
        if tool is not None:
            matches = tool.check(text[:8000])
            tool_issue_count = len(matches)
    except Exception:
        tool_issue_count = None

    raw = tool_issue_count if tool_issue_count is not None else len(issues) * 3
    words = max(1, len(re.findall(r"\w+", text)))
    error_rate = raw / (words / 100)  # errors per 100 words
    score = max(0, min(100, round(100 - error_rate * 6)))
    return {
        "score": score,
        "issues": issues,
        "tool_issue_count": tool_issue_count,
        "estimated_errors": raw,
    }


@lru_cache(maxsize=1)
def _get_language_tool(module):  # pragma: no cover - only if user installs it
    try:
        return module.LanguageTool("en-US")
    except Exception:
        return None


def detect_duplicates(text: str) -> dict[str, Any]:
    lines = [re.sub(r"\s+", " ", ln.strip().lower()) for ln in text.splitlines() if len(ln.strip()) > 20]
    counts: dict[str, int] = {}
    for ln in lines:
        counts[ln] = counts.get(ln, 0) + 1
    dup_lines = [ln for ln, c in counts.items() if c > 1]
    return {"duplicate_line_count": len(dup_lines), "examples": dup_lines[:3]}


def formatting_metrics(text: str) -> dict[str, Any]:
    """ATS-friendliness of the extracted text (proxy for layout hazards)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    bullets = sum(1 for ln in lines if re.match(r"^\s*(?:[-•*▪◦]|\d+[.)])\s+", ln))
    # Multiple wide gaps within lines often indicate tables/columns that break ATS parsers
    tabbish = sum(1 for ln in lines if re.search(r"\S {3,}\S {3,}\S", ln))
    non_ascii = len(re.findall(r"[^\x00-\x7F]", text))
    caps_headers = sum(1 for ln in lines if ln.strip().isupper() and len(ln.strip()) < 40)
    issues: list[str] = []
    if tabbish > max(4, len(lines) * 0.15):
        issues.append("possible multi-column/table layout (risky for ATS parsing)")
    if non_ascii > 40:
        issues.append("many special characters/icons that some ATS strip out")
    if bullets == 0:
        issues.append("no bullet points detected — recruiters skim bullets")
    score = 100
    score -= min(35, max(0, (tabbish - 3)) * 4)
    score -= min(20, max(0, (non_ascii - 20)) // 5)
    score += min(15, bullets)
    score = max(0, min(100, score))
    return {"score": score, "bullets": bullets, "column_risk": tabbish, "special_chars": non_ascii, "caps_headers": caps_headers, "issues": issues}


# ---------------------------------------------------------------------------
# spaCy-powered structure signals (optional)
# ---------------------------------------------------------------------------
def spacy_entities(text: str) -> dict[str, list[str]]:
    nlp = _get_spacy()
    ents: dict[str, list[str]] = {"ORG": [], "GPE": [], "DATE": [], "PERSON": []}
    if nlp is None or not nlp.has_pipe("ner"):
        return ents
    try:
        doc = nlp(text[:6000])
        for ent in doc.ents:
            if ent.label_ in ents and ent.text.strip() not in ents[ent.label_]:
                ents[ent.label_].append(ent.text.strip())
    except Exception:
        pass
    return {k: v[:10] for k, v in ents.items()}


# ===========================================================================
# THE SCORING ENGINE
# ===========================================================================
SCORE_WEIGHTS: dict[str, float] = {
    "Resume Structure": 0.15,
    "Skill Match": 0.25,
    "Experience": 0.20,
    "Projects": 0.15,
    "Education": 0.10,
    "Formatting": 0.05,
    "Achievements": 0.05,
    "Grammar": 0.05,
}


def compute_ats(
    resume_text: str,
    domain: str,
    matched_skills: list[str],
    required_skills: list[str],
    job_description: str | None = None,
) -> dict[str, Any]:
    """Produce the full explainable ATS scorecard.

    ``required_skills`` should be the domain skill pool (or JD skills when a job
    description is supplied) — the target set the resume is measured against.
    """
    text = resume_text or ""
    lower = text.lower()
    words = _tokenize(text)
    word_count = len(words)

    # ---- Sub-signals -----------------------------------------------------
    sections_present = detect_resume_sections(lower)
    n_sections = sum(1 for v in sections_present.values() if v)
    total_sections = len(sections_present)

    verbs = detect_action_verbs(lower)
    achievements = detect_achievements(text)
    yoe = years_of_experience(text)
    read = readability_metrics(text)
    gram = grammar_metrics(text)
    fmt = formatting_metrics(text)
    dupes = detect_duplicates(text)
    certs = detect_certifications(lower)
    softs = detect_soft_skills(lower)
    degrees = detect_degrees(lower)

    # Semantic skill coverage against the target skill set
    match_report = semantic_match_skills(text, required_skills)
    sem_matched = match_report["matched"]
    sem_missing = [m["skill"] for m in match_report["missing"]]
    coverage = len(sem_matched) / max(1, len(required_skills))

    # Optional JD relevance via embeddings / BM25
    jd_relevance = None
    if job_description:
        jd_relevance = _jd_relevance(text, job_description)

    # ---- Dimension scores (0-100) ---------------------------------------
    structure = min(100, round((n_sections / total_sections) * 100 * 0.85 + (12 if sections_present.get("LinkedIn") or sections_present.get("GitHub") else 0)))

    skill_score = round(20 + coverage * 80)
    if jd_relevance is not None:
        skill_score = round(skill_score * 0.7 + jd_relevance * 30)
    skill_score = max(0, min(100, skill_score))

    exp_base = 25 + min(40, yoe * 8)
    exp_base += 15 if sections_present.get("Work Experience") else 0
    exp_base += min(20, verbs["strong_count"] * 2)
    experience = max(0, min(100, round(exp_base - verbs["weak_count"] * 2)))

    proj_base = 20
    proj_base += 35 if sections_present.get("Projects") else 0
    proj_base += min(30, len(achievements) * 4 + verbs["strong_count"] * 2)
    projects = max(0, min(100, round(proj_base)))

    education = 30
    if degrees:
        education = 78 + min(20, (len(degrees) - 1) * 8)
    elif sections_present.get("Education"):
        education = 60
    education = min(100, education)

    formatting = fmt["score"]

    ach_score = 25 + min(60, len(achievements) * 8)
    ach_score += min(15, len(certs) * 5)
    achievements_score = max(0, min(100, round(ach_score)))

    grammar = gram["score"]
    if dupes["duplicate_line_count"]:
        grammar = max(0, grammar - min(20, dupes["duplicate_line_count"] * 5))

    dimensions = {
        "Resume Structure": structure,
        "Skill Match": skill_score,
        "Experience": experience,
        "Projects": projects,
        "Education": education,
        "Formatting": formatting,
        "Achievements": achievements_score,
        "Grammar": grammar,
    }

    overall = round(sum(dimensions[k] * SCORE_WEIGHTS[k] for k in dimensions))
    overall = max(0, min(100, overall))

    # ---- Confidence & derived recruiter metrics -------------------------
    caps = engine_capabilities()
    confidence = _confidence(word_count, n_sections, caps, len(sem_matched))
    recruiter_readiness = round(overall * 0.6 + skill_score * 0.25 + structure * 0.15)
    interview_probability = round(
        max(3, min(95, overall * 0.5 + skill_score * 0.3 + experience * 0.2 - 5))
    )
    hiring_confidence = round(max(2, min(92, interview_probability * 0.75 + achievements_score * 0.15)))

    # ---- Weak areas (lowest weighted contribution first) ----------------
    weak_areas = _weak_areas(dimensions, sections_present, verbs, achievements, read, dupes, fmt)

    # ---- Explainability --------------------------------------------------
    explanation = _explain(
        dimensions, coverage, len(sem_matched), len(required_skills), n_sections,
        total_sections, verbs, achievements, yoe, degrees, certs, read, caps,
    )

    return {
        "overall": overall,
        "sections": dimensions,
        "weights": {k: round(v * 100) for k, v in SCORE_WEIGHTS.items()},
        "confidence": confidence,
        "recruiter_readiness": recruiter_readiness,
        "interview_probability": interview_probability,
        "hiring_confidence": hiring_confidence,
        "evidence": explanation,
        "weak_areas": weak_areas,
        "matched_skill_details": sem_matched,
        "missing_skill_details": match_report["missing"],
        "skill_coverage_pct": round(coverage * 100),
        "features": {
            "sections_present": sections_present,
            "action_verbs": verbs,
            "achievements": achievements,
            "years_of_experience": yoe,
            "readability": read,
            "grammar": gram,
            "formatting": fmt,
            "duplicates": dupes,
            "certifications": certs,
            "soft_skills": softs,
            "degrees": degrees,
            "word_count": word_count,
        },
        "semantic_missing_skills": sem_missing[:12],
        "jd_relevance": jd_relevance,
        "engine": caps,
    }


def _tfidf_cosine(a: str, b: str) -> float:
    """TF-IDF vector cosine similarity (algorithm #2 fallback for document relevance)."""
    if not (_HAS_SKLEARN and TfidfVectorizer is not None and _HAS_NUMPY):
        return 0.0
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        matrix = vec.fit_transform([a or "", b or ""])
        if matrix.shape[0] < 2:
            return 0.0
        num = float(matrix[0].multiply(matrix[1]).sum())
        denom = float(_np.linalg.norm(matrix[0].toarray()) * _np.linalg.norm(matrix[1].toarray()))
        if denom <= 0:
            return 0.0
        return max(0.0, min(1.0, num / denom))
    except Exception:
        return 0.0


def _jd_relevance(resume_text: str, jd: str) -> float:
    """0-1 relevance between resume and a job description.

    Preference order:
      1. Sentence-Transformers cosine similarity
      2. TF-IDF cosine similarity
      3. BM25
      4. Jaccard token overlap
    """
    sim = semantic_similarity(resume_text, jd)
    if sim > 0:
        return round(max(0.0, min(1.0, sim)), 3)
    tfidf_sim = _tfidf_cosine(resume_text, jd)
    if tfidf_sim > 0:
        return round(tfidf_sim, 3)
    if _HAS_BM25:
        try:
            corpus = [_tokenize(resume_text)]
            bm = BM25Okapi(corpus)
            scores = bm.get_scores(_tokenize(jd))
            raw = float(scores[0]) if len(scores) else 0.0
            return round(max(0.0, min(1.0, raw / (raw + 10))), 3)
        except Exception:
            pass
    a, b = set(_tokenize(resume_text)), set(_tokenize(jd))
    return round(len(a & b) / max(1, len(a | b)), 3)


def _confidence(word_count: int, n_sections: int, caps: dict[str, Any], matched: int) -> dict[str, Any]:
    base = 45
    if word_count >= 250:
        base += 20
    elif word_count >= 120:
        base += 10
    base += min(15, n_sections * 2)
    base += min(10, matched * 2)
    if caps.get("embeddings"):
        base += 12
    if caps.get("spacy_ner"):
        base += 4
    value = max(20, min(99, base))
    method = "semantic embeddings + NLP" if caps.get("embeddings") else "ontology + NLP heuristics"
    return {
        "value": value,
        "basis": f"Signal strength from {word_count} words, {n_sections} sections, {matched} matched skills via {method}.",
    }


def _weak_areas(dimensions, sections, verbs, achievements, read, dupes, fmt) -> list[dict[str, Any]]:
    weak: list[dict[str, Any]] = []
    ranked = sorted(dimensions.items(), key=lambda kv: kv[1])
    for name, score in ranked:
        if score >= 70:
            continue
        problem, rec, gain = _weakness_detail(name, score, sections, verbs, achievements, read, dupes, fmt)
        weak.append({
            "area": name,
            "score": score,
            "problem": problem,
            "recommendation": rec,
            "expected_ats_gain": gain,
            "priority": "high" if score < 45 else "medium",
        })
    return weak[:6]


def _weakness_detail(name, score, sections, verbs, achievements, read, dupes, fmt):
    weight = round(SCORE_WEIGHTS.get(name, 0.05) * 100)
    gain = f"+{max(1, round((75 - score) * SCORE_WEIGHTS.get(name, 0.05)))} ATS points"
    if name == "Resume Structure":
        missing = [s for s, present in sections.items() if not present][:4]
        return (f"Missing sections: {', '.join(missing) or 'key sections'}.",
                "Add clearly labelled sections (Summary, Experience, Projects, Skills, Education).", gain)
    if name == "Skill Match":
        return ("Resume does not surface enough of the skills this domain screens for.",
                "Mirror the target job's core skills using the exact terminology recruiters search.", gain)
    if name == "Experience":
        return (f"Weak experience signal ({verbs['weak_count']} weak verbs, {verbs['strong_count']} strong).",
                "Replace 'worked/helped' with 'led/built/delivered' and quantify scope.", gain)
    if name == "Projects":
        return ("Projects lack measurable impact or a dedicated section.",
                "Add 2-3 projects with a result metric (users, %, revenue, accuracy).", gain)
    if name == "Education":
        return ("No recognisable degree/education block was detected.",
                "State your degree, institution and year in a clear Education section.", gain)
    if name == "Formatting":
        return (f"ATS-format risks: {', '.join(fmt['issues']) or 'layout may not parse cleanly'}.",
                "Use a single-column layout, standard fonts and text bullets (avoid tables/icons).", gain)
    if name == "Achievements":
        return (f"Only {len(achievements)} quantified achievements found.",
                "Turn duties into achievements with numbers (e.g. 'reduced cost by 35%').", gain)
    if name == "Grammar":
        extra = f" {dupes['duplicate_line_count']} duplicated lines." if dupes["duplicate_line_count"] else ""
        return (f"Grammar/quality issues detected.{extra}",
                "Proofread, remove duplicates and fix spacing/capitalisation.", gain)
    return (f"{name} is below target (weight {weight}%).", "Strengthen this dimension.", gain)


def _explain(dimensions, coverage, matched, required, n_sections, total_sections,
             verbs, achievements, yoe, degrees, certs, read, caps) -> list[str]:
    method = "semantic embeddings" if caps.get("embeddings") else "the skill ontology"
    ev = [
        f"Skill Match {dimensions['Skill Match']}/100: {matched} of {required} target skills evidenced via {method} ({round(coverage*100)}% coverage).",
        f"Resume Structure {dimensions['Resume Structure']}/100: {n_sections} of {total_sections} standard sections detected.",
        f"Experience {dimensions['Experience']}/100: ~{yoe} years signalled with {verbs['strong_count']} strong action verbs.",
        f"Projects {dimensions['Projects']}/100 and Achievements {dimensions['Achievements']}/100: {len(achievements)} quantified outcomes detected.",
        f"Education {dimensions['Education']}/100: {', '.join(degrees) if degrees else 'no formal degree detected'}.",
        f"Readability {read['score']}/100 (Flesch {read['flesch_reading_ease']}); Grammar {dimensions['Grammar']}/100.",
    ]
    if certs:
        ev.append("Certifications recognised: " + ", ".join(c["provider"] for c in certs) + ".")
    ev.append(
        "Scoring rubric (weights): " + ", ".join(f"{k} {round(v*100)}%" for k, v in SCORE_WEIGHTS.items()) + "."
    )
    return ev
