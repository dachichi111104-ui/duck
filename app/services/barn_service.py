from __future__ import annotations

from app.database.connection import session_scope
from app.database.models import Barn
from app.repositories.barn_repository import BarnRepository
from app.utils.validators import require_not_empty, require_positive_number, ValidationError
from app.utils.logger import log_action, get_logger

logger = get_logger("barn_service")


class BarnService:
    def __init__(self) -> None:
        self._repo = BarnRepository()

    def list_barns(self) -> list[Barn]:
        with session_scope() as session:
            barns = self._repo.get_all(session)
            session.expunge_all()
            return barns

    def get_barn(self, barn_id: int) -> Barn | None:
        with session_scope() as session:
            barn = self._repo.get_by_id(session, barn_id)
            if barn:
                session.expunge(barn)
            return barn

    def create_barn(self, actor: str, code: str, name: str, location: str,
                     capacity: float, description: str = "") -> Barn:
        code = require_not_empty(code, "Mã chuồng")
        name = require_not_empty(name, "Tên chuồng")
        capacity_val = int(require_positive_number(capacity, "Sức chứa"))

        with session_scope() as session:
            if self._repo.get_by_code(session, code):
                raise ValidationError(f"Mã chuồng '{code}' đã tồn tại.")
            barn = Barn(code=code, name=name, location=location, capacity=capacity_val,
                        current_count=0, description=description)
            self._repo.add(session, barn)
            session.expunge(barn)
        log_action(actor, "CREATE_BARN", code)
        return barn

    def update_barn(self, actor: str, barn_id: int, **fields) -> Barn:
        with session_scope() as session:
            barn = self._repo.get_by_id(session, barn_id)
            if barn is None:
                raise ValidationError("Không tìm thấy chuồng.")
            if "name" in fields:
                barn.name = require_not_empty(fields["name"], "Tên chuồng")
            if "location" in fields:
                barn.location = fields["location"]
            if "capacity" in fields:
                new_capacity = int(require_positive_number(fields["capacity"], "Sức chứa"))
                if new_capacity < barn.current_count:
                    raise ValidationError(
                        f"Sức chứa mới ({new_capacity}) nhỏ hơn số lượng hiện tại ({barn.current_count})."
                    )
                barn.capacity = new_capacity
            if "status" in fields:
                barn.status = fields["status"]
            if "description" in fields:
                barn.description = fields["description"]
            session.flush()
            session.expunge(barn)
        log_action(actor, "UPDATE_BARN", str(barn_id))
        return barn

    def delete_barn(self, actor: str, barn_id: int) -> None:
        with session_scope() as session:
            barn = self._repo.get_by_id(session, barn_id)
            if barn is None:
                return
            if barn.current_count > 0:
                raise ValidationError("Không thể xóa chuồng đang có vịt.")
            self._repo.delete(session, barn)
        log_action(actor, "DELETE_BARN", str(barn_id))

    def check_capacity(self, barn_id: int, additional_count: int) -> None:
        barn = self.get_barn(barn_id)
        if barn is None:
            raise ValidationError("Không tìm thấy chuồng.")
        if barn.current_count + additional_count > barn.capacity:
            remaining = max(barn.capacity - barn.current_count, 0)
            raise ValidationError(
                f"Số lượng nhập vượt quá sức chứa chuồng '{barn.code}'. Còn lại: {remaining}."
            )
