"""
Vercel serverless entry point — exposes the FastAPI app for ASGI.
Vercel auto-detects the `app` variable as an ASGI application.
"""
import sys
from pathlib import Path

# Ensure repo root is on the path so 'notifier' package is importable
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from notifier.main import app
