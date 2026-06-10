from sentence_transformers import SentenceTransformer, util
import numpy as np

# Load model once
model = SentenceTransformer('all-MiniLM-L6-v2')

COMMON_SKILLS = [
    "python", "java", "javascript", "html", "css",
    "sql", "mongodb", "aws", "docker", "react",
    "node", "c", "c++", "data analysis",
    "machine learning", "deep learning"
]


def calculate_similarity(resume_text, job_description):
    embeddings = model.encode([resume_text, job_description])
    similarity = util.cos_sim(embeddings[0], embeddings[1])
    return round(float(similarity[0][0]) * 100, 2)


def skill_gap_analysis(resume_text, job_description):
    resume_text = resume_text.lower()
    job_description = job_description.lower()

    # Extract skills from resume & JD
    resume_skills = [skill for skill in COMMON_SKILLS if skill in resume_text]
    jd_skills = [skill for skill in COMMON_SKILLS if skill in job_description]

    matched_skills = list(set(resume_skills) & set(jd_skills))
    missing_skills = list(set(jd_skills) - set(resume_skills))

    # AI similarity per skill
    skill_scores = {}
    for skill in jd_skills:
        skill_embedding = model.encode(skill)
        resume_embedding = model.encode(resume_text)
        score = util.cos_sim(skill_embedding, resume_embedding)
        skill_scores[skill] = round(float(score[0][0]) * 100, 2)

    return {
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_match_scores": skill_scores
    }
def generate_learning_roadmap(missing_skills):
    roadmap = []

    for skill in missing_skills:
        skill_lower = skill.lower()

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
# ============================================
# AI-Based Skill Weighting System
# ============================================

def weighted_skill_match(resume_skills, job_description):
    """
    Calculate weighted skill matching score.
    """

    # Define skill weights (you can expand this)
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

    jd_lower = job_description.lower()
    resume_lower = [skill.lower() for skill in resume_skills]

    total_weight = 0
    matched_weight = 0
    matched_skills = []

    for skill, weight in skill_weights.items():
        if skill in jd_lower:
            total_weight += weight
            if skill in resume_lower:
                matched_weight += weight
                matched_skills.append(skill)

    if total_weight == 0:
        return 0, []

    score = (matched_weight / total_weight) * 100

    return round(score, 2), matched_skills
# ============================================
# Job Role Prediction
# ============================================

import joblib
import os

MODEL_PATH = "role_model.pkl"
VECTORIZER_PATH = "role_vectorizer.pkl"

role_model = None
role_vectorizer = None

if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
    role_model = joblib.load(MODEL_PATH)
    role_vectorizer = joblib.load(VECTORIZER_PATH)


def predict_job_role(resume_text):
    if not role_model or not role_vectorizer:
        return "Model Not Trained"

    X = role_vectorizer.transform([resume_text])
    prediction = role_model.predict(X)

    return prediction[0]
