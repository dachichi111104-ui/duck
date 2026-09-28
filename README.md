# 🦆 Wild Duck Farm Management System
### Hệ thống quản lý chăn nuôi & thú y vịt trời

Desktop application quản lý chăn nuôi/thú y cho trang trại vịt trời, xây dựng bằng
**Python 3.11+ · PyQt6 · SQLAlchemy · SQLite**, với kiến trúc sẵn sàng tích hợp
pipeline AI (YOLOv8 + ByteTrack + Behavior Classifier) từ môn Thị giác máy tính.

Đây là đồ án chuyên ngành CNTT — ứng dụng chạy thật, có database thật,
CRUD thật, không phải prototype hay demo tĩnh.

---

## 1. Cài đặt (Windows / PyCharm)

### Bước 1 — Clone / giải nén project

```bash
cd wild_duck_farm
```

### Bước 2 — Tạo virtual environment

Windows (cmd/PowerShell):
```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 3 — Cài thư viện

```bash
pip install -r requirements.txt
```

> Nếu bạn dùng PyCharm: File → Settings → Project → Python Interpreter →
> chọn `.venv` vừa tạo, sau đó PyCharm sẽ tự nhận `requirements.txt` và
> gợi ý cài đặt.

### Bước 4 — Chạy ứng dụng

```bash
python main.py
```

Lần chạy đầu tiên, hệ thống sẽ **tự động**:
- Tạo file database SQLite tại `data/database/wild_duck_farm.db`
- Tạo toàn bộ bảng (16 bảng)
- Seed dữ liệu mẫu: 3 chuồng, 3 đàn, vật tư kho, bệnh án, lịch tiêm, sản
  lượng 14 ngày — để Dashboard không bị trống ngay lần đầu chạy.

Không cần tự tạo database bằng tay.

### Bước 5 — Đăng nhập

| Tài khoản | Mật khẩu    | Vai trò              |
|-----------|-------------|-----------------------|
| admin     | admin123    | Quản trị viên (ADMIN) |
| manager   | manager123  | Quản lý trang trại    |
| vet       | vet123      | Bác sĩ thú y          |
| staff     | staff123    | Nhân viên             |

Mật khẩu được hash bằng bcrypt (passlib), không lưu plain-text.

---

## 2. Cơ sở dữ liệu (Database Architecture)

- **Local Storage (Máy trạm Desktop)**: **SQLite** (`data/database/wild_duck_farm.db`).
  - Đảm bảo tính năng **Offline-First**: giúp nông dân sử dụng ứng dụng mượt mà, ghi nhận dữ liệu tức thì ngay cả khi mất kết nối Internet hoặc máy chủ web bảo trì.
- **Central Storage (Máy chủ Web Cloud)**: **PostgreSQL Cloud (Neon DB)**.
  - Lưu trữ tập trung cho toàn hệ thống, kết nối qua Web REST API (`API_BASE_URL`).
- **Đồng bộ dữ liệu (Sync Engine)**: Tự động đồng bộ 2 chiều (Push & Pull) giữa SQLite local và PostgreSQL Cloud qua `SyncService` chạy ngầm.
- **ORM**: **SQLAlchemy 2.0** (declarative style, type-annotated `Mapped[...]`).
- **16 bảng nghiệp vụ**: `users`, `roles`, `barns`, `flocks`, `flock_events`, `production_records`, `inventory_categories`, `inventory_items`, `inventory_transactions`, `diseases`, `veterinary_records`, `vaccinations`, `ai_analysis_sessions`, `ai_detection_results`, `ai_alerts`, `notifications` (đã bổ sung các cột đồng bộ `sync_status`, `last_modified_at`, `remote_id`).

---

## 3. Kiến trúc hệ thống

```text
UI (PyQt6)  →  Service  →  Repository  →  SQLite Local (Phản hồi tức thì)
                                              ↕
                                       SyncService (QThread)
                                              ↕ (REST API)
                                       FastAPI Backend  →  PostgreSQL Cloud (Neon DB)
