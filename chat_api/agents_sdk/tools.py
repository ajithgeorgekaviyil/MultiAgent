"""
Mock tools and data for the Agents SDK.

Exposed tools:
- recommend_courses(interest, limit=4, type_filter=None, level=None)
- lookup_schedule()
- summarize_text(text)
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Sequence

from agents import function_tool
from openai import OpenAI

__all__ = ["recommend_courses", "lookup_schedule", "summarize_text"]

# ---------------------------------------------------------------------------
# Catalog data
# ---------------------------------------------------------------------------

INTEREST_ALIASES: Dict[str, str] = {
    # Data Science
    "ml": "data science",
    "machine learning": "data science",
    "datascience": "data science",
    "data-science": "data science",
    "data science": "data science",
    # Artificial Intelligence
    "ai": "artificial intelligence",
    "artificial-intelligence": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",
    # Web
    "web dev": "web",
    "web development": "web",
    # Cloud
    "cloud computing": "cloud",
    # Cybersecurity
    "cybersec": "cybersecurity",
    "security": "cybersecurity",
    # Business Analytics
    "analytics": "business analytics",
    "ba": "business analytics",
    # Data Engineering
    "data engineering": "data engineering",
}

# Each course: code, title, level (UG/PG), credits (int), type ("core"/"elective"), tags (list[str])
COURSE_CATALOG: Dict[str, List[Dict[str, object]]] = {
    "data science": [
        {"code": "DS101", "title": "Intro to Data Science", "level": "UG", "credits": 3, "type": "core", "tags": ["python", "basics"]},
        {"code": "DS201", "title": "Statistics for ML", "level": "UG", "credits": 3, "type": "core", "tags": ["stats", "probability"]},
        {"code": "DS230", "title": "Data Visualization", "level": "UG", "credits": 3, "type": "elective", "tags": ["viz", "tableau"]},
        {"code": "DS310", "title": "Machine Learning", "level": "UG", "credits": 4, "type": "core", "tags": ["ml", "supervised"]},
        {"code": "DS330", "title": "Applied NLP", "level": "UG", "credits": 3, "type": "elective", "tags": ["nlp"]},
        {"code": "DS420", "title": "Deep Learning", "level": "PG", "credits": 4, "type": "core", "tags": ["dl", "neural nets"]},
        {"code": "DS430", "title": "MLOps Foundations", "level": "PG", "credits": 3, "type": "elective", "tags": ["mlops", "devops"]},
        {"code": "DS450", "title": "Responsible & Ethical AI", "level": "PG", "credits": 3, "type": "elective", "tags": ["ethics"]},
    ],
    "artificial intelligence": [
        {"code": "AI210", "title": "Foundations of AI", "level": "UG", "credits": 3, "type": "core", "tags": ["search", "logic"]},
        {"code": "AI320", "title": "Probabilistic Graphical Models", "level": "PG", "credits": 4, "type": "elective", "tags": ["pgm", "bayes"]},
        {"code": "AI410", "title": "Reinforcement Learning", "level": "PG", "credits": 4, "type": "elective", "tags": ["rl"]},
        {"code": "AI430", "title": "Generative Models", "level": "PG", "credits": 3, "type": "elective", "tags": ["diffusion", "vae", "gan"]},
        {"code": "AI440", "title": "AI Safety & Policy", "level": "PG", "credits": 3, "type": "elective", "tags": ["safety"]},
    ],
    "web": [
        {"code": "CS120", "title": "Web Dev Basics", "level": "UG", "credits": 3, "type": "core", "tags": ["html", "css", "js"]},
        {"code": "CS220", "title": "APIs & Microservices", "level": "UG", "credits": 3, "type": "core", "tags": ["rest", "microservices"]},
        {"code": "CS330", "title": "Full-Stack with Django", "level": "UG", "credits": 4, "type": "elective", "tags": ["django", "postgres"]},
        {"code": "CS340", "title": "Frontend Engineering", "level": "UG", "credits": 3, "type": "elective", "tags": ["react"]},
        {"code": "CS360", "title": "DevOps for Web", "level": "PG", "credits": 3, "type": "elective", "tags": ["ci/cd", "docker"]},
    ],
    "cloud": [
        {"code": "CL200", "title": "Cloud Fundamentals", "level": "UG", "credits": 3, "type": "core", "tags": ["iaas", "paas", "saas"]},
        {"code": "CL310", "title": "AWS Services & Architecture", "level": "UG", "credits": 3, "type": "elective", "tags": ["aws"]},
        {"code": "CL320", "title": "Azure Cloud Engineer", "level": "UG", "credits": 3, "type": "elective", "tags": ["azure"]},
        {"code": "CL350", "title": "Cloud Solution Design", "level": "PG", "credits": 4, "type": "core", "tags": ["architecture"]},
        {"code": "CL410", "title": "Cloud Security", "level": "PG", "credits": 3, "type": "elective", "tags": ["security"]},
    ],
    "cybersecurity": [
        {"code": "CY110", "title": "Cybersecurity Basics", "level": "UG", "credits": 3, "type": "core", "tags": ["cia triad"]},
        {"code": "CY210", "title": "Network Security", "level": "UG", "credits": 3, "type": "elective", "tags": ["tcp/ip", "firewalls"]},
        {"code": "CY320", "title": "Application Security", "level": "PG", "credits": 3, "type": "core", "tags": ["owasp", "sast", "dast"]},
        {"code": "CY330", "title": "Ethical Hacking", "level": "PG", "credits": 3, "type": "elective", "tags": ["pentest"]},
        {"code": "CY410", "title": "Cloud Security Practices", "level": "PG", "credits": 3, "type": "elective", "tags": ["iam", "kms"]},
    ],
    "data engineering": [
        {"code": "DE200", "title": "Data Warehousing", "level": "UG", "credits": 3, "type": "core", "tags": ["dimensional", "etl"]},
        {"code": "DE310", "title": "Big Data Systems", "level": "UG", "credits": 3, "type": "elective", "tags": ["hadoop", "spark"]},
        {"code": "DE320", "title": "Spark Programming", "level": "PG", "credits": 4, "type": "core", "tags": ["spark", "pyspark"]},
        {"code": "DE330", "title": "Data Pipelines & Orchestration", "level": "PG", "credits": 3, "type": "elective", "tags": ["airflow"]},
        {"code": "DE410", "title": "Streaming Systems", "level": "PG", "credits": 3, "type": "elective", "tags": ["kafka", "flink"]},
    ],
    "business analytics": [
        {"code": "BA200", "title": "Intro to Business Analytics", "level": "UG", "credits": 3, "type": "core", "tags": ["analytics"]},
        {"code": "BA310", "title": "SQL for Analytics", "level": "UG", "credits": 3, "type": "core", "tags": ["sql"]},
        {"code": "BA320", "title": "Data Visualization with Tableau", "level": "UG", "credits": 3, "type": "elective", "tags": ["tableau"]},
        {"code": "BA325", "title": "Information Visualization & Storytelling", "level": "UG", "credits": 3, "type": "elective", "tags": ["viz", "d3"]},
        {"code": "BA330", "title": "Forecasting & Time Series", "level": "PG", "credits": 3, "type": "elective", "tags": ["arima", "ets"]},
        {"code": "BA410", "title": "Experimentation & A/B Testing", "level": "PG", "credits": 3, "type": "elective", "tags": ["causal", "abtest"]},
    ],
}

ACADEMIC_SCHEDULE: Dict[str, str] = {
    "term_start": "2025-09-01",
    "add_drop_deadline": "2025-09-12",
    "midterms_window": "2025-10-20 to 2025-10-31",
    "finals_window": "2025-12-10 to 2025-12-19",
    "graduation_ceremony": "2025-12-21",
    "class_times": "UG: Mon–Fri 09:00–17:00; PG: Mon–Thu 18:00–20:00; Labs: Sat 10:00–12:00 (as scheduled)",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _Catalog:
    """Catalog lookups and normalization."""

    VIZ_SYNONYMS: Sequence[str] = (
        "visualization", "visualisation", "viz", "tableau",
        "chart", "charts", "graph", "graphs", "d3", "d3.js"
    )

    @staticmethod
    def _strip_punct(s: str) -> str:
        # Keep letters, digits, spaces and hyphens, drop everything else.
        return re.sub(r"[^a-z0-9\s\-]", "", s.lower())

    @classmethod
    def normalize_interest(cls, interest: str) -> str:
        """
        Normalize a free-form interest to a known category key.
        """
        raw = (interest or "").strip().lower()
        raw = cls._strip_punct(raw)
        key = re.sub(r"[\s\-]+", " ", raw)
        compact = key.replace(" ", "")

        # 1) Alias hits in various shapes
        for cand in (key, compact, key.replace(" ", "-")):
            if cand in INTEREST_ALIASES:
                return INTEREST_ALIASES[cand]

        # 2) Exact category
        if key in COURSE_CATALOG:
            return key

        # 3) Substring match against known categories
        for cat in COURSE_CATALOG.keys():
            if cat in key:
                return cat

        # 4) Alias by compact form
        if compact in INTEREST_ALIASES:
            return INTEREST_ALIASES[compact]
        if compact == "datascience":
            return "data science"

        # 5) Fallback to normalized key
        return key

    @classmethod
    def keyword_match_electives(cls, interest_key: str) -> List[Dict[str, object]]:
        """Cross-category elective search for visualization-like interests."""
        t = interest_key.lower()
        wants_viz = any(k in t for k in ("visualization", "visualisation", "viz"))
        if not wants_viz:
            return []
        syn = set(cls.VIZ_SYNONYMS)
        items: List[Dict[str, object]] = []
        for courses in COURSE_CATALOG.values():
            for c in courses:
                if str(c.get("type", "")).lower() != "elective":
                    continue
                title = str(c.get("title", "")).lower()
                tags = {str(x).lower() for x in c.get("tags", [])}
                hay = set(title.split()) | tags
                if hay & syn:
                    items.append(c)
        return items

    @staticmethod
    def slice_limit(items: List[Dict[str, object]], limit: int) -> List[Dict[str, object]]:
        limit_clamped = max(1, min(int(limit or 0), 10))
        return items[:limit_clamped]


#(reads OPENAI_API_KEY from environment)
_client = OpenAI()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@function_tool
def recommend_courses(
    interest: str,
    limit: int = 4,
    type_filter: Optional[str] = None,  # "elective" or "core"
    level: Optional[str] = None,        # "UG" or "PG"
) -> str:
    """
    Return a JSON list of recommended courses for an interest.

    Optional filters:
      - type_filter: "elective" or "core"
      - level: "UG" or "PG"
    """
    key = _Catalog.normalize_interest(interest)
    items = COURSE_CATALOG.get(key, [])

    # Cross-category fallback for visualization-flavored queries
    if not items:
        items = _Catalog.keyword_match_electives(key)

    # Heuristic for beginner phrasing if the agent didn't pass filters
    interest_lc = (interest or "").lower()
    if type_filter is None and level is None and any(w in interest_lc for w in ("beginner", "beginners", "intro", "introductory", "foundation", "foundations")):
        type_filter = "elective"
        level = "UG"

    # Apply optional filters
    if type_filter:
        items = [c for c in items if str(c.get("type", "")).lower() == type_filter.lower()]
    if level:
        items = [c for c in items if str(c.get("level", "")).upper() == level.upper()]

    # Default: if still empty for a known category, fall back to first few items
    if not items and key in COURSE_CATALOG:
        items = COURSE_CATALOG[key][:4]

    items = _Catalog.slice_limit(items, limit)
    return json.dumps(items, ensure_ascii=False)


@function_tool
def lookup_schedule() -> str:
    """Return academic schedule as 'key: value' lines in stable order."""
    return "\n".join(f"{k}: {v}" for k, v in ACADEMIC_SCHEDULE.items())


@function_tool
def summarize_text(text: str) -> str:
    """Summarize text to one concise sentence using the Responses API."""
    resp = _client.responses.create(
        model="gpt-4.1-mini",
        input=f"Summarize in one concise sentence:\n\n{text}",
    )
    return (getattr(resp, "output_text", "") or "").strip() or "No summary produced."
