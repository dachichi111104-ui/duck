# 🦆 Wild Duck Farm Management System
### Hệ thống quản lý chăn nuôi & thú y vịt trời

Desktop application quản lý chăn nuôi/thú y cho trang trại vịt trời, xây dựng bằng
**Python 3.11+ · PyQt6 · SQLAlchemy · SQLite · YOLOv8 · BoT-SORT**, tích hợp trực tiếp
pipeline Computer Vision hoàn chỉnh phát hiện bệnh/hành vi bất thường ở vịt (vịt lật ngửa, bất động)
cùng cơ chế đồng bộ **Offline-First** 2 chiều với máy chủ Web Cloud (**FastAPI + PostgreSQL Neon DB**).

Đây là đồ án chuyên ngành CNTT — ứng dụng chạy thật, có database thật,
CRUD thật, AI model thật, không phải prototype hay demo tĩnh.

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
- Tạo toàn bộ bảng (16 bảng nghiệp vụ)
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

Mật khẩu được hash bằng bcrypt (passlib), hỗ trợ xác thực trực tiếp qua Web API hoặc offline fallback.

---

## 2. Cơ sở dữ liệu (Database Architecture)

- **Local Storage (Máy trạm Desktop)**: **SQLite** (`data/database/wild_duck_farm.db`).
  - Đảm bảo tính năng **Offline-First**: giúp nông dân/kỹ sư sử dụng ứng dụng mượt mà, ghi nhận dữ liệu tức thì ngay cả khi mất kết nối Internet hoặc máy chủ web bảo trì.
- **Central Storage (Máy chủ Web Cloud)**: **PostgreSQL Cloud (Neon DB)**.
  - Lưu trữ tập trung cho toàn hệ thống, kết nối qua Web REST API (`https://duckcare.onrender.com/api/v1`).
- **Đồng bộ dữ liệu (Sync Engine)**: Tự động đồng bộ 2 chiều (Push & Pull) giữa SQLite local và PostgreSQL Cloud qua `SyncWorker` (chạy ngầm định kỳ 30s) với cơ chế giải quyết xung đột Last-Write-Wins.
- **ORM**: **SQLAlchemy 2.0** (declarative style, type-annotated `Mapped[...]`).
- **16 bảng nghiệp vụ**: `users`, `roles`, `barns`, `flocks`, `flock_events`, `production_records`, `inventory_categories`, `inventory_items`, `inventory_transactions`, `diseases`, `veterinary_records`, `vaccinations`, `ai_analysis_sessions`, `ai_detection_results`, `ai_alerts`, `notifications` (đầy đủ các cột đồng bộ `sync_status`, `last_modified_at`, `remote_id`).

---

## 3. Kiến trúc hệ thống

```text
UI (PyQt6)  →  Service  →  Repository  →  SQLite Local (Phản hồi tức thì)
                                               ↕
                                        SyncService (QThread)
                                               ↕ (REST API Bearer JWT)
                                        FastAPI Backend  →  PostgreSQL Cloud (Neon DB)
```

- **UI** (`app/ui/`): PyQt6 widgets/dialogs. Không bao giờ chạy SQL trực tiếp.
- **Service** (`app/services/`): business logic, validation, orchestration. Đây là nơi duy nhất UI gọi vào.
- **Repository** (`app/repositories/`): truy vấn SQLAlchemy thuần túy, không chứa business logic.
- **Database** (`app/database/`): models, connection/session, seed data.
- **AI Core** (`duckai_package/` & `app/ai/`): Pipeline Computer Vision chạy trực tiếp model YOLOv8n + BoT-SORT + Phân loại hành vi thời gian thực.

