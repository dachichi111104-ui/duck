from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from app.database.connection import session_scope
from app.repositories.flock_repository import FlockRepository, ProductionRecordRepository
from app.repositories.inventory_repository import InventoryTransactionRepository
from app.repositories.veterinary_repository import VeterinaryRecordRepository
from app.repositories.ai_repository import AISessionRepository
from app.config.settings import EXPORTS_DIR
from app.utils.logger import log_action, get_logger

logger = get_logger("report_service")

HEADER_FILL = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


@dataclass
class ReportFilter:
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    flock_id: int | None = None
    barn_id: int | None = None


def _style_header(ws, row_idx: int = 1) -> None:
    for cell in ws[row_idx]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT


def _autosize(ws) -> None:
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 10), 45)


class ReportService:
    def __init__(self) -> None:
        self._flock_repo = FlockRepository()
        self._prod_repo = ProductionRecordRepository()
        self._txn_repo = InventoryTransactionRepository()
        self._vet_repo = VeterinaryRecordRepository()
        self._ai_repo = AISessionRepository()

    # ------------------------------------------------------------------
    def flock_report_data(self, filters: ReportFilter) -> list[dict]:
        with session_scope() as session:
            flocks = self._flock_repo.get_all(session)
            if filters.barn_id:
                flocks = [f for f in flocks if f.barn_id == filters.barn_id]
            rows = [{
                "Mã đàn": f.flock_code, "Tên đàn": f.name,
                "Chuồng": f.barn.code if f.barn else "-",
                "Số lượng ban đầu": f.initial_count, "Số lượng hiện tại": f.current_count,
                "Số chết": f.dead_count, "Tỷ lệ sống (%)": f.survival_rate,
                "Ngày nhập": f.start_date.isoformat(), "Trạng thái": f.status,
            } for f in flocks]
            return rows

    def production_report_data(self, filters: ReportFilter) -> list[dict]:
        with session_scope() as session:
            since = filters.date_from or (dt.date.today() - dt.timedelta(days=30))
            records = self._prod_repo.get_since(session, since)
            if filters.date_to:
                records = [r for r in records if r.record_date <= filters.date_to]
            if filters.flock_id:
                records = [r for r in records if r.flock_id == filters.flock_id]
            rows = [{
                "Ngày": r.record_date.isoformat(), "Đàn": r.flock.flock_code if r.flock else r.flock_id,
                "Sản lượng trứng": r.egg_quantity, "Trọng lượng TB (kg)": r.average_weight,
                "Thức ăn tiêu thụ (kg)": r.feed_consumption,
            } for r in records]
            return rows

    def inventory_report_data(self, filters: ReportFilter) -> list[dict]:
        with session_scope() as session:
            txns = self._txn_repo.get_recent(session, limit=1000)
            if filters.date_from:
                txns = [t for t in txns if t.transaction_date >= filters.date_from]
            if filters.date_to:
                txns = [t for t in txns if t.transaction_date <= filters.date_to]
            rows = [{
                "Ngày": t.transaction_date.isoformat(),
                "Vật tư": t.item.name if t.item else t.item_id,
                "Loại giao dịch": t.transaction_type, "Số lượng": t.quantity,
                "Tham chiếu": t.reference or "", "Ghi chú": t.note or "",
            } for t in txns]
            return rows

    def veterinary_report_data(self, filters: ReportFilter) -> list[dict]:
        with session_scope() as session:
            records = self._vet_repo.get_all(session)
            if filters.flock_id:
                records = [r for r in records if r.flock_id == filters.flock_id]
            if filters.date_from:
                records = [r for r in records if r.diagnosis_date >= filters.date_from]
            if filters.date_to:
                records = [r for r in records if r.diagnosis_date <= filters.date_to]
            rows = [{
                "Ngày": r.diagnosis_date.isoformat(),
                "Đàn": r.flock.flock_code if r.flock else r.flock_id,
                "Bệnh": r.disease.name if r.disease else "-",
                "Triệu chứng": r.symptoms or "", "Điều trị": r.treatment or "",
                "Trạng thái": r.status, "Nguồn": r.source,
            } for r in records]
            return rows

    def ai_report_data(self, filters: ReportFilter) -> list[dict]:
        with session_scope() as session:
            sessions = self._ai_repo.get_all(session)
            rows = [{
                "Tệp video": s.file_name, "Thời lượng (s)": s.duration,
                "Độ phân giải": s.resolution, "FPS": s.fps,
                "Bắt đầu": s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "",
                "Trạng thái": s.status, "Phiên bản model": s.model_version,
            } for s in sessions]
            return rows

    # ------------------------------------------------------------------
    def export_to_excel(self, actor: str, report_name: str, rows: list[dict]) -> str:
        wb = Workbook()
        ws = wb.active
        ws.title = report_name[:31] if report_name else "Report"

        if rows:
            headers = list(rows[0].keys())
            ws.append(headers)
            for row in rows:
                ws.append([row.get(h, "") for h in headers])
            _style_header(ws)
            _autosize(ws)
        else:
            ws.append(["Không có dữ liệu"])

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in report_name if c.isalnum() or c in ("_", "-")) or "report"
        output_path = EXPORTS_DIR / f"{safe_name}_{timestamp}.xlsx"
        wb.save(output_path)
        log_action(actor, "EXPORT_EXCEL", str(output_path))
        return str(output_path)
