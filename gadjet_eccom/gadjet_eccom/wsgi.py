"""
WSGI config for gadjet_eccom project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

# Add the repo root (eccomm-backend) to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gadjet_eccom.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
