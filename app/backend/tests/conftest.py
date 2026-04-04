"""Bootstrap env before any fashion_backend import (used by pytest for app/backend/tests)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 'pytest_backend.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["DATA_DIR"] = str(_tmp / "data")
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""
