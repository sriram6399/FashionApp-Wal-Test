"""Unit tests for fashion_backend.tag_input."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fashion_backend.tag_input import parse_tags_field


class TestParseTagsField(unittest.TestCase):
    def test_none_returns_empty(self) -> None:
        self.assertEqual(parse_tags_field(None), [])

    def test_blank_returns_empty(self) -> None:
        self.assertEqual(parse_tags_field(""), [])
        self.assertEqual(parse_tags_field("   "), [])

    def test_comma_separated(self) -> None:
        self.assertEqual(parse_tags_field("a, b"), ["a", "b"])

    def test_semicolon_split(self) -> None:
        self.assertEqual(parse_tags_field("x; y"), ["x", "y"])

    def test_json_array(self) -> None:
        self.assertEqual(parse_tags_field('["a", " b "]'), ["a", "b"])

    def test_json_array_starts_with_bracket_not_object(self) -> None:
        self.assertEqual(parse_tags_field("[1, 2]"), ["1", "2"])

    def test_json_object_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_tags_field('{"tags":["a"]}')
        self.assertIn("array", str(ctx.exception).lower())

    def test_json_non_list_raises(self) -> None:
        with patch("fashion_backend.tag_input.json.loads", return_value=42):
            with self.assertRaises(ValueError) as ctx:
                parse_tags_field("[ignored]")
        self.assertIn("array", str(ctx.exception).lower())

    def test_invalid_json_propagates(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            parse_tags_field("[broken")


if __name__ == "__main__":
    unittest.main()
