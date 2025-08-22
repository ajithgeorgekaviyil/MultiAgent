"""WSGI entrypoint for the project"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "multi_agent.settings")

application = get_wsgi_application()
