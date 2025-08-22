"""
Helpers for orchestrating agents and managing per-session state.

- Consult Triage every turn.
- Execute specialists in order: Poet → Scheduler → Advisor.
- Use tools for schedules and recommendations.
- Preserve session memory via SQLiteSession.
"""

from __future__ import annotations

import asyncio
import re
from typing import Dict, Optional, List, TypedDict, Pattern

from agents import Runner, SQLiteSession
from .agents import get_agents
from .intents import (
    has_poem_intent,
    poem_is_campus,
    has_schedule_intent,
    has_course_intent,
    has_summary_intent,
)

# ----- Types ------------------------------------------------------------------

class Segment(TypedDict):
    """One agent's response chunk."""
    agent: str
    text: str


class DispatchResult(TypedDict):
    """Structured result returned to the caller."""
    segments: List[Segment]
    handoff_chain: List[str]
    agent_key: str
    agent_name: str
    text: str


# ----- Routing constants ------------------------------------------------------

AGENT_KEYS = ("poet", "scheduler", "advisor")
AGENT_ORDER: Dict[str, int] = {"poet": 0, "scheduler": 1, "advisor": 2}
HANDOFF_START = "Triage"

DISPLAY_TO_KEY = {
    "UniversityPoet": "poet",
    "SchedulingAssistant": "scheduler",
    "CourseAdvisor": "advisor",
}

# ----- Schedule targeting patterns -------------------------------------------

_PATTERNS_TO_FIELDS: List[tuple[Pattern[str], str]] = [
    (re.compile(r"\b(midterm|midterms)\b", re.I), "midterms_window"),
    (re.compile(r"\b(final|finals)\b", re.I), "finals_window"),
    (re.compile(r"\bexam(s)?\b", re.I), "finals_window"),
    (re.compile(r"\badd\s*/?\s*drop\b|add[- ]drop\b|adddrop\b", re.I), "add_drop_deadline"),
    (re.compile(r"\b(term\s*start|term\b.*\bstart|start\b.*\bterm)\b", re.I), "term_start"),
    (re.compile(r"\b(graduation\s+ceremony|convocation|ceremony)\b", re.I), "graduation_ceremony"),
    (re.compile(r"\bclass\s*times?\b|\bclass\s*timings?\b|\bclass\s*hours?\b", re.I), "class_times"),
]

_SPECIFIC_DAY = re.compile(r"\b(today|tomorrow|day after tomorrow|\d{4}-\d{2}-\d{2})\b", re.I)
_COURSE_CODE = re.compile(r"\b[A-Z]{2,4}\d{3}\b")
_CLASS_SCHEDULE_PHRASE = re.compile(r"\bclass schedule\b|\bschedule for\b", re.I)

_EXPLICIT_TIME_ASK = re.compile(
    r"\b(when|what time|what times|what date|what dates|date|dates|time|times|schedules?|"
    r"deadline|deadlines|window|windows|period|periods|timetable|calendar|add/?\s*drop|"
    r"census date|start of term|term start)\b",
    re.I,
)

_FIELD_QUESTION = re.compile(r"\b(midterms?|finals?|exam(?:s)?)\s*\?", re.I)

_ADVISE_WORDS_REGEX = re.compile(
    r"\b(elective|electives|prereq|prereqs|prerequisite|prerequisites|"
    r"credit|credits|unit|units|requirement|requirements|eligibility|"
    r"recommend|recommendation|advisor|advise|suggest)\b",
    re.I,
)
_ADVISE_PHRASES = (
    "which course", "what courses", "degree plan", "course plan", "plan my courses", "track",
)


# ----- Event loop -------------------------------------------------------------

