"""Unit tests for fashion_backend.embeddings."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fashion_backend import config


class TestEmbedText(unittest.IsolatedAsyncioTestCase):
    async def test_raises_without_api_key(self) -> None:
        with patch.object(config.settings, "openrouter_api_key", None), patch.object(
            config.settings, "openai_api_key", None
        ):
            from fashion_backend.embeddings import embed_text

            with self.assertRaises(RuntimeError) as ctx:
                await embed_text("hello")
            self.assertIn("embeddings require", str(ctx.exception))

    async def test_empty_string_becomes_space(self) -> None:
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1, 0.2])])
        )
        with (
            patch.object(config.settings, "openai_api_key", "sk"),
            patch.object(config.settings, "openrouter_api_key", None),
            patch.object(config.settings, "embedding_model", None),
            patch.object(config.settings, "llm_base_url", None),
            patch("fashion_backend.llm_client.build_async_openai_client", return_value=mock_client),
        ):
            from fashion_backend.embeddings import embed_text

            vec = await embed_text("   ")
            self.assertEqual(vec, [0.1, 0.2])
            mock_client.embeddings.create.assert_awaited_once()
            call_kw = mock_client.embeddings.create.call_args.kwargs
            self.assertEqual(call_kw["input"], " ")

    async def test_truncates_long_input(self) -> None:
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[1.0])])
        )
        long_text = "x" * 20000
        with (
            patch.object(config.settings, "openai_api_key", "sk"),
            patch.object(config.settings, "openrouter_api_key", None),
            patch("fashion_backend.llm_client.build_async_openai_client", return_value=mock_client),
        ):
            from fashion_backend.embeddings import embed_text

            await embed_text(long_text)
            sent = mock_client.embeddings.create.call_args.kwargs["input"]
            self.assertEqual(len(sent), 12000)


if __name__ == "__main__":
    unittest.main()