```

- **UI** (`app/ui/`): PyQt6 widgets/dialogs. Không bao giờ chạy SQL trực tiếp.
- **Service** (`app/services/`): business logic, validation, orchestration.
  Đây là nơi duy nhất UI gọi vào.
- **Repository** (`app/repositories/`): truy vấn SQLAlchemy thuần túy, không
  chứa business logic.
- **Database** (`app/database/`): models, connection/session, seed data.
- **AI** (`app/ai/`): interface + placeholder cho pipeline Computer Vision
  (xem mục 6).

```text
wild_duck_farm/
├── main.py
├── requirements.txt
├── app/
│   ├── config/          settings.py, constants.py (design system, roles, enums)
│   ├── database/        connection.py, base.py, seed.py, models/
│   ├── repositories/    1 file / aggregate (barn, flock, inventory, ...)
│   ├── services/        business logic (auth, flock, inventory, ai, report, ...)
│   ├── ai/               AI Service interface + placeholders (seam for CV pipeline)
│   ├── ui/
│   │   ├── login_window.py, main_window.py
│   │   ├── dashboard/ flocks/ barns/ inventory/ veterinary/
│   │   ├── ai_monitoring/ reports/ users/ settings/
│   │   └── components/  reusable widgets (KpiCard, EmptyState, table helpers)
│   ├── utils/            security, logger, error_handling, validators
│   └── resources/styles/app.qss   (design system stylesheet)
├── data/{database,videos,exports,reports}/
├── logs/                 rotating file log (login/logout/CRUD/errors/exports)
└── tests/                pytest unit tests
```

---

## 4. Tính năng đã triển khai

- ✅ **Việt hóa 100% giao diện**: Toàn bộ nhãn, nút bấm, thông báo, menu, tooltip và hộp thoại được chuyển sang tiếng Việt phù hợp với người quản lý nông trại.
- ✅ **Chỉ dùng Vector Icons (QtAwesome)**: Loại bỏ hoàn toàn emoji, sử dụng bộ icon chuẩn font-awesome `fa5s...` đảm bảo thẩm mỹ chuyên nghiệp.
- ✅ **Đăng nhập / Phân quyền**: Đăng nhập mật khẩu mã hóa bcrypt, phân quyền vai trò (ADMIN, FARM_MANAGER, VETERINARIAN, STAFF) với sidebar tự động ẩn mục không có quyền.
- ✅ **Dashboard**: KPI tổng vịt, đàn, sản lượng, cảnh báo + đồ thị tăng trưởng (PyQtGraph) load từ SQLite.
- ✅ **CRUD Đàn vịt & Chuồng**: Lọc/tìm kiếm, kiểm tra sức chứa chuồng (capacity validation), xem chi tiết đàn đa tab.
- ✅ **Sản lượng & Kho**: Theo dõi trứng, trọng lượng TB, thức ăn; Nhập/xuất/điều chỉnh kho, cảnh báo tồn kho thấp & hàng sắp hết hạn.
- ✅ **Bệnh án & Tiêm phòng**: Quản lý bệnh án 2 bệnh mục tiêu (Lật ngửa, Tụ huyết trùng), lập lịch tiêm phòng và cảnh báo quá hạn.
- ✅ **Cảnh báo & Notification Center**: Tổng hợp cảnh báo hệ thống (Đỏ/Cam/Xanh), hỗ trợ lọc theo mức độ.
- ✅ **Mối nối AI & Trực quan Bounding Box**:
  - Chuẩn hóa AI Contract (`DuckTrack`, `AIDetection`, `AIAlertResult`, `AIAnalysisResult`).
  - Trực quan hóa Bounding Box (`draw_duck_overlay`): Vẽ khung nhật nhận diện, ID, độ tin cậy và màu viền (Xanh `#2E7D32` = Khỏe mạnh, Đỏ `#D32F2F` = Có bệnh) trực tiếp trên video.
  - 2 hình thức ghi nhận: Quay video trực tiếp bằng Webcam (`WebcamRecorderDialog`) + Tải tệp video từ máy.
  - Tab **Giám sát nhiều chuồng (Mô phỏng demo)**: Chạy đồng thời 3 luồng camera chuồng nuôi với bộ lọc 5 khung hình liên tiếp để tránh báo động giả.
  - **Tự động hóa quy trình Cảnh báo ↔ Bệnh án**: Phát hiện AI vịt bệnh tự động gửi cảnh báo Đỏ và mở Bệnh án nháp (gắn nguồn "AI Analysis").
