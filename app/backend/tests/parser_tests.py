"""Unit tests for fashion_backend.parser."""

from __future__ import annotations

import json
import unittest

from fashion_backend.parser import normalize_raw_payload, parse_model_output


class TestNormalizeRawPayload(unittest.TestCase):
    def test_dict_passthrough(self) -> None:
        d = {"a": 1}
        self.assertIs(normalize_raw_payload(d), d)

    def test_strips_fenced_json(self) -> None:
        raw = '```json\n{"x":1}\n```'
        self.assertEqual(normalize_raw_payload(raw), {"x": 1})

    def test_extracts_json_after_preamble(self) -> None:
        raw = 'Here is the result:\n{"description": "d", "structured": {"garment_type": "dress"}}\nThanks.'
        self.assertEqual(
            normalize_raw_payload(raw),
            {"description": "d", "structured": {"garment_type": "dress"}},
        )


class TestParseModelOutput(unittest.TestCase):
    def test_description_from_summary_and_caption(self) -> None:
        out = parse_model_output({"summary": "S", "structured": {"garment_type": "x"}})
        self.assertEqual(out.description, "S")
        out2 = parse_model_output({"caption": "C", "structured": {}})
        self.assertEqual(out2.description, "C")

    def test_non_string_description_coerced(self) -> None:
        out = parse_model_output({"description": 42, "structured": {"garment_type": "x"}})
        self.assertEqual(out.description, "42")

    def test_structured_not_dict_falls_back_empty(self) -> None:
        out = parse_model_output({"description": "d", "structured": "bad"})
        self.assertIsNone(out.structured.garment_type)

    def test_flat_garment_type_keys(self) -> None:
        out = parse_model_output({"description": "d", "garment_type": "coat", "country": "IT"})
        self.assertEqual(out.structured.garment_type, "coat")
        self.assertEqual(out.structured.location_context.country if out.structured.location_context else None, "IT")

    def test_flat_branch_only_when_garment_type_string_or_none(self) -> None:
        out = parse_model_output({"description": "d", "garment_type": 9, "structured": {"garment_type": "bag"}})
        self.assertEqual(out.structured.garment_type, "bag")
        out2 = parse_model_output({"description": "d", "garment_type": 9})
        self.assertIsNone(out2.structured.garment_type)

    def test_colors_alias(self) -> None:
        out = parse_model_output({"description": "d", "structured": {"garment_type": "x", "colors": "a|b"}})
        self.assertEqual(set(out.structured.color_palette), {"a", "b"})

    def test_coerce_list_non_string_non_list(self) -> None:
        out = parse_model_output({"description": "d", "structured": {"garment_type": "x", "color_palette": 99}})
        self.assertEqual(out.structured.color_palette, ["99"])

    def test_coerce_list_empty_string_value(self) -> None:
        out = parse_model_output({"description": "d", "structured": {"garment_type": "x", "color_palette": "   "}})
        self.assertEqual(out.structured.color_palette, [])

    def test_time_from_invalid_year_month(self) -> None:
        out = parse_model_output(
            {
                "description": "d",
                "structured": {"garment_type": "x", "time_context": {"year": "nope", "month": "bad"}},
            }
        )
        tm = out.structured.time_context
        self.assertIsNone(tm.year)
        self.assertIsNone(tm.month)

    def test_time_month_out_of_range(self) -> None:
        out = parse_model_output(
            {"description": "d", "structured": {"garment_type": "x", "time_context": {"month": 13}}}
        )
        self.assertIsNone(out.structured.time_context.month)

    def test_location_nested_non_dict_builds_from_flat(self) -> None:
        out = parse_model_output(
            {
                "description": "d",
                "structured": {
                    "garment_type": "x",
                    "location_context": "nope",
                    "continent": "EU",
                    "city": "Paris",
                },
            }
        )
        loc = out.structured.location_context
        self.assertEqual(loc.continent, "EU")
        self.assertEqual(loc.city, "Paris")

    def test_invalid_json_raises(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            parse_model_output("not json")


if __name__ == "__main__":
    unittest.main()
