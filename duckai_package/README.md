# Demo tiến độ Duck AI

Phiên bản `0.2.0-demo40` ngày 21/10/2026. Gói mã nguồn và weights để thử nghiệm trên Windows, không phải file EXE và không phải bản hoàn thiện.

## Chạy cho người mới

1. Giải nén ZIP ra một thư mục, ví dụ `C:\DuckAI_Demo`. Không chạy trực tiếp bên trong ZIP.
2. Máy cần Python **3.11 bản 64-bit**, có Python Launcher và Tkinter. Nếu đã có Python 3.11, có thể bỏ qua cài Python.
3. Trong thư mục vừa giải nén, nhấp đúp **SETUP.cmd**. Cần mạng để tải thư viện; lần đầu có thể lâu và cần vài GB trống. Không cần quyền Administrator và không cần Activate.ps1.
4. Sau khi cài xong, nhấp đúp **RUN_DEMO.cmd**, chọn video vịt trong cửa sổ hiện ra.
5. Đợi cửa sổ báo `Finished`. Mở thư mục **outputs**, mở thư mục lượt chạy mới nhất, rồi mở **behavior_preview.mp4**.

Mỗi lần chạy có thư mục riêng, không ghi đè lượt trước. Pipeline xử lý offline rồi mới xuất preview; chưa có giao diện phát hiện trực tiếp hoặc cam kết realtime. Preview không giữ âm thanh nguồn.

Để xem lại chức năng cũ, nhấp đúp **RUN_LAT_NGUA.cmd**. Video kết quả của chế độ đó là **lat_ngua_preview.mp4**. Hai chế độ được chạy riêng, chưa tích hợp trong cùng một lượt phát hiện.

Nếu cài hoặc chạy lỗi, giữ cửa sổ lại và gửi ảnh hoặc phần thông báo lỗi. Không cần tự đọc các CSV.

## Bản này có những gì

- **Hành vi mới**: weights Run A, BoT-SORT, đo khoảng cách đàn, tốc độ tương đối, bù camera gần đúng và rule theo thời gian.
- Ngưỡng **nghi ngờ 30 giây, cảnh báo 40 giây liên tục**, chỉ áp dụng chế độ hành vi mới. Xám là thiếu dữ liệu; xanh là chưa đạt điều kiện hiện tại; vàng là quan sát; cam là nghi ngờ; đỏ là cảnh báo hành vi.
- **Lật ngửa cũ**: giữ mã module và weights v1-5 của ZIP demo cũ, chạy bằng một chế độ riêng. Không thay thời gian cửa sổ lật ngửa thành 40 giây.
- Weights không được train lại. Thay đổi mới là cấu hình cảnh báo hành vi 40 giây và cách đóng gói để chạy trên máy khác.

## Giới hạn cần nói rõ khi demo

- Chưa sửa box trùng, mất/đổi ID, gộp track từ ô chuồng bên cạnh hoặc reset do dao động một frame.
- Một track không nhất thiết là một con thật. Cần đủ đàn nhìn thấy và đúng đàn mục tiêu mới có ý nghĩa đối chứng.
- Mất quan sát hoặc đổi ID vẫn ngắt bộ đếm. Giảm 60 xuống 40 giây không bảo đảm video thật sẽ xuất hiện box đỏ.
- Dùng FPS trung bình để đo thời gian; video FPS biến đổi có sai lệch so với timestamp nguồn. Chưa hiệu chuẩn mặt sàn.
- Chưa có độ chính xác hành vi được xác nhận bằng nhãn. Chưa nhận diện riêng gãy chân, liệt, bị tật hoặc bệnh truyền nhiễm.
- Kết quả 14 video trong báo cáo kèm theo là **baseline 60 giây**, không phải kết quả chạy lại toàn bộ ở ngưỡng 40 giây.
- Kiểm tra tổng hợp mốc 40 giây chỉ kiểm tra logic phần mềm, không thay thế ca vịt thật có nhãn. Xem `VERIFICATION.json` để biết kiểm thử nào thực sự đã chạy.

## Dành cho người phát triển

Ở PowerShell trong thư mục gói:

```powershell
& ".\.venv\Scripts\python.exe" ".\demo.py" --video "C:\Videos\vit.mp4"
& ".\.venv\Scripts\python.exe" ".\demo.py" --mode lat-ngua --video "C:\Videos\vit.mp4"
& ".\.venv\Scripts\python.exe" -B -m unittest discover -s tests -v
```

Hai weights có tên khác nhau để không dùng nhầm: `models/behavior_runA.pt` và `models/lat_ngua_v1_5.pt`. Cấu hình hiện tại ở `configs/duck_behavior_rules.json`; cấu hình tham chiếu 60 giây ở `configs/duck_behavior_rules_baseline60.json`. Mã phụ trợ ở `tools/`; module lật ngửa cũ ở `legacy/`.

`SETUP.cmd` chọn PyTorch CPU để không phụ thuộc CUDA trên máy nhận; chạy CPU có thể chậm. Môi trường đã thử trước đó dùng Python 3.11 và PyTorch CUDA. Không cam kết cài mới CPU đã được thử nếu `VERIFICATION.json` ghi chưa thử. Chỉ dùng weights tin cậy vì checkpoint PyTorch có thể chứa mã thực thi.

Gói không mang theo `.venv`, IDE, dataset, video riêng tư hoặc kết quả CSV lớn. Các thư viện phụ thuộc có giấy phép riêng; gói không phân phối các thư viện đã cài sẵn.
