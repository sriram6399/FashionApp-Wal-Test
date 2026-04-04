"""Unit tests for fashion_backend.llm_client — one test module per source file."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fashion_backend import config


class TestBuildAsyncOpenAIClient(unittest.TestCase):
    """Covers build_async_openai_client() every branch."""

    def test_raises_when_no_api_key(self) -> None:
        with patch.object(config.settings, "openrouter_api_key", None), patch.object(
            config.settings, "openai_api_key", None
        ):
            from fashion_backend.llm_client import build_async_openai_client

            with self.assertRaises(RuntimeError) as ctx:
                build_async_openai_client()
            self.assertIn("No LLM API key", str(ctx.exception))

    @patch("openai.AsyncOpenAI")
    def test_openai_direct_no_base_url(self, mock_cls: MagicMock) -> None:
        with (
            patch.object(config.settings, "openrouter_api_key", None),
            patch.object(config.settings, "openai_api_key", "sk-openai"),
            patch.object(config.settings, "llm_base_url", None),
        ):
            from fashion_backend.llm_client import build_async_openai_client

            mock_cls.reset_mock()
            build_async_openai_client()
            call_kw = mock_cls.call_args.kwargs
            self.assertEqual(call_kw["api_key"], "sk-openai")
            self.assertNotIn("base_url", call_kw)
            self.assertNotIn("default_headers", call_kw)

    @patch("openai.AsyncOpenAI")
    def test_openrouter_base_url_and_referer(self, mock_cls: MagicMock) -> None:
        with (
            patch.object(config.settings, "openrouter_api_key", "sk-or"),
            patch.object(config.settings, "openai_api_key", None),
            patch.object(config.settings, "llm_base_url", None),
            patch.object(config.settings, "openrouter_site_url", "https://example.com"),
            patch.object(config.settings, "openrouter_app_name", "MyApp"),
        ):
            from fashion_backend.llm_client import build_async_openai_client

            mock_cls.reset_mock()
            build_async_openai_client()
            call_kw = mock_cls.call_args.kwargs
            self.assertEqual(call_kw["base_url"], "https://openrouter.ai/api/v1")
            self.assertEqual(call_kw["default_headers"]["HTTP-Referer"], "https://example.com")
            self.assertEqual(call_kw["default_headers"]["X-OpenRouter-Title"], "MyApp")
            self.assertEqual(call_kw["default_headers"]["X-Title"], "MyApp")

    @patch("openai.AsyncOpenAI")
    def test_openrouter_without_site_url(self, mock_cls: MagicMock) -> None:
        with (
            patch.object(config.settings, "openrouter_api_key", "sk-or"),
            patch.object(config.settings, "openai_api_key", None),
            patch.object(config.settings, "llm_base_url", None),
            patch.object(config.settings, "openrouter_site_url", None),
            patch.object(config.settings, "openrouter_app_name", "Fashion"),
        ):
            from fashion_backend.llm_client import build_async_openai_client

            mock_cls.reset_mock()
            build_async_openai_client()
            headers = mock_cls.call_args.kwargs["default_headers"]
            self.assertNotIn("HTTP-Referer", headers)
            self.assertEqual(headers["X-OpenRouter-Title"], "Fashion")
            self.assertEqual(headers["X-Title"], "Fashion")

    @patch("openai.AsyncOpenAI")
    def test_llm_base_url_override_strips_slash(self, mock_cls: MagicMock) -> None:
        with (
            patch.object(config.settings, "openai_api_key", "sk"),
            patch.object(config.settings, "openrouter_api_key", None),
            patch.object(config.settings, "llm_base_url", "https://proxy.example/v1/"),
        ):
            from fashion_backend.llm_client import build_async_openai_client

            mock_cls.reset_mock()
            build_async_openai_client()
            self.assertEqual(mock_cls.call_args.kwargs["base_url"], "https://proxy.example/v1")


if __name__ == "__main__":
    unittest.main()
