# Nhật ký thay đổi

**`v1.1.0`** là tag đầu tiên của dự án, gắn ngày 16/09/2026 — nó đánh dấu toàn
bộ trạng thái mô tả bên dưới, không riêng phần cuối cùng. Lịch sử trước đó không
có tag nào, nên các mốc được nhóm theo ngày chứ không theo số phiên bản.

Phần lớn các mục "Sửa" ở đây đến từ những cuộc migrate chạy thật, không phải từ
đọc lại code — chỗ nào có số liệu cụ thể là chỗ đó có một đêm trực đứng sau.

---

## 18/09/2026 — Đo trên IceWarp thật

### Đổi

- **IceWarp (Windows) làm đích, đo thật** IceWarp → IceWarp qua WebDAV: hình
  URL `/webdav/{email}/Calendar/` và `/Contacts/` đúng; `If-None-Match: *` trả
  412 (khác Zimbra); `X-POSTBOAT-*` và mô tả giữ nguyên; chạy lại "0 ghi, 2 đã
  có". **IceWarp tôn trọng `SCHEDULE-AGENT=CLIENT` cả hai chiều** (organizer
  lẫn attendee, không mail nào), nên với đích IceWarp `keep_attendees = true`
  an toàn mà không cần tắt gì phía admin. PUT thô không tham số thì vẫn gửi lời
  mời/reply, và DELETE object còn attendee gửi "cancelled"/"declined" —
  Postboat không bao giờ DELETE, nhưng phần dọn dẹp của `testrig/pimprobe.py`
  thì có, nên nó vô hiệu hoá sự kiện trước khi xoá. Bảng đo đầy đủ ở
  `research/calendar-contacts.md`.
- **`lists` sinh `icewarp.cmd` / `icewarp.sh` gọi thẳng `tool.exe`** thay vì
  trông vào `tool.exe file batch`: trên máy IceWarp test, `file batch` chạy im
  lặng và không tạo gì, còn gõ thẳng `tool.exe create account ... u_type 7
  u_name ... g_listfile ...` thì tạo ngay và `display` trả về đúng ba biến.
  Script `cd` vào thư mục cài (`--tooldir`, mặc định `C:\Program Files\IceWarp`
  hoặc `/opt/icewarp`) rồi sau mỗi `create` có một `display` để đọc kết quả tại
  chỗ. `icewarp.batch` vẫn sinh để tham khảo. Đo đến cùng: nhóm tạo bằng lệnh
  đó với file thành viên "mỗi địa chỉ một dòng" **giao thư đúng cho cả 3 thành
  viên** khi gửi một thư vào nhóm — cú pháp file thành viên không còn là suy
  đoán.
- **Đầu nguồn M365 đo trên tenant thật** (`techsysad.onmicrosoft.com`): thêm
  `docs/m365-lists-export.ps1` gom ba lệnh xuất, đăng nhập qua trình duyệt
  (`-DisableWAM` khi chạy từ tiến trình không có cửa sổ). Dữ liệu thật sửa ba
  chỗ: file xuất **rỗng** (tenant không có distribution group) giờ là 0 nhóm
  kèm cảnh báo thay vì dừng lệnh; thành viên không có mailbox (`MemberType`
  `User`, địa chỉ trống) bị bỏ có báo; `icewarp.cmd` thêm `chcp 65001` vì tên
  nhóm thật có dấu tiếng Việt. Kết quả: 2 Microsoft 365 Group, 5 thành viên,
  ra đúng bộ lệnh cho IceWarp.

---

## 17/09/2026 — Ống lịch và danh bạ

### Thêm

- **`postboat.py pim`** — ống riêng cho lịch và danh bạ, nằm ngoài đường IMAP
  và mặc định tắt (`[pim] enabled = false`). Đọc nguồn bằng CalDAV/CardDAV
  (IceWarp, Zimbra; Yahoo/Zoho/iCloud nếu khai `source_webdav_base`) hoặc
  Microsoft Graph (M365, cùng app Entra đã có nhưng thêm quyền ứng dụng
  `Calendars.Read` + `Contacts.Read` và admin consent), rồi PUT CalDAV/CardDAV
  vào đích IceWarp hoặc Zimbra (server CalDAV khác: khai `webdav_base`; M365 và
  Gmail làm đích chưa có vì phải ghi bằng Graph/OAuth). Giữ UID nên chạy lại
  không nhân bản. Bỏ `METHOD` và gắn
  `SCHEDULE-AGENT=CLIENT` trước khi PUT để server đích không gửi lại lời mời
  họp cho cả công ty. `--dry` chỉ đọc. Vì sao phải có ống riêng và vì sao
  Gmail chưa có: `research/calendar-contacts.md`.
