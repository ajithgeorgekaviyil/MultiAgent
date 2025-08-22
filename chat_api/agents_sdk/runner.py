"""
Routing entrypoint for triage-first, multi-agent handling.

- Uses session-bound memory via SQLiteSession.
- Invokes helpers.dispatch_message for orchestration.
- Normalizes Scheduler/Advisor text for UI and logs.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

from agents import SQLiteSession
from .helpers import dispatch_message

# Session database file used by SQLiteSession
SESSION_DB_FILE = "agents_sessions.sqlite3"


class _TextNormalizer:
    """Normalize agent outputs"""

    # Scheduler markdown → "key: value"
    SCHED_MD_LABEL = re.compile(r'^\s*-\s*\*\*(.+?)\*\*:\s*', re.M)
    SCHED_BULLETS = re.compile(r'^\s*-\s*', re.M)
    DASHES_MAP = str.maketrans({'–': '-', '—': '-'})

    # Advisor markdown cleanup
    ADVISOR_BOLD = re.compile(r'\*\*(.+?)\*\*', re.M)
    ADVISOR_CODEFENCE = re.compile(r'^\s*`{3,}.*?$|`{3,}\s*$', re.M)

    @classmethod
    def scheduler(cls, text: str) -> str:
        """Convert bullets/labels to 'key: value' lines and normalize dashes."""
        if not text:
            return text
        s = cls.SCHED_MD_LABEL.sub(r'\1: ', text)
        s = cls.SCHED_BULLETS.sub('', s)
        s = s.translate(cls.DASHES_MAP)
        return s.strip()

    @classmethod
    def advisor(cls, text: str) -> str:
        """Strip bold/code fences from CourseAdvisor output."""
        if not text:
            return text
        s = cls.ADVISOR_CODEFENCE.sub('', text)
        s = cls.ADVISOR_BOLD.sub(r'\1', s)
        return s.strip()


def run_with_agents_sdk(message: str, session_id: str) -> Dict[str, object]:
    """Route a message via Triage and specialists, then return a structured payload."""
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return {
            "session_id": session_id,
            "agent": "system",
            "segments": [],
            "response": "Configuration issue: set OPENAI_API_KEY in your environment and restart the server.",
            "handoff": None,
        }

    session = SQLiteSession(session_id, SESSION_DB_FILE)
    routed = dispatch_message(message=message, session=session)

    segments: List[Dict[str, str]] = routed.get("segments", [])
    chain = routed.get("handoff_chain", ["Triage"])
    handoff = " -> ".join(chain) if chain else None

    # Normalize per-segment text (Poet remains untouched).
    for s in segments or []:
        agent = s.get("agent")
        if agent == "SchedulingAssistant":
            s["text"] = _TextNormalizer.scheduler(s.get("text", ""))
        elif agent == "CourseAdvisor":
            s["text"] = _TextNormalizer.advisor(s.get("text", ""))

    # Fallback normalization when only legacy fields are present.
    if segments:
        response_text = "\n\n".join(f"{s['agent']}: {s['text']}" for s in segments)
        last_agent = segments[-1]["agent"]
    else:
        response_text = routed.get("text", "")
        last_agent = routed.get("agent_name", "system")
        if last_agent == "SchedulingAssistant":
            response_text = _TextNormalizer.scheduler(response_text)
        elif last_agent == "CourseAdvisor":
            response_text = _TextNormalizer.advisor(response_text)

    return {
        "session_id": session_id,
        "agent": last_agent,
        "segments": segments,
        "response": response_text,
        "handoff": handoff,
    }