```text
wild_duck_farm/
├── main.py
├── requirements.txt
├── .env                  Cấu hình API_BASE_URL, đồng bộ
├── duckai_package/       Gói Computer Vision độc lập & tích hợp
│   ├── best.pt           Weights mô hình YOLOv8n (Run A: classes thân, chân)
│   ├── duck_tracker.py   Bộ theo dõi đa đối tượng BoT-SORT
│   ├── duck_classifier.py Bộ phân loại hành vi bất thường / lật ngửa theo thời gian
│   ├── duck_botsort.yaml Cấu hình tham số BoT-SORT
│   ├── demo.py           Script CLI chạy phân tích video độc lập
│   └── BASELINE_14_CLIPS.md Báo cáo đánh giá hiệu năng trên 14 clip thực tế
├── app/
│   ├── config/          settings.py, constants.py (design system, roles, enums)
│   ├── database/        connection.py, base.py, seed.py, models/
│   ├── repositories/    1 file / aggregate (barn, flock, inventory, ...)
│   ├── services/        business logic (auth, flock, inventory, ai, report, ...)
│   ├── sync/            sync_service.py, api_client.py, tokens.py (Offline-First sync)
│   ├── ai/              real_ai_service.py, ai_service.py, contract.py, overlay.py
│   ├── ui/
│   │   ├── login_window.py, main_window.py
│   │   ├── dashboard/ flocks/ barns/ inventory/ veterinary/
│   │   ├── ai_monitoring/ reports/ users/ settings/
│   │   └── components/  reusable widgets (KpiCard, EmptyState, table helpers)
│   ├── utils/            security, logger, error_handling, validators
│   └── resources/styles/app.qss   (design system stylesheet)
├── data/{database,videos,exports,reports}/
├── logs/                 rotating file log (login/logout/CRUD/errors/sync)
└── tests/                pytest unit tests
```

---

## 4. Tính năng đã triển khai

- ✅ **Việt hóa 100% giao diện**: Toàn bộ nhãn, nút bấm, thông báo, menu, tooltip và hộp thoại được thiết kế chuyên nghiệp bằng tiếng Việt.
- ✅ **Chỉ dùng Vector Icons (QtAwesome)**: Sử dụng chuẩn icon `fa5s...`, loại bỏ hoàn toàn emoji, giao diện hiện đại đồng nhất.
- ✅ **Đăng nhập & Phân quyền**: Đăng nhập JWT qua REST API kết hợp mật khẩu mã hóa bcrypt local; phân quyền vai trò (ADMIN, FARM_MANAGER, VETERINARIAN, STAFF) với sidebar tự động ẩn mục không có quyền.
- ✅ **Đồng bộ Offline-First 2 chiều**: Hoạt động mượt mà khi mất mạng; tự động đồng bộ lên cloud Render / PostgreSQL Neon khi có kết nối lại.
- ✅ **Dashboard**: KPI tổng đàn, sản lượng, cảnh báo + đồ thị tăng trưởng (PyQtGraph) tải trực tiếp từ DB.
- ✅ **CRUD Đàn vịt & Chuồng**: Lọc/tìm kiếm, kiểm tra sức chứa chuồng (capacity validation), xem chi tiết đàn đa tab.
- ✅ **Sản lượng & Kho**: Theo dõi trứng, trọng lượng TB, thức ăn; Nhập/xuất/điều chỉnh kho, cảnh báo tồn kho thấp & hàng sắp hết hạn.
- ✅ **Bệnh án & Tiêm phòng**: Quản lý bệnh án 2 bệnh mục tiêu (Lật ngửa, Tụ huyết trùng), lập lịch tiêm phòng và cảnh báo quá hạn.
- ✅ **Tích hợp Model AI Computer Vision thật**:
  - Tích hợp model **YOLOv8n** (`duckai_package/best.pt`) nhận diện bộ phận vịt (`than`, `chan`).
  - Tích hợp tracker **BoT-SORT** (`duck_botsort.yaml`) gán ID liên tục cho từng cá thể vịt qua các khung hình.
  - Bộ phân loại hành vi (`DuckBehaviorClassifier`) phân tích hình học vị trí chân/thân và cửa sổ thời gian (30s nghi vấn, 40s cảnh báo lật ngửa liên tục).
  - Trực quan hóa Bounding Box (`draw_duck_overlay`): Vẽ khung nhận diện, ID, độ tin cậy và màu viền (Xanh `#2E7D32` = Khỏe mạnh, Đỏ `#D32F2F` = Bất thường/Lật ngửa).
  - 2 hình thức ghi nhận: Phân tích tệp video thực tế và quay trực tiếp từ Webcam.
  - Tab **Giám sát nhiều chuồng (Mô phỏng demo)**: Chạy đồng thời 3 luồng camera chuồng nuôi với bộ lọc 5 khung hình liên tiếp để tránh báo động giả.
  - **Tự động hóa quy trình Cảnh báo ↔ Bệnh án**: Phát hiện AI vịt bệnh tự động gửi cảnh báo Đỏ và mở Bệnh án nháp (gắn nguồn "AI Analysis").
- ✅ **Báo cáo & Export Excel**: Báo cáo theo đàn, sản lượng, kho, thú y, AI và **Báo cáo độ chính xác theo mật độ đàn** (6, 10, 20, 30, 50 vịt/frame), xuất Excel định dạng chuẩn.
- ✅ **Cài đặt & Quản lý người dùng**: Đổi thông tin trang trại, cấu hình theme, CRUD tài khoản.