- Chạy thật ghi `state/pim.json`; `handover` đọc file đó, thêm bảng "Lịch và
  danh bạ" vào biên bản và bỏ hai mục ấy khỏi "Không thuộc phạm vi" — thay
  bằng những gì ống PIM vẫn không chở (lịch chia sẻ, phòng họp, ảnh danh
  thiếp, ngoại lệ chuỗi họp). Không có file thì biên bản y như cũ.
- Token Graph được kiểm `roles` ngay sau khi lấy, cùng cách với IMAP: thiếu
  admin consent thì báo tên quyền còn thiếu thay vì chết ở lần gọi Graph đầu.
- **Đo thật trên Zimbra 8.8.15 (lab, 17/09)**, Zimbra → Zimbra qua CalDAV:
  đọc/ghi đúng, RRULE và vCard đi nguyên vẹn, tên file `{UID}.ics` được nhận.
  Hai chỗ bộ test giả không bắt được: (1) Zimbra trả 2xx cho PUT đè dù có
  `If-None-Match: *`, nên "đã có" giờ hỏi bằng PROPFIND trước khi PUT thay vì
  tin mã trả về; (2) **Zimbra bỏ qua `SCHEDULE-AGENT=CLIENT`** và gửi lời mời
  cho mọi attendee khi hộp thư đích là organizer, gửi reply cho organizer khi
  là attendee. Mặc định mới: sự kiện có người tham dự thì bỏ
  `ORGANIZER`/`ATTENDEE` khỏi VEVENT, giữ dưới dạng `X-POSTBOAT-*` và ghi danh
  sách vào mô tả; `[pim] keep_attendees = true` là opt-in. Biên bản bàn giao
  nói rõ điều này.
- **`postboat.py lists`** — nhóm phân phối, hai cặp đầu: M365 và Google
  Workspace sang IceWarp. Đọc file xuất của nguồn (PowerShell
  `Get-DistributionGroup`/`-Member`, `gam print group-members`, hoặc
  `lists.csv`), đổi địa chỉ theo `users.csv`, ghi `lists.csv` trung gian và, với
  đích IceWarp, bộ lệnh cho `tool file batch` (`u_type 7` group hoặc `u_type 1`
  mailing list, theo tài liệu API IceWarp) kèm file thành viên mỗi địa chỉ một
  dòng. Không gọi mạng; admin chạy bộ lệnh trên máy đích. `handover` thêm bảng
  nhóm và đổi câu ngoài phạm vi thành "quy tắc gửi, kiểm duyệt của nhóm".
- Chưa có: Gmail/Google Workspace nguồn cho lịch/danh bạ (cần service account +
  domain-wide delegation), Exchange tự dựng (EWS), Tasks/Notes, bộ lệnh tạo
  nhóm cho đích khác IceWarp.

---

## 16/09/2026 — Tách tài liệu nguồn

### Đổi

- **`docs/nguon.md`** — mục "Chuẩn bị phía nguồn" ra file riêng, 255 dòng, đúng
  nguyên văn cũ. Nó chiếm 20% README nhưng không ai đọc tuần tự: người ta nhảy
  vào đúng mục Gmail hoặc M365 rồi thoát, nên để nguyên khối ở giữa dòng chảy
  "cài → cấu hình → chạy thử → chạy thật" chỉ làm đứt mạch. README còn 1077
  dòng, đọc được từ đầu đến cuối.
- README giữ lại phần khai `provider` cùng một trỏ dẫn ở đúng chỗ cũ, nên thứ tự
  các bước không đổi. Các link cũ trỏ vào mục đã chuyển được sửa sang file mới;
  RUNBOOK trỏ thêm ở D-10 và D-7.

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
