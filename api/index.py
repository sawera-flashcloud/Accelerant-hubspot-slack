"""Vercel serverless entry point — exposes the FastAPI app."""
import sys
from pathlib import Path

# Make sure the repo root is on the path so 'notifier' package is importable
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from notifier.main import app
