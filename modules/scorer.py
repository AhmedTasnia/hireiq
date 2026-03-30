"""
Scoring engine: given job criteria and candidate CV info,
produces a score out of 100 with a detailed breakdown.

Default weights (configurable):
  Education       30 pts
  Experience      25 pts
  Skills          20 pts
  Age             15 pts
  Gender          10 pts
"""

from typing import Optional

DEFAULT_WEIGHTS = {
    "education": 30,
    "experience": 25,
    "skills": 20,
    "age": 15,
    "gender": 10,
}

EDUCATION_HIERARCHY = ["SSC", "HSC", "Diploma", "Bachelor's", "MBA", "Master's", "PhD"]


def _education_score(criteria: dict, cv: dict, max_pts: int) -> tuple[float, str]:
    required_level = criteria.get("education", {}).get("level")
    required_field = criteria.get("education", {}).get("field")
    cv_level = cv.get("education", {}).get("level")
    cv_field = cv.get("education", {}).get("field")

    if not required_level:
        return max_pts, "No education requirement specified — full marks"

    # Check level
    req_idx = EDUCATION_HIERARCHY.index(required_level) if required_level in EDUCATION_HIERARCHY else -1
    cv_idx = EDUCATION_HIERARCHY.index(cv_level) if cv_level in EDUCATION_HIERARCHY else -1

    if cv_idx == -1:
        level_score = 0.1
        note = f"Education level not detected in CV"
    elif cv_idx >= req_idx:
        level_score = 1.0
        note = f"✅ {cv_level} meets requirement ({required_level})"
    elif cv_idx == req_idx - 1:
        level_score = 0.5
        note = f"⚠️ {cv_level} is one level below requirement ({required_level})"
    else:
        level_score = 0.15
        note = f"❌ {cv_level} is well below requirement ({required_level})"

    # Field bonus/penalty
    field_multiplier = 1.0
    if required_field and cv_field:
        req_f = required_field.lower()
        cv_f = cv_field.lower()
        if req_f in cv_f or cv_f in req_f:
            field_multiplier = 1.0
            note += f" | ✅ Field match ({cv_field})"
        else:
            field_multiplier = 0.7
            note += f" | ⚠️ Field mismatch (required {required_field}, found {cv_field})"
    elif required_field and not cv_field:
        field_multiplier = 0.8
        note += f" | ⚠️ Field not detected in CV (required {required_field})"

    score = round(max_pts * level_score * field_multiplier, 1)
    return score, note


def _experience_score(criteria: dict, cv: dict, max_pts: int) -> tuple[float, str]:
    req = criteria.get("experience", {})
    req_min = req.get("min") or 0
    req_max = req.get("max")
    cv_years = cv.get("experience_years") or 0

    if req_min == 0 and not req_max:
        return max_pts, "No experience requirement specified — full marks"

    if cv_years >= req_min:
        if req_max and cv_years > req_max:
            score = max_pts * 0.85
            note = f"⚠️ {cv_years} yrs experience (above max {req_max} yrs)"
        else:
            score = max_pts
            note = f"✅ {cv_years} yrs meets requirement (min {req_min} yrs)"
    elif cv_years >= req_min - 1:
        score = max_pts * 0.6
        note = f"⚠️ {cv_years} yrs is close to requirement (min {req_min} yrs)"
    else:
        ratio = cv_years / req_min if req_min > 0 else 0
        score = round(max_pts * max(0.1, ratio * 0.4), 1)
        note = f"❌ {cv_years} yrs is below requirement (min {req_min} yrs)"

    return round(score, 1), note


def _skills_score(criteria: dict, cv: dict, max_pts: int) -> tuple[float, str]:
    required_skills = criteria.get("skills", [])
    cv_skills = cv.get("skills", [])

    if not required_skills:
        return max_pts, "No specific skills required — full marks"

    req_set = set(s.lower() for s in required_skills)
    cv_set = set(s.lower() for s in cv_skills)
    matched = req_set & cv_set
    ratio = len(matched) / len(req_set) if req_set else 1.0
    score = round(max_pts * ratio, 1)

    if matched:
        note = f"✅ Matched {len(matched)}/{len(req_set)} skills: {', '.join(sorted(matched))}"
    else:
        note = f"❌ No required skills matched (required: {', '.join(sorted(req_set))})"

    return score, note


def _age_score(criteria: dict, cv: dict, max_pts: int) -> tuple[float, str]:
    age_req = criteria.get("age", {})
    min_age = age_req.get("min")
    max_age = age_req.get("max")
    cv_age = cv.get("age")

    if not min_age and not max_age:
        return max_pts, "No age requirement specified — full marks"

    if cv_age is None:
        return max_pts * 0.5, "⚠️ Age not found in CV"

    in_range = True
    notes = []
    if min_age and cv_age < min_age:
        in_range = False
        notes.append(f"❌ Age {cv_age} below minimum {min_age}")
    if max_age and cv_age > max_age:
        in_range = False
        notes.append(f"❌ Age {cv_age} above maximum {max_age}")

    if in_range:
        score = max_pts
        note = f"✅ Age {cv_age} is within required range"
    else:
        score = 0.0
        note = " | ".join(notes)

    return score, note


def _gender_score(criteria: dict, cv: dict, max_pts: int) -> tuple[float, str]:
    required_gender = criteria.get("gender")
    cv_gender = cv.get("gender")

    if not required_gender:
        return max_pts, "No gender preference stated — full marks for all"

    if not cv_gender:
        return max_pts * 0.5, f"⚠️ Gender not detected in CV (preferred: {required_gender})"

    if cv_gender.lower() == required_gender.lower():
        return max_pts, f"✅ Gender matches preference ({required_gender})"
    else:
        return 0.0, f"❌ Gender mismatch (required {required_gender}, found {cv_gender})"


# ── public API ────────────────────────────────────────────────────────────────

def score_cv(criteria: dict, cv_info: dict, weights: Optional[dict] = None) -> dict:
    """
    Score a single CV against job criteria.

    Returns:
        {
            total: float (0-100),
            breakdown: {
                education: {score, max, note},
                experience: {score, max, note},
                skills: {score, max, note},
                age: {score, max, note},
                gender: {score, max, note},
            }
        }
    """
    w = weights or DEFAULT_WEIGHTS

    edu_score, edu_note = _education_score(criteria, cv_info, w["education"])
    exp_score, exp_note = _experience_score(criteria, cv_info, w["experience"])
    sk_score, sk_note = _skills_score(criteria, cv_info, w["skills"])
    age_score, age_note = _age_score(criteria, cv_info, w["age"])
    gen_score, gen_note = _gender_score(criteria, cv_info, w["gender"])

    total = edu_score + exp_score + sk_score + age_score + gen_score

    return {
        "total": round(total, 1),
        "breakdown": {
            "education": {"score": edu_score, "max": w["education"], "note": edu_note},
            "experience": {"score": exp_score, "max": w["experience"], "note": exp_note},
            "skills": {"score": sk_score, "max": w["skills"], "note": sk_note},
            "age": {"score": age_score, "max": w["age"], "note": age_note},
            "gender": {"score": gen_score, "max": w["gender"], "note": gen_note},
        },
    }


def rank_candidates(candidates: list) -> list:
    """Sort candidates by total score descending and assign rank."""
    sorted_candidates = sorted(candidates, key=lambda c: c["score"]["total"], reverse=True)
    for i, c in enumerate(sorted_candidates):
        c["rank"] = i + 1
    return sorted_candidates
