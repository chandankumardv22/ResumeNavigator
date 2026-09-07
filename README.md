# ResumeNavigator — Smart Resume Analyzer & Job Recommendation System

Full-stack resume intelligence platform that **actually runs** five technologies in one pipeline:

1. **NLP** — PDF/DOCX parsing & structured extraction  
2. **TF-IDF** — feature vectors for role prediction  
3. **Logistic Regression** — fallback career-role classifier  
4. **Sentence Transformers + Cosine Similarity** — semantic job matching  
5. **Gemini 2.5 Flash** — validation, realistic roles, roadmap (does **not** replace ML)

---

## Technologies and Their Role

| Technology | Role in the system | Primary modules |
| ---------- | ------------------ | --------------- |
| **NLP** | Resume parsing & information extraction (name, email, phone, skills, education, experience, projects, certifications, years) | `services/resume_parser.py`, `resume_nlp.py`, `pdf_parser.py`, `skills.py` |
| **TF-IDF** | Text feature extraction from resume/skills into numerical vectors | `services/role_classifier.py`, `models/tfidf_vectorizer.pkl` |
| **Logistic Regression** | Fallback career-role classification on TF-IDF features | `services/role_classifier.py`, `models/logistic_regression.pkl` |
| **Sentence Transformers** | Dense embeddings of full resume and job description (`all-MiniLM-L6-v2`) | `services/similarity_engine.py` |
| **Cosine Similarity** | Mathematical similarity score + skill-gap analysis | `services/similarity_engine.py` |
| **Gemini 2.5 Flash** | Advanced reasoning: validation, realistic role, ATS narrative, roadmap, milestones | `services/gemini_service.py` |

**Important:** Gemini receives *structured outputs* from NLP / TF-IDF+LR / cosine matching. It must not invent the ML predictions.

---

## System architecture / data flow

```text
UPLOAD PDF/DOCX
      ↓
NLP TEXT EXTRACTION + STRUCTURED PARSE
      ↓
TF-IDF FEATURE EXTRACTION
      ↓
LOGISTIC REGRESSION ROLE PREDICTION  (fallback classifier)
      ↓
SENTENCE TRANSFORMER EMBEDDINGS
      ↓
COSINE SIMILARITY  (resume ↔ job description)
      ↓
SKILL GAP + DETERMINISTIC ATS BREAKDOWN
      ↓
GEMINI 2.5 FLASH  (validate + realistic role + roadmap)
      ↓
LOCAL JOB OPENINGS + FRONTEND DASHBOARD
```

---

## Model training (TF-IDF + Logistic Regression)

```bash
cd backend
python train_role_model.py
```

- Dataset: `backend/data/role_dataset.csv`
- Artifacts: `backend/models/tfidf_vectorizer.pkl`, `backend/models/logistic_regression.pkl`
- Roles: Machine Learning Engineer, Data Analyst, Full Stack Developer, DevOps Engineer, Backend Developer, Frontend Developer, Data Scientist, Software Developer

The classifier is also auto-trained on first use if pickles are missing.

---

## Environment variables

Copy `backend/.env.example` → `backend/.env`:

| Variable | Purpose |
| -------- | ------- |
| `GEMINI_API_KEY` | Gemini 2.5 Flash (optional; heuristic intelligence if missing) |
| `ENABLE_EMBEDDINGS=true` | Turn on Sentence Transformers |
| `EMBEDDING_MODEL` | Default `sentence-transformers/all-MiniLM-L6-v2` |
| `RAPIDAPI_KEY` / Adzuna keys | Optional live India job providers |

Never put API keys in frontend code.

---

## Installation & run

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install -r requirements-ml.txt   # Sentence Transformers
python train_role_model.py
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm start
```

Or use `quick-start.bat` / `quick-start.sh`.

---

## API documentation

| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| `POST` | `/api/analyze-resume` | Full pipeline (file + optional `job_description`) |
| `POST` | `/analyze` | Same pipeline (compat) |
| `POST` | `/api/predict-role` | TF-IDF + LR only |
| `POST` | `/api/match-job` | Sentence Transformers + cosine |
| `POST` | `/api/analyze-skills` | NLP skills + gap |
| `POST` | `/api/generate-roadmap` | Gemini/heuristic roadmap |
| `GET` | `/api/algorithms` | Live algorithm status |
| `GET` | `/health` | Health + algorithm flags |

### Example response shape (`/api/analyze-resume`)

```json
{
  "resume": { "name": "", "email": "", "skills": [], "education": [], "experience": [], "total_experience": 0 },
  "role_prediction": { "predicted_role": "Data Analyst", "confidence": 0.87, "alternative_roles": [] },
  "semantic_analysis": { "semantic_match_score": 78, "matched_skills": [], "missing_skills": [], "skill_gap": [] },
  "ats_analysis": { "ats_score": 82, "score_breakdown": { "skills": 0, "keywords": 0, "experience": 0, "education": 0, "projects": 0, "semantic_match": 0, "completeness": 0 } },
  "ai_analysis": { "realistic_role": "Entry-Level Data Analyst", "learning_roadmap": [], "career_milestones": [] }
}
```

---

## Frontend dashboard

Shows: ATS score, TF-IDF/LR predicted role, Gemini realistic target, semantic match %, skill gaps, improvements, roadmap, milestones, and location-filtered job apply links.

---

## Project layout (services)

```text
backend/
  services/
    resume_parser.py      # NLP structured JSON
    role_classifier.py    # TF-IDF + Logistic Regression
    similarity_engine.py  # Sentence Transformers + cosine
    ats_engine.py         # Deterministic ATS breakdown
    gemini_service.py     # Gemini 2.5 Flash intelligence
    analysis_pipeline.py  # Orchestrator
  models/                 # *.pkl
  data/role_dataset.csv
  main.py                 # FastAPI routes
```

See also [ALGORITHMS.md](ALGORITHMS.md).