def ensure_loop() -> None:
    """Ensure an asyncio event loop exists for the current thread."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


# ----- Orchestrator -----------------------------------------------------------

class _Orchestrator:
    """Routes a message to the right agents and aggregates their replies."""

    def __init__(self, session: SQLiteSession) -> None:
        """Store the session and resolve agent instances."""
        self.session = session
        self.agents = get_agents()

    # ---- Small utilities ----

    @staticmethod
    def _has_advising_action(text: str) -> bool:
        """Return True when the message contains explicit advising intent."""
        t = (text or "").lower()
        if any(p in t for p in _ADVISE_PHRASES):
            return True
        return bool(_ADVISE_WORDS_REGEX.search(t))

    @staticmethod
    def _requested_schedule_fields(msg: str) -> List[str]:
        """Extract requested schedule fields from the message."""
        text = (msg or "").lower()
        return [field for pat, field in _PATTERNS_TO_FIELDS if pat.search(text)]

    def _run(self, agent_key: str, prompt: str) -> str:
        """Run an agent synchronously and return its non-empty final text."""
        agent = self.agents[agent_key]
        out = Runner.run_sync(agent, input=prompt, session=self.session)
        txt = str(out.final_output or "").strip()
        return txt or "No reply produced."

    # ---- Plan building ----

    def _build_plan(self, message: str) -> List[str]:
        """Compute the list of agent keys that should respond this turn."""
        triage_out = Runner.run_sync(self.agents["triage"], input=message, session=self.session)
        triage_label = str(triage_out.final_output or "").strip().lower()

        plan: List[str] = []
        if triage_label in AGENT_KEYS:
            plan.append(triage_label)

        if has_poem_intent(message) and poem_is_campus(message):
            plan.append("poet")

        if has_schedule_intent(message):
            time_word = bool(_EXPLICIT_TIME_ASK.search(message or ""))
            field_q = bool(_FIELD_QUESTION.search(message or ""))
            explicit_schedule = time_word or field_q
            poem_only = has_poem_intent(message) and poem_is_campus(message) and not explicit_schedule
            if not poem_only and explicit_schedule:
                plan.append("scheduler")

        if (has_course_intent(message) and (not has_schedule_intent(message) or self._has_advising_action(message))) or not plan:
            plan.append("advisor")

        # Deterministic order, dedupe while preserving first occurrences
        plan = sorted(list(dict.fromkeys(plan)), key=lambda k: AGENT_ORDER.get(k, 99))
        return plan

    # ---- Prompt builders ----

    @staticmethod
    def _poet_prompt(message: str) -> str:
        """Build the prompt for the Poet, enforcing haiku constraints."""
        return (
            "Write a haiku about campus or student social life based on the user's message.\n"
            "FORMAT: exactly three lines (5-7-5). No title, no extra text.\n"
            "Do not include any dates or scheduling details (like exact days or ranges).\n"
            f"User message: {message}"
        )

    def _scheduler_prompt(self, message: str) -> str:
        """Build the prompt for the Scheduler, targeting specific or default fields."""
        msg_lc = (message or "").lower()
        wants_specific = bool(
            _SPECIFIC_DAY.search(msg_lc)
            or _COURSE_CODE.search(message or "")
            or _CLASS_SCHEDULE_PHRASE.search(msg_lc)
        )
        if wants_specific:
            return (
                'If the user asks for a per-day or per-course class schedule (e.g., "today", "tomorrow", a specific date, '
                'or a course code like DS201), reply exactly with one line:\n'
                '"Details for that specific schedule are not available in the current data."'
            )

        fields = self._requested_schedule_fields(message)
        if fields:
            field_list = ", ".join(fields)
            return (
                "Use ONLY the schedule tool and answer strictly from its result. "
                "Write concise, factual SENTENCES for exactly these fields: "
                f"{field_list}. Use 'YYYY-MM-DD' for dates and 'to' for ranges. "
                "One sentence per field. Do NOT include any other fields."
            )
        return (
            "Use ONLY the schedule tool and answer strictly from its result. "
            "Write concise, factual SENTENCES for: "
            "term_start, add_drop_deadline, midterms_window, finals_window, graduation_ceremony. "
            "Use 'YYYY-MM-DD' for dates and 'to' for ranges. One sentence per field."
        )

    @staticmethod
    def _advisor_prompt(message: str, summary: bool) -> str:
        """Build the prompt for the Advisor; handles summary and meta recall."""
        if summary:
            return (
                "You are the CourseAdvisor. The user asked for a ONE-SENTENCE SUMMARY.\n"
                "Rules:\n"
                "1) Identify the user's interest area from this turn or prior session context.\n"
                "2) If recommendations for that interest are not already explicit in this turn, "
                "   you MUST call `recommend_courses` to obtain ~3–4 items.\n"
                "3) Then you MUST call `summarize_text` on the recommendations to produce "
                "   exactly one concise sentence. Do not include dates or poetry.\n"
                "If the user asks what they asked previously or to recap the last recommendations, "
                "respond with one concise sentence summarizing that prior request/recommendations using session context.\n"
                f"User message: {message}"
            )
        return (
            "You are the CourseAdvisor. Focus ONLY on course advising (credits, requirements, prerequisites, eligibility, recommendations). "
            "Do NOT include any dates or schedule info.\n"
            "Conversation meta (allowed): If the user asks what they asked previously, or to recap/clarify earlier recommendations, "
            "briefly paraphrase the relevant prior request or your last recommendations. This is in scope and must NOT trigger the out-of-scope guard.\n"
            "Out-of-scope guard: If the message is unrelated to academics (e.g., weather, politics, sports, stock prices, exchange rates, news, "
            "general facts), reply exactly with: "
            "\"I can only assist with course advising. Please ask about courses, electives, prerequisites, credits, requirements, or eligibility.\" "
            "Do NOT call any tools in that case.\n"
            "Instructions:\n"
            "1) Extract any interest area mentioned by the user (e.g., 'data science', 'AI', 'web', 'cloud'; include aliases like 'ML').\n"
            "2) If an interest area is present OR was previously discussed in session, you MUST call the `recommend_courses` tool with that interest "
            "and suggest ~3–4 options.\n"
            "3) If no clear interest area is present, ask ONE focused clarifying question and still call `recommend_courses` with the best guess.\n"
            "Keep to 2–4 concise sentences.\n"
            f"User message: {message}"
        )

    # ---- Execution ----

    def dispatch(self, message: str) -> DispatchResult:
        """Execute the plan, collect agent outputs, and build the handoff chain."""
        plan = self._build_plan(message)
        segments: List[Segment] = []
        handoff_chain: List[str] = [HANDOFF_START]

        for step in plan:
            if step == "poet":
                text = self._run("poet", self._poet_prompt(message))
                segments.append({"agent": self.agents["poet"].name, "text": text})
                handoff_chain.append(self.agents["poet"].name)

            elif step == "scheduler":
                text = self._run("scheduler", self._scheduler_prompt(message))
                segments.append({"agent": self.agents["scheduler"].name, "text": text})
                handoff_chain.append(self.agents["scheduler"].name)

            elif step == "advisor":
                adv_prompt = self._advisor_prompt(message, summary=has_summary_intent(message))
                text = self._run("advisor", adv_prompt)
                segments.append({"agent": self.agents["advisor"].name, "text": text})
                handoff_chain.append(self.agents["advisor"].name)

        last_agent = segments[-1]["agent"] if segments else "CourseAdvisor"
        last_key = DISPLAY_TO_KEY.get(last_agent, "advisor")
        combined = "\n\n".join(f"{s['agent']}: {s['text']}" for s in segments)

        return {
            "segments": segments,
            "handoff_chain": handoff_chain,
            "agent_key": last_key,
            "agent_name": last_agent,
            "text": combined,
        }


def dispatch_message(
    message: str,
    session: SQLiteSession,
    force_agent: Optional[str] = None,
) -> DispatchResult:
    """
    Route a message through Triage and specialists and return their outputs.
    """
    ensure_loop()
    orchestrator = _Orchestrator(session)

    if force_agent in AGENT_KEYS:
        agent = get_agents()[force_agent]
        out = Runner.run_sync(agent, input=message, session=session)
        reply = str(out.final_output or "").strip() or "No reply produced."
        return {
            "segments": [{"agent": agent.name, "text": reply}],
            "handoff_chain": ["Forced", agent.name],
            "agent_key": force_agent,
            "agent_name": agent.name,
            "text": reply,
        }

    return orchestrator.dispatch(message)
