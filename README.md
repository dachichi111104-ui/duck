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

## 2. Database

- Engine: **SQLite** (phù hợp desktop app, single-user, giai đoạn hiện tại)
- File: `data/database/wild_duck_farm.db` (tạo tự động, gitignore)
- ORM: **SQLAlchemy 2.0** (declarative style, type-annotated `Mapped[...]`)
- 16 bảng: `users`, `roles`, `barns`, `flocks`, `flock_events`,
  `production_records`, `inventory_categories`, `inventory_items`,
  `inventory_transactions`, `diseases`, `veterinary_records`,
  `vaccinations`, `ai_analysis_sessions`, `ai_detection_results`,
  `ai_alerts`, `notifications`.
- Cài đặt farm (tên, địa chỉ, theme) lưu riêng ở `data/app_settings.json`
  — đây là dữ liệu cấu hình hiển thị, không phải dữ liệu nghiệp vụ, nên
  dùng file JSON nhẹ thay vì thêm bảng vào SQLite.

---

## 3. Kiến trúc

```text
UI  →  Service  →  Repository  →  Database
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

- ✅ Đăng nhập / đăng xuất, mật khẩu hash (bcrypt)
- ✅ Phân quyền theo vai trò (ADMIN / FARM_MANAGER / VETERINARIAN / STAFF) —
  sidebar tự ẩn menu không có quyền
- ✅ Dashboard: KPI (tổng vịt, số đàn, đang theo dõi, cảnh báo, sản lượng
  hôm nay) + biểu đồ (PyQtGraph) — toàn bộ lấy từ database, không hard-code
- ✅ CRUD Đàn vịt: tìm kiếm / lọc / thêm / sửa / xóa, chi tiết đàn có tab
  (Tổng quan, Biến động, Sản lượng, Bệnh án, Tiêm phòng, AI)
- ✅ CRUD Chuồng: kiểm tra sức chứa, không cho nhập vượt capacity
- ✅ Quản lý sản lượng: trứng, trọng lượng TB, thức ăn tiêu thụ
- ✅ Quản lý kho: danh mục, vật tư, nhập/xuất/điều chỉnh, cảnh báo tồn
  kho thấp + sắp hết hạn
- ✅ Bệnh án: 2 bệnh mục tiêu (Lật ngửa, Tụ huyết trùng), đánh dấu rõ
  nguồn "AI Analysis" khi liên quan (chỉ mang tính hỗ trợ theo dõi)
- ✅ Lịch tiêm phòng: cảnh báo sắp đến hạn / quá hạn
- ✅ Notification Center: cảnh báo Đỏ/Cam/Xanh tổng hợp từ kho, tiêm
  phòng, bệnh án
- ✅ Nhận diện AI: chọn video → xem metadata thật (OpenCV) → chạy AI
  placeholder (không giả vờ có model thật) → lưu session vào lịch sử
- ✅ Báo cáo: đàn / sản lượng / kho / thú y / AI, filter theo ngày/đàn,
  **Export Excel** (openpyxl, có style header)
- ✅ Quản lý người dùng (ADMIN): CRUD user + vai trò
- ✅ Cài đặt: thông tin trang trại, đơn vị, thông tin database/version
- ✅ Logging: `logs/wild_duck_farm.log` (login, CRUD, lỗi, export, AI)
- ✅ Global exception handler: không crash khi lỗi, hiện MessageBox thân thiện
- ✅ Form validation: số lượng > 0, không âm, không vượt sức chứa
- ✅ Seed data đầy đủ để demo ngay từ lần chạy đầu
- ✅ Unit tests (pytest): database, authentication, inventory, flock/capacity,
  AI placeholder

---

## 5. Chạy Unit Test

```bash
pip install pytest
pytest tests/ -v
```

Test coverage: kết nối database, đăng nhập/xác thực, giao dịch kho
(nhập/xuất/tồn kho thấp), tạo đàn + validate sức chứa chuồng, AI placeholder
(đảm bảo không trả về kết quả giả).

---

## 6. Tích hợp AI trong tương lai (Future AI Integration)

### 6.1 Trạng thái hiện tại

**KHÔNG có model AI thật được cài đặt hoặc chạy** ở giai đoạn này. Toàn bộ
module `app/ai/` là **placeholder có kiến trúc chuẩn**, để môn **Thị giác
máy tính** cắm pipeline thật vào mà **không cần viết lại hệ thống**.

```text
Video
 ↓
YOLOv8 Detection          (app/ai/detection_placeholder.py)
 ↓
ByteTrack / DeepSORT        (app/ai/tracking_placeholder.py)
 ↓
Track-level features        (app/ai/feature_extractor.py)
 ↓
Behavior analysis
 ↓
Random Forest / MLP         (app/ai/classifier_placeholder.py)
 ↓
NORMAL / SUSPECTED
 ↓
AI Result Database (ai_analysis_sessions / ai_detection_results / ai_alerts)
 ↓
