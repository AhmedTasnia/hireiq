import re
from typing import Optional


# ── helpers ──────────────────────────────────────────────────────────────────

def _find_age(text: str) -> dict:
    """Extract min/max age constraints."""
    result = {"min": None, "max": None}
    text_l = text.lower()

    # "under 30", "below 35", "not more than 40"
    m = re.search(r"(?:under|below|less than|not more than|maximum age[:\s]*)\s*(\d{2})", text_l)
    if m:
        result["max"] = int(m.group(1))

    # "above 18", "minimum age 22", "at least 25"
    m = re.search(r"(?:above|over|more than|minimum age[:\s]*|at least)\s*(\d{2})", text_l)
    if m:
        result["min"] = int(m.group(1))

    # "between 25 and 35" / "25-35 years"
    m = re.search(r"(\d{2})\s*(?:to|-|–)\s*(\d{2})\s*years?", text_l)
    if m:
        result["min"] = int(m.group(1))
        result["max"] = int(m.group(2))

    return result


def _find_gender(text: str) -> Optional[str]:
    """Detect stated gender preference."""
    text_l = text.lower()
    male_kw = ["male", "man", "men", "gentleman", "he/him"]
    female_kw = ["female", "woman", "women", "lady", "ladies", "she/her"]

    gender_section = re.search(
        r"(?:gender|sex)[:\s–-]+([^\n.]{0,60})", text_l
    )
    if gender_section:
        snippet = gender_section.group(1)
        if any(k in snippet for k in male_kw):
            return "male"
        if any(k in snippet for k in female_kw):
            return "female"

    # Fallback: look for "prefer male / female candidates"
    if re.search(r"prefer(?:red)?\s+male", text_l):
        return "male"
    if re.search(r"prefer(?:red)?\s+female", text_l):
        return "female"

    return None


def _find_experience(text: str) -> dict:
    """Extract required years of experience."""
    result = {"min": None, "max": None}
    text_l = text.lower()

    # "minimum 3 years", "at least 2 years experience"
    m = re.search(
        r"(?:minimum|at least|min\.?)\s*(\d+)\+?\s*years?\s*(?:of\s*)?(?:work\s*)?experience",
        text_l,
    )
    if m:
        result["min"] = int(m.group(1))

    # "3+ years", "5 years experience"
    m = re.search(r"(\d+)\+\s*years?\s*(?:of\s*)?(?:work\s*)?experience", text_l)
    if m and result["min"] is None:
        result["min"] = int(m.group(1))

    # Plain "X years experience"
    m = re.search(r"(\d+)\s*years?\s*(?:of\s*)?(?:work\s*)?experience", text_l)
    if m and result["min"] is None:
        result["min"] = int(m.group(1))

    # "1-3 years"
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*years?\s*(?:of\s*)?(?:work\s*)?experience", text_l)
    if m:
        result["min"] = int(m.group(1))
        result["max"] = int(m.group(2))

    return result


def _find_education(text: str) -> dict:
    """Extract required education level and field."""
    result = {"level": None, "field": None}
    text_l = text.lower()

    levels = [
        ("phd", "PhD"),
        ("doctorate", "PhD"),
        ("master", "Master's"),
        ("mba", "MBA"),
        ("bachelor", "Bachelor's"),
        ("b.sc", "Bachelor's"),
        ("bsc", "Bachelor's"),
        ("b.s.", "Bachelor's"),
        ("hsc", "HSC"),
        ("ssc", "SSC"),
        ("diploma", "Diploma"),
        ("hnd", "HND"),
    ]
    for kw, label in levels:
        if kw in text_l:
            result["level"] = label
            break

    # field of study
    field_patterns = [
        r"(?:in|of)\s+(computer science|cse|information technology|it|business administration|"
        r"finance|accounting|marketing|economics|engineering|electrical|mechanical|civil|"
        r"human resources|hr|mathematics|statistics|law|medicine|pharmacy|nursing|"
        r"management|commerce|science)",
    ]
    for pat in field_patterns:
        m = re.search(pat, text_l)
        if m:
            result["field"] = m.group(1).strip().title()
            break

    return result


def _find_skills(text: str) -> list:
    """Extract a list of technical/professional skills mentioned."""
    skill_kw = [
        "python", "java", "javascript", "sql", "excel", "word", "powerpoint",
        "photoshop", "autocad", "matlab", "r ", "c++", "php", "html", "css",
        "machine learning", "deep learning", "data analysis", "project management",
        "communication", "leadership", "teamwork", "ms office", "erp", "sap",
        "accounting", "auditing", "tally", "quickbooks", "customer service",
        "sales", "marketing", "research", "writing", "presentation",
        "problem solving", "critical thinking", "time management",
    ]
    text_l = text.lower()
    found = []
    for sk in skill_kw:
        if sk in text_l and sk not in found:
            found.append(sk.strip())
    return found


def _find_job_title(text: str) -> str:
    """Try to extract the job title from the first few lines."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:15]:
        lower = line.lower()
        if any(k in lower for k in ["position", "post", "vacancy", "job title", "role", "designation"]):
            # grab what comes after the colon/dash
            m = re.search(r"[:–-]\s*(.+)", line)
            if m:
                return m.group(1).strip()
        # Or if a line is short and title-cased, it might be the title
        if len(line) < 60 and line.istitle() and len(line.split()) >= 2:
            return line
    return "Unspecified Position"


# ── public API ────────────────────────────────────────────────────────────────

def parse_circular(text: str) -> dict:
    """
    Parse a job circular and return a structured dict of criteria.

    Returns:
        {
            job_title: str,
            age: {min, max},
            gender: str | None,
            experience: {min, max},
            education: {level, field},
            skills: [str],
            raw_text: str
        }
    """
    criteria = {
        "job_title": _find_job_title(text),
        "age": _find_age(text),
        "gender": _find_gender(text),
        "experience": _find_experience(text),
        "education": _find_education(text),
        "skills": _find_skills(text),
        "raw_text": text,
    }
    return criteria
