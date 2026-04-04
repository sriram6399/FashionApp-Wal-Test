"""Unit tests for fashion_backend.models."""

from __future__ import annotations

import unittest
from datetime import timezone

from fashion_backend.models import ImageRecord, _utcnow


class TestUtcNow(unittest.TestCase):
    def test_utc_timezone(self) -> None:
        dt = _utcnow()
        self.assertEqual(dt.tzinfo, timezone.utc)


class TestImageRecord(unittest.TestCase):
    def test_tablename(self) -> None:
        self.assertEqual(ImageRecord.__tablename__, "images")


if __name__ == "__main__":
    unittest.main()
