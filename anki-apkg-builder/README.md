# anki-apkg-builder

Tạo file `.apkg` cho Anki từ các file TSV từ vựng tiếng Trung, dùng đúng note type `SpoonFed++` đang có trong Anki.
File tạo ra **không có audio**; voice được add sau trong Anki bằng HyperTTS.

## Cấu trúc thư mục

```
anki-apkg-builder/
├── README.md
├── AGENTS.md              ghi chú ngắn cho AI agent làm việc trong thư mục này
├── .devin/skills/build-apkg/   skill cho AI agent: quy trình từ TSV tới .apkg, kèm script kiểm tra TSV và import thử
├── build_apkg.py          script build (Python 3 có sẵn trên macOS, không cần cài thêm gì)
├── template/
│   └── sample.apkg        khuôn: file export từ Anki, script lấy note type SpoonFed++ từ đây
├── decks/
│   └── 越南美食/           mỗi thư mục con = 1 bộ thẻ, tên thư mục = tên deck cha
│       ├── 1. 粉面.tsv     mỗi file TSV = 1 deck con, tên file = tên deck con
│       └── …
└── output/
    └── 越南美食.apkg       file kết quả để import vào Anki
```

## Làm một bộ thẻ mới

1. Tạo thư mục `decks/<Tên deck>/`.
2. Bỏ các file `.tsv` vào đó, đặt tên kiểu `1. xxx.tsv`, `2. yyy.tsv`. Số ở đầu quyết định thứ tự; tên file (bỏ `.tsv`) thành tên deck con.
3. Mở Terminal tại thư mục này và chạy:

   ```bash
   python3 build_apkg.py "<Tên deck>"
   ```

4. Mở `output/<Tên deck>.apkg` để import vào Anki.
5. Add voice trong Anki bằng HyperTTS: `Hanzi` → `Audio` (đọc từ), `Example` → `SP` (đọc câu).

Muốn bộ thẻ nằm sẵn dưới một deck khác thì thêm `--deck`:

```bash
python3 build_apkg.py 越南美食 --deck "B. 读书::越南美食"
```

## Định dạng file TSV

- UTF-8, các cột cách nhau bằng tab, dòng đầu là header đúng như bảng dưới (sai header là script báo lỗi).
- Mỗi dòng đủ 7 cột, cột `Vocabulary` không được trống. Dòng trống bị bỏ qua.
- Nội dung được lấy nguyên văn (không hiểu HTML, dấu `"` là ký tự thường).
- Trong một bộ, `Vocabulary` không được trùng nhau giữa các file (script báo lỗi và chỉ ra file bị trùng).

| Cột trong TSV | Field trong note type `SpoonFed++` |
|---|---|
| `Vocabulary` | `Hanzi` |
| `Pronunciation` | `Pinyin` |
| `English` | `English` |
| `Vietnamese` | `Vietnamese` |
| `Example` | `Example` |
| `Sentence Pinyin` | `Sentence Pinyin` |
| `Sentence Translation` | `Sentence Translation` |
| (không có) | `Audio`, `SP`: để trống |

## Kết quả sau khi import

- Deck: `<Tên deck>::<tên file TSV>`, mỗi dòng TSV là 1 note và 1 thẻ.
- Tất cả là thẻ mới, thứ tự học theo thứ tự file rồi thứ tự dòng.
- Note type giữ nguyên id của `SpoonFed++`, nên Anki dùng lại note type sẵn có chứ không tạo bản trùng.

## Lưu ý quan trọng

**1. Build lại rồi import lại có thể xoá voice đã add.**
Mỗi từ được nhận diện bằng `Hanzi`. File build mới luôn "mới hơn" note trong Anki, nên với tuỳ chọn import mặc định (*Update notes: If newer*) Anki ghi đè toàn bộ note của bộ đó và `Audio`/`SP` trở về trống. Đã thử: 177 note bị ghi đè, mất hết audio.

| Muốn làm gì | Cách làm |
|---|---|
| Thêm từ mới vào bộ đã import | Thêm dòng vào TSV, build lại, khi import chọn **Update notes: Never**. Chỉ từ mới được thêm, note cũ và audio giữ nguyên (đã thử). |
| Sửa nội dung một từ đã import | Sửa thẳng trong Anki, rồi sửa TSV cho khớp. |
| Sửa `Hanzi` trong TSV | Anki coi đó là từ mới; note cũ vẫn còn trong Anki, phải tự xoá. |
| Import lại đúng file cũ | Không sao, Anki bỏ qua hết (0 note mới). |

