"""Unit tests for fashion_backend.vector_store."""

from __future__ import annotations

import gc
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from fashion_backend import config


@contextmanager
def _temp_chroma_data_dir():
    """Use an isolated Chroma path and release handles before temp cleanup (Windows-friendly)."""
    import fashion_backend.vector_store as vs

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        with patch.object(config.settings, "data_dir", Path(td)):
            vs.clear_cache()
            try:
                yield
            finally:
                vs.clear_cache()
                gc.collect()


class TestVectorStore(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        import fashion_backend.vector_store as vs

        vs.clear_cache()

    async def asyncTearDown(self) -> None:
        import fashion_backend.vector_store as vs

        vs.clear_cache()
        gc.collect()

    async def test_upsert_query_roundtrip(self) -> None:
        from fashion_backend.vector_store import query_similar, upsert_image_vector

        with _temp_chroma_data_dir():
            emb = [0.1] * 8
            await upsert_image_vector(7, "doc seven", emb)
            hits = await query_similar(emb, top_k=5)
            ids = [h[0] for h in hits]
            self.assertIn(7, ids)

    async def test_delete_swallows_errors(self) -> None:
        from fashion_backend.vector_store import delete_image_vector

        with _temp_chroma_data_dir():
            await delete_image_vector(99999)

    async def test_query_empty_collection(self) -> None:
        from fashion_backend.vector_store import query_similar

        with _temp_chroma_data_dir():
            hits = await query_similar([0.0] * 8, top_k=10)
            self.assertEqual(hits, [])

    async def test_query_top_k_clamped(self) -> None:
        from fashion_backend.vector_store import query_similar, upsert_image_vector

        with _temp_chroma_data_dir():
            e = [0.0] * 8
            await upsert_image_vector(1, "a", e)
            hits = await query_similar(e, top_k=500)
            self.assertLessEqual(len(hits), 200)

    def test_query_sync_skips_invalid_ids(self) -> None:
        import fashion_backend.vector_store as vs

        col = MagicMock()
        col.query.return_value = {"ids": [["not-an-int"]], "distances": [[0.5]]}
        with patch.object(vs, "_collection", return_value=col):
            out = vs._query_sync([0.0] * 4, top_k=5)
        self.assertEqual(out, [])

    def test_clear_cache(self) -> None:
        import fashion_backend.vector_store as vs

        vs.clear_cache()


if __name__ == "__main__":
    unittest.main()
