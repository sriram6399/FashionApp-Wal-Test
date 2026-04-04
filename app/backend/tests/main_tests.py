"""Unit tests for fashion_backend.main FastAPI routes."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx import ASGITransport

from fashion_backend import config
from fashion_backend.main import app
from fashion_backend.schemas import ImageCreateResponse, ImageListSearchMeta, StructuredGarmentMetadata
from fashion_backend.services.images import ListFilteredResult


def _sample_create_response() -> ImageCreateResponse:
    return ImageCreateResponse(
        id=42,
        description="d",
        structured=StructuredGarmentMetadata(garment_type="shirt"),
        designer_tags=["t"],
        designer_notes=None,
        designer_name=None,
        user_caption=None,
        upload_metadata=None,
        file_url="/api/files/x.jpg",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


class TestMainRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_health_no_llm_key(self) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r = await client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["classifier"], "mock")
        self.assertEqual(body["search"], "lexical")
        self.assertIsNone(body["embedding_model"])

    async def test_health_openrouter(self) -> None:
        with patch.object(config.settings, "openrouter_api_key", "k"), patch.object(
            config.settings, "openai_api_key", None
        ):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                r = await client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["classifier"], "openrouter")
        self.assertEqual(body["search"], "vector")

    async def test_health_openai_only(self) -> None:
        with patch.object(config.settings, "openrouter_api_key", None), patch.object(
            config.settings, "openai_api_key", "k"
        ):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                r = await client.get("/api/health")
        body = r.json()
        self.assertEqual(body["classifier"], "openai")

    @patch("fashion_backend.main.image_service.save_upload_and_classify", new_callable=AsyncMock)
    async def test_upload_rejects_non_image(self, mock_save: AsyncMock) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            files = {"file": ("x.txt", b"hi", "text/plain")}
            r = await client.post("/api/images", files=files)
        self.assertEqual(r.status_code, 400)
        mock_save.assert_not_called()

    @patch("fashion_backend.main.image_service.save_upload_and_classify", new_callable=AsyncMock)
    @patch.object(config.settings, "max_upload_bytes", 10)
    async def test_upload_rejects_too_large(self, mock_save: AsyncMock) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            files = {"file": ("x.png", b"x" * 20, "image/png")}
            r = await client.post("/api/images", files=files)
        self.assertEqual(r.status_code, 400)
        self.assertIn("large", r.json()["detail"].lower())
        mock_save.assert_not_called()

    @patch("fashion_backend.main.image_service.save_upload_and_classify", new_callable=AsyncMock)
    async def test_upload_bad_tags(self, mock_save: AsyncMock) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            files = {"file": ("x.png", b"x", "image/png")}
            data = {"tags": "["}
            r = await client.post("/api/images", files=files, data=data)
        self.assertEqual(r.status_code, 400)
        mock_save.assert_not_called()

    @patch("fashion_backend.main.image_service.save_upload_and_classify", new_callable=AsyncMock)
    async def test_upload_metadata_invalid_json(self, mock_save: AsyncMock) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            files = {"file": ("x.png", b"x", "image/png")}
            data = {"upload_metadata": "not-json"}
            r = await client.post("/api/images", files=files, data=data)
        self.assertEqual(r.status_code, 400)
        mock_save.assert_not_called()

    @patch("fashion_backend.main.image_service.save_upload_and_classify", new_callable=AsyncMock)
    async def test_upload_metadata_not_object(self, mock_save: AsyncMock) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            files = {"file": ("x.png", b"x", "image/png")}
            data = {"upload_metadata": "[1]"}
            r = await client.post("/api/images", files=files, data=data)
        self.assertEqual(r.status_code, 400)
        mock_save.assert_not_called()

    @patch("fashion_backend.main.image_service.save_upload_and_classify", new_callable=AsyncMock)
    async def test_upload_success(self, mock_save: AsyncMock) -> None:
        mock_save.return_value = _sample_create_response()
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            files = {"file": ("x.png", b"x", "image/png")}
            data = {"tags": "a,b", "upload_metadata": '{"k":1}', "caption": " hi "}
            r = await client.post("/api/images", files=files, data=data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["id"], 42)
        mock_save.assert_awaited_once()
        call_kw = mock_save.await_args.kwargs
        self.assertEqual(call_kw["caption"], " hi ")
        self.assertEqual(call_kw["upload_metadata"], {"k": 1})
        self.assertEqual(call_kw["tags"], ["a", "b"])

    @patch("fashion_backend.main.image_service.list_filtered", new_callable=AsyncMock)
    @patch("fashion_backend.main.image_service.row_to_response")
    async def test_list_images_builds_filters(self, mock_row: MagicMock, mock_list: AsyncMock) -> None:
        row = MagicMock()
        mock_list.return_value = ListFilteredResult(
            rows=[row],
            search=ImageListSearchMeta(kind="lexical", message="Top matches."),
        )
        mock_row.return_value = _sample_create_response()
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r = await client.get(
                "/api/images",
                params={
                    "q": "x",
                    "garment_type": "shirt",
                    "color_palette": ["red", "blue"],
                },
            )
        self.assertEqual(r.status_code, 200)
        payload = r.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["search"]["kind"], "lexical")
        args = mock_list.await_args.args
        self.assertEqual(args[1], "x")
        self.assertEqual(
            args[2],
            {
                "garment_type": "shirt",
                "color_palette": ["red", "blue"],
            },
        )

    @patch("fashion_backend.main.image_service.collect_filter_facets", new_callable=AsyncMock)
    async def test_get_filters(self, mock_facets: AsyncMock) -> None:
        from fashion_backend.schemas import FilterOptions

        mock_facets.return_value = {name: [] for name in FilterOptions.model_fields}
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r = await client.get("/api/filters")
        self.assertEqual(r.status_code, 200)

    @patch("fashion_backend.main.image_service.patch_image", new_callable=AsyncMock)
    @patch("fashion_backend.main.image_service.row_to_response")
    async def test_patch_404(self, mock_row: MagicMock, mock_patch: AsyncMock) -> None:
        mock_patch.return_value = None
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r = await client.patch("/api/images/99", json={})
        self.assertEqual(r.status_code, 404)
        mock_row.assert_not_called()

    @patch("fashion_backend.main.image_service.patch_image", new_callable=AsyncMock)
    @patch("fashion_backend.main.image_service.row_to_response")
    async def test_patch_ok(self, mock_row: MagicMock, mock_patch: AsyncMock) -> None:
        mock_patch.return_value = MagicMock()
        mock_row.return_value = _sample_create_response()
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r = await client.patch(
                "/api/images/1",
                json={"designer_tags": ["x"], "designer_notes": "n", "designer_name": "dn"},
            )
        self.assertEqual(r.status_code, 200)

    async def test_get_file_not_found(self) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r = await client.get("/api/files/missing.bin")
        self.assertEqual(r.status_code, 404)

    async def test_get_file_path_traversal_rejected(self) -> None:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r = await client.get("/api/files/../secrets.txt")
        self.assertEqual(r.status_code, 404)

    async def test_get_file_serves_upload(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
            tf.write(b"abc")
            name = Path(tf.name).name
        try:
            dest = config.settings.upload_dir / name
            dest.write_bytes(b"abc")
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                r = await client.get(f"/api/files/{name}")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.content, b"abc")
        finally:
            Path(tf.name).unlink(missing_ok=True)
            (config.settings.upload_dir / name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
