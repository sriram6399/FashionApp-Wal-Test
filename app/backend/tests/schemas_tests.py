"""Unit tests for fashion_backend.schemas helpers."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from fashion_backend.schemas import StructuredGarmentMetadata, structured_from_dict, structured_to_dict


class TestStructuredRoundTrip(unittest.TestCase):
    def test_structured_to_dict(self) -> None:
        s = StructuredGarmentMetadata(garment_type="coat", color_palette=["navy"])
        d = structured_to_dict(s)
        self.assertEqual(d["garment_type"], "coat")
        self.assertEqual(d["color_palette"], ["navy"])

    def test_structured_from_dict_none(self) -> None:
        s = structured_from_dict(None)
        self.assertIsInstance(s, StructuredGarmentMetadata)
        self.assertIsNone(s.garment_type)

    def test_structured_from_dict_empty(self) -> None:
        s = structured_from_dict({})
        self.assertEqual(s.color_palette, [])

    def test_structured_from_dict_invalid_raises(self) -> None:
        with self.assertRaises(ValidationError):
            structured_from_dict({"time_context": {"month": 13}})


if __name__ == "__main__":
    unittest.main()
