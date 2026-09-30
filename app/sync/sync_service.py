"""
Sync Service for Offline-First Data Synchronization.

Runs on a background QThread to push local SQLite PENDING mutations to the
FastAPI web backend and pull remote Postgres updates seamlessly.

Backoff Strategy:
Exponential delay on network error (30s, 60s, 120s..., max 10 minutes).

Conflict Resolution:
Last Write Wins with CONFLICT flag fallback and UI choice dialog.
"""
from __future__ import annotations

import logging
import time
import datetime as dt
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from app.config.settings import SYNC_ENABLED, SYNC_INTERVAL_SECONDS
from app.database.connection import session_scope
from app.database.models import (
    User, Barn, Camera, Flock, FlockEvent, ProductionRecord, InventoryCategory,
    InventoryItem, InventoryTransaction, Disease, VeterinaryRecord,
    Vaccination, AIAnalysisSession, AIDetectionResult, AIAlert, Notification
)
from app.repositories.base_repository import BaseRepository
from app.sync.api_client import APIClient, AuthRequiredError
from app.sync.schema_mapper import serialize_model, ENDPOINT_MAP, apply_remote_to_local

logger = logging.getLogger("wdf.sync.service")

# Skip User model from auto-sync (managed via Auth API)
SYNC_MODELS = [
    Barn, Camera, Flock, FlockEvent, ProductionRecord,
    InventoryCategory, InventoryItem, InventoryTransaction,
    Disease, VeterinaryRecord, Vaccination,
    AIAnalysisSession, AIDetectionResult, AIAlert, Notification
]