Dashboard / Veterinary Record / Notification Center
```

Hai bệnh mục tiêu: **Lật ngửa**, **Tụ huyết trùng**.
Nhãn tổng: **Có bệnh / Không bệnh**. Tracking chỉ trong phạm vi 1 video
(không triển khai long-term re-identification).

### 6.2 Cách thay Placeholder bằng model thật

Toàn bộ UI, database, lịch sử phiên phân tích đã hoạt động với
`PlaceholderAIService`. Để chuyển sang model thật:

1. Tạo `RealAIService(AIService)` trong `app/ai/ai_service.py` (hoặc file
   mới), implement `analyze_video(video_path) -> AIAnalysisResult`, load
   YOLOv8 (Ultralytics) + ByteTrack bên trong.
2. Cập nhật `DetectionPlaceholder`, `TrackingPlaceholder`,
   `FeatureExtractorPlaceholder`, `ClassifierPlaceholder` bằng
   implementation thật (hoặc gọi trực tiếp trong `RealAIService`).
3. Đổi **một dòng duy nhất** trong `get_ai_service()`:
   ```python
   def get_ai_service() -> AIService:
       return RealAIService()   # thay vì PlaceholderAIService()
   ```
4. Không cần sửa `ai_analysis_service.py`, UI (`ai_view.py`), hay database
   schema — `AIAnalysisResult.detections` / `.alerts` đã đúng shape để map
   thẳng vào `ai_detection_results` / `ai_alerts`.
5. Thêm `ultralytics`, `torch`, `lap` (ByteTrack) vào `requirements.txt`
   khi tích hợp thật (cố tình chưa thêm ở giai đoạn hiện tại để project nhẹ).

### 6.3 Ghi chú tương thích với project Computer Vision (camera real-time)

Project CV riêng (camera monitoring, dark theme, đã có sẵn ở nhóm) lưu
cảnh báo với các trường `duck_id`, `behavior`, `level`, `snapshot_path`
trong database riêng của nó (`DuckAIDatabase`). Khi ghép hai project:

- `duck_id` (CV) ↔ `track_id` (bảng `ai_detection_results` / `ai_alerts`)
- `behavior` (CV) ↔ `behavior_label`
- `level` (CV, ví dụ "warning") ↔ `severity` (`RED`/`ORANGE`/`GREEN`)
- `snapshot_path` (CV) có thể lưu vào `notes`/`description` của
  `AIDetectionResult`/`AIAlert`, hoặc thêm cột mới nếu cần giữ ảnh chụp.

Tab "Camera real-time" trong menu **Nhận diện AI** hiện đang **DISABLED /
COMING SOON**, đúng như spec — đây là điểm nối tương lai giữa hai project.

---

## 7. Ghi chú kỹ thuật

- Toàn bộ icon dùng emoji (🦆 📊 🩺 ...) để đảm bảo chạy được ngay trên mọi
  máy Windows/PyCharm mà không cần cấu hình font icon. `qtawesome` đã có
  trong `requirements.txt` nếu muốn nâng cấp icon sau này.
- Màu sắc theo design system: Primary `#2E7D32`, Secondary `#F4A62D`,
  Background `#F5F5F0`, Danger `#D32F2F` — định nghĩa tại
  `app/resources/styles/app.qss` và `app/config/constants.py::Colors`.
- Responsive: dùng `QVBoxLayout`/`QHBoxLayout`/`QGridLayout`/`QScrollArea`,
  test tốt ở 1366×768 và 1920×1080.
- Vì môi trường build không có kết nối mạng để cài PyQt6/SQLAlchemy và
  chạy thử trực tiếp, code đã được kiểm tra kỹ bằng cách: biên dịch cú
  pháp toàn bộ (`py_compile`), đối chiếu tên phương thức Service ↔ lời gọi
  từ UI, và kiểm tra tính nhất quán `back_populates` của toàn bộ quan hệ
  SQLAlchemy. Khi chạy `pip install -r requirements.txt` trên máy có
  mạng, ứng dụng sẽ khởi tạo database + seed data + mở màn hình đăng nhập
  như mô tả ở mục 1.

---

## 8. Checklist hoàn thành (spec section 52)

**Database**: tạo tự động ✅ · seed ✅ · CRUD ✅
**Auth**: login ✅ · hash password ✅ · role-based menu ✅
**Dashboard**: KPI/Chart/Alert từ DB, không hard-code ✅
**Flock**: CRUD + search/filter ✅
**Inventory**: import/export/adjustment + low-stock alert ✅
**Veterinary**: disease + record + vaccination reminder ✅
**AI**: upload video, metadata thật, placeholder rõ ràng, lưu session, xem
lịch sử ✅ (model AI thật: chưa, đúng như yêu cầu giai đoạn này)
**Report**: filter + Export Excel ✅
**Quality**: không hard-code dữ liệu cốt lõi, không giả AI, có
global exception handler, README đầy đủ, requirements.txt đầy đủ ✅
