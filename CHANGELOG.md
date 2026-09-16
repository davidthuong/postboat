# Nhật ký thay đổi

**`v1.1.0`** là tag đầu tiên của dự án, gắn ngày 16/09/2026 — nó đánh dấu toàn
bộ trạng thái mô tả bên dưới, không riêng phần cuối cùng. Lịch sử trước đó không
có tag nào, nên các mốc được nhóm theo ngày chứ không theo số phiên bản.

Phần lớn các mục "Sửa" ở đây đến từ những cuộc migrate chạy thật, không phải từ
đọc lại code — chỗ nào có số liệu cụ thể là chỗ đó có một đêm trực đứng sau.

---

## 16/09/2026 — Thương hiệu

### Đổi

- **Đổi tên dự án thành Postboat.** `migrate_mail/` → `postboat/`, `mm.py` →
  `postboat.py`. Không để lại lớp tương thích cho tên cũ.
- Tên sản phẩm viết hoa ở chỗ người đọc (README, tiêu đề dashboard, `--version`,
  LICENSE); tên file và unit systemd giữ thường.

### Thêm

- `brand/` — bộ nhận diện: năm bản logo nền trong suốt, bảng màu lấy thẳng từ
  file gốc (navy `#021833`, lime `#70CD02`), kèm hai hạn chế đã biết.
- Logo trên header dashboard và favicon, nhúng dạng `data:` URI nên trang vẫn
  không tải gì từ bên ngoài. CSP nới đúng một chỗ: `img-src 'self' data:`.

---

## 15/09/2026 — Bàn giao, và mở dashboard ra ngoài

### Thêm

- **Lệnh `handover`** — biên bản bàn giao cho khách: trang bìa, kết quả từng
  mailbox, bảng đối chiếu ngày tháng kèm phương pháp, mục "không thuộc phạm vi",
  và chỗ ký của hai bên. Chưa chạy `verify` thì biên bản **nói thẳng là chưa đối
  chiếu** chứ không bỏ trống mục đó.
- `verify` ghi thêm `state/verify.json` để `handover` dùng làm bằng chứng. Gộp
  chứ không đè, giống `preflight`.
- Dashboard có thêm `doctor`, `providers`, `report`, `handover`, và **tải tệp
  về từ trình duyệt** — không phải SCP nữa. Tệp luôn gửi dạng đính kèm, kể cả
  `.html`.
- `deploy/` — cấu hình Caddy (HTTPS + mật khẩu + lọc IP) và unit systemd, để
  vào dashboard từ xa mà không phải dựng SSH tunnel mỗi lần.
- `LICENSE` — sở hữu riêng, giữ toàn quyền, song ngữ Việt/Anh.

### Sửa

- **Khối chữ khởi động của dashboard không ra khi chạy nền.** `serve()` dùng
  `print()` trần, mà Python gom đệm stdout khi đầu ra không phải terminal —
  token nằm trong khối chữ đó, nên chạy `nohup` là mất luôn đường vào dashboard
  của chính mình. Giờ đi qua `say()`, vốn đã có `flush=True`.
- `doctor` nhìn vào trong token OAuth thay vì chỉ báo là lấy được.
- Đích báo tạo được folder rồi báo không tồn tại (IceWarp với `Archive`) — có
  gợi ý riêng, và nói rõ **mail không mất**.
- `verify` phân biệt "không mở nổi hộp thư" với "không có gì để đối chiếu".

---

## 14/09/2026 — Một loạt sửa từ chạy thật

### Sửa

- **`Ctrl-C` không dừng được `sync`**, và `--only` lặp bị nuốt im lặng.
- **Một đầu biến mất giữa chừng**: đọc được lỗi, và đếm đúng số mail đã sang.
  imapsync bị tín hiệu hạ thì không kịp in khối thống kê, nên số được đếm lại
  từ chính những dòng `copied to` — đó là mail đã sang thật, không phải ước
  lượng.