**2. Cùng một `Hanzi` ở hai bộ khác nhau là cùng một note.**
Nếu từ đã có trong Anki từ một bộ build trước, import bộ sau sẽ không thêm thẻ mới cho từ đó.

**3. Không xoá hay đổi tên `template/sample.apkg`.**
Script lấy note type, cấu hình và cấu trúc database từ file này. Nếu sửa note type `SpoonFed++` trong Anki (thêm/bớt field, đổi template) thì nên thay khuôn: export một deck chỉ dùng note type đó, tick *Support older Anki versions*, lưu đè lên `template/sample.apkg`. Khuôn lệch với note type trong Anki thì lúc import có thể bị báo conflict.

**4. `Hanzi` có dấu `/`.**
TTS sẽ đọc cả hai từ, và ô gõ đáp án đòi gõ đúng cả chuỗi kèm dấu `/`.

## Kiểm tra file trước khi import (tuỳ chọn)

Lệnh dưới import thử file vào một collection tạm bằng Python đi kèm Anki. Nó không đụng tới profile Anki thật.

```bash
"$HOME/Library/Application Support/AnkiProgramFiles/.venv/bin/python" - "output/越南美食.apkg" <<'EOF'
import os, sys, tempfile
from anki.collection import Collection
from anki import import_export_pb2 as pb

col = Collection(os.path.join(tempfile.mkdtemp(), "test.anki2"))
req = pb.ImportAnkiPackageRequest(package_path=os.path.abspath(sys.argv[1]), options=pb.ImportAnkiPackageOptions(with_scheduling=True))
log = col.import_anki_package(req).log
print("new:", len(log.new), "| conflicting:", len(log.conflicting))
for d in col.decks.all_names_and_ids():
    print(f"{col.db.scalar('select count(*) from cards where did=?', d.id):4}  {d.name}")
col.close()
EOF
```

Kết quả đúng là `new` bằng tổng số dòng TSV, `conflicting` bằng 0, và mỗi deck con có đúng số thẻ.

## Các bộ đã build

| Bộ | Số note | Ghi chú |
|---|---|---|
| `越南美食` | 177 (7 deck con: 29, 12, 25, 31, 27, 32, 21) | Hai note có `/` trong Hanzi: `越南春卷 / 夏卷` (3. 咸点), `甜汤 / 糖水` (6. 甜品) |
| `世界美食` | 50 (2 deck con: 25, 25) | Hai từ trùng với `越南美食`: `越南河粉`, `越南法棍` (đều ở 26-50). Nếu `越南美食` đã có trong Anki thì import với **Update notes: Never**; chỉ 48 note được thêm, deck `26-50` còn 23 thẻ |

Ngày 2026-11-22 toàn bộ file TSV và `.apkg` của hai bộ trên đã được xoá khỏi thư mục, trừ `output/世界美食.apkg`. Nếu chúng đã được import thì note vẫn còn trong Anki, nhưng script không còn dò được từ trùng với hai bộ này; khi build bộ mới, import với **Update notes: Never** cho an toàn.

## Cấu trúc file `.apkg` (tham khảo)

File `.apkg` là một file ZIP. Script tạo ra đúng dạng mà `template/sample.apkg` đang dùng (dạng "legacy 2", đọc được trên cả Anki cũ lẫn mới):

| Thành phần | Nội dung |
|---|---|
| `meta` | 2 byte `08 02`, báo database chính là `collection.anki21` |
| `collection.anki21` | Database SQLite chính: bảng `col` (cấu hình, deck, note type dạng JSON), `notes`, `cards`, `revlog` |
| `collection.anki2` | Database giả, chỉ để Anki rất cũ hiện thông báo "hãy cập nhật" |
| `media` | JSON map `{"0": "tên file thật.mp3", …}`; script ghi `{}` vì không có audio |
| `0`, `1`, … | Các file media, tên là số thứ tự (file do script tạo không có) |

Trong bảng `notes`, các field của một note nối nhau bằng ký tự `0x1F` trong cột `flds`; `guid` là khoá Anki dùng để nhận ra note trùng khi import.
