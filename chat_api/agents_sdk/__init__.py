"""OpenAI Agents SDK integration for the multi-agent

Public API:
- `run_with_agents_sdk(message: str, session_id: str) -> dict`
"""

from .runner import run_with_agents_sdk

__all__ = ["run_with_agents_sdk"]
