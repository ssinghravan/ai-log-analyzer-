# wsgi.py
# -------
# PythonAnywhere WSGI entry point.
# In the PythonAnywhere WSGI config file, point to this file:
#   from wsgi import application

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.app import app as application
