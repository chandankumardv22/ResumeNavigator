from __future__ import annotations

import re
from typing import Any

DOMAIN_PROFILES: dict[str, dict[str, Any]] = {
    "Cloud & DevOps": {
        "signals": (
            "aws", "azure", "gcp", "cloud", "devops", "kubernetes", "docker",
            "terraform", "ci/cd", "ec2", "s3", "lambda", "cloudformation", "ansible",
        ),
        "roles": [
            "Cloud Engineer", "DevOps Engineer", "AWS Solutions Architect",
            "Site Reliability Engineer", "Platform Engineer", "Cloud Support Engineer",
        ],
        "skill_pool": [
            "aws", "azure", "gcp", "ec2", "s3", "lambda", "cloudformation",
            "docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd",
            "linux", "monitoring", "vpc", "iam", "rds", "eks",
        ],
    },
    "Information Technology": {
        "signals": (
            "python", "java", "javascript", "react", "sql", "api", "software",
            "developer", "programming", "machine learning", "data", "cloud", "devops",
        ),
        "roles": [
            "Software Developer", "Full Stack Developer", "Data Analyst",
            "Backend Developer", "Frontend Developer", "QA Engineer",
        ],
        "skill_pool": [
            "python", "javascript", "typescript", "react", "node.js", "sql",
            "git", "docker", "aws", "rest api", "agile", "testing", "html", "css",
            "microservices", "mongodb", "postgresql", "redis", "fastapi", "django",
        ],
    },
    "Network Engineering": {
        "signals": (
            "cisco", "routing", "switching", "tcp/ip", "wireshark", "bgp", "ospf",
            "firewall", "vlan", "dns", "dhcp", "lan", "wan", "network", "ccna", "juniper",
        ),
        "roles": [
            "Network Engineer", "NOC Engineer", "Network Administrator",
            "Security Network Engineer", "Infrastructure Engineer",
        ],
        "skill_pool": [
            "cisco", "routing", "switching", "tcp/ip", "wireshark", "bgp", "ospf",
            "firewall", "vlan", "dns", "dhcp", "lan", "wan", "network security", "ccna",
        ],
    },
    "Commerce & Finance": {
        "signals": (
            "accounting", "finance", "commerce", "gst", "tally", "excel", "audit",
            "banking", "tax", "bookkeeping", "economics", "financial analysis",
        ),
        "roles": [
            "Accounts Executive", "Financial Analyst", "Tax Associate",
            "Business Development Executive", "Operations Coordinator",
        ],
        "skill_pool": [
            "financial analysis", "ms excel", "tally", "gst compliance",
            "financial reporting", "bank reconciliation", "budgeting", "forecasting",
        ],
    },
    "Marketing & Operations": {
        "signals": (
            "marketing", "digital marketing", "seo", "sem", "branding", "operations",
            "supply chain", "logistics", "customer relations", "crm", "sales",
        ),
        "roles": [
            "Marketing Executive", "Digital Marketing Specialist", "Operations Executive",
            "Business Analyst", "Customer Relations Manager",
        ],
        "skill_pool": [
            "digital marketing", "seo", "content strategy", "operations management",
            "customer relations", "crm", "market research", "campaign management",
        ],
    },
    "Healthcare": {
        "signals": (
            "nursing", "patient care", "clinical", "pharmacy", "medical", "hospital",
            "healthcare", "diagnosis", "b.pharm", "b.sc nursing",
        ),
        "roles": [
            "Staff Nurse", "Pharmacy Assistant", "Medical Records Coordinator",
            "Healthcare Administrator", "Clinical Research Coordinator",
        ],
        "skill_pool": [
            "patient care", "clinical documentation", "medical terminology",
            "healthcare compliance", "pharmacology basics", "vital signs monitoring",
        ],
    },
    "Education": {
        "signals": (
            "teaching", "education", "curriculum", "classroom", "tutoring", "pedagogy",
            "b.ed", "lecturer", "academic", "training",
        ),
        "roles": [
            "Academic Coordinator", "Corporate Trainer", "Teaching Assistant",
            "Instructional Designer", "Education Counselor",
        ],
        "skill_pool": [
            "curriculum planning", "classroom management", "lesson delivery",
            "student assessment", "educational technology", "communication",
        ],
    },
    "Management": {
        "signals": (
            "management", "leadership", "mba", "project management", "team lead",
            "strategy", "stakeholder", "business management", "hr",
        ),
        "roles": [
            "Management Trainee", "Project Coordinator", "HR Executive",
            "Business Operations Manager", "Assistant Manager",
        ],
        "skill_pool": [
            "project management", "leadership", "stakeholder management",
            "business communication", "team management", "strategic planning",
        ],
    },
    "Arts & Humanities": {
        "signals": (
            "english", "literature", "history", "psychology", "sociology",
            "content", "writing", "journalism", "media", "communication",
        ),
        "roles": [
            "Content Writer", "Social Media Executive", "HR Coordinator",
            "Customer Support Specialist", "Research Assistant",
        ],
        "skill_pool": [
            "written communication", "research", "content writing", "editing",
            "critical thinking", "presentation", "customer service",
        ],
    },
    "Administration": {
        "signals": (
            "administration", "office", "clerical", "reception", "coordination",
            "scheduling", "documentation", "executive assistant",
        ),
        "roles": [
            "Administrative Assistant", "Office Coordinator", "Executive Assistant",
            "Operations Assistant", "Front Office Executive",
        ],
        "skill_pool": [
            "ms office", "scheduling", "documentation", "coordination",
            "email etiquette", "record keeping", "customer handling",
        ],
    },
    "Core Engineering": {
        "signals": (
            "mechanical", "civil", "electrical", "electronics", "manufacturing",
            "autocad", "solidworks", "thermodynamics", "circuit",
        ),
        "roles": [
            "Graduate Engineer Trainee", "Design Engineer", "Site Engineer",
            "Quality Engineer", "Production Engineer",
        ],
        "skill_pool": [
            "autocad", "technical drawing", "safety standards", "quality control",
            "project documentation", "team coordination",
        ],
    },
    "General / Fresher": {
        "signals": ("fresher", "graduate", "intern", "trainee", "entry level", "bachelor"),
        "roles": [
            "Graduate Trainee", "Management Trainee", "Junior Executive",
            "Customer Support Associate", "Operations Trainee",
        ],
        "skill_pool": [
            "communication", "ms office", "teamwork", "time management",
            "problem solving", "adaptability", "customer relations",
        ],
    },
}

