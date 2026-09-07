"""
TF-IDF feature extraction + Logistic Regression role classifier
(Technologies #2 and #3 — FALLBACK role prediction)

Pipeline:
  Resume text → TfidfVectorizer → feature matrix → LogisticRegression → role
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
_MODELS = _BACKEND / "models"
_DATA = _BACKEND / "data"
MODEL_PATH = _MODELS / "logistic_regression.pkl"
VECTORIZER_PATH = _MODELS / "tfidf_vectorizer.pkl"
# Keep legacy paths as fallbacks
_LEGACY_MODEL = _BACKEND / "role_model.pkl"
_LEGACY_VECTORIZER = _BACKEND / "role_vectorizer.pkl"
DATASET_CSV = _DATA / "role_dataset.csv"

TARGET_ROLES = [
    "Machine Learning Engineer",
    "Data Analyst",
    "Full Stack Developer",
    "DevOps Engineer",
    "Backend Developer",
    "Frontend Developer",
    "Data Scientist",
    "Software Developer",
]

# Seed training corpus (expanded; also written to CSV)
TRAINING_ROWS: list[tuple[str, str]] = [
    ("python machine learning deep learning tensorflow pytorch neural networks nlp computer vision mlops", "Machine Learning Engineer"),
    ("scikit-learn keras feature engineering model deployment python ai research huggingface transformers", "Machine Learning Engineer"),
    ("pytorch cuda llm fine tuning reinforcement learning computer vision opencv machine learning engineer", "Machine Learning Engineer"),
    ("excel sql data analysis power bi tableau statistics pandas reporting dashboards analytics", "Data Analyst"),
    ("business intelligence sql power query visualization kpi metrics data cleaning etl excel", "Data Analyst"),
    ("python pandas numpy matplotlib seaborn data analysis statistics reporting dashboards", "Data Analyst"),
    ("html css javascript react node mongodb full stack web frontend backend api express", "Full Stack Developer"),
    ("react express typescript next.js rest api postgres docker mern stack web development", "Full Stack Developer"),
    ("javascript typescript react node.js mongodb sql fullstack developer web applications", "Full Stack Developer"),
    ("docker kubernetes aws ci cd linux devops automation terraform jenkins pipeline monitoring", "DevOps Engineer"),
    ("github actions kubernetes helm prometheus grafana infrastructure as code ansible devops", "DevOps Engineer"),
    ("aws azure gcp terraform docker containers continuous integration continuous deployment", "DevOps Engineer"),
    ("java spring boot microservices hibernate maven backend api rest sql postgresql", "Backend Developer"),
    ("python django flask fastapi node express backend api microservices database sql", "Backend Developer"),
    ("golang java spring restful api backend engineer database redis kafka message queue", "Backend Developer"),
    ("html css javascript react angular vue typescript frontend ui ux responsive design", "Frontend Developer"),
    ("react next.js typescript redux css tailwind frontend developer web interface", "Frontend Developer"),
    ("javascript typescript react vue figma frontend engineer spa progressive web app", "Frontend Developer"),
    ("python data science machine learning statistics pandas numpy scikit-learn jupyter", "Data Scientist"),
    ("data scientist statistical modeling regression classification nlp feature engineering", "Data Scientist"),
    ("python r statistics machine learning deep learning data scientist experimentation ab testing", "Data Scientist"),
    ("java python javascript software developer algorithms data structures oop system design", "Software Developer"),
    ("software engineer programming problem solving git agile scrum unit testing debugging", "Software Developer"),
    ("c++ java python software development object oriented design design patterns clean code", "Software Developer"),
]

_model = None
_vectorizer = None
_loaded = False


def _sklearn_ok() -> bool:
    try:
        import joblib  # noqa: F401
        from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
        from sklearn.linear_model import LogisticRegression  # noqa: F401
        return True
    except Exception:
        return False


def ensure_dataset_csv() -> Path:
    _DATA.mkdir(parents=True, exist_ok=True)
    if not DATASET_CSV.is_file():
        with DATASET_CSV.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["text", "role"])
            for text, role in TRAINING_ROWS:
                writer.writerow([text, role])
    return DATASET_CSV


def _load_training_data() -> tuple[list[str], list[str]]:
    ensure_dataset_csv()
    texts, labels = [], []
    with DATASET_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            t = (row.get("text") or "").strip()
            r = (row.get("role") or "").strip()
            if t and r:
                texts.append(t)
                labels.append(r)
    if not texts:
        texts = [t for t, _ in TRAINING_ROWS]
        labels = [r for _, r in TRAINING_ROWS]
    return texts, labels


def train_and_save() -> dict[str, Any]:
    """Train TF-IDF + Logistic Regression and persist under backend/models/."""
    if not _sklearn_ok():
        raise RuntimeError("scikit-learn and joblib are required.")

    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    texts, labels = _load_training_data()
    _MODELS.mkdir(parents=True, exist_ok=True)

    # Explicit pipeline: TF-IDF → Logistic Regression
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    X = vectorizer.fit_transform(texts)
    clf = LogisticRegression(max_iter=2000, solver="lbfgs")
    clf.fit(X, labels)

    joblib.dump(clf, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    # Also refresh legacy paths for older imports
    joblib.dump(clf, _LEGACY_MODEL)
    joblib.dump(vectorizer, _LEGACY_VECTORIZER)

    return {
        "samples": len(texts),
        "classes": list(clf.classes_),
        "model_path": str(MODEL_PATH),
        "vectorizer_path": str(VECTORIZER_PATH),
        "algorithm": "TF-IDF + Logistic Regression",
    }


def _ensure_loaded() -> bool:
    global _model, _vectorizer, _loaded
    if _model is not None and _vectorizer is not None:
        return True
    if _loaded:
        return False
    _loaded = True
    if not _sklearn_ok():
        return False
    import joblib

    try:
        model_file = MODEL_PATH if MODEL_PATH.is_file() else _LEGACY_MODEL
        vec_file = VECTORIZER_PATH if VECTORIZER_PATH.is_file() else _LEGACY_VECTORIZER
        if not (model_file.is_file() and vec_file.is_file()):
            train_and_save()
            model_file, vec_file = MODEL_PATH, VECTORIZER_PATH
        _model = joblib.load(model_file)
        _vectorizer = joblib.load(vec_file)
        return True
    except Exception:
        _model = None
        _vectorizer = None
        return False


def predict_role(resume_text: str, skills: list[str] | None = None) -> dict[str, Any]:
    """
    FALLBACK role prediction via TF-IDF features + Logistic Regression.
    Returns predicted_role, confidence (0-1), and alternative_roles.
    """
    if not _ensure_loaded():
        return {
            "predicted_role": None,
            "confidence": 0.0,
            "alternative_roles": [],
            "available": False,
            "algorithm": "TF-IDF + Logistic Regression",
            "error": "Classifier unavailable — install scikit-learn/joblib and train models.",
        }

    skills_blob = " ".join(skills or [])
    document = f"{skills_blob}\n{resume_text or ''}".strip().lower()
    if len(document) < 12:
        return {
            "predicted_role": None,
            "confidence": 0.0,
            "alternative_roles": [],
            "available": True,
            "algorithm": "TF-IDF + Logistic Regression",
            "error": "Insufficient text for TF-IDF classification.",
        }

    # TF-IDF feature extraction
    X = _vectorizer.transform([document])
    # Logistic Regression classification
    pred = str(_model.predict(X)[0])
    alternatives: list[dict[str, Any]] = []
    confidence = 0.0
    if hasattr(_model, "predict_proba"):
        probs = _model.predict_proba(X)[0]
        classes = [str(c) for c in _model.classes_]
        ranked = sorted(zip(classes, probs), key=lambda x: float(x[1]), reverse=True)
        confidence = float(ranked[0][1])
        pred = ranked[0][0]
        alternatives = [
            {"role": role, "confidence": round(float(p), 4)}
            for role, p in ranked[1:4]
        ]

    return {
        "predicted_role": pred,
        "confidence": round(confidence, 4),
        "alternative_roles": alternatives,
        "available": True,
        "algorithm": "TF-IDF + Logistic Regression",
        "pipeline": "Resume text -> TF-IDF Vectorizer -> feature matrix -> Logistic Regression -> Predicted Career Role",
    }


def classifier_status() -> dict[str, Any]:
    ready = _ensure_loaded()
    return {
        "available": ready,
        "algorithm": "TF-IDF + Logistic Regression",
        "model_path": str(MODEL_PATH if MODEL_PATH.is_file() else _LEGACY_MODEL),
        "classes": [str(c) for c in getattr(_model, "classes_", [])] if ready else list(TARGET_ROLES),
    }
