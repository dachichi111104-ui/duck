"""
Unit tests for Offline-First Sync Architecture (SyncWorker, BaseRepository, APIClient, TokenManager).
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.database.connection import init_database, session_scope
from app.database.models import Barn, Flock
from app.repositories.base_repository import BaseRepository
from app.sync.api_client import APIClient, AuthRequiredError
from app.sync.token_manager import TokenManager
from app.sync.sync_service import SyncWorker


class TestSyncService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        self.token_manager = TokenManager()

    def test_offline_record_creation_sets_pending(self):
        """1. Thêm bản ghi khi mất mạng -> sync_status=PENDING."""
        with session_scope() as session:
            repo = BaseRepository()
            repo.model = Barn
            barn = Barn(
                code="TEST_BARN_SYNC_01",
                name="Chuồng Thử Nghiệm Sync",
                capacity=500,
                current_count=0
            )
            repo.add(session, barn)
            session.flush()

            self.assertEqual(barn.sync_status, "PENDING")
            self.assertIsNotNone(barn.last_modified_at)
            self.assertIsNone(barn.remote_id)

    @patch("app.sync.api_client.APIClient.request")
    def test_sync_push_updates_to_synced(self, mock_request):
        """2. Có mạng lại -> tự đẩy lên server, cập nhật SYNCED và remote_id."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 999111, "code": "TEST_BARN_SYNC_02"}
        mock_request.return_value = mock_resp

        worker = SyncWorker(interval=10)
        worker.api_client.request = mock_request

        barn_id = None
        with session_scope() as session:
            repo = BaseRepository()
            repo.model = Barn
            barn = Barn(
                code="TEST_BARN_SYNC_02",
                name="Chuồng Sync Thành Công",
                capacity=300
            )
            repo.add(session, barn)
            session.flush()
            barn_id = barn.id

        worker.push_pending_records()

        with session_scope() as session:
            repo = BaseRepository()
            repo.model = Barn
            saved_barn = repo.get_by_id(session, barn_id)
            self.assertEqual(saved_barn.sync_status, "SYNCED")
            self.assertEqual(saved_barn.remote_id, 999111)

    @patch("app.sync.api_client.APIClient.request")
    def test_sync_conflict_marks_conflict_status(self, mock_request):
        """3. Giả lập xung đột (Conflict 409) -> đánh dấu CONFLICT, không tự ghi đè."""
        mock_resp = MagicMock()
        mock_resp.status_code = 409
        mock_request.return_value = mock_resp

        worker = SyncWorker(interval=10)
        worker.api_client.request = mock_request

        barn_id = None
        with session_scope() as session:
            repo = BaseRepository()
            repo.model = Barn
            barn = Barn(
                code="TEST_BARN_CONFLICT_03",
                name="Chuồng Xung Đột",
                capacity=300,
                remote_id=888222
            )
            repo.add(session, barn)
            session.flush()
            barn_id = barn.id

        worker.push_pending_records()

        with session_scope() as session:
            repo = BaseRepository()
            repo.model = Barn
            saved_barn = repo.get_by_id(session, barn_id)
            self.assertEqual(saved_barn.sync_status, "CONFLICT")

    @patch("app.sync.api_client.requests.post")
    def test_token_expiration_and_refresh(self, mock_post):
        """4. Token hết hạn -> tự gọi refresh token hoặc dừng sync đúng cách."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "new_access_token_abc",
            "refresh_token": "new_refresh_token_xyz"
        }
        mock_post.return_value = mock_resp

        self.token_manager.save_tokens("old_access", "valid_refresh")

        client = APIClient()
        new_token = client.refresh_access_token()

        self.assertEqual(new_token, "new_access_token_abc")
        self.assertEqual(self.token_manager.get_access_token(), "new_access_token_abc")


if __name__ == "__main__":
    unittest.main()
