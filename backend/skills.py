# Copyright (c) 2026 chandankumardv22
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


# ---------------------------------------------------------------------------
# Role-specific skill requirements for the Role Explorer feature
# ---------------------------------------------------------------------------

ROLE_SKILL_REQUIREMENTS: dict[str, dict[str, Any]] = {
    # ── Information Technology ──────────────────────────────────────────
    "Software Developer": {
        "domain": "Information Technology",
        "core_skills": [
            "python", "java", "javascript", "data structures", "algorithms",
            "sql", "git", "rest api", "agile", "testing",
        ],
        "good_to_have": [
            "docker", "aws", "microservices", "ci/cd", "typescript",
            "design patterns", "system design",
        ],
    },
    "Full Stack Developer": {
        "domain": "Information Technology",
        "core_skills": [
            "javascript", "react", "node.js", "html", "css", "sql",
            "rest api", "git", "mongodb", "typescript",
        ],
        "good_to_have": [
            "docker", "aws", "graphql", "redis", "next.js", "tailwind css",
            "ci/cd", "testing",
        ],
    },
    "Frontend Developer": {
        "domain": "Information Technology",
        "core_skills": [
            "javascript", "react", "html", "css", "typescript",
            "responsive design", "git", "rest api",
        ],
        "good_to_have": [
            "next.js", "vue.js", "angular", "tailwind css", "figma",
            "webpack", "testing", "accessibility",
        ],
    },
    "Backend Developer": {
        "domain": "Information Technology",
        "core_skills": [
            "python", "java", "sql", "rest api", "git",
            "microservices", "database design", "linux",
        ],
        "good_to_have": [
            "docker", "kubernetes", "redis", "mongodb", "aws",
            "message queues", "graphql", "ci/cd",
        ],
    },
    "Data Analyst": {
        "domain": "Information Technology",
        "core_skills": [
            "python", "sql", "excel", "data visualization", "statistics",
            "pandas", "power bi", "data cleaning",
        ],
        "good_to_have": [
            "tableau", "r", "machine learning", "etl", "big data",
            "google analytics", "storytelling",
        ],
    },
    "Data Scientist": {
        "domain": "Information Technology",
        "core_skills": [
            "python", "machine learning", "statistics", "sql", "pandas",
            "numpy", "data visualization", "scikit-learn",
        ],
        "good_to_have": [
            "deep learning", "tensorflow", "pytorch", "nlp", "spark",
            "r", "feature engineering", "model deployment",
        ],
    },
    "Machine Learning Engineer": {
        "domain": "Information Technology",
        "core_skills": [
            "python", "machine learning", "deep learning", "tensorflow",
            "pytorch", "sql", "data pipelines", "model deployment",
        ],
        "good_to_have": [
            "mlops", "kubernetes", "docker", "spark", "aws sagemaker",
            "computer vision", "nlp", "feature engineering",
        ],
    },
    "QA Engineer": {
        "domain": "Information Technology",
        "core_skills": [
            "testing", "selenium", "test planning", "bug tracking",
            "sql", "api testing", "agile",
        ],
        "good_to_have": [
            "cypress", "jira", "postman", "ci/cd", "performance testing",
            "automation frameworks", "python",
        ],
    },
    "Mobile App Developer": {
        "domain": "Information Technology",
        "core_skills": [
            "react native", "javascript", "mobile ui design", "rest api",
            "git", "app deployment",
        ],
        "good_to_have": [
            "flutter", "kotlin", "swift", "firebase", "redux",
            "push notifications", "app store optimization",
        ],
    },
    "Database Administrator": {
        "domain": "Information Technology",
        "core_skills": [
            "sql", "database design", "postgresql", "mysql", "backup & recovery",
            "performance tuning", "linux",
        ],
        "good_to_have": [
            "oracle", "mongodb", "redis", "replication", "security",
            "cloud databases", "scripting",
        ],
    },
    # ── Cloud & DevOps ──────────────────────────────────────────────────
    "Cloud Engineer": {
        "domain": "Cloud & DevOps",
        "core_skills": [
            "aws", "azure", "linux", "networking", "docker",
            "terraform", "ci/cd", "iam", "vpc", "monitoring",
        ],
        "good_to_have": [
            "kubernetes", "ansible", "cloudformation", "gcp",
            "serverless", "cost optimization", "security",
        ],
    },
    "DevOps Engineer": {
        "domain": "Cloud & DevOps",
        "core_skills": [
            "docker", "kubernetes", "ci/cd", "jenkins", "linux",
            "terraform", "git", "aws", "monitoring", "scripting",
        ],
        "good_to_have": [
            "ansible", "helm", "prometheus", "grafana", "argocd",
            "infrastructure as code", "security scanning",
        ],
    },
    "AWS Solutions Architect": {
        "domain": "Cloud & DevOps",
        "core_skills": [
            "aws", "ec2", "s3", "vpc", "iam", "cloudformation",
            "lambda", "rds", "networking", "security",
        ],
        "good_to_have": [
            "eks", "fargate", "api gateway", "dynamodb", "cost optimization",
            "multi-account strategy", "well-architected framework",
        ],
    },
    "Site Reliability Engineer": {
        "domain": "Cloud & DevOps",
        "core_skills": [
            "linux", "python", "kubernetes", "monitoring", "incident management",
            "docker", "ci/cd", "networking",
        ],
        "good_to_have": [
            "prometheus", "grafana", "terraform", "chaos engineering",
            "slo/sli", "on-call management", "capacity planning",
        ],
    },
    # ── Network Engineering ─────────────────────────────────────────────
    "Network Engineer": {
        "domain": "Network Engineering",
        "core_skills": [
            "cisco", "routing", "switching", "tcp/ip", "firewall",
            "vlan", "dns", "dhcp", "network security",
        ],
        "good_to_have": [
            "bgp", "ospf", "wireshark", "juniper", "sd-wan",
            "network automation", "ccna",
        ],
    },
    "Network Administrator": {
        "domain": "Network Engineering",
        "core_skills": [
            "networking", "tcp/ip", "dns", "dhcp", "firewall",
            "lan", "wan", "vpn", "active directory",
        ],
        "good_to_have": [
            "cisco", "linux", "monitoring", "cloud networking",
            "scripting", "network troubleshooting",
        ],
    },
    "Cybersecurity Analyst": {
        "domain": "Network Engineering",
        "core_skills": [
            "network security", "firewall", "siem", "vulnerability assessment",
            "incident response", "linux", "tcp/ip",
        ],
        "good_to_have": [
            "penetration testing", "python", "wireshark", "compliance",
            "cloud security", "threat intelligence", "forensics",
        ],
    },
    # ── Commerce & Finance ──────────────────────────────────────────────
    "Financial Analyst": {
        "domain": "Commerce & Finance",
        "core_skills": [
            "financial analysis", "ms excel", "financial modeling",
            "budgeting", "forecasting", "financial reporting", "accounting",
        ],
        "good_to_have": [
            "power bi", "tally", "sap", "sql", "valuation",
            "corporate finance", "dashboard creation",
        ],
    },
    "Accounts Executive": {
        "domain": "Commerce & Finance",
        "core_skills": [
            "accounting", "tally", "gst compliance", "ms excel",
            "bank reconciliation", "financial reporting", "bookkeeping",
        ],
        "good_to_have": [
            "sap", "taxation", "auditing", "payroll",
            "accounts payable", "accounts receivable",
        ],
    },
    "Tax Associate": {
        "domain": "Commerce & Finance",
        "core_skills": [
            "taxation", "gst compliance", "income tax", "tally",
            "financial reporting", "accounting", "ms excel",
        ],
        "good_to_have": [
            "tax planning", "audit", "corporate law", "sap",
            "compliance", "financial analysis",
        ],
    },
    "Business Analyst": {
        "domain": "Commerce & Finance",
        "core_skills": [
            "business analysis", "requirements gathering", "sql",
            "ms excel", "data visualization", "stakeholder management",
            "documentation",
        ],
        "good_to_have": [
            "power bi", "tableau", "jira", "agile", "process mapping",
            "python", "ux research",
        ],
    },
    # ── Marketing & Operations ──────────────────────────────────────────
    "Digital Marketing Specialist": {
        "domain": "Marketing & Operations",
        "core_skills": [
            "digital marketing", "seo", "sem", "google analytics",
            "content strategy", "social media marketing", "campaign management",
        ],
        "good_to_have": [
            "email marketing", "copywriting", "google ads", "facebook ads",
            "crm", "marketing automation", "a/b testing",
        ],
    },
    "Marketing Executive": {
        "domain": "Marketing & Operations",
        "core_skills": [
            "marketing", "market research", "branding", "communication",
            "content strategy", "campaign management",
        ],
        "good_to_have": [
            "digital marketing", "seo", "crm", "event management",
            "public relations", "ms office",
        ],
    },
    "Operations Executive": {
        "domain": "Marketing & Operations",
        "core_skills": [
            "operations management", "supply chain", "logistics",
            "ms excel", "coordination", "inventory management",
        ],
        "good_to_have": [
            "sap", "lean management", "six sigma", "erp",
            "vendor management", "process improvement",
        ],
    },
    "Product Manager": {
        "domain": "Marketing & Operations",
        "core_skills": [
            "product management", "market research", "stakeholder management",
            "roadmap planning", "agile", "user research", "data analysis",
        ],
        "good_to_have": [
            "sql", "figma", "jira", "a/b testing", "pricing strategy",
            "competitive analysis", "technical understanding",
        ],
    },
    # ── Healthcare ──────────────────────────────────────────────────────
    "Staff Nurse": {
        "domain": "Healthcare",
        "core_skills": [
            "patient care", "clinical documentation", "vital signs monitoring",
            "medical terminology", "medication administration", "infection control",
        ],
        "good_to_have": [
            "critical care", "emergency response", "ehr systems",
            "patient education", "teamwork", "communication",
        ],
    },
    "Healthcare Administrator": {
        "domain": "Healthcare",
        "core_skills": [
            "healthcare management", "healthcare compliance", "medical terminology",
            "operations management", "budgeting", "documentation",
        ],
        "good_to_have": [
            "ehr systems", "quality assurance", "patient relations",
            "regulatory compliance", "ms office", "leadership",
        ],
    },
    # ── Education ───────────────────────────────────────────────────────
    "Corporate Trainer": {
        "domain": "Education",
        "core_skills": [
            "training delivery", "curriculum planning", "communication",
            "presentation", "assessment design", "adult learning",
        ],
        "good_to_have": [
            "lms", "e-learning", "instructional design", "ms office",
            "public speaking", "content creation",
        ],
    },
    "Instructional Designer": {
        "domain": "Education",
        "core_skills": [
            "instructional design", "curriculum planning", "e-learning",
            "content creation", "assessment design", "lms",
        ],
        "good_to_have": [
            "articulate", "adobe captivate", "video editing",
            "graphic design", "ux design", "gamification",
        ],
    },
    # ── Management ──────────────────────────────────────────────────────
    "Project Manager": {
        "domain": "Management",
        "core_skills": [
            "project management", "stakeholder management", "agile",
            "team management", "budgeting", "risk management", "communication",
        ],
        "good_to_have": [
            "jira", "pmp", "scrum", "ms project", "confluence",
            "resource planning", "change management",
        ],
    },
    "HR Executive": {
        "domain": "Management",
        "core_skills": [
            "recruitment", "employee relations", "hr policies",
            "payroll", "compliance", "communication", "ms office",
        ],
        "good_to_have": [
            "hris", "talent management", "performance management",
            "employer branding", "training & development", "labor law",
        ],
    },
    "Management Trainee": {
        "domain": "Management",
        "core_skills": [
            "communication", "leadership", "teamwork", "ms office",
            "problem solving", "business communication", "adaptability",
        ],
        "good_to_have": [
            "project management", "data analysis", "presentation",
            "strategic thinking", "time management",
        ],
    },
    # ── Arts & Humanities ───────────────────────────────────────────────
    "Content Writer": {
        "domain": "Arts & Humanities",
        "core_skills": [
            "content writing", "seo", "research", "editing",
            "grammar", "communication", "creativity",
        ],
        "good_to_have": [
            "copywriting", "wordpress", "social media", "content strategy",
            "cms", "storytelling", "analytics",
        ],
    },
    "UX Designer": {
        "domain": "Arts & Humanities",
        "core_skills": [
            "ui/ux", "figma", "wireframing", "prototyping",
            "user research", "design thinking", "usability testing",
        ],
        "good_to_have": [
            "adobe xd", "sketch", "html", "css", "interaction design",
            "accessibility", "visual design",
        ],
    },
    # ── Administration ──────────────────────────────────────────────────
    "Administrative Assistant": {
        "domain": "Administration",
        "core_skills": [
            "ms office", "scheduling", "documentation", "coordination",
            "email etiquette", "record keeping", "communication",
        ],
        "good_to_have": [
            "data entry", "customer handling", "travel management",
            "filing systems", "erp", "typing speed",
        ],
    },
    "Executive Assistant": {
        "domain": "Administration",
        "core_skills": [
            "ms office", "calendar management", "documentation",
            "communication", "travel coordination", "email etiquette",
        ],
        "good_to_have": [
            "presentation", "minute taking", "event coordination",
            "confidentiality", "multitasking", "crm",
        ],
    },
    # ── Core Engineering ────────────────────────────────────────────────
    "Design Engineer": {
        "domain": "Core Engineering",
        "core_skills": [
            "autocad", "solidworks", "technical drawing", "3d modeling",
            "engineering analysis", "quality control",
        ],
        "good_to_have": [
            "ansys", "catia", "gd&t", "project documentation",
            "manufacturing processes", "prototyping",
        ],
    },
    "Site Engineer": {
        "domain": "Core Engineering",
        "core_skills": [
            "site supervision", "quality control", "safety standards",
            "project documentation", "autocad", "material management",
        ],
        "good_to_have": [
            "ms project", "primavera", "cost estimation",
            "structural analysis", "team coordination", "surveying",
        ],
    },
    # ── General / Fresher ───────────────────────────────────────────────
    "Graduate Trainee": {
        "domain": "General / Fresher",
        "core_skills": [
            "communication", "ms office", "teamwork", "problem solving",
            "adaptability", "time management",
        ],
        "good_to_have": [
            "presentation", "data entry", "customer relations",
            "basic computing", "english proficiency",
        ],
    },
}


