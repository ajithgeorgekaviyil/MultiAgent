"""Django app configuration for chat_api."""

from django.apps import AppConfig


class ChatApiConfig(AppConfig):
    """Configuration class for the chat_api app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "chat_api"
    verbose_name = "Chat API"
