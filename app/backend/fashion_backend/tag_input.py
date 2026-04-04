"""Parse optional tags from mobile/web upload (comma-separated or JSON array string)."""

from __future__ import annotations

import json


def parse_tags_field(raw: str | None) -> list[str]:
    if raw is None or not str(raw).strip():
        return []
    s = str(raw).strip()
    if s.startswith("[") or s.startswith("{"):
        data = json.loads(s)
        if isinstance(data, dict):
            raise ValueError("tags must be a JSON array of strings, not an object")
        if not isinstance(data, list):
            raise ValueError("tags must be a JSON array of strings")
        return [str(x).strip() for x in data if str(x).strip()]
    return [t.strip() for t in s.replace(";", ",").split(",") if t.strip()]
