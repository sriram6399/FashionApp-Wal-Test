"""Unit tests for fashion_backend.classifier."""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fashion_backend import config


class TestClassifier(unittest.IsolatedAsyncioTestCase):
    async def test_mock_path_without_api_key(self) -> None:
        with patch.object(config.settings, "openai_api_key", None), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            from fashion_backend.classifier import classify_image_bytes

            out = await classify_image_bytes(b"\xff\x00" * 20, mime="image/jpeg")
            self.assertTrue(out.description)
            self.assertIsNotNone(out.structured.garment_type)

    async def test_api_path_parses_json(self) -> None:
        payload = json.dumps(
            {
                "description": "A red hat.",
                "structured": {"garment_type": "hat", "color_palette": ["red"]},
            }
        )
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content=payload))])
        )
        with (
            patch.object(config.settings, "openai_api_key", "sk"),
            patch.object(config.settings, "openrouter_api_key", None),
            patch.object(config.settings, "vision_model", "gpt-4o-mini"),
            patch("fashion_backend.llm_client.build_async_openai_client", return_value=mock_client),
        ):
            from fashion_backend.classifier import classify_image_bytes

            out = await classify_image_bytes(b"img", mime="image/png", caption="cap", tags=["a"], upload_metadata={"k": 1})
            self.assertIn("hat", (out.structured.garment_type or "").lower())
            mock_client.chat.completions.create.assert_awaited()

    async def test_api_path_invalid_json_fallback(self) -> None:
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="not json {{{"))])
        )
        with (
            patch.object(config.settings, "openai_api_key", "sk"),
            patch.object(config.settings, "openrouter_api_key", None),
            patch("fashion_backend.llm_client.build_async_openai_client", return_value=mock_client),
        ):
            from fashion_backend.classifier import classify_image_bytes

            out = await classify_image_bytes(b"x", mime="image/jpeg")
            self.assertIn("not json", out.description)
            self.assertIsNone(out.structured.garment_type)


class TestUserContextBlock(unittest.TestCase):
    def test_includes_all_parts(self) -> None:
        from fashion_backend.classifier import _user_context_block

        text = _user_context_block("c1", {"x": 1}, ["t1", "t2"])
        self.assertIn("c1", text)
        self.assertIn("t1", text)
        self.assertIn('"x": 1', text)

    def test_empty_optional_fields(self) -> None:
        from fashion_backend.classifier import _user_context_block

        text = _user_context_block(None, None, None)
        self.assertIn("(none)", text)
        self.assertIn("{}", text)


if __name__ == "__main__":
    unittest.main()
