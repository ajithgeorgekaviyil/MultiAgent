"""REST endpoints for health checks and Agents SDK–based chat."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional, Tuple

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .agents_sdk import run_with_agents_sdk


# ---- Internal helpers --------------------------------------------------------

def _method_guard_post(request: HttpRequest) -> Optional[JsonResponse]:
    """Reject non-POST requests with 405, otherwise return None."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    return None


def _parse_json_body(request: HttpRequest) -> Tuple[Optional[Dict[str, Any]], Optional[JsonResponse]]:
    """Parse request.body into a dict, or return (None, error response)."""
    try:
        data = json.loads(request.body.decode("utf-8"))
        if not isinstance(data, dict):
            return None, JsonResponse({"error": "Invalid JSON object"}, status=400)
        return data, None
    except Exception:
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


# ---- Public endpoints --------------------------------------------------------

def health(_: HttpRequest) -> JsonResponse:
    """Liveness and clock check."""
    return JsonResponse({
        "status": "ok",
        "time": timezone.now().isoformat(),
        "app": "multi_agent",
    })


@csrf_exempt
def chat_sdk(request: HttpRequest) -> HttpResponse:
    """Main chat endpoint: triage + multi-specialist flow via Agents SDK."""
    guard = _method_guard_post(request)
    if guard:
        return guard

    data, err = _parse_json_body(request)
    if err:
        return err

    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Field 'message' is required"}, status=400)

    # Use provided session_id or generate a new one
    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())

    # Run through multi-agent orchestration
    result = run_with_agents_sdk(message=message, session_id=session_id)
    segments = result.get("segments") or []

    # Preserve the first contributing agent
    agent_routed_from = segments[0]["agent"] if segments else result.get("agent")

    payload = {
        "session_id": result.get("session_id", session_id),
        "agent_routed_from": agent_routed_from,
        "handoff": result.get("handoff"),
        "agent": result.get("agent"),
        "segments": segments,
        "response": result.get("response", ""),
        "history": None,
    }
    return JsonResponse(payload)
