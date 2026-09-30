"""
Schema Mapper for Desktop App <-> Web Backend API.

Explicitly defines field translations, endpoint mappings, and Foreign Key
remote_id resolution between local SQLite models and REST API JSON models.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from app.database.connection import session_scope
from app.database.models import (
    Barn, Camera, Flock, FlockEvent, ProductionRecord, InventoryCategory,
    InventoryItem, InventoryTransaction, Disease, VeterinaryRecord,
    Vaccination, AIAnalysisSession, AIDetectionResult, AIAlert, Notification, User
)


ENDPOINT_MAP = {
    User: ["users"],
    Barn: ["barns"],
    Camera: ["cameras"],
    Flock: ["flocks"],
    FlockEvent: ["flock-events", "flocks/{flock_id}/events"],
    ProductionRecord: ["production"],
    InventoryCategory: ["inventory/categories"],
    InventoryItem: ["inventory/items"],
    InventoryTransaction: ["inventory/transactions"],
    Disease: ["veterinary/diseases"],
    VeterinaryRecord: ["veterinary/records"],
    Vaccination: ["veterinary/vaccinations"],
    AIAnalysisSession: ["ai/sessions"],
    AIDetectionResult: ["ai/sessions/{session_id}/detections", "ai/detections"],
    AIAlert: ["ai/alerts"],
    Notification: ["notifications"],
}


def serialize_model(instance: Any, session: Any = None) -> dict[str, Any]:
    """Convert local SQLite ORM instance into API request dictionary."""
    data = {}
    for col in instance.__table__.columns:
        key = col.name
        # Skip local primary key, sync tracking metadata, and password hash
        if key in ("id", "sync_status", "last_modified_at", "remote_id", "hashed_password", "created_at"):
            continue

        val = getattr(instance, key)
        if isinstance(val, (dt.date, dt.datetime)):
            data[key] = val.isoformat()
        else:
            data[key] = val

    # Special field alias mappings for Web Backend API Pydantic schemas
    if isinstance(instance, Flock):
        data["code"] = instance.flock_code
        data["flock_code"] = instance.flock_code
        data["initial_quantity"] = getattr(instance, "initial_count", None) or getattr(instance, "current_count", None) or 500
        data["current_quantity"] = getattr(instance, "current_count", None) or 500
        start_dt = getattr(instance, "start_date", None)
        if isinstance(start_dt, (dt.date, dt.datetime)):
            data["entry_date"] = start_dt.isoformat()
        else:
            data["entry_date"] = str(start_dt) if start_dt else dt.date.today().isoformat()
        st = getattr(instance, "status", "ACTIVE")
        if st in ("BROODING", "GROWING", "LAYING", "COMPLETED"):
            data["status"] = st
        else:
            data["status"] = "GROWING"

    elif isinstance(instance, FlockEvent):
        data["description"] = getattr(instance, "reason", None) or getattr(instance, "notes", None) or "Sự kiện đàn vịt"

    elif isinstance(instance, Disease):
        if "code" not in data or not data["code"]:
            data["code"] = f"DIS-{instance.id:03d}" if instance.id else "DIS-001"
        if "symptoms" not in data or not data["symptoms"]:
            data["symptoms"] = getattr(instance, "behavior_signs", None) or "Nhiễm bệnh thú y"
        data["treatment"] = getattr(instance, "behavior_signs", None) or "Điều trị theo phác đồ thú y"

    elif isinstance(instance, VeterinaryRecord):
        data["treatment_plan"] = getattr(instance, "treatment", None) or "Cách ly theo dõi"
        data["veterinarian_name"] = getattr(instance, "veterinarian", None) or "BSTY Nguyễn Văn A"
        st = getattr(instance, "status", "THEO_DOI")
        if st in ("MONITORING", "TREATING", "RECOVERED", "CULLED"):
            data["status"] = st
        elif st == "THEO_DOI":
            data["status"] = "MONITORING"
        else:
            data["status"] = "TREATING"

    elif isinstance(instance, Vaccination):
        if "scheduled_date" not in data or not data["scheduled_date"]:
            data["scheduled_date"] = instance.vaccination_date.isoformat() if getattr(instance, "vaccination_date", None) else dt.date.today().isoformat()

    elif isinstance(instance, AIAnalysisSession):
        data["video_filename"] = getattr(instance, "file_name", None) or getattr(instance, "video_path", None) or "video.mp4"
        data["duration_seconds"] = float(getattr(instance, "duration", 0.0) or getattr(instance, "duration_seconds", 0.0) or 0.0)
        data["total_ducks_detected"] = len(getattr(instance, "detections", [])) if hasattr(instance, "detections") else 0
        data["abnormal_count"] = sum(1 for d in getattr(instance, "detections", []) if "bệnh" in str(getattr(d, "behavior_label", "")).lower() or "ngửa" in str(getattr(d, "behavior_label", "")).lower()) if hasattr(instance, "detections") else 0
        data["status"] = getattr(instance, "status", "COMPLETED") or "COMPLETED"

    elif isinstance(instance, AIDetectionResult):
        data["session_id"] = getattr(instance, "session_id", 1) or 1
        data["frame_index"] = getattr(instance, "frame_index", 0) or 0
        data["timestamp_sec"] = float(getattr(instance, "timestamp", 0.0) or 0.0)
        data["track_id"] = int(getattr(instance, "track_id", 1) or 1)
        data["behavior_label"] = str(getattr(instance, "behavior_label", None) or getattr(instance, "health_status", None) or "Bình thường")
        data["confidence"] = float(getattr(instance, "confidence", 0.95) or 0.95)
        data["bbox_x"] = float(getattr(instance, "bbox_x", 0.0) or 0.0)
        data["bbox_y"] = float(getattr(instance, "bbox_y", 0.0) or 0.0)
        data["bbox_w"] = float(getattr(instance, "bbox_width", 0.0) or getattr(instance, "bbox_w", 0.0) or 0.0)
        data["bbox_h"] = float(getattr(instance, "bbox_height", 0.0) or getattr(instance, "bbox_h", 0.0) or 0.0)

    # Resolve foreign key IDs and remote_ids
    def _do_resolve(sess: Any):
        if isinstance(instance, (Flock, Camera)) and instance.barn_id:
            barn = sess.get(Barn, instance.barn_id)
            if barn:
                target_barn_id = barn.remote_id or barn.id
                data["barn_id"] = target_barn_id
                data["barn_remote_id"] = target_barn_id

        elif isinstance(instance, FlockEvent) and instance.flock_id:
            flock = sess.get(Flock, instance.flock_id)
            if flock:
                target_flock_id = flock.remote_id or flock.id
                data["flock_id"] = target_flock_id
                data["flock_remote_id"] = target_flock_id

        elif isinstance(instance, ProductionRecord) and instance.flock_id:
            flock = sess.get(Flock, instance.flock_id)
            if flock:
                target_flock_id = flock.remote_id or flock.id
                data["flock_id"] = target_flock_id
                data["flock_remote_id"] = target_flock_id

        elif isinstance(instance, InventoryItem) and instance.category_id:
            cat = sess.get(InventoryCategory, instance.category_id)
            if cat:
                target_cat_id = cat.remote_id or cat.id
                data["category_id"] = target_cat_id
                data["category_remote_id"] = target_cat_id

        elif isinstance(instance, InventoryTransaction) and instance.item_id:
            item = sess.get(InventoryItem, instance.item_id)
            if item:
                target_item_id = item.remote_id or item.id
                data["item_id"] = target_item_id
                data["item_remote_id"] = target_item_id

        elif isinstance(instance, VeterinaryRecord):
            if instance.flock_id:
                flock = sess.get(Flock, instance.flock_id)
                if flock:
                    target_flock_id = flock.remote_id or flock.id
                    data["flock_id"] = target_flock_id
                    data["flock_remote_id"] = target_flock_id
            if instance.disease_id:
                disease = sess.get(Disease, instance.disease_id)
                if disease:
                    target_dis_id = disease.remote_id or disease.id
                    data["disease_id"] = target_dis_id
                    data["disease_remote_id"] = target_dis_id
            else:
                first_disease = sess.query(Disease).first()
                if first_disease:
                    data["disease_id"] = first_disease.remote_id or first_disease.id
                else:
                    data["disease_id"] = 1

        elif isinstance(instance, Vaccination) and instance.flock_id:
            flock = sess.get(Flock, instance.flock_id)
            if flock:
                target_flock_id = flock.remote_id or flock.id
                data["flock_id"] = target_flock_id
                data["flock_remote_id"] = target_flock_id

        elif isinstance(instance, AIAnalysisSession):
            if "barn_id" not in data or not data["barn_id"]:
                first_barn = sess.query(Barn).first()
                if first_barn:
                    data["barn_id"] = first_barn.remote_id or first_barn.id
                else:
                    data["barn_id"] = 1
            if "flock_id" not in data or not data["flock_id"]:
                first_flock = sess.query(Flock).first()
                if first_flock:
                    data["flock_id"] = first_flock.remote_id or first_flock.id
                else:
                    data["flock_id"] = 1

        elif isinstance(instance, AIDetectionResult) and instance.session_id:
            ai_sess = sess.get(AIAnalysisSession, instance.session_id)
            if ai_sess:
                target_sess_id = ai_sess.remote_id or ai_sess.id
                data["session_id"] = target_sess_id
                data["session_remote_id"] = target_sess_id

    # Ensure non-null integer FK defaults for Web API Pydantic schemas
    if isinstance(instance, (Flock, Camera)) and not data.get("barn_id"):
        data["barn_id"] = 1
    if isinstance(instance, (FlockEvent, ProductionRecord, Vaccination, VeterinaryRecord)) and not data.get("flock_id"):
        data["flock_id"] = 1
    if isinstance(instance, VeterinaryRecord) and not data.get("disease_id"):
        data["disease_id"] = 1
    if isinstance(instance, InventoryItem) and not data.get("category_id"):
        data["category_id"] = 1
    if isinstance(instance, InventoryTransaction) and not data.get("item_id"):
        data["item_id"] = 1

    if session is not None:
        _do_resolve(session)
    else:
        with session_scope() as sess:
            _do_resolve(sess)

    return data


def _resolve_local_fk(session: Any, target_model: Any, remote_fk_val: Any) -> int | None:
    if session is None:
        return remote_fk_val
    try:
        if remote_fk_val is not None:
            rec = session.query(target_model).filter(target_model.remote_id == remote_fk_val).first()
            if rec:
                return rec.id
            rec = session.query(target_model).filter(target_model.id == remote_fk_val).first()
            if rec:
                return rec.id
        first_rec = session.query(target_model).first()
        if first_rec:
            return first_rec.id
    except Exception:
        pass
    return 1


def apply_remote_to_local(instance: Any, remote_data: dict[str, Any], session: Any = None) -> None:
    """Update local SQLite instance attributes with data received from server API."""
    if "id" in remote_data:
        instance.remote_id = remote_data["id"]

    r_id = remote_data.get("id") or 1
    if hasattr(instance, "code") and not getattr(instance, "code", None):
        if isinstance(instance, Camera):
            instance.code = remote_data.get("code") or f"CAM-{r_id:02d}"
        elif isinstance(instance, Barn):
            instance.code = remote_data.get("code") or f"C-{r_id:03d}"
        elif isinstance(instance, InventoryItem):
            instance.code = remote_data.get("code") or f"VT-{r_id:03d}"
        else:
            instance.code = remote_data.get("code") or f"REF-{r_id:03d}"

    if hasattr(instance, "flock_code") and not getattr(instance, "flock_code", None):
        instance.flock_code = remote_data.get("flock_code") or remote_data.get("code") or f"FL-{r_id:03d}"

    if session is not None:
        fk_map = {
            "barn_id": Barn,
            "flock_id": Flock,
            "category_id": InventoryCategory,
            "item_id": InventoryItem,
            "disease_id": Disease,
            "session_id": AIAnalysisSession,
            "camera_id": Camera,
        }
        for fk_field, model_cls in fk_map.items():
            if hasattr(instance, fk_field):
                val = remote_data.get(fk_field)
                resolved_id = _resolve_local_fk(session, model_cls, val)
                if resolved_id is not None:
                    setattr(instance, fk_field, resolved_id)

    if isinstance(instance, AIAnalysisSession):
        instance.video_path = remote_data.get("video_path") or f"session_{r_id}.mp4"
        instance.file_name = remote_data.get("file_name") or f"session_{r_id}.mp4"

    elif isinstance(instance, Notification):
        instance.alert_type = remote_data.get("alert_type") or remote_data.get("type") or "SYSTEM_ALERT"
        instance.severity = remote_data.get("severity") or remote_data.get("level") or "INFO"
        instance.title = remote_data.get("title") or "Thông báo hệ thống"
        instance.message = remote_data.get("message") or "Có cập nhật mới từ hệ thống"

    elif isinstance(instance, Flock):
        if not getattr(instance, "start_date", None):
            s_date = remote_data.get("start_date") or remote_data.get("entry_date") or remote_data.get("created_at")
            if isinstance(s_date, str):
                try:
                    instance.start_date = dt.date.fromisoformat(s_date[:10])
                except Exception:
                    instance.start_date = dt.date.today()
            else:
                instance.start_date = dt.date.today()

        if getattr(instance, "initial_count", None) is None or getattr(instance, "initial_count", 0) == 0:
            instance.initial_count = remote_data.get("initial_count") or remote_data.get("initial_quantity") or 500
        if getattr(instance, "current_count", None) is None or getattr(instance, "current_count", 0) == 0:
            instance.current_count = remote_data.get("current_count") or remote_data.get("current_quantity") or 480
        if getattr(instance, "dead_count", None) is None:
            instance.dead_count = remote_data.get("dead_count") or 0

    elif isinstance(instance, InventoryTransaction):
        if not getattr(instance, "transaction_date", None):
            t_date = remote_data.get("transaction_date") or remote_data.get("date") or remote_data.get("created_at")
            if isinstance(t_date, str):
                try:
                    instance.transaction_date = dt.datetime.fromisoformat(t_date.replace("Z", "+00:00"))
                except Exception:
                    instance.transaction_date = dt.datetime.utcnow()
            else:
                instance.transaction_date = dt.datetime.utcnow()
        if "notes" in remote_data or "note" in remote_data:
            instance.note = remote_data.get("note") or remote_data.get("notes") or ""

    elif isinstance(instance, VeterinaryRecord):
        if not getattr(instance, "diagnosis_date", None):
            e_date = remote_data.get("diagnosis_date") or remote_data.get("examination_date") or remote_data.get("date") or remote_data.get("created_at")
            if isinstance(e_date, str):
                try:
                    instance.diagnosis_date = dt.date.fromisoformat(e_date[:10])
                except Exception:
                    instance.diagnosis_date = dt.date.today()
            else:
                instance.diagnosis_date = dt.date.today()
        if "treatment_plan" in remote_data and not getattr(instance, "treatment", None):
            instance.treatment = remote_data["treatment_plan"]
        if "veterinarian_name" in remote_data and not getattr(instance, "veterinarian", None):
            instance.veterinarian = remote_data["veterinarian_name"]
        if "suspected_disease" in remote_data and not getattr(instance, "diagnosis", None):
            instance.diagnosis = remote_data["suspected_disease"]

    elif isinstance(instance, Vaccination):
        if not getattr(instance, "vaccination_date", None):
            v_date = remote_data.get("vaccination_date") or remote_data.get("scheduled_date") or remote_data.get("date")
            if isinstance(v_date, str):
                try:
                    instance.vaccination_date = dt.date.fromisoformat(v_date[:10])
                except Exception:
                    instance.vaccination_date = dt.date.today()
            else:
                instance.vaccination_date = dt.date.today()

    elif isinstance(instance, FlockEvent):
        instance.quantity = remote_data.get("quantity") if remote_data.get("quantity") is not None else 0
        if not getattr(instance, "event_date", None):
            e_date = remote_data.get("event_date") or remote_data.get("date") or remote_data.get("created_at")
            if isinstance(e_date, str):
                try:
                    instance.event_date = dt.date.fromisoformat(e_date[:10])
                except Exception:
                    instance.event_date = dt.date.today()
            else:
                instance.event_date = dt.date.today()

    elif isinstance(instance, Disease):
        if not getattr(instance, "behavior_signs", None):
            instance.behavior_signs = remote_data.get("behavior_signs") or remote_data.get("symptoms") or "Nhiễm bệnh thú y"

    cols_by_name = {col.name: col for col in instance.__table__.columns}

    for key, val in remote_data.items():
        if key not in cols_by_name or key in ("id", "sync_status", "remote_id"):
            continue
        if session is not None and key in ("barn_id", "flock_id", "category_id", "item_id", "disease_id", "session_id", "camera_id"):
            continue

        if val is None:
            col = cols_by_name.get(key)
            if key in ("code", "flock_code") and getattr(instance, key, None):
                continue
            if col is not None and not col.nullable and getattr(instance, key, None) is not None:
                continue
            setattr(instance, key, None)
            continue

        if isinstance(instance, AIAlert) and key == "timestamp" and isinstance(val, str):
            try:
                val = dt.datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
            except Exception:
                val = 0.0

        col = cols_by_name.get(key)
        if col is not None:
            col_type_str = str(col.type).upper()
            if "DATETIME" in col_type_str and isinstance(val, str):
                try:
                    val = dt.datetime.fromisoformat(val.replace("Z", "+00:00"))
                except Exception:
                    pass
            elif "DATE" in col_type_str and isinstance(val, str):
                try:
                    val = dt.date.fromisoformat(val[:10])
                except Exception:
                    pass

        setattr(instance, key, val)
