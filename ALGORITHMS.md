# ResumeNavigator — Algorithm Stack

This project implements the following algorithms end-to-end in the `/analyze` pipeline.

## 1. Natural Language Processing (NLP)

**Module:** `backend/resume_nlp.py`, `backend/pdf_parser.py`, `backend/skills.py`

- Extracts unstructured text from **PDF** and **Word (.docx)** resumes
- Cleans / normalizes text (whitespace, encoding)
- Extracts **skills**, **academic degrees**, and **years of experience** using custom rule engines and regular expressions

## 2. TF-IDF (Term Frequency–Inverse Document Frequency)

**Module:** `backend/role_predictor.py`

- Converts resume skills and phrases into numerical feature vectors
- Powers the fallback / ensemble role-prediction model
- Artifacts: `backend/role_model.pkl`, `backend/role_vectorizer.pkl`
- Retrain: `python train_role_model.py` (from `backend/`)

## 3. Logistic Regression

**Module:** `backend/role_predictor.py`

- Classifies the resume into a target career role from TF-IDF features
- Roles include Machine Learning Engineer, Data Analyst, Full Stack Developer, DevOps Engineer, and related profiles
- Used when Gemini is unavailable, and always reported as an ensemble signal alongside Gemini

## 4. Sentence Transformers & Cosine Similarity

**Module:** `backend/nlp_engine.py`

- Encodes resume text / skills into dense embeddings (`sentence-transformers`)
- Computes **Cosine Similarity** for semantic skill matching and skill-gap analysis
- Also scores resume ↔ job-description relevance on `/api/job-match`

Enable:

```bash
pip install -r requirements-ml.txt
# in backend/.env
ENABLE_EMBEDDINGS=true
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## 5. Generative AI — Gemini LLM (`gemini-2.5-flash`)

**Module:** `backend/main.py` → `analyze_resume_with_gemini`

- Validates uploaded resumes
- Produces domain-aware role suggestions and narrative career guidance
- Generates personalized milestone roadmaps as structured JSON
- Requires `GEMINI_API_KEY` in `backend/.env`

---

## Pipeline order

```text
Upload PDF/DOCX
    → NLP parse (text, skills, degrees, YoE)
    → Gemini LLM (validate, roles, roadmap)  [if key set]
    → TF-IDF + Logistic Regression (role classify / ensemble)
    → Sentence Transformers + Cosine Similarity (ATS / skill gap)  [if embeddings on]
    → Location-filtered direct-apply job openings
```

Inspect live status: `GET /health` or `GET /api/algorithms`
