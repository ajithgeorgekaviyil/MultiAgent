"""Project-level URL routes."""

from django.contrib import admin
from django.urls import path, include
from chat_api.frontend_views import chat_ui  # serve the SPA at root "/"

urlpatterns = [
    # --- Admin ---
    path("admin/", admin.site.urls),

    # --- API ---
    path("api/", include("chat_api.urls")),  # chat, health, sdk endpoints

    # --- Frontend ---
    path("", chat_ui, name="chat-ui"),       # root path serves the UI
]
