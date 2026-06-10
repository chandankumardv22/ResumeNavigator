import re
from pdfminer.high_level import extract_text
from docx import Document


# ---------------------------
# SKILL LIST (customizable)
# ---------------------------
SKILLS_DB = [
    "python", "java", "c", "c++", "javascript",
    "react", "node", "mongodb", "sql",
    "aws", "docker", "html", "css",
    "machine learning", "deep learning",
    "data analysis", "pandas", "numpy",
    "tensorflow", "pytorch"
]


# ---------------------------
# TEXT EXTRACTION
# ---------------------------
def normalize_utf8(text):
    """
    Normalize any parser output into UTF-8-safe text on Windows consoles.
    Replaces unsupported/surrogate chars instead of crashing.
    """
    if not text:
        return ""
    return str(text).encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def extract_resume_text(file_path):
    if file_path.endswith(".pdf"):
        return normalize_utf8(extract_text(file_path))

    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        return normalize_utf8("\n".join([para.text for para in doc.paragraphs]))

    else:
        return ""


# ---------------------------
# SKILL EXTRACTION
# ---------------------------
def extract_skills(text):
    text_lower = text.lower()
    found_skills = []

    for skill in SKILLS_DB:
        if skill in text_lower:
            found_skills.append(skill)

    return list(set(found_skills))


# ---------------------------
# EXPERIENCE EXTRACTION
# ---------------------------
def extract_experience(text):
    """
    Extract total years of experience using regex
    Example matches:
    - 2 years
    - 3+ years
    - 5 yrs
    """

    pattern = r"(\d+)\+?\s*(years|yrs)"
    matches = re.findall(pattern, text.lower())

    years = [int(match[0]) for match in matches]

    if years:
        return max(years)
    else:
        return 0


# ---------------------------
# EDUCATION EXTRACTION
# ---------------------------
def extract_education(text):
    degrees = ["b.tech", "bachelor", "m.tech", "master", "b.e", "mca", "phd"]
    text_lower = text.lower()

    found_degrees = []

    for degree in degrees:
        if degree in text_lower:
            found_degrees.append(degree)

    return list(set(found_degrees))


# ---------------------------
# MAIN PARSER FUNCTION
# ---------------------------
def parse_resume(file_path):

    raw_text = extract_resume_text(file_path)

    cleaned_text = normalize_utf8(raw_text).lower()

    skills = extract_skills(cleaned_text)
    experience = extract_experience(cleaned_text)
    education = extract_education(cleaned_text)

    return {
        "cleaned_text": cleaned_text,
        "skills": skills,
        "experience_years": experience,
        "education": education
    }
