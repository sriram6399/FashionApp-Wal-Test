"""Unit tests for fashion_backend.config.Settings properties."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fashion_backend import config


class TestSettingsProperties(unittest.TestCase):
    def test_cors_origins_list_trims(self) -> None:
        with patch.object(config.settings, "cors_origins", " http://a , http://b "):
            self.assertEqual(config.settings.cors_origins_list, ["http://a", "http://b"])

    def test_llm_api_key_openrouter_wins(self) -> None:
        with (
            patch.object(config.settings, "openrouter_api_key", "or"),
            patch.object(config.settings, "openai_api_key", "oa"),
        ):
            self.assertEqual(config.settings.llm_api_key, "or")

    def test_llm_api_key_fallback_openai(self) -> None:
        with patch.object(config.settings, "openrouter_api_key", None), patch.object(
            config.settings, "openai_api_key", "oa"
        ):
            self.assertEqual(config.settings.llm_api_key, "oa")

    def test_llm_base_url_resolved_custom(self) -> None:
        with patch.object(config.settings, "llm_base_url", "https://x.com/v1//"):
            self.assertEqual(config.settings.llm_base_url_resolved, "https://x.com/v1")

    def test_llm_base_url_openrouter_default(self) -> None:
        with (
            patch.object(config.settings, "llm_base_url", None),
            patch.object(config.settings, "openrouter_api_key", "k"),
        ):
            self.assertEqual(config.settings.llm_base_url_resolved, "https://openrouter.ai/api/v1")

    def test_llm_base_url_none_for_openai_only(self) -> None:
        with (
            patch.object(config.settings, "llm_base_url", None),
            patch.object(config.settings, "openrouter_api_key", None),
            patch.object(config.settings, "openai_api_key", "k"),
        ):
            self.assertIsNone(config.settings.llm_base_url_resolved)

    def test_uses_openrouter_from_key(self) -> None:
        with patch.object(config.settings, "openrouter_api_key", "k"), patch.object(
            config.settings, "llm_base_url", None
        ):
            self.assertTrue(config.settings.uses_openrouter)

    def test_uses_openrouter_from_base_url(self) -> None:
        with patch.object(config.settings, "openrouter_api_key", None), patch.object(
            config.settings, "llm_base_url", "https://openrouter.ai/api/v1"
        ):
            self.assertTrue(config.settings.uses_openrouter)

    def test_vision_model_explicit(self) -> None:
        with patch.object(config.settings, "vision_model", "mymodel"), patch.object(
            config.settings, "openrouter_api_key", None
        ), patch.object(config.settings, "openai_api_key", "k"), patch.object(
            config.settings, "llm_base_url", None
        ):
            self.assertEqual(config.settings.vision_model_resolved, "mymodel")

    def test_vision_default_openrouter(self) -> None:
        with (
            patch.object(config.settings, "vision_model", None),
            patch.object(config.settings, "openrouter_api_key", "k"),
            patch.object(config.settings, "llm_base_url", None),
        ):
            self.assertEqual(config.settings.vision_model_resolved, "google/gemini-2.0-flash-001")

    def test_vision_default_openai(self) -> None:
        with (
            patch.object(config.settings, "vision_model", None),
            patch.object(config.settings, "openrouter_api_key", None),
            patch.object(config.settings, "openai_api_key", "k"),
            patch.object(config.settings, "llm_base_url", None),
        ):
            self.assertEqual(config.settings.vision_model_resolved, "gpt-4o-mini")

    def test_embedding_model_explicit(self) -> None:
        with patch.object(config.settings, "embedding_model", "emb-x"):
            self.assertEqual(config.settings.embedding_model_resolved, "emb-x")

    def test_embedding_default_openrouter(self) -> None:
        with (
            patch.object(config.settings, "embedding_model", None),
            patch.object(config.settings, "openrouter_api_key", "k"),
        ):
            self.assertEqual(config.settings.embedding_model_resolved, "openai/text-embedding-3-small")

    def test_embedding_default_openai(self) -> None:
        with (
            patch.object(config.settings, "embedding_model", None),
            patch.object(config.settings, "openrouter_api_key", None),
            patch.object(config.settings, "openai_api_key", "k"),
        ):
            self.assertEqual(config.settings.embedding_model_resolved, "text-embedding-3-small")

    def test_max_upload_mb_from_bytes(self) -> None:
        with patch.object(config.settings, "max_upload_bytes", 5 * 1024 * 1024):
            self.assertEqual(config.settings.max_upload_mb, 5)


if __name__ == "__main__":
    unittest.main()
