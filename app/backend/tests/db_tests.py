"""Unit tests for fashion_backend.db."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class TestMigrateSqliteImagesColumns(unittest.TestCase):
    def test_skips_when_no_images_table(self) -> None:
        from fashion_backend.db import _migrate_sqlite_images_columns

        sync_conn = MagicMock()
        insp = MagicMock()
        insp.has_table.return_value = False
        with patch("sqlalchemy.inspect", return_value=insp):
            _migrate_sqlite_images_columns(sync_conn)
        sync_conn.execute.assert_not_called()

    def test_adds_user_caption_when_missing(self) -> None:
        from fashion_backend.db import _migrate_sqlite_images_columns

        sync_conn = MagicMock()
        insp = MagicMock()
        insp.has_table.return_value = True
        insp.get_columns.return_value = [
            {"name": "id"},
            {"name": "file_path"},
            {"name": "upload_metadata"},
        ]
        with patch("sqlalchemy.inspect", return_value=insp):
            _migrate_sqlite_images_columns(sync_conn)
        sqls = [str(c.args[0]) for c in sync_conn.execute.call_args_list]
        self.assertTrue(any("user_caption" in s for s in sqls))

    def test_adds_upload_metadata_when_missing(self) -> None:
        from fashion_backend.db import _migrate_sqlite_images_columns

        sync_conn = MagicMock()
        insp = MagicMock()
        insp.has_table.return_value = True
        insp.get_columns.return_value = [
            {"name": "id"},
            {"name": "user_caption"},
        ]
        with patch("sqlalchemy.inspect", return_value=insp):
            _migrate_sqlite_images_columns(sync_conn)
        sqls = [str(c.args[0]) for c in sync_conn.execute.call_args_list]
        self.assertTrue(any("upload_metadata" in s for s in sqls))

    def test_no_alter_when_columns_exist(self) -> None:
        from fashion_backend.db import _migrate_sqlite_images_columns

        sync_conn = MagicMock()
        insp = MagicMock()
        insp.has_table.return_value = True
        insp.get_columns.return_value = [
            {"name": "user_caption"},
            {"name": "upload_metadata"},
        ]
        with patch("sqlalchemy.inspect", return_value=insp):
            _migrate_sqlite_images_columns(sync_conn)
        sync_conn.execute.assert_not_called()


class TestGetSession(unittest.IsolatedAsyncioTestCase):
    async def test_yields_one_session(self) -> None:
        from fashion_backend.db import get_session

        n = 0
        async for _session in get_session():
            n += 1
            self.assertIsNotNone(_session)
        self.assertEqual(n, 1)


class TestInitDb(unittest.IsolatedAsyncioTestCase):
    async def test_init_db_smoke(self) -> None:
        from fashion_backend.db import init_db

        await init_db()


if __name__ == "__main__":
    unittest.main()
