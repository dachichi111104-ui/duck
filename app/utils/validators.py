"""Reusable form validation helpers (spec section 30)."""
from __future__ import annotations

import datetime as dt


class ValidationError(Exception):
    pass


def require_not_empty(value: str, field_label: str) -> str:
    if value is None or str(value).strip() == "":
        raise ValidationError(f"'{field_label}' không được để trống.")
    return value.strip()


def require_positive_number(value, field_label: str, allow_zero: bool = False):
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field_label}' phải là số hợp lệ.")
    if allow_zero and num < 0:
        raise ValidationError(f"'{field_label}' không được âm.")
    if not allow_zero and num <= 0:
        raise ValidationError(f"'{field_label}' phải lớn hơn 0.")
    return num


def require_valid_date(value, field_label: str) -> dt.date:
    if isinstance(value, dt.date):
        return value
    try:
        return dt.datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"'{field_label}' không đúng định dạng ngày (YYYY-MM-DD).")


def require_within_capacity(new_count: int, capacity: int, current_in_barn: int, field_label: str = "Số lượng"):
    if current_in_barn + new_count > capacity:
        remaining = max(capacity - current_in_barn, 0)
        raise ValidationError(
            f"{field_label} vượt quá sức chứa chuồng. Sức chứa còn lại: {remaining}."
        )
