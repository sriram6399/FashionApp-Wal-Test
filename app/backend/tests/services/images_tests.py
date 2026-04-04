"""Unit tests for fashion_backend.services.images."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fashion_backend import config
from fashion_backend.schemas import ClassificationResult, ImagePatch, StructuredGarmentMetadata
from fashion_backend.services import images as svc


def _row(
    *,
    rid: int = 1,
    file_path: str = "/tmp/u.jpg",
    description: str = "desc",
    ai_metadata: dict | None = None,
    designer_tags: list | None = None,
    designer_notes: str | None = None,
    designer_name: str | None = None,
    user_caption: str | None = None,
    upload_metadata: dict | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    r = MagicMock()
    r.id = rid
    r.file_path = file_path
    r.description = description
    r.ai_metadata = ai_metadata or {"garment_type": "shirt"}
    r.designer_tags = designer_tags or []
    r.designer_notes = designer_notes
    r.designer_name = designer_name
    r.user_caption = user_caption
    r.upload_metadata = upload_metadata
    r.created_at = created_at or datetime(2024, 6, 1, tzinfo=timezone.utc)
    return r


class TestRowToResponse(unittest.TestCase):
    def test_relative_file_url(self) -> None:
        row = _row(file_path="/abs/path/to/file.png")
        out = svc.row_to_response(row)
        self.assertEqual(out.file_url, "/api/files/file.png")

    def test_base_url_prefix(self) -> None:
        row = _row()
        out = svc.row_to_response(row, base_url="https://x.com")
        self.assertEqual(out.file_url, "https://x.com/api/files/u.jpg")


class TestBuildSearchDocument(unittest.TestCase):
    def test_all_optional_parts(self) -> None:
        row = _row(
            user_caption="cap",
            upload_metadata={"a": 1},
            designer_notes="dn",
            designer_tags=["t1", "t2"],
            designer_name="Ann",
            ai_metadata={"garment_type": "coat", "color_palette": ["navy"]},
        )
        doc = svc.build_search_document(row)
        self.assertIn("User caption: cap", doc)
        self.assertIn("User metadata:", doc)
        self.assertIn("AI description:", doc)
        self.assertIn("Structured attributes:", doc)
        self.assertIn("Designer notes: dn", doc)
        self.assertIn("Designer tags: t1, t2", doc)
        self.assertIn("Designer name: Ann", doc)

    def test_minimal_row(self) -> None:
        row = _row(ai_metadata={}, designer_tags=[], user_caption=None, upload_metadata=None)
        doc = svc.build_search_document(row)
        self.assertIn("AI description:", doc)


class TestJsonDumpsSafe(unittest.TestCase):
    def test_serializes(self) -> None:
        self.assertEqual(svc.json_dumps_safe({"x": 1}), '{"x": 1}')


class TestTextBlob(unittest.TestCase):
    def test_combines_fields(self) -> None:
        row = _row(
            description="d",
            user_caption="c",
            upload_metadata={"k": "v"},
            designer_notes="n",
            designer_tags=["a", "b"],
            ai_metadata={"garment_type": "g"},
        )
        blob = svc._text_blob(row)
        self.assertIn("d", blob)
        self.assertIn("c", blob)
        self.assertIn("n", blob)
        self.assertIn("a", blob)
        self.assertIn("g", blob.lower())


class TestMatchHelpers(unittest.TestCase):
    def test_match_query_empty(self) -> None:
        self.assertTrue(svc._match_query("hello world", None))
        self.assertTrue(svc._match_query("hello", "   "))
        self.assertTrue(svc._match_query("a", "  \t"))

    def test_match_query_words(self) -> None:
        self.assertTrue(svc._match_query("hello world", "world hello"))
        self.assertFalse(svc._match_query("hello", "world"))

    def test_scalar_eq_blank_filter(self) -> None:
        self.assertTrue(svc._scalar_eq("x", None))
        self.assertTrue(svc._scalar_eq("x", ""))

    def test_scalar_eq_case(self) -> None:
        self.assertTrue(svc._scalar_eq("Shirt", "shirt"))

    def test_list_intersect(self) -> None:
        self.assertTrue(svc._list_intersect(["Red"], []))
        self.assertTrue(svc._list_intersect(["Red", "Blue"], ["red"]))
        self.assertFalse(svc._list_intersect(["Blue"], ["red"]))


class TestRowMatchesFilters(unittest.TestCase):
    def test_scalar_filters(self) -> None:
        row = _row(ai_metadata={"garment_type": "A", "style": "S", "material": "M", "pattern": "P"})
        self.assertTrue(svc.row_matches_filters(row, {"garment_type": "a"}))
        self.assertFalse(svc.row_matches_filters(row, {"garment_type": "other"}))

    def test_location_filters(self) -> None:
        row = _row(
            ai_metadata={
                "garment_type": "x",
                "location_context": {"continent": "EU", "country": "DE", "city": "Berlin"},
            }
        )
        self.assertTrue(svc.row_matches_filters(row, {"continent": "eu"}))
        self.assertFalse(svc.row_matches_filters(row, {"continent": "asia"}))

    def test_location_missing(self) -> None:
        row = _row(ai_metadata={"garment_type": "x"})
        self.assertFalse(svc.row_matches_filters(row, {"country": "DE"}))

    def test_time_filters(self) -> None:
        row = _row(
            ai_metadata={
                "garment_type": "x",
                "time_context": {"year": 2020, "month": 3, "season": "spring"},
            }
        )
        self.assertTrue(svc.row_matches_filters(row, {"year": 2020, "month": 3, "time_season": "Spring"}))
        self.assertFalse(svc.row_matches_filters(row, {"year": 2021}))

    def test_designer_and_color(self) -> None:
        row = _row(
            ai_metadata={"garment_type": "x", "color_palette": ["navy"]},
            designer_name="D1",
        )
        self.assertTrue(svc.row_matches_filters(row, {"designer_name": "d1", "color_palette": ["Navy"]}))
        self.assertFalse(svc.row_matches_filters(row, {"color_palette": ["red"]}))

    def test_designer_tags_filter(self) -> None:
        row = _row(ai_metadata={"garment_type": "x"}, designer_tags=["eval", "drop"])
        self.assertTrue(svc.row_matches_filters(row, {"designer_tags": "eval"}))
        self.assertFalse(svc.row_matches_filters(row, {"designer_tags": "other"}))

    def test_color_palette_string_wanted(self) -> None:
        row = _row(ai_metadata={"garment_type": "x", "color_palette": ["navy"]})
        self.assertTrue(svc.row_matches_filters(row, {"color_palette": "navy"}))


class TestIndexRowForSearch(unittest.IsolatedAsyncioTestCase):
    async def test_noop_without_api_key(self) -> None:
        row = _row()
        with patch.object(config.settings, "openrouter_api_key", None), patch.object(
            config.settings, "openai_api_key", None
        ):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as m_emb:
                await svc.index_row_for_search(row)
        m_emb.assert_not_called()

    async def test_upserts_when_key_set(self) -> None:
        row = _row()
        with patch.object(config.settings, "openai_api_key", "k"), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as m_emb:
                m_emb.return_value = [0.0, 1.0]
                with patch.object(svc, "upsert_image_vector", new_callable=AsyncMock) as m_up:
                    await svc.index_row_for_search(row)
        m_emb.assert_awaited_once()
        m_up.assert_awaited_once()

    async def test_swallows_errors(self) -> None:
        row = _row()
        with patch.object(config.settings, "openai_api_key", "k"), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as m_emb:
                m_emb.side_effect = RuntimeError("boom")
                with patch.object(svc, "upsert_image_vector", new_callable=AsyncMock) as m_up:
                    await svc.index_row_for_search(row)
        m_up.assert_not_awaited()


class TestSaveUploadAndClassify(unittest.IsolatedAsyncioTestCase):
    async def test_writes_file_and_persists(self) -> None:
        result = ClassificationResult(description="d", structured=StructuredGarmentMetadata(garment_type="tee"))
        session = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        stored: list = []

        def _capture_add(obj: object) -> None:
            stored.append(obj)

        session.add.side_effect = _capture_add

        async def _refresh(obj: object) -> None:
            setattr(obj, "id", 7)

        session.refresh.side_effect = _refresh

        data = b"\xff\xd8\xff"
        with patch.object(svc, "classify_image_bytes", new_callable=AsyncMock) as clf:
            clf.return_value = result
            with patch.object(svc, "index_row_for_search", new_callable=AsyncMock):
                with patch("fashion_backend.services.images.uuid.uuid4", return_value=MagicMock(hex="cafef00d")):
                    out = await svc.save_upload_and_classify(session, data, "image/jpeg", caption=" hi ")
        self.assertEqual(out.id, 7)
        self.assertEqual(out.description, "d")
        clf.assert_awaited_once()
        rec = stored[0]
        self.assertEqual(rec.user_caption, "hi")
        path = config.settings.upload_dir / "cafef00d.jpg"
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), data)
        path.unlink(missing_ok=True)

    async def test_png_extension(self) -> None:
        result = ClassificationResult(description="d", structured=StructuredGarmentMetadata())
        session = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock(side_effect=lambda o: setattr(o, "id", 1) or None)
        session.add = MagicMock()
        with patch.object(svc, "classify_image_bytes", new_callable=AsyncMock) as clf:
            clf.return_value = result
            with patch.object(svc, "index_row_for_search", new_callable=AsyncMock):
                with patch("fashion_backend.services.images.uuid.uuid4", return_value=MagicMock(hex="aaa")):
                    await svc.save_upload_and_classify(session, b"x", "image/png")
        p = config.settings.upload_dir / "aaa.png"
        self.assertTrue(p.is_file())
        p.unlink(missing_ok=True)

    async def test_webp_extension(self) -> None:
        result = ClassificationResult(description="d", structured=StructuredGarmentMetadata())
        session = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock(side_effect=lambda o: setattr(o, "id", 1) or None)
        session.add = MagicMock()
        with patch.object(svc, "classify_image_bytes", new_callable=AsyncMock) as clf:
            clf.return_value = result
            with patch.object(svc, "index_row_for_search", new_callable=AsyncMock):
                with patch("fashion_backend.services.images.uuid.uuid4", return_value=MagicMock(hex="bbb")):
                    await svc.save_upload_and_classify(session, b"x", "image/webp; charset=utf-8")
        p = config.settings.upload_dir / "bbb.webp"
        self.assertTrue(p.is_file())
        p.unlink(missing_ok=True)

    async def test_classify_mime_strips_params(self) -> None:
        result = ClassificationResult(description="d", structured=StructuredGarmentMetadata())
        session = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock(side_effect=lambda o: setattr(o, "id", 1) or None)
        session.add = MagicMock()
        with patch.object(svc, "classify_image_bytes", new_callable=AsyncMock) as clf:
            clf.return_value = result
            with patch.object(svc, "index_row_for_search", new_callable=AsyncMock):
                with patch("fashion_backend.services.images.uuid.uuid4", return_value=MagicMock(hex="ccc")):
                    await svc.save_upload_and_classify(session, b"x", "image/jpeg; foo=bar")
        clf.assert_awaited_once()
        self.assertEqual(clf.await_args.kwargs["mime"], "image/jpeg")
        (config.settings.upload_dir / "ccc.jpg").unlink(missing_ok=True)


class TestPatchImage(unittest.IsolatedAsyncioTestCase):
    async def test_missing_returns_none(self) -> None:
        session = MagicMock()
        session.get = AsyncMock(return_value=None)
        out = await svc.patch_image(session, 99, ImagePatch(designer_tags=["x"]))
        self.assertIsNone(out)

    async def test_updates_fields(self) -> None:
        row = _row()
        session = MagicMock()
        session.get = AsyncMock(return_value=row)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        with patch.object(svc, "index_row_for_search", new_callable=AsyncMock):
            out = await svc.patch_image(
                session,
                1,
                ImagePatch(designer_tags=["a"], designer_notes="n", designer_name="dn"),
            )
        self.assertIs(out, row)
        self.assertEqual(row.designer_tags, ["a"])
        self.assertEqual(row.designer_notes, "n")
        self.assertEqual(row.designer_name, "dn")


class TestListFiltered(unittest.IsolatedAsyncioTestCase):
    def _session_with_rows(self, rows: list) -> MagicMock:
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = rows
        session.execute = AsyncMock(return_value=result)
        return session

    async def test_no_query_applies_filters_only(self) -> None:
        ok = _row(rid=1, ai_metadata={"garment_type": "shirt"})
        bad = _row(rid=2, ai_metadata={"garment_type": "pants"})
        session = self._session_with_rows([ok, bad])
        result = await svc.list_filtered(session, None, {"garment_type": "shirt"})
        self.assertIsNone(result.search)
        self.assertEqual([r.id for r in result.rows], [1])

    async def test_lexical_search_without_llm_key(self) -> None:
        row = _row(rid=1, description="summer linen dress", ai_metadata={"garment_type": "dress"})
        session = self._session_with_rows([row])
        with patch.object(config.settings, "openai_api_key", None), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            result = await svc.list_filtered(session, "linen summer", {})
        self.assertEqual(result.search.kind, "lexical")
        self.assertEqual(len(result.rows), 1)

    async def test_lexical_no_hits_returns_none_meta(self) -> None:
        row = _row(rid=1, description="alpha beta gamma", ai_metadata={})
        session = self._session_with_rows([row])
        with patch.object(config.settings, "openai_api_key", None), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            result = await svc.list_filtered(session, "zzznotfound", {})
        self.assertEqual(result.search.kind, "none")
        self.assertEqual(len(result.rows), 0)

    async def test_vector_ranking_when_key_and_hits(self) -> None:
        r1 = _row(rid=10, description="a", ai_metadata={"garment_type": "x"})
        r2 = _row(rid=20, description="b", ai_metadata={"garment_type": "x"})
        session = self._session_with_rows([r1, r2])
        with patch.object(config.settings, "openai_api_key", "k"), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as emb:
                emb.return_value = [0.1]
                with patch.object(svc, "query_similar", new_callable=AsyncMock) as q:
                    q.return_value = [(20, 0.1), (10, 0.2)]
                    result = await svc.list_filtered(session, "q", {})
        self.assertEqual(result.search.kind, "semantic")
        self.assertEqual([r.id for r in result.rows], [20, 10])

    async def test_vector_only_distant_uses_semantic_fallback(self) -> None:
        r1 = _row(rid=10, description="z", ai_metadata={"garment_type": "x"})
        session = self._session_with_rows([r1])
        with patch.object(config.settings, "openai_api_key", "k"), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as emb:
                emb.return_value = [0.1]
                with patch.object(svc, "query_similar", new_callable=AsyncMock) as q:
                    q.return_value = [(10, 0.9)]
                    result = await svc.list_filtered(session, "q", {})
        self.assertEqual(result.search.kind, "semantic_fallback")
        self.assertEqual([r.id for r in result.rows], [10])

    async def test_semantic_fallback_caps_at_ten_rows(self) -> None:
        db_rows = [_row(rid=i, description=f"x{i}", ai_metadata={"garment_type": "x"}) for i in range(1, 16)]
        session = self._session_with_rows(db_rows)
        ranked = [(i, 0.9) for i in range(1, 16)]
        with patch.object(config.settings, "openai_api_key", "k"), patch.object(
            config.settings, "openrouter_api_key", None
        ):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as emb:
                emb.return_value = [0.1]
                with patch.object(svc, "query_similar", new_callable=AsyncMock) as q:
                    q.return_value = ranked
                    result = await svc.list_filtered(session, "q", {})
        self.assertEqual(result.search.kind, "semantic_fallback")
        self.assertEqual(len(result.rows), 10)
        self.assertEqual([r.id for r in result.rows], list(range(1, 11)))

    async def test_vector_empty_falls_back_lexical(self) -> None:
        row = _row(rid=1, description="hello world", ai_metadata={})
        session = self._session_with_rows([row])
        with patch.object(config.settings, "openai_api_key", "k"):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as emb:
                emb.return_value = [0.1]
                with patch.object(svc, "query_similar", new_callable=AsyncMock) as q:
                    q.return_value = []
                    result = await svc.list_filtered(session, "hello", {})
        self.assertEqual(result.search.kind, "lexical")
        self.assertEqual(len(result.rows), 1)

    async def test_vector_exception_falls_back_lexical(self) -> None:
        row = _row(rid=1, description="fallback text", ai_metadata={})
        session = self._session_with_rows([row])
        with patch.object(config.settings, "openai_api_key", "k"):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as emb:
                emb.side_effect = RuntimeError("x")
                result = await svc.list_filtered(session, "fallback", {})
        self.assertEqual(result.search.kind, "lexical")
        self.assertEqual(len(result.rows), 1)

    async def test_vector_hits_filtered_out_use_lexical(self) -> None:
        row = _row(rid=1, description="unique token xyz", ai_metadata={"garment_type": "dress"})
        session = self._session_with_rows([row])
        with patch.object(config.settings, "openai_api_key", "k"):
            with patch.object(svc, "embed_text", new_callable=AsyncMock) as emb:
                emb.return_value = [0.1]
                with patch.object(svc, "query_similar", new_callable=AsyncMock) as q:
                    q.return_value = [(999, 0.0)]
                    result = await svc.list_filtered(session, "unique token", {"garment_type": "dress"})
        self.assertEqual(result.search.kind, "lexical")
        self.assertEqual(len(result.rows), 1)


class TestCollectFilterFacets(unittest.IsolatedAsyncioTestCase):
    async def test_collects_distinct_values(self) -> None:
        rows = [
            _row(
                rid=1,
                ai_metadata={
                    "garment_type": "G",
                    "style": "S",
                    "material": "M",
                    "pattern": "P",
                    "season": "summer",
                    "occasion": "casual",
                    "consumer_profile": "youth",
                    "trend_notes": "t",
                    "color_palette": ["red"],
                    "location_context": {"continent": "EU", "country": "FR", "city": "Paris"},
                    "time_context": {"year": 2021, "month": 6, "season": "summer"},
                },
                designer_name="D",
                designer_tags=["tag"],
            ),
        ]
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = rows
        session.execute = AsyncMock(return_value=result)
        facets = await svc.collect_filter_facets(session)
        self.assertIn("G", facets["garment_type"])
        self.assertIn("red", facets["color_palette"])
        self.assertIn(2021, facets["year"])
        self.assertIn(6, facets["month"])
        self.assertIn("EU", facets["continent"])
        self.assertIn("D", facets["designer_name"])
        self.assertIn("tag", facets["designer_tags"])


if __name__ == "__main__":
    unittest.main()
