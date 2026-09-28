"""
Database migration helper.

Automatically inspects SQLite tables on application startup and adds
the sync columns (sync_status, last_modified_at, remote_id) if missing.
Guarantees zero data loss and seamless upgrade for existing databases.
"""
from __future__ import annotations

import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("wdf.migration")

TABLES_TO_MIGRATE = [
    "roles",
    "users",
    "barns",
    "cameras",
    "flocks",
    "flock_events",
    "production_records",
    "inventory_categories",
    "inventory_items",
    "inventory_transactions",
    "diseases",
    "veterinary_records",
    "vaccinations",
    "ai_analysis_sessions",
    "ai_detection_results",
    "ai_alerts",
    "notifications",
]


def ensure_sync_columns(engine: Engine) -> None:
    """Check each business table and add missing sync tracking columns."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.connect() as conn:
        for table_name in TABLES_TO_MIGRATE:
            if table_name not in existing_tables:
                continue

            columns = {col["name"] for col in inspector.get_columns(table_name)}

            if "sync_status" not in columns:
                logger.info("Migrating table '%s': adding column 'sync_status'", table_name)
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN sync_status VARCHAR(20) DEFAULT 'PENDING'"))

            if "last_modified_at" not in columns:
                logger.info("Migrating table '%s': adding column 'last_modified_at'", table_name)
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN last_modified_at DATETIME"))

            if "remote_id" not in columns:
                logger.info("Migrating table '%s': adding column 'remote_id'", table_name)
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN remote_id INTEGER"))

            # Ensure any local record without a remote_id is flagged as PENDING (except notifications and users)
            if table_name not in ("users", "notifications"):
                conn.execute(text(f"UPDATE {table_name} SET sync_status = 'PENDING' WHERE sync_status IS NULL OR (sync_status = 'SYNCED' AND remote_id IS NULL)"))
            else:
                conn.execute(text(f"UPDATE {table_name} SET sync_status = 'SYNCED' WHERE sync_status IS NULL OR sync_status = 'PENDING'"))

        conn.commit()