_STOPWORDS = frozenset({
    "and", "the", "for", "with", "from", "your", "have", "this", "that", "email",
    "phone", "mobile", "address", "name", "resume", "curriculum", "vitae", "gmail",
    "yahoo", "hotmail", "contact", "objective", "summary", "profile", "skills",
    "experience", "education", "project", "projects", "india", "linkedin",
    "bengaluru", "bangalore", "mumbai", "delhi", "chennai", "hyderabad", "pune",
    "kolkata", "karnataka", "maharashtra", "dayananda", "sagar", "engineering",
})

_NON_RESUME_SIGNALS = (
    "chapter ", "textbook", "assignment", "question paper", "table of contents",
    "bibliography", "isbn", "abstract", "syllabus", "lecture notes", "unit ",
    "lesson plan", "research paper", "journal article", "theorem", "exercise ",
    "study note", "random image", "image log", "text snippet", "figure ",
    "diagram ", "equation ", "solve the following", "marks)", "total marks",
)

_RESUME_SIGNALS = (
    "resume", "curriculum vitae", "cv", "experience", "education", "skills",
    "internship", "projects", "objective", "summary", "work history", "employment",
    "certification", "qualification", "profile", "responsibilities", "achievements",
)

_GLOBAL_EXTENDED_SKILLS = (
    "aws", "amazon web services", "azure", "google cloud", "gcp", "ec2", "s3", "lambda",
    "cloudformation", "elastic beanstalk", "route 53", "cloudwatch", "iam", "vpc", "rds",
    "dynamodb", "sns", "sqs", "eks", "ecs", "fargate", "terraform", "ansible", "puppet",
    "chef", "jenkins", "gitlab ci", "github actions", "ci/cd", "kubernetes", "helm",
    "docker", "linux", "bash", "shell scripting", "prometheus", "grafana", "splunk",
    "microservices", "serverless", "api gateway", "load balancing", "nginx", "apache",
    "spring boot", "hibernate", "maven", "gradle", "jira", "confluence", "agile", "scrum",
    "salesforce", "sap", "power bi", "tableau", "snowflake", "databricks", "spark",
    "hadoop", "kafka", "redis", "mongodb", "postgresql", "mysql", "oracle", "nosql",
    "figma", "ui/ux", "selenium", "cypress", "postman", "swagger",
)

