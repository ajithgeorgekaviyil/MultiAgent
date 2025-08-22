"""
Intent detection aligned with routing rules:

- Course/Advising → CourseAdvisor
- Schedule/Dates → SchedulingAssistant
- Poem (haiku) → UniversityPoet on campus/student-life topics
- Summary → one-sentence/short summaries for Advisor
"""

from __future__ import annotations

from typing import FrozenSet

__all__ = [
    "has_course_intent",
    "has_schedule_intent",
    "has_poem_intent",
    "poem_is_campus",
    "has_summary_intent",
]


def _norm(text: str) -> str:
    """Lowercase and collapse whitespace for consistent matching."""
    return " ".join((text or "").strip().lower().split())


def _matches(tokens: FrozenSet[str], text: str) -> bool:
    """Return True if any token appears in the normalized text."""
    t = _norm(text)
    return any(k in t for k in tokens)


# ---------- Summary / one-sentence intent ----------

_SUMMARY_TOKENS: FrozenSet[str] = frozenset({
    "summarize",
    "summarise",
    "in one sentence",
    "in 1 sentence",
    "one sentence",
    "short summary",
    "concise summary",
})


def has_summary_intent(text: str) -> bool:
    """True when the user explicitly asks for a short/one-sentence summary."""
    return _matches(_SUMMARY_TOKENS, text)


# ---------- Course / advising ----------

# Signals for course selection and academic planning (no dates).
_COURSE_TOKENS: FrozenSet[str] = frozenset({
    "course", "courses", "class", "classes",
    "elective", "electives", "curriculum", "advisor", "track",
    "major", "minor", "prereq", "prereqs", "prerequisite", "prerequisites",
    "credit", "credits", "unit", "units",
    "requirement", "requirements", "eligibility",
    "degree plan", "graduation requirements",
})


def has_course_intent(text: str) -> bool:
    """True when the message is about course planning or advising."""
    return _matches(_COURSE_TOKENS, text)


# ---------- Schedule / dates ----------

# Signals for class times, exam schedules, and key academic dates.
_SCHEDULE_TOKENS: FrozenSet[str] = frozenset({
    "when", "date", "time", "schedule", "deadline", "window", "period",
    "term start", "start of term", "timetable", "calendar",
    "add/drop", "add drop", "census date",
    "midterm", "midterms", "final", "finals",
    "exam", "exams", "examination", "examinations",
    "graduation ceremony", "convocation",
})


def has_schedule_intent(text: str) -> bool:
    """True when the message asks about dates/times or academic milestones."""
    return _matches(_SCHEDULE_TOKENS, text)


# ---------- Poem intent + topic ----------

# User explicitly asks for a poem/haiku.
_POEM_TOKENS: FrozenSet[str] = frozenset({
    "poem", "poems", "haiku", "poetry", "write a poem", "write poem", "verse",
    "limerick",
})


def has_poem_intent(text: str) -> bool:
    """True when the user asks for a poem/haiku (any topic)."""
    return _matches(_POEM_TOKENS, text)


# Campus/student-life markers for poem topic.
_CAMPUS_MARKERS: FrozenSet[str] = frozenset({
    "campus", "student life", "students",
    "social life",
    "dorm", "dorms", "dormitory", "hostel", "residence hall",
    "library", "libraries", "quad", "student union",
    "cafeteria", "canteen", "mess", "coffee shop", "cafe", "café",
    "club", "clubs", "society", "societies",
    "lecture hall", "classroom", "classrooms",
    "lab", "labs", "hallway",
    "late-night", "late night", "study", "study sessions",
    "orientation", "orientation week", "welcome week", "freshers", "freshers week", "orientation day", "club fair",
    "exam", "exams", "midterm", "midterms", "final", "finals",
    # Common campus events
    "fest", "fests", "festival", "festivals",
    "hackathon", "hackathons",
    "tech fest", "cultural fest",
    "career fair", "job fair",
    "meetup", "meetups",
})


def poem_is_campus(text: str) -> bool:
    """True only when the poem topic relates to campus or student social life."""
    return _matches(_CAMPUS_MARKERS, text)