def get_skills_for_role(role_name: str) -> dict[str, Any] | None:
    """Look up the required skills for a role using fuzzy matching.

    Returns the best-matching entry from ROLE_SKILL_REQUIREMENTS, or None.
    """
    if not role_name or not role_name.strip():
        return None
    query = role_name.strip().lower()

    # 1. Exact match (case-insensitive)
    for role, profile in ROLE_SKILL_REQUIREMENTS.items():
        if role.lower() == query:
            return {"role": role, **profile}

    # 2. Substring match — query inside role name or vice-versa
    candidates: list[tuple[str, int]] = []
    for role, profile in ROLE_SKILL_REQUIREMENTS.items():
        role_lower = role.lower()
        if query in role_lower or role_lower in query:
            # Prefer shorter edit distance (tighter match)
            candidates.append((role, abs(len(role_lower) - len(query))))

    if candidates:
        candidates.sort(key=lambda c: c[1])
        best = candidates[0][0]
        return {"role": best, **ROLE_SKILL_REQUIREMENTS[best]}

    # 3. Token overlap — at least half the query tokens match a role name
    query_tokens = set(re.findall(r"[a-z]+", query))
    best_role: str | None = None
    best_overlap = 0
    for role in ROLE_SKILL_REQUIREMENTS:
        role_tokens = set(re.findall(r"[a-z]+", role.lower()))
        overlap = len(query_tokens & role_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_role = role
    if best_role and best_overlap >= max(1, len(query_tokens) // 2):
        return {"role": best_role, **ROLE_SKILL_REQUIREMENTS[best_role]}

    # 4. Domain fallback — find the closest domain and return its first role
    domain = detect_domain(role_name)
    profile = DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["General / Fresher"])
    first_role = profile["roles"][0] if profile["roles"] else "Graduate Trainee"
    if first_role in ROLE_SKILL_REQUIREMENTS:
        return {"role": first_role, **ROLE_SKILL_REQUIREMENTS[first_role]}

    return None


def analyze_for_target_role(
    matched_skills: list[str], target_role: str
) -> dict[str, Any]:
    """Compare the user's detected resume skills against a target role's needs.

    Returns a structured gap analysis with match %, present/missing skills,
    a 3-step roadmap, and a narrative recommendation.
    """
    role_info = get_skills_for_role(target_role)
    if role_info is None:
        return {
            "target_role": target_role,
            "matched_role": None,
            "error": f"Could not find a matching role profile for '{target_role}'. Try a more common role title.",
        }

    resolved_role = role_info["role"]
    core: list[str] = role_info.get("core_skills", [])
    nice: list[str] = role_info.get("good_to_have", [])
    domain: str = role_info.get("domain", "General / Fresher")
    all_required = core + nice

    matched_lower = {s.lower() for s in matched_skills}

    skills_you_have: list[str] = []
    skills_you_need: list[str] = []
    core_have: list[str] = []
    core_need: list[str] = []

    for skill in core:
        if skill.lower() in matched_lower:
            skills_you_have.append(skill)
            core_have.append(skill)
        else:
            skills_you_need.append(skill)
            core_need.append(skill)

    for skill in nice:
        if skill.lower() in matched_lower:
            skills_you_have.append(skill)
        else:
            skills_you_need.append(skill)

    total = max(1, len(all_required))
    match_pct = round(100 * len(skills_you_have) / total)

    # Build a tailored 3-step roadmap
    top_gaps = core_need[:4] if core_need else skills_you_need[:4]
    roadmap = [
        {
            "step": 1,
            "title": f"Master {resolved_role} fundamentals",
            "focus": f"Prioritize learning {', '.join(top_gaps[:3]) or 'role-critical skills'} as these are core requirements.",
            "project_idea": f"Complete a hands-on project demonstrating {top_gaps[0] if top_gaps else 'core competency'} in a realistic scenario.",
        },
        {
            "step": 2,
            "title": "Build proof of competence",
            "focus": f"Strengthen {', '.join(top_gaps[1:3]) or 'remaining skill gaps'} through structured courses or certifications.",
            "project_idea": f"Create a portfolio piece or case study relevant to {resolved_role} positions.",
        },
        {
            "step": 3,
            "title": f"Position yourself for {resolved_role}",
            "focus": f"Tailor your resume to highlight {', '.join(skills_you_have[:3]) or 'your existing strengths'} and showcase your new competencies.",
            "project_idea": f"Apply to {resolved_role} roles and prepare for domain-specific interview questions.",
        },
    ]

    # Build recommendation narrative
    if match_pct >= 75:
        recommendation = (
            f"Excellent fit! You already possess {len(skills_you_have)} of {total} skills needed for a {resolved_role} role. "
            f"Focus on polishing {', '.join(core_need[:2]) or 'advanced competencies'} to strengthen your candidacy. "
            f"Your existing expertise in {', '.join(skills_you_have[:3])} positions you well for this transition."
        )
    elif match_pct >= 45:
        recommendation = (
            f"Good foundation for a {resolved_role} role. You have {len(skills_you_have)} of {total} required skills. "
            f"The key gaps are in {', '.join(core_need[:3])} — addressing these will significantly improve your readiness. "
            f"Leverage your strengths in {', '.join(skills_you_have[:3]) or 'your current skill set'} as a springboard."
        )
    else:
        recommendation = (
            f"Transitioning to {resolved_role} will require focused upskilling. You currently match {len(skills_you_have)} of {total} skills. "
            f"Start with the core requirements: {', '.join(core_need[:3])}. "
            f"Consider structured courses and hands-on projects to build a credible profile for this role."
        )

    return {
        "target_role": target_role,
        "matched_role": resolved_role,
        "domain": domain,
        "role_match_percentage": match_pct,
        "skills_you_have": skills_you_have,
        "skills_you_need": skills_you_need,
        "core_skills_matched": len(core_have),
        "core_skills_total": len(core),
        "learning_roadmap": roadmap,
        "recommendation": recommendation,
    }


# ===========================================================================
# SEMANTIC SKILL ONTOLOGY
# ---------------------------------------------------------------------------
# Maps a canonical/parent skill to the concrete tools, libraries, frameworks
# and concepts that imply it. This powers "semantic" skill matching WITHOUT
# relying on exact keyword hits: a resume that lists Flask / FastAPI / Pandas
# is credited with "python"; TensorFlow / CNN / Neural Networks imply
# "deep learning", etc. When sentence-transformer embeddings are available the
# NLP engine augments this ontology with true vector similarity; when they are
# not, this ontology is the deterministic fallback so the behaviour degrades
# gracefully instead of collapsing back to keyword counting.
# ===========================================================================

SKILL_ONTOLOGY: dict[str, list[str]] = {
    # ── Programming & software ──────────────────────────────────────────
    "python": [
        "flask", "fastapi", "django", "pandas", "numpy", "scipy", "opencv",
        "pytest", "asyncio", "sqlalchemy", "matplotlib", "seaborn", "poetry",
    ],
    "javascript": [
        "react", "node.js", "nodejs", "express", "vue.js", "angular", "next.js",
        "typescript", "jquery", "redux", "svelte", "webpack", "vite",
    ],
    "java": ["spring boot", "spring", "hibernate", "maven", "gradle", "jsp", "servlets", "kotlin"],
    "c++": ["stl", "qt", "unreal engine", "boost", "opencv"],
    "c#": [".net", "asp.net", "unity", "entity framework", "blazor"],
    "go": ["golang", "gin", "goroutines"],
    "php": ["laravel", "symfony", "wordpress", "codeigniter"],
    "ruby": ["rails", "ruby on rails", "sinatra"],
    "sql": [
        "mysql", "postgresql", "postgres", "oracle", "sql server", "sqlite",
        "t-sql", "pl/sql", "stored procedures", "query optimization", "joins",
    ],
    "nosql": ["mongodb", "cassandra", "dynamodb", "couchdb", "redis", "neo4j", "firebase"],
    # ── Data / AI / ML ─────────────────────────────────────────────────
    "machine learning": [
        "scikit-learn", "sklearn", "xgboost", "lightgbm", "random forest",
        "regression", "classification", "clustering", "feature engineering",
        "gradient boosting", "svm", "decision trees",
    ],
    "deep learning": [
        "tensorflow", "keras", "pytorch", "cnn", "rnn", "lstm", "gan",
        "neural networks", "transformers", "bert", "convolutional",
        "computer vision", "attention", "backpropagation",
    ],
    "nlp": [
        "natural language processing", "spacy", "nltk", "bert", "gpt",
        "hugging face", "huggingface", "transformers", "text classification",
        "named entity recognition", "sentiment analysis", "word embeddings", "llm",
    ],
    "data science": [
        "pandas", "numpy", "jupyter", "statistics", "hypothesis testing",
        "data wrangling", "exploratory data analysis", "eda", "a/b testing",
    ],
    "data visualization": ["tableau", "power bi", "matplotlib", "seaborn", "plotly", "d3.js", "looker"],
    "big data": ["spark", "hadoop", "hive", "kafka", "flink", "databricks", "airflow", "mapreduce"],
    "data engineering": ["etl", "elt", "airflow", "dbt", "data pipelines", "snowflake", "redshift", "bigquery"],
    # ── Cloud / DevOps ─────────────────────────────────────────────────
    "aws": [
        "ec2", "s3", "lambda", "cloudformation", "eks", "ecs", "rds", "dynamodb",
        "iam", "vpc", "cloudwatch", "route 53", "sagemaker", "fargate", "sns", "sqs",
    ],
    "azure": ["azure devops", "azure functions", "aks", "blob storage", "azure ad", "cosmos db"],
    "gcp": ["google cloud", "bigquery", "gke", "cloud run", "vertex ai", "pub/sub"],
    "cloud computing": ["aws", "azure", "gcp", "cloud", "serverless", "iaas", "paas", "saas"],
    "devops": [
        "ci/cd", "jenkins", "github actions", "gitlab ci", "docker", "kubernetes",
        "terraform", "ansible", "helm", "argocd", "infrastructure as code",
    ],
    "kubernetes": ["k8s", "helm", "eks", "aks", "gke", "kubectl", "openshift"],
    "docker": ["containers", "containerization", "docker compose", "podman"],
    "ci/cd": ["jenkins", "github actions", "gitlab ci", "circleci", "travis", "azure devops"],
    # ── Networking / Security ──────────────────────────────────────────
    "networking": ["tcp/ip", "dns", "dhcp", "vlan", "routing", "switching", "lan", "wan", "vpn", "subnetting"],
    "cisco": ["ccna", "ccnp", "ios", "routing", "switching", "packet tracer"],
    "cybersecurity": [
        "network security", "penetration testing", "siem", "firewall",
        "vulnerability assessment", "incident response", "ethical hacking",
        "owasp", "threat intelligence", "encryption",
    ],
    # ── Commerce / Finance ─────────────────────────────────────────────
    "financial analysis": [
        "financial modeling", "valuation", "forecasting", "budgeting",
        "dcf", "ratio analysis", "variance analysis", "financial reporting",
    ],
    "accounting": ["tally", "bookkeeping", "gst", "accounts payable", "accounts receivable", "quickbooks", "ledger"],
    "taxation": ["gst", "income tax", "tds", "tax planning", "tax compliance", "vat"],
    "investment": ["portfolio management", "equity research", "mutual funds", "trading", "wealth management"],
    # ── Marketing / Sales ──────────────────────────────────────────────
    "digital marketing": [
        "seo", "sem", "google ads", "facebook ads", "content marketing",
        "email marketing", "social media marketing", "google analytics", "ppc",
    ],
    "marketing": ["branding", "market research", "campaign management", "crm", "advertising", "public relations"],
    "sales": ["lead generation", "business development", "b2b", "b2c", "cold calling", "negotiation", "crm"],
    # ── Design ─────────────────────────────────────────────────────────
    "ui/ux": ["figma", "adobe xd", "sketch", "wireframing", "prototyping", "user research", "usability testing"],
    "graphic design": ["photoshop", "illustrator", "indesign", "canva", "coreldraw", "typography"],
    # ── Core Engineering ───────────────────────────────────────────────
    "mechanical engineering": ["autocad", "solidworks", "catia", "ansys", "thermodynamics", "gd&t", "cnc"],
    "civil engineering": ["autocad", "staad pro", "revit", "structural analysis", "estimation", "surveying", "bim"],
    "electrical engineering": ["circuit design", "plc", "scada", "matlab", "power systems", "control systems"],
    # ── Healthcare ─────────────────────────────────────────────────────
    "patient care": ["clinical documentation", "vital signs", "medication administration", "nursing", "bedside care"],
    "clinical research": ["clinical trials", "gcp", "protocol design", "regulatory compliance", "pharmacovigilance"],
    # ── Management / soft ──────────────────────────────────────────────
    "project management": ["agile", "scrum", "kanban", "jira", "pmp", "prince2", "gantt", "stakeholder management"],
    "leadership": ["team management", "mentoring", "people management", "delegation", "strategic planning"],
}

# Reverse index: concrete term -> the parent/canonical skill(s) it implies.
SKILL_ALIAS_INDEX: dict[str, set[str]] = {}
for _canonical, _aliases in SKILL_ONTOLOGY.items():
    SKILL_ALIAS_INDEX.setdefault(_canonical, set()).add(_canonical)
    for _alias in _aliases:
        SKILL_ALIAS_INDEX.setdefault(_alias.lower(), set()).add(_canonical)


def expand_skill_terms(text_lower: str) -> set[str]:
    """Return the set of canonical skills implied by the concrete terms present.

    Example: a resume containing "flask" and "pandas" yields {"python", ...};
    "tensorflow" and "cnn" yield {"deep learning"}. This is the deterministic
    backbone of semantic matching used when embeddings are unavailable.
    """
    implied: set[str] = set()
    for term, canonicals in SKILL_ALIAS_INDEX.items():
        if term in text_lower:
            implied.update(canonicals)
    return implied


# ===========================================================================
# CERTIFICATION KNOWLEDGE BASE
# ===========================================================================

CERTIFICATION_PROVIDERS: dict[str, list[str]] = {
    "AWS": ["aws certified", "solutions architect", "aws developer", "aws sysops", "cloud practitioner"],
    "Microsoft": ["azure fundamentals", "az-900", "az-104", "az-204", "microsoft certified", "mcsa", "mcse", "power platform"],
    "Google": ["google cloud certified", "associate cloud engineer", "professional data engineer", "google analytics", "google ads certified"],
    "IBM": ["ibm data science", "ibm certified"],
    "Oracle": ["oracle certified", "oca", "ocp", "java se"],
    "Cisco": ["ccna", "ccnp", "ccie", "cisco certified"],
    "Salesforce": ["salesforce certified", "salesforce administrator", "platform developer"],
    "NVIDIA": ["nvidia deep learning", "dli certificate"],
    "Coursera": ["coursera", "specialization"],
    "Udemy": ["udemy"],
    "NPTEL": ["nptel", "swayam"],
    "Databricks": ["databricks certified", "lakehouse"],
    "Snowflake": ["snowpro", "snowflake certified"],
    "DeepLearning.AI": ["deeplearning.ai", "deep learning specialization"],
    "HuggingFace": ["hugging face", "huggingface course"],
    "Meta": ["meta certified", "meta front-end", "meta back-end"],
    "OpenAI": ["openai"],
    "PMI": ["pmp", "capm", "prince2"],
    "Scrum": ["csm", "psm", "certified scrum master"],
    "CompTIA": ["comptia", "security+", "network+", "a+"],
}


def detect_certifications(text_lower: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for provider, markers in CERTIFICATION_PROVIDERS.items():
        for marker in markers:
            if marker in text_lower and provider not in seen:
                seen.add(provider)
                found.append({"provider": provider, "evidence": marker})
                break
    return found


# ===========================================================================
# SOFT SKILLS  (detected via contextual verb/phrase cues, not just the word)
# ===========================================================================

SOFT_SKILL_CUES: dict[str, tuple[str, ...]] = {
    "Leadership": ("led", "managed a team", "mentored", "spearheaded", "directed", "supervised", "headed"),
    "Communication": ("presented", "communicated", "documented", "authored", "liaised", "negotiated", "articulated"),
    "Ownership": ("owned", "responsible for", "drove", "took ownership", "accountable"),
    "Teamwork": ("collaborated", "cross-functional", "team of", "partnered", "coordinated with"),
    "Critical Thinking": ("analyzed", "evaluated", "assessed", "diagnosed", "investigated"),
    "Problem Solving": ("solved", "resolved", "troubleshot", "debugged", "optimized", "streamlined"),
    "Time Management": ("prioritized", "on schedule", "met deadlines", "delivered on time", "scheduled"),
    "Presentation": ("presented", "demonstrated", "showcased", "pitched"),
    "Negotiation": ("negotiated", "closed deals", "vendor management", "contract"),
    "Adaptability": ("adapted", "flexible", "learned quickly", "fast-paced", "versatile"),
    "Decision Making": ("decided", "prioritized", "strategic", "judgement", "evaluated options"),
    "Creativity": ("designed", "created", "innovated", "conceptualized", "reimagined"),
}


def detect_soft_skills(text_lower: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for skill, cues in SOFT_SKILL_CUES.items():
        hit = next((cue for cue in cues if cue in text_lower), None)
        if hit:
            found.append({"skill": skill, "evidence": hit})
    return found


# ===========================================================================
# ACTION VERBS  (strong vs. weak)
# ===========================================================================

STRONG_ACTION_VERBS = frozenset({
    "designed", "built", "developed", "implemented", "reduced", "increased",
    "created", "managed", "optimized", "generated", "automated", "led",
    "launched", "delivered", "architected", "engineered", "improved",
    "spearheaded", "streamlined", "accelerated", "transformed", "pioneered",
    "orchestrated", "drove", "scaled", "deployed", "established", "boosted",
})

WEAK_VERBS = frozenset({
    "worked", "helped", "assisted", "involved", "participated", "responsible",
    "handled", "did", "made", "used", "tried", "attempted", "supported",
})


# ===========================================================================
# EDUCATION / DEGREE DETECTION  (all domains)
# ===========================================================================

DEGREE_PATTERNS: dict[str, tuple[str, ...]] = {
    "B.E / B.Tech": ("b.e", "b.tech", "be ", "btech", "bachelor of engineering", "bachelor of technology"),
    "M.E / M.Tech": ("m.e", "m.tech", "mtech", "master of engineering", "master of technology"),
    "MCA": ("mca", "master of computer applications"),
    "BCA": ("bca", "bachelor of computer applications"),
    "B.Sc": ("b.sc", "bsc", "bachelor of science"),
    "M.Sc": ("m.sc", "msc", "master of science"),
    "MBA": ("mba", "master of business administration", "pgdm"),
    "B.Com": ("b.com", "bcom", "bachelor of commerce"),
    "M.Com": ("m.com", "mcom", "master of commerce"),
    "BA": ("b.a", "bachelor of arts"),
    "MA": ("m.a", "master of arts"),
    "LLB": ("llb", "ll.b", "bachelor of law", "bachelor of laws"),
    "LLM": ("llm", "ll.m", "master of law"),
    "MBBS": ("mbbs", "bachelor of medicine"),
    "BDS": ("bds",),
    "B.Pharm": ("b.pharm", "bpharm", "bachelor of pharmacy"),
    "B.Arch": ("b.arch", "bachelor of architecture"),
    "B.Ed": ("b.ed", "bachelor of education"),
    "Ph.D": ("ph.d", "phd", "doctorate", "doctor of philosophy"),
    "Diploma": ("diploma", "polytechnic"),
    "PhD": ("ph.d", "phd"),
}


def detect_degrees(text_lower: str) -> list[str]:
    found: list[str] = []
    for degree, markers in DEGREE_PATTERNS.items():
        if degree in found:
            continue
        if any(re.search(r"\b" + re.escape(m) + r"\b", text_lower) for m in markers):
            found.append(degree)
    # Deduplicate near-identical (Ph.D vs PhD)
    out: list[str] = []
    seen: set[str] = set()
    for d in found:
        key = d.replace(".", "").replace(" ", "").lower()
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


# ===========================================================================
# RESUME SECTION TAXONOMY  (full set for structure scoring)
# ===========================================================================

RESUME_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "Header / Name": ("resume", "curriculum vitae", "cv"),
    "Contact Details": ("contact", "email", "phone", "mobile"),
    "LinkedIn": ("linkedin.com", "linkedin"),
    "GitHub": ("github.com", "github"),
    "Portfolio": ("portfolio", "behance", "dribbble", ".dev", "personal website"),
    "Professional Summary": ("summary", "objective", "profile", "about me", "career objective"),
    "Work Experience": ("experience", "work history", "employment", "professional experience", "internship"),
    "Projects": ("projects", "project work", "academic projects", "key projects"),
    "Skills": ("skills", "technical skills", "core competencies", "competencies"),
    "Education": ("education", "academic", "qualification", "academics"),
    "Certifications": ("certification", "certificate", "certified", "licenses"),
    "Publications": ("publication", "research paper", "journal", "conference"),
    "Awards": ("award", "honor", "honour", "recognition"),
    "Achievements": ("achievement", "accomplishment", "key achievements"),
    "Languages": ("languages known", "languages:", "linguistic"),
    "Extra Activities": ("extracurricular", "volunteer", "hobbies", "interests", "activities"),
}


def detect_resume_sections(text_lower: str) -> dict[str, bool]:
    present: dict[str, bool] = {}
    for section, markers in RESUME_SECTION_ALIASES.items():
        present[section] = any(m in text_lower for m in markers)
    return present
