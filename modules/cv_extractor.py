import re
from typing import Optional


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_name(text: str) -> str:
    """Best-effort name extraction from the first few lines."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:8]:
        # Skip lines that look like labels or section headers
        skip = ["curriculum", "resume", "cv", "contact", "profile", "objective",
                "summary", "email", "phone", "address", "name:"]
        if any(s in line.lower() for s in skip):
            continue
        # Name: <value> pattern
        m = re.match(r"(?:name|full name)[:\s–-]+(.+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # A short title-ish line with 2-4 words is likely the name
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            return line
    return "Unknown Candidate"


def _extract_email(text: str) -> Optional[str]:
    m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return m.group(0) if m else None


def _extract_phone(text: str) -> Optional[str]:
    m = re.search(
        r"(?:\+?88)?(?:01[3-9]\d{8}|"          # BD mobile
        r"\+?\d{1,3}[\s\-]?\d{7,12})",          # International
        text
    )
    return m.group(0).strip() if m else None


def _extract_age(text: str) -> Optional[int]:
    text_l = text.lower()
    # "Age: 27", "DOB: 01/01/1997" → compute from DOB if possible
    m = re.search(r"age[:\s]+(\d{2})", text_l)
    if m:
        return int(m.group(1))
    # Try DOB
    dob = re.search(
        r"(?:dob|date of birth|born)[:\s]+(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",
        text_l
    )
    if dob:
        from datetime import date
        try:
            birth_year = int(dob.group(3))
            age = date.today().year - birth_year
            return age
        except Exception:
            pass
    return None


def _extract_gender(text: str) -> Optional[str]:
    text_l = text.lower()
    m = re.search(r"gender[:\s–-]+([^\n,]{1,20})", text_l)
    if m:
        val = m.group(1).strip().lower()
        if "male" in val and "female" not in val:
            return "male"
        if "female" in val:
            return "female"
    if re.search(r"\b(he|him|his)\b", text_l):
        return "male"
    if re.search(r"\b(she|her|hers)\b", text_l):
        return "female"
    return None


def _extract_experience_years(text: str) -> float:
    """Estimate total years of work experience from CV text."""
    text_l = text.lower()

    # "X years of experience"
    m = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of\s*)?(?:work\s*)?experience", text_l)
    if m:
        return float(m.group(1))

    # Count date ranges like "2018 - 2022" and sum up differences
    ranges = re.findall(r"(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|19\d{2}|present|current|now)", text_l)
    total = 0.0
    from datetime import date
    current_year = date.today().year
    for start, end in ranges:
        try:
            s = int(start)
            e = current_year if end in ("present", "current", "now") else int(end)
            if 1990 <= s <= current_year and s <= e:
                total += e - s
        except Exception:
            pass
    if total > 0:
        return round(total, 1)

    return 0.0


def _extract_education(text: str) -> dict:
    """Extract highest education level and field."""
    result = {"level": None, "field": None}
    text_l = text.lower()

    levels = [
        ("phd", "PhD"), ("doctorate", "PhD"),
        ("master", "Master's"), ("mba", "MBA"), ("msc", "Master's"),
        ("bachelor", "Bachelor's"), ("b.sc", "Bachelor's"), ("bsc", "Bachelor's"),
        ("b.s.", "Bachelor's"), ("honours", "Bachelor's"),
        ("hsc", "HSC"), ("ssc", "SSC"), ("diploma", "Diploma"),
    ]
    for kw, label in levels:
        if kw in text_l:
            result["level"] = label
            break

    fields = [
        "computer science", "cse", "information technology", "business administration",
        "finance", "accounting", "marketing", "economics", "engineering",
        "electrical", "mechanical", "civil", "mathematics", "statistics",
        "management", "commerce", "pharmacy", "nursing", "law", "medicine",
        "human resources", "science",
    ]
    for f in fields:
        if f in text_l:
            result["field"] = f.title()
            break

    return result


def _extract_skills(text: str) -> list:
    """Return list of skills found in CV text."""
    skill_kw = [
        "python", "java", "javascript", "sql", "excel", "word", "powerpoint",
        "photoshop", "autocad", "matlab", "c++", "php", "html", "css",
        "machine learning", "deep learning", "data analysis", "project management",
        "communication", "leadership", "teamwork", "ms office", "erp", "sap",
        "accounting", "auditing", "tally", "quickbooks", "customer service",
        "sales", "marketing", "research", "writing", "presentation",
        "problem solving", "critical thinking", "time management",
    ]
    text_l = text.lower()
    return [sk for sk in skill_kw if sk in text_l]


# ── public API ────────────────────────────────────────────────────────────────

def extract_cv_info(text: str) -> dict:
    """
    Extract structured information from raw CV text.

    Returns:
        {
            name, email, phone, age, gender,
            experience_years, education:{level, field}, skills:[str]
        }
    """
    return {
        "name": _extract_name(text),
        "email": _extract_email(text),
        "phone": _extract_phone(text),
        "age": _extract_age(text),
        "gender": _extract_gender(text),
        "experience_years": _extract_experience_years(text),
        "education": _extract_education(text),
        "skills": _extract_skills(text),
    }