_SKILL_ROLE_MAP: dict[str, list[str]] = {
    "aws": ["Cloud Engineer", "AWS Solutions Architect", "DevOps Engineer"],
    "azure": ["Cloud Engineer", "Azure Administrator", "DevOps Engineer"],
    "gcp": ["Cloud Engineer", "Cloud Architect", "DevOps Engineer"],
    "kubernetes": ["DevOps Engineer", "Platform Engineer", "Site Reliability Engineer"],
    "docker": ["DevOps Engineer", "Backend Developer", "Cloud Engineer"],
    "terraform": ["DevOps Engineer", "Infrastructure Engineer", "Cloud Engineer"],
    "python": ["Software Developer", "Backend Developer", "Data Analyst"],
    "react": ["Frontend Developer", "Full Stack Developer"],
    "javascript": ["Frontend Developer", "Full Stack Developer", "Software Developer"],
    "java": ["Software Developer", "Backend Developer"],
    "sql": ["Data Analyst", "Backend Developer", "Database Administrator"],
    "cisco": ["Network Engineer", "Network Administrator"],
    "financial analysis": ["Financial Analyst", "Business Analyst"],
    "digital marketing": ["Digital Marketing Specialist", "Marketing Executive"],
    "patient care": ["Staff Nurse", "Healthcare Administrator"],
}


