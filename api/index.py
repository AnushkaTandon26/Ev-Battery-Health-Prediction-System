"""
Vercel Serverless Function entry point.
Exposes Flask WSGI app for Vercel deployment.
"""
import sys
import os
from pathlib import Path

# Add project root and backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.app import app

# Vercel entrypoint callable
app_handler = app
