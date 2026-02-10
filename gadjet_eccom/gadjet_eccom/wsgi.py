import os
import sys

# Ensure repo root is in Python path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gadjet_eccom.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
