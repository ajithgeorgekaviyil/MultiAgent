"""Frontend view for serving the minimal chat UI page."""

from django.shortcuts import render


def chat_ui(request):
    """Render the single-page chat interface."""
    return render(request, "index.html")
