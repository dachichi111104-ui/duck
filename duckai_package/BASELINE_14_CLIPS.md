# Mốc kiểm thử trước khi đổi sang demo 40 giây

Ngày 12/10/2026: 14 video, 36.334 frame, khoảng 782,91 giây video. Bản đó dùng nghi ngờ 30 giây, cảnh báo 60 giây; 0 nghi ngờ và 0 cảnh báo kéo dài. Không được dùng số liệu này như độ chính xác của cấu hình 40 giây.

Các điểm đã quan sát:

- Một con có thể được tạo nhiều box thân, làm số track lớn hơn số cá thể thật.
- Clip đứng riêng dài 81,92 giây chỉ có đoạn đạt rule liên tục dài nhất 6,06 giây; chuỗi track liên tục dài nhất clip là 35,18 giây.
- Trên cùng ID, tỷ số xa tâm có thể tụt dưới ngưỡng trong một frame rồi tăng trở lại, khiến bộ đếm bị reset.
- Có cảnh thiếu đàn đối chứng, quay gần, hoặc nhìn thấy vịt ở nhiều ô chuồng; baseline chưa tách chúng theo ô.
- Sai lệch giữa đồng hồ FPS trung bình và timestamp nguồn có thể tới khoảng 1,063 giây trong bộ video này.

Gói demo 40 giây chưa sửa các vấn đề trên. Chưa train lại weights, chưa có nhãn bệnh được xác minh và chưa có precision/recall hành vi. Các kết quả kiểm tra riêng của gói hiện tại được ghi trong `VERIFICATION.json`.
