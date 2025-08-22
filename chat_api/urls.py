"""URL routing for chat_api.

Exposes:
- REST API endpoints (`/chat-sdk/`, `/health/`)
- Frontend UI (`/ui/`)
"""

from django.urls import path
from .views import health, chat_sdk
from .frontend_views import chat_ui  # serves the minimal HTML page

urlpatterns = [
    # --- API endpoints ---
    path("chat-sdk/", chat_sdk, name="api-chat-sdk"),
    path("health/", health, name="api-health"),

    # --- Frontend ---
    path("ui/", chat_ui, name="api-ui"),
]