- ✅ **Báo cáo & Export Excel**: Báo cáo theo đàn, sản lượng, kho, thú y, AI và **Báo cáo độ chính xác theo mật độ đàn** (6, 10, 20, 30, 50 vịt/frame), xuất Excel định dạng đẹp.
- ✅ **Cài đặt & Quản lý người dùng**: Đổi thông tin trang trại, cấu hình theme, CRUD tài khoản.

---

## 5. Chạy Unit Test

```bash
pip install pytest
pytest tests/ -v
```

Test coverage: kết nối database, đăng nhập/xác thực, giao dịch kho (nhập/xuất/tồn kho thấp), tạo đàn + validate sức chứa chuồng, AI contract & simulated analysis.

---

## 6. Tích hợp AI trong tương lai (Future AI Integration Guide)

### 6.1 Trạng thái kiến trúc (AI Seam)

Hệ thống được thiết kế theo kiến trúc Seam Pattern sẵn sàng cắm model thật từ môn **Thị giác máy tính** mà **không cần thay đổi UI, Service hay Database Schema**.

```text
Video / Webcam Input
 ↓
YOLOv8 Detection          (app/ai/detection_placeholder.py -> RealAIService)
 ↓
ByteTrack / DeepSORT        (app/ai/tracking_placeholder.py -> RealAIService)
 ↓
Feature Extractor           (app/ai/feature_extractor.py)
 ↓
Behavior Classifier         (app/ai/classifier_placeholder.py)
 ↓
AI Contract Result         (DuckTrack, AIDetection, AIAlertResult, AIAnalysisResult)
 ↓
Overlay Drawer (OpenCV)    (draw_duck_overlay -> QImage -> UI Label)
 ↓
Auto Workflow              (AIAnalysisService -> Database + Alert + Draft Vet Record)
```

### 6.2 Hướng dẫn cắm weights YOLOv8 + ByteTrack thật

Khi có weights huấn luyện thật (`.pt` file):

1. **Thêm thư viện**: Thêm `ultralytics`, `torch`, `lap` vào `requirements.txt` và chạy `pip install -r requirements.txt`.
2. **Triển khai `RealAIService`**: Mở file `app/ai/ai_service.py` và hoàn thiện lớp `RealAIService(AIServiceBase)`:
   ```python
   from ultralytics import YOLO

   class RealAIService(AIServiceBase):
       def __init__(self, model_path: str = "models/duck_yolov8.pt"):
           self.model = YOLO(model_path)

       def analyze_video(self, video_path: str) -> AIAnalysisResult:
           results = self.model.track(source=video_path, tracker="bytetrack.yaml", stream=True)
           # Chuyển đổi kết quả của Ultralytics sang danh sách DuckTrack, AIDetection, AIAlertResult
           # ...
           return AIAnalysisResult(...)
   ```
3. **Kích hoạt Service thật**: Đổi 1 dòng trong `app/ai/ai_service.py`:
   ```python
   def get_ai_service() -> AIServiceBase:
       return RealAIService()  # Thay cho PlaceholderAIService()
   ```
4. **Không cần sửa đổi UI hay DB**: Kết quả `AIAnalysisResult` được `AIAnalysisService` tự động lưu vào database (`ai_analysis_sessions`, `ai_detection_results`, `ai_alerts`), hiển thị Bounding Box overlay và kích hoạt quy trình thú y tự động.

---

## 7. Đồng bộ dữ liệu với Web (Offline-First Sync)

### 7.1 Kiến trúc Đồng bộ Offline-First

Ứng dụng Desktop sử dụng kiến trúc **Offline-First**, hoạt động hoàn toàn độc lập với cơ sở dữ liệu local SQLite, đồng thời tự động đồng bộ 2 chiều với Backend Web API (FastAPI + Neon PostgreSQL Cloud).