---

## 5. Chạy Unit Test

```bash
pip install pytest
pytest tests/ -v
```

Test coverage: 25 unit tests kiểm tra toàn diện kết nối database, xác thực, giao dịch kho, tạo đàn + validate sức chứa chuồng, AI contract, Real AI Service integration, và simulated multi-barn monitoring.

---

## 6. Hệ thống Trí tuệ Nhân tạo & Thị giác Máy tính (Computer Vision Pipeline)

### 6.1 Kiến trúc Pipeline Computer Vision

Pipeline AI được xây dựng theo kiến trúc đa tầng (Multi-stage Video Analytics) chuyên biệt cho bài toán phát hiện vịt bị bệnh/hành vi bất thường (triệu chứng lật ngửa):

```text
Video File / Webcam Stream
       ↓
Stage 1: YOLOv8 Object Detection (duckai_package/best.pt)
       ├── Nhận diện bộ phận: Thân vịt ('than'), Chân vịt ('chan')
       └── Trích xuất Bounding Box & Confidence Score
       ↓
Stage 2: Multi-Object Tracking (BoT-SORT)
       ├── Gán Track ID ổn định cho từng cá thể vịt qua các frame
       └── Sử dụng cấu hình tối ưu duckai_package/duck_botsort.yaml
       ↓
Stage 3: Spatial Feature Extraction (Hình học không gian)
       └── Tính toán vị trí tương đối giữa chân và thân:
           Nếu bounding box chân nằm ở phía TRÊN thân vịt → dấu hiệu lật ngửa
       ↓
Stage 4: Temporal Behavior Classifier (Quy tắc thời gian)
       ├── Theo dõi thời gian lật ngửa tích lũy theo từng Track ID
       ├── Ngưỡng nghi vấn: Tích lũy liên tục >= 30 giây (Trạng thái SUSPECT)
       └── Ngưỡng báo động: Tích lũy liên tục >= 40 giây (Trạng thái ALERT)
       ↓
Stage 5: Visualization & UI Feedback
       ├── Vẽ Bounding Box, Track ID, trạng thái (Xanh = Bình thường, Đỏ = Bất thường)
       └── Hiển thị video phân tích trực tiếp trên giao diện PyQt6
       ↓
Stage 6: Automated Veterinary Workflow
       ├── Lưu phiên phân tích vào DB (ai_analysis_sessions)
       ├── Lưu các phát hiện bất thường (ai_detection_results)
       ├── Kích hoạt cảnh báo hệ thống (ai_alerts)
       └── Tự động tạo Bệnh án nháp (veterinary_records) gắn nhãn nguồn "AI Analysis"
```

### 6.2 Mô hình huấn luyện (Model Specs)

- **Kiến trúc mạng**: **YOLOv8n** (Ultralytics nano version, tối ưu tốc độ suy luận thời gian thực trên CPU và GPU).
- **Trọng số weights**: `duckai_package/best.pt` (huấn luyện từ Run A).
- **Tập nhãn (2 classes)**:
  - Class 0: `than` (Thân vịt)
  - Class 1: `chan` (Chân vịt)
- **Tập tham số huấn luyện**: Kích thước ảnh 640x640, 100 epochs, batch size 32, optimizer AdamW, augmentations phù hợp môi trường chuồng trại thực tế.
- **Cơ chế suy luận tích hợp**: `RealAIService` (tại `app/ai/real_ai_service.py`) nạp trực tiếp model từ `duckai_package` và tương thích 100% với AI contract của hệ thống.

### 6.3 Chạy thử nghiệm độc lập (CLI Demo)

Bạn có thể chạy thử pipeline AI độc lập mà không cần khởi động toàn bộ giao diện:

```bash
# Phân tích một clip và xuất video kết quả có vẽ bounding box:
python duckai_package/demo.py --video data/videos/sample_duck.mp4 --output data/videos/output_tracked.mp4

# Xem chi tiết đánh giá độ chính xác trên 14 clip mẫu:
# Tham khảo tệp duckai_package/BASELINE_14_CLIPS.md
```

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
**AI**: tích hợp model YOLOv8n + BoT-SORT thật (duckai_package/best.pt), upload video phân tích thật, webcam recorder, Bounding Box overlay xanh/đỏ, 3-barn simulation, lưu session DB & tự động mở bệnh án ✅
**Report**: filter + Export Excel ✅
**Quality**: không hard-code dữ liệu, unit test pytest 25/25 passed ✅