class SyncWorker(QThread):
    # Signals: state (str), message (str), pending_count (int), conflict_count (int)
    sync_status_changed = pyqtSignal(str, str, int, int)
    conflict_occurred = pyqtSignal(str, int)  # entity_name, local_id
    auth_failed = pyqtSignal()

    def __init__(self, interval: int = SYNC_INTERVAL_SECONDS, parent=None):
        super().__init__(parent)
        self.interval = interval
        self.enabled = SYNC_ENABLED
        self.api_client = APIClient()
        self._running = True
        self._backoff_delay = interval
        self.current_state = "IDLE"
        self._last_pull_time: dict[str, str] = {}

    def stop(self):
        self._running = False

    def run(self):
        logger.info("SyncWorker started (interval=%ss, enabled=%s)", self.interval, self.enabled)

        # Startup health check log
        health = self.api_client.check_health()
        if not health["online"]:
            self.current_state = "OFFLINE"
            self.sync_status_changed.emit("OFFLINE", "Mất kết nối API", 0, 0)

        while self._running:
            if not self.enabled:
                self.msleep(5000)
                continue

            try:
                self.perform_sync_cycle()
                self._backoff_delay = self.interval  # Reset backoff on success
            except AuthRequiredError:
                logger.warning("Sync paused: Authentication required.")
                self.current_state = "AUTH_ERROR"
                self.sync_status_changed.emit("AUTH_ERROR", "Cần đăng nhập lại", 0, 0)
                self.auth_failed.emit()
                self.msleep(10000)
            except Exception as e:
                logger.warning("Sync iteration error: %s. Applying backoff %ss", e, self._backoff_delay)
                self.current_state = "OFFLINE"
                pending, conflicts = self.count_pending_and_conflicts()
                self.sync_status_changed.emit("OFFLINE", str(e), pending, conflicts)
                self._backoff_delay = min(self._backoff_delay * 2, 600)  # Max 10 mins

            # Sleep in 1-second chunks to allow graceful exit
            sleep_time = self._backoff_delay
            for _ in range(int(sleep_time)):
                if not self._running:
                    break
                self.msleep(1000)

    def count_pending_and_conflicts(self) -> tuple[int, int]:
        total_pending = 0
        total_conflicts = 0
        with session_scope() as session:
            for model_cls in SYNC_MODELS:
                if model_cls in (User, Notification):
                    continue
                repo = BaseRepository()
                repo.model = model_cls
                total_pending += len(repo.get_pending(session))
                total_conflicts += len(repo.get_conflicts(session))
        return total_pending, total_conflicts

    def _ensure_authenticated(self) -> bool:
        if not self.api_client.token_manager.get_access_token():
            u, p = self.api_client.token_manager.get_credentials()
            if u and p:
                try:
                    self.api_client.login(u, p)
                    logger.info("Auto-authenticated sync session for user=%s", u)
                    return True
                except Exception as ex:
                    logger.warning("Auto-authentication attempt failed for user=%s: %s", u, ex)
            return False
        return True

    def perform_sync_cycle(self):
        health = self.api_client.check_health()
        if not health["online"]:
            pending, conflicts = self.count_pending_and_conflicts()
            self.sync_status_changed.emit("OFFLINE", "Mất kết nối API", pending, conflicts)
            return

        self._ensure_authenticated()

        pending, conflicts = self.count_pending_and_conflicts()
        if pending > 0 or conflicts > 0:
            self.sync_status_changed.emit("SYNCING", "Đang đồng bộ...", pending, conflicts)

        try:
            # 1. PUSH local PENDING changes to remote API
            self.push_pending_records()
            # 2. PULL remote updates to local SQLite
            self.pull_remote_updates()
        except AuthRequiredError:
            # Attempt auto-login retry once
            if self._ensure_authenticated():
                self.push_pending_records()
                self.pull_remote_updates()
            else:
                raise

        # 3. Final state check
        pending_after, conflicts_after = self.count_pending_and_conflicts()
        if conflicts_after > 0:
            self.sync_status_changed.emit("CONFLICT", f"Có {conflicts_after} xung đột", pending_after, conflicts_after)
        elif pending_after > 0:
            self.sync_status_changed.emit("SYNCING", f"{pending_after} thay đổi chờ đồng bộ", pending_after, 0)
        else:
            self.sync_status_changed.emit("SYNCED", "Đã đồng bộ với server", 0, 0)

    def _call_endpoint_candidates(self, method: str, candidates: list[str], payload: dict | None = None,
                                  remote_id: int | None = None, params: dict | None = None):
        """Try candidate endpoint paths until non-404 response is received."""
        last_resp = None
        for cand in candidates:
            cand_path = cand.rstrip("/")
            if payload:
                try:
                    cand_path = cand_path.format(**payload)
                except KeyError:
                    pass

            if remote_id is not None:
                url_path = f"{cand_path}/{remote_id}"
            else:
                url_path = cand_path

            try:
                if method == "POST":
                    resp = self.api_client.request("POST", url_path, json=payload, params=params, timeout=30)
                elif method == "PUT":
                    resp = self.api_client.request("PUT", url_path, json=payload, params=params, timeout=30)
                elif method == "GET":
                    resp = self.api_client.request("GET", url_path, params=params, timeout=30)
                else:
                    resp = self.api_client.request(method, url_path, params=params, timeout=30)

                last_resp = resp
                if resp and resp.status_code != 404:
                    return resp, cand_path
            except AuthRequiredError:
                raise
            except Exception as ex:
                logger.warning("HTTP request exception on %s %s: %s", method, url_path, ex)
        return last_resp, candidates[0] if candidates else ""

    def push_pending_records(self):
        with session_scope() as session:
            for model_cls in SYNC_MODELS:
                if model_cls in (User, Notification):
                    continue
                repo = BaseRepository()
                repo.model = model_cls
                pending_records = repo.get_pending(session)
                candidates = ENDPOINT_MAP.get(model_cls, [])
                if isinstance(candidates, str):
                    candidates = [candidates]
                if not candidates:
                    continue

                for record in pending_records:
                    payload = serialize_model(record, session=session)

                    try:
                        if record.remote_id is None:
                            # CREATE on server
                            resp, _ = self._call_endpoint_candidates("POST", candidates, payload=payload)
                            is_dup = False
                            if resp and resp.status_code in (400, 409, 422):
                                try:
                                    res_json = resp.json()
                                    detail_str = str(res_json.get("detail", "")) if isinstance(res_json, dict) else resp.text
                                except Exception:
                                    detail_str = resp.text if resp else ""
                                if any(kw in detail_str.lower() for kw in ("tồn tại", "ton tai", "exists", "already", "t\u1ed3n t\u1ea1i", "duplicate")):
                                    is_dup = True

                            if resp and resp.status_code in (200, 201):
                                res_json = resp.json()
                                remote_id = res_json.get("id") or res_json.get("remote_id")
                                repo.mark_synced(session, record, remote_id=remote_id)
                                logger.info("Pushed NEW %s (local_id=%s -> remote_id=%s)", model_cls.__name__, record.id, remote_id)
                            elif is_dup or (resp and resp.status_code in (400, 409)):
                                # Record code already exists on server -> Link & mark synced
                                repo.mark_synced(session, record)
                                logger.info("Record %s local_id=%s already exists on server, marked SYNCED", model_cls.__name__, record.id)
                            else:
                                err_text = (resp.text if resp else "No response").encode("ascii", "replace").decode("ascii")
                                status_code = resp.status_code if resp else "ERR"
                                logger.warning("Failed POST %s: HTTP %s - %s", model_cls.__name__, status_code, err_text[:200])
                        else:
                            # UPDATE on server
                            resp, _ = self._call_endpoint_candidates("PUT", candidates, payload=payload, remote_id=record.remote_id)
                            if resp and resp.status_code in (200, 204):
                                repo.mark_synced(session, record)
                                logger.info("Pushed UPDATE %s (remote_id=%s)", model_cls.__name__, record.remote_id)
                            elif resp and resp.status_code == 409:
                                repo.mark_conflict(session, record)
                                self.conflict_occurred.emit(model_cls.__name__, record.id)
                                logger.warning("Conflict detected on PUSH %s remote_id=%s", model_cls.__name__, record.remote_id)
                            else:
                                err_text = (resp.text if resp else "No response").encode("ascii", "replace").decode("ascii")
                                status_code = resp.status_code if resp else "ERR"
                                logger.warning("Failed PUT %s: HTTP %s - %s", model_cls.__name__, status_code, err_text[:200])
                    except AuthRequiredError:
                        raise
                    except Exception as e:
                        err_msg = str(e).encode("ascii", "replace").decode("ascii")
                        logger.warning("Error pushing record %s id=%s: %s", model_cls.__name__, record.id, err_msg)

    def pull_remote_updates(self):
        with session_scope() as session:
            for model_cls in SYNC_MODELS:
                repo = BaseRepository()
                repo.model = model_cls
                candidates = ENDPOINT_MAP.get(model_cls, [])
                if isinstance(candidates, str):
                    candidates = [candidates]
                if not candidates:
                    continue

                model_name = model_cls.__name__
                params = {}
                last_time = self._last_pull_time.get(model_name)
                if last_time:
                    params["updated_since"] = last_time

                pull_start_time = dt.datetime.utcnow().isoformat()

                try:
                    resp, _ = self._call_endpoint_candidates("GET", candidates, params=params)
                    if not resp or resp.status_code != 200:
                        continue

                    remote_items = resp.json()
                    if isinstance(remote_items, dict):
                        if "data" in remote_items and isinstance(remote_items["data"], list):
                            remote_items = remote_items["data"]
                        elif "items" in remote_items and isinstance(remote_items["items"], list):
                            remote_items = remote_items["items"]
                        elif "results" in remote_items and isinstance(remote_items["results"], list):
                            remote_items = remote_items["results"]
                    if not isinstance(remote_items, list):
                        continue

                    for item in remote_items:
                        r_id = item.get("id")
                        if not r_id:
                            continue

                        try:
                            local_record = repo.get_by_remote_id(session, r_id)
                            if local_record is None:
                                code_val = item.get("code") or item.get("flock_code")
                                if not code_val:
                                    if model_cls == Camera:
                                        code_val = f"CAM-{r_id:02d}"
                                    elif model_cls == Barn:
                                        code_val = f"C-{r_id:03d}"
                                    elif model_cls == InventoryItem:
                                        code_val = f"VT-{r_id:03d}"

                                name_val = item.get("name")
                                if code_val and hasattr(model_cls, "code"):
                                    local_record = session.query(model_cls).filter(model_cls.code == code_val).first()
                                elif code_val and hasattr(model_cls, "flock_code"):
                                    local_record = session.query(model_cls).filter(model_cls.flock_code == code_val).first()

                                if local_record is None and name_val and hasattr(model_cls, "name"):
                                    local_record = session.query(model_cls).filter(model_cls.name == name_val).first()

                            if local_record is None:
                                # Create new local record from server item
                                new_instance = model_cls()
                                apply_remote_to_local(new_instance, item, session=session)
                                new_instance.sync_status = "SYNCED"
                                new_instance.remote_id = r_id
                                session.add(new_instance)
                                session.flush()
                                logger.info("Pulled NEW %s remote_id=%s", model_name, r_id)
                            else:
                                # Link remote_id and update local record
                                local_record.remote_id = r_id
                                apply_remote_to_local(local_record, item, session=session)
                                local_record.sync_status = "SYNCED"
                                session.flush()
                        except Exception as item_err:
                            session.rollback()
                            err_msg = str(item_err).encode("ascii", "replace").decode("ascii")
                            logger.warning("Error pulling item %s r_id=%s: %s", model_name, r_id, err_msg)

                    self._last_pull_time[model_name] = pull_start_time

                except AuthRequiredError:
                    raise
                except Exception as e:
                    session.rollback()
                    err_msg = str(e).encode("ascii", "replace").decode("ascii")
                    logger.warning("Error pulling updates for %s: %s", model_name, err_msg)


class SyncService:
    """Manager class to interface SyncWorker QThread with PyQt Application."""
    _instance: SyncService | None = None

    def __init__(self, parent=None):
        self.worker = SyncWorker(parent=parent)

    @classmethod
    def get_instance(cls, parent=None) -> SyncService:
        if cls._instance is None:
            cls._instance = SyncService(parent=parent)
        return cls._instance

    def start(self):
        if not self.worker.isRunning():
            self.worker.start()

    def stop(self):
        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)

    def trigger_sync_now(self):
        if self.worker.isRunning():
            self.worker._backoff_delay = 1