```text
UI (PyQt6)  →  Service  →  Repository  →  SQLite Local (NGAY LẬP TỨC - status=PENDING)
                                              ↓ (quét định kỳ 30s)
                                       SyncService (QThread)
                                              ↓ (HTTP Authorization: Bearer JWT)
                                       REST API (FastAPI /api/v1)
                                              ↓
                                       PostgreSQL Cloud (Neon DB)
```

### 7.2 Cấu hình API Backend

File cấu hình `.env` tại thư mục gốc:

```env
API_BASE_URL=http://localhost:8000/api/v1
SYNC_ENABLED=true
SYNC_INTERVAL_SECONDS=30
```

- Để thử nghiệm trên máy cục bộ: trỏ `API_BASE_URL=http://localhost:8000/api/v1`.
- Để trỏ tới máy chủ cloud (Render/AWS): trỏ `API_BASE_URL=https://duckcare-api.onrender.com/api/v1`.

Khi ứng dụng khởi động, log sẽ hiển thị rõ ràng:
- `Đã kết nối API tại http://localhost:8000/api/v1, database backend: PostgreSQL Cloud @ Neon Postgres`
- Hoặc `Không kết nối được API, chạy chế độ offline hoàn toàn` nếu không có mạng.

### 7.3 Hướng dẫn Demo kịch bản Offline-First

1. **Thao tác khi mất mạng (Offline)**:
   - Tắt kết nối internet hoặc tắt backend API.
   - Mở ứng dụng Desktop và đăng nhập (sử dụng phiên đã lưu local).
   - Thực hiện thêm mới / chỉnh sửa Đàn vịt, Chuồng nuôi, hoặc Giao dịch kho.
   - Quan sát thanh trạng thái dưới cùng: hiển thị icon Cam `X thay đổi chờ đồng bộ (mất kết nối)`. Giao diện phản hồi ngay lập tức, không bị đơ giật.
2. **Tự động đồng bộ khi có mạng lại (Online)**:
   - Bật lại internet hoặc khởi động backend API server.
   - Quan sát biểu tượng thanh trạng thái tự động chuyển sang Xoay tròn `Đang đồng bộ...` và chuyển sang Xanh `Đã đồng bộ với server`.
3. **Kiểm tra chéo dữ liệu trên Web App**:
   - Truy cập giao diện Web hoặc kiểm tra database PostgreSQL cloud — dữ liệu vừa tạo ở máy Desktop đã tự động xuất hiện với đầy đủ thông tin.

---

## 8. Ghi chú kỹ thuật

- Toàn bộ icon sử dụng bộ icon chuẩn font-awesome `fa5s...` qua thư viện `qtawesome`.
- Màu sắc theo design system: Primary `#2E7D32`, Secondary `#F4A62D`, Background `#F5F7F3`, Danger `#D32F2F` — định nghĩa tại `app/resources/styles/app.qss` và `app/config/constants.py::Colors`.
- Responsive: sử dụng `QVBoxLayout`/`QHBoxLayout`/`QGridLayout`/`QScrollArea`, tối ưu hiển thị cho độ phân giải từ 1366×768 tới 1920×1080.

---

## 9. Checklist hoàn thành (spec section 52)

**Database**: tạo tự động ✅ · migration tự động ✅ · seed ✅ · CRUD ✅
**Auth**: login JWT API shared với web ✅ · offline token local fallback ✅ · role-based menu ✅
**Offline-First Sync**: PENDING / SYNCED / CONFLICT ✅ · Last Write Wins + dialog xử lý xung đột ✅ · SyncStatusWidget thanh trạng thái ✅
**Dashboard**: KPI/Chart/Alert từ DB, không hard-code ✅
**Flock**: CRUD + search/filter ✅
**Inventory**: import/export/adjustment + low-stock alert ✅
**Veterinary**: disease + record + vaccination reminder ✅
**AI**: upload video, webcam recorder, Bounding Box overlay, 3-barn simulation, lưu session ✅
**Report**: filter + Export Excel ✅
**Quality**: không hard-code dữ liệu, unit test pytest 25/25 passed ✅
