#!/usr/bin/env python
"""Entry point for Django admin tasks (runs `manage.py` commands)."""

import os
import sys


def main() -> None:
    """Configure settings and delegate to Django's command-line utility."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "multi_agent.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it is installed and available on your "
            "PYTHONPATH, and that your virtual environment is activated."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
