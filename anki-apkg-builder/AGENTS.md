# AGENTS.md

Thư mục này build file Anki `.apkg` từ TSV. Đọc `README.md` trước, quy trình đầy đủ nằm ở đó.

- **Quy trình:** khi người dùng đưa file TSV, nhờ thêm từ, build lại hay kiểm tra một file `.apkg`, dùng skill `build-apkg` (`.devin/skills/build-apkg/SKILL.md`). Skill có sẵn `check_tsv.py` (dò lỗi và từ trùng trước khi build) và `verify_apkg.py` (import thử vào collection tạm, kể cả khi Anki đã có các bộ khác).
- **Build:** `python3 build_apkg.py "<tên thư mục trong decks/>"` (chỉ dùng thư viện chuẩn của Python 3, không có dependency).
- **Kiểm tra:** chạy lệnh ở mục "Kiểm tra file trước khi import" trong README (import thử vào collection tạm bằng Python đi kèm Anki). Không bao giờ mở hay ghi collection thật trong `~/Library/Application Support/Anki2`.
- **Không tự build đè** lên file trong `output/` đã được import vào Anki khi người dùng chưa yêu cầu: import file build mới với tuỳ chọn mặc định sẽ xoá audio đã add (xem "Lưu ý quan trọng" trong README).
- **`template/sample.apkg`** là file export thật của người dùng (có lịch sử học). Chỉ đọc, không sửa.
- **Giữ nguyên cách sinh GUID** trong `build_apkg.py` (`guid_for(id note type, Hanzi)`). Đổi cách sinh thì mọi từ đã import sẽ bị coi là từ mới.
- Khi build thêm bộ mới, thêm một dòng vào bảng "Các bộ đã build" trong README.