- **`verify` đếm cả mail không kiểm được** thay vì lặng lẽ bỏ qua. Trước đó mail
  không có `Message-Id` biến mất khỏi mọi con số, và verify báo "khớp hết" trong
  khi im lặng bỏ qua một phần hộp thư.
- `verify` gọi tên mail nó không tìm thấy, thay vì chỉ đếm — một ca thật báo
  "thiếu 1" mà không ai truy được vì không biết là mail nào.
- `--since-days` đo theo ngày mail **về**, không theo header `Date:`.
- Đọc không được mail: tách phiên chết ra khỏi mail hỏng. Hai việc ngược nhau —
  đoán nhầm thì hoặc vứt mail còn đọc được, hoặc chạy lại mãi một mail hỏng.
- Thêm mailbox trên dashboard làm hỏng `users.csv` và đứng hình cả trang.
- Tên folder có dấu `=`: `verify` đi tìm sai chỗ.
- Preflight đánh dấu được từng dòng trên dashboard.

---

## 08–11/09/2026 — TLS, và những gì testrig tìm ra

### Thêm

- **Đối chiếu chứng chỉ TLS** — trước đó tool không kiểm gì cả. Kèm `tls_verify`
  và phần kiểm tên host.
- Bên đích cũng đọc cờ SPECIAL-USE thay vì tra bảng tĩnh.
- `testrig`: hai Dovecot thật để thử `auth = master`, chạy trên VPS thật.

### Sửa

- Ba lỗi chỉ lộ ra khi chạy trên server thật, gộp từ nhánh sửa-sau-testrig.
- Đọc hết body trước khi trả 401, để client nhận được câu trả lời chứ không phải
  connection reset.
- `discover` in tên folder đích đọc được, thôi in UTF-7 thô.
- Dùng mã thoát `USER1`/`USER2` của imapsync để nói đầu nào hỏng.

---

## 31/08–07/09/2026 — Không chỉ còn là Gmail

### Thêm

- **Hỗ trợ migrate từ nhiều nhà cung cấp**, không chỉ Gmail: Microsoft 365,
  Exchange, Dovecot (cPanel/DirectAdmin/Plesk), Courier, Zimbra, Yahoo, Zoho,
  iCloud, và IMAP chung.
- **`auth = master`** — một tài khoản quản trị mở mọi hộp thư, khỏi đi xin mật
  khẩu từng khách.
- **Lệnh `mkusers`** — sinh `users.csv` từ danh sách mailbox của nguồn.
- Tách gợi ý sửa lỗi ra card riêng trên dashboard.

---

## 25–29/08/2026 — Những ngày đầu

### Thêm

- Tool migrate mailbox trên nền imapsync, Gmail → IceWarp.
- **`verify`** — đối chiếu ngày tháng thật giữa hai đầu, thay vì tin là mail giữ
  nguyên ngày.
- `discover` và `discover --dest` — xem kế hoạch chuyển đổi trước khi chạy.
- **Dashboard web** để theo dõi và chạy migration trên trình duyệt.
- `--sizes` để biết trước một hộp thư cần chạy mấy ngày; `--folders-only`;
  `--resume`.
- `install.sh` đọc danh sách module Perl từ chính file imapsync thay vì giữ một
  danh sách viết tay.

### Sửa

- **`report --all` cộng dồn khối lượng qua mọi lần chạy**, không lấy lần cuối.
  Một hộp bị Gmail cắt giữa chừng rồi chạy lại đã chuyển mail ở cả hai lần —
  cách cũ báo 87.936 mail trong khi thực tế đã chuyển gần 122.700.
- **Gợi ý được tính lại từ log** mỗi lần xem, thay vì đọc gợi ý đã đóng băng
  trong file run. Nhờ vậy luật chẩn đoán tốt lên thì mọi báo cáo cũ tự đúng
  theo.
- `--f1f2` dùng sai dấu phân cách nên mapping folder không có tác dụng.
- `doctor` đối chiếu flag với bảng `GetOptions` thay vì với `--help`.