def build_skill_vocabulary(domain: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    domains = [domain] if domain in DOMAIN_PROFILES else []
    domains.extend(d for d in DOMAIN_PROFILES if d not in domains)
    for dom in domains:
        for skill in DOMAIN_PROFILES[dom]["skill_pool"]:
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                ordered.append(skill)
    return ordered


def detect_domain(text: str) -> str:
    lower = text.lower()
    scores: list[tuple[str, int]] = []
    for domain, profile in DOMAIN_PROFILES.items():
        if domain == "General / Fresher":
            continue
        hits = sum(1 for sig in profile["signals"] if sig in lower)
        scores.append((domain, hits))
    scores.sort(key=lambda item: item[1], reverse=True)
    if scores and scores[0][1] > 0:
        return scores[0][0]
    return "General / Fresher"


def extract_professional_skills(text: str, domain: str) -> list[str]:
    lower = text.lower()
    vocabulary = build_skill_vocabulary(domain)
    for skill in _GLOBAL_EXTENDED_SKILLS:
        if skill not in vocabulary:
            vocabulary.append(skill)
    matched: list[str] = []
    seen: set[str] = set()
    for skill in vocabulary:
        key = skill.lower()
        if key in seen:
            continue
        if key in lower:
            seen.add(key)
            matched.append(skill)
        if len(matched) >= 24:
            break
    matched.extend(extract_experience_inferred_skills(text))
    deduped: list[str] = []
    seen.clear()
    for skill in matched:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(skill)
    return deduped[:24]


def extract_experience_inferred_skills(text: str) -> list[str]:
    lower = text.lower()
    inferred: list[str] = []
    has_timeline = bool(
        re.search(r"\b(19|20)\d{2}\s*[-–—to]{1,3}\s*((19|20)\d{2}|present|current)\b", lower)
    )
    has_company = any(
        marker in lower
        for marker in (" pvt", " ltd", " limited", " technologies", " solutions", " services", " infotech")
    )
    has_work_verbs = any(
        verb in lower
        for verb in ("developed", "implemented", "managed", "designed", "built", "led", "maintained", "deployed")
    )
    if has_timeline or has_company:
        inferred.append("professional experience")
    if has_work_verbs:
        inferred.append("project delivery")
    if "team" in lower and has_work_verbs:
        inferred.append("team collaboration")
    if "client" in lower or "stakeholder" in lower:
        inferred.append("stakeholder management")
    if "cloud" in lower and "aws" not in lower:
        inferred.append("cloud computing")
    return inferred


def infer_roles_from_skills(matched_skills: list[str], domain: str) -> list[str]:
    role_scores: dict[str, int] = {}
    profile = DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["General / Fresher"])
    for role in profile["roles"]:
        role_scores[role] = role_scores.get(role, 0) + 2
    for skill in matched_skills:
        key = skill.lower()
        for skill_key, roles in _SKILL_ROLE_MAP.items():
            if skill_key in key or key in skill_key:
                for role in roles:
                    role_scores[role] = role_scores.get(role, 0) + 3
    for dom_name, dom_profile in DOMAIN_PROFILES.items():
        dom_hits = sum(1 for s in matched_skills if s.lower() in dom_profile["skill_pool"])
        if dom_hits >= 2:
            for role in dom_profile["roles"][:3]:
                role_scores[role] = role_scores.get(role, 0) + dom_hits
    ranked = sorted(role_scores.items(), key=lambda item: item[1], reverse=True)
    return [role for role, score in ranked if score > 0][:6]


def merge_recommended_roles(primary: list[str], skill_roles: list[str], limit: int = 6) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for role in primary + skill_roles:
        key = role.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(role.strip())
        if len(merged) >= limit:
            break
    return merged


def sanitize_skills(skills: list[str], metadata: dict[str, str]) -> list[str]:
    email = (metadata.get("candidate_email") or "").lower()
    phone_digits = re.sub(r"\D", "", metadata.get("candidate_phone") or "")
    name = (metadata.get("candidate_name") or "").strip()
    name_parts = {p.lower() for p in name.split() if len(p) > 1}
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in skills:
        skill = str(raw).strip()
        if not skill:
            continue
        sl = skill.lower()
        if sl in seen or sl in _STOPWORDS or sl == "not found":
            continue
        if re.search(r"@|\.com|\.in|\.org", sl):
            continue
        if re.fullmatch(r"\+?[\d\s\-()]{7,}", skill):
            continue
        if email and email != "not found" and (email in sl or sl in email):
            continue
        skill_digits = re.sub(r"\D", "", sl)
        if phone_digits and len(phone_digits) >= 8 and phone_digits in skill_digits:
            continue
        tokens = [t for t in re.findall(r"[a-z]+", sl) if len(t) > 2]
        if name_parts and tokens and all(t in name_parts for t in tokens):
            continue
        if name and name.lower() == sl:
            continue
        if len(sl) < 2 or len(sl) > 48:
            continue
        if "," in skill and _looks_like_location_skill(skill):
            continue
        seen.add(sl)
        cleaned.append(skill)
    return cleaned[:24]


def _looks_like_location_skill(value: str) -> bool:
    lower = value.lower()
    markers = (
        "india", "bengaluru", "bangalore", "mumbai", "delhi", "chennai",
        "hyderabad", "pune", "kolkata", "karnataka", "street", "road",
    )
    return any(m in lower for m in markers)


def compute_missing_skills(matched: list[str], domain: str) -> list[str]:
    pool = DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["General / Fresher"])["skill_pool"]
    matched_lower = {m.lower() for m in matched}
    missing = [s for s in pool if s.lower() not in matched_lower]
    return missing[:8] if missing else pool[:4]
