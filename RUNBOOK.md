# Runbook: chạy một cuộc migrate

Checklist vận hành cho **một job có khách hàng thật**. In ra, tick dần.

Đây không phải tài liệu tham khảo — mọi lời giải thích nằm trong
[README.md](README.md). Trang này chỉ trả lời *"giờ làm gì tiếp"*.

Mốc thời gian tính ngược từ **D-0 = đêm cutover**.

---

## D-10 · Khảo sát, trước khi báo giá

- [ ] Nguồn là gì? Chạy `postboat.py providers <tên>` để xem phải chuẩn bị gì
- [ ] Bao nhiêu mailbox, tổng dung lượng bao nhiêu
- [ ] Hộp lớn nhất bao nhiêu **mail** — đây mới là con số quyết định lịch, không
      phải số GB. Xem [Ước lượng thời gian](#ước-lượng-thời-gian-để-báo-giá)
- [ ] Admin bên nguồn có bật được IMAP cho cả tổ chức không
- [ ] Nguồn là Microsoft 365? → phải dựng app OAuth trên Entra ID, tính thêm
      một buổi và một khoản phụ thu
- [ ] Đích đã có chỗ chưa: hộp thư đã tạo, quota đủ, giới hạn kích thước mail

> **Nói trước, đừng để khách tự phát hiện:** lịch, danh bạ, công việc, ghi chú,
> bộ lọc, chữ ký và cấu hình chuyển tiếp **không đi qua IMAP** nên không nằm
> trong phạm vi. Đây là câu hỏi đầu tiên của mọi khách M365. Mục "Không thuộc
> phạm vi" trong biên bản bàn giao nói đúng điều này — gửi đoạn đó kèm báo giá.

---

## D-7 · Dựng

- [ ] Cài hoặc cập nhật tool trên VPS — làm theo
      [deploy/README.md](deploy/README.md), phần 1 nếu máy mới, phần 2 nếu máy
      đã có sẵn từ job trước
- [ ] `postboat.py doctor` — xanh hết mới đi tiếp
- [ ] `cp config.example.ini config.ini`, điền `[source]` và `[dest]`
- [ ] Điền `[handover]`: tên khách, bên thực hiện, người ký. Làm bây giờ để
      đêm cutover khỏi phải nghĩ
- [ ] Sinh `users.csv` — `postboat.py mkusers <file>` hoặc điền tay
- [ ] `postboat.py preflight` — **phải xanh hết**. Đây là chỗ rẻ nhất để phát
      hiện sai mật khẩu, chứ không phải lúc 2 giờ sáng

---

## D-7 · Gửi khách checklist chuẩn bị

Copy phần này gửi cho admin bên khách:

- [ ] **Hạ TTL bản ghi MX xuống 300 giây**, làm ngay hôm nay — TTL cũ có thể là
      86400, và không hạ trước thì sau khi đổi MX vẫn còn cả ngày mail chạy về
      server cũ
- [ ] Bật IMAP ở cấp tổ chức bên nguồn
- [ ] Tạo App Password cho từng hộp thư (Gmail/Yahoo/Zoho/iCloud), hoặc cấp
      quyền cho app OAuth (M365), hoặc tài khoản quản trị (Dovecot/Zimbra)
- [ ] **Đóng băng việc đổi mật khẩu** từ giờ tới sau cutover — một người đổi
      mật khẩu giữa chừng là một hộp thư dừng lại mà không ai biết
- [ ] Không tạo hộp thư mới, không đổi tên hộp thư trong giai đoạn này
- [ ] Chốt danh sách hộp thư cuối cùng, kèm người nào là ai
- [ ] Báo trước cho nhân viên: đêm cutover mail có thể chậm vài giờ

---

## D-5 · Chạy thử

- [ ] `postboat.py discover` — xem kế hoạch folder bên nguồn
- [ ] `postboat.py discover --dest` — kiểm tên folder bên đích trước khi tạo
- [ ] `postboat.py sync --sizes` — biết trước hộp nào cần mấy đêm
- [ ] `postboat.py sync --folders-only` — dựng cây folder bên đích
- [ ] `postboat.py sync --dry` — chạy khan
- [ ] **Chạy thật MỘT hộp thư trước**: `sync --only <một-địa-chỉ>`, rồi mở hộp
      đó bằng mắt xem folder, tiếng Việt, ngày tháng có đúng không

---

## D-5 → D-1 · Chạy đầy đủ

- [ ] `postboat.py sync` — bắt đầu **sớm hơn cutover vài ngày**, đừng để đêm cuối
- [ ] Mỗi sáng: `postboat.py report --all` xem đêm qua tới đâu
- [ ] Hộp bị cắt giữa chừng → `postboat.py sync --resume` đêm sau. Mail đã
      chuyển không bị chép lại
- [ ] Lặp tới khi tất cả xanh

> **Gmail cắt theo số lệnh IMAP, không theo dung lượng.** Một hộp 14,6 GB có thể
> chạy liền 11 tiếng không sao, trong khi hộp 13,8 GB nhưng 48 nghìn mail thì bị
> chặn. **Hộp nhiều mail nhỏ rủi ro hơn hộp ít mail nặng** — hẹn lịch theo số
> mail, không theo số GB. Bị chặn không phải là hỏng: chờ reset rồi chạy lại.

> Gmail làm **đích** thì chậm gấp khoảng 8 lần (đo thật: 38,6 KiB/s so với
> 311,6 KiB/s sang IceWarp). Nhân lịch lên tương ứng.

> **Microsoft 365 làm nguồn cũng nghẽn theo số mail, không theo dung lượng** —
> khác cơ chế với Gmail nhưng cùng hệ quả. Đo thật 15/09/2026, M365 → IceWarp,
> `workers = 1`, một hộp thư: **3.130 mail / 129,1 MB trong 1h05m** — tức
> **0,79 mail/giây**, khoảng 33 KB/s, mail trung bình 41 KB. Một lá 41 KB mà
> mất hơn một giây thì nghẽn nằm ở tần suất request, không phải ở băng thông.
>
> Một hộp thư, một tenant, một lần chạy — là điểm dữ liệu để báo giá, không
> phải một quy luật.

---

### Ước lượng thời gian để báo giá

Lấy **số mail** nhân với giây mỗi mail, đừng lấy số GB chia băng thông:

| Nguồn | Đo được | Một hộp 3.000 mail mất khoảng |
|---|---|---|
| Microsoft 365 | 0,79 mail/giây (`workers = 1`) | 1 giờ |
| Gmail | không đoán được — xem cảnh báo ở trên | chạy `sync --sizes` trước |

Với M365, đòn bẩy là **chạy song song nhiều mailbox**, không phải làm một hộp
nhanh lên: throttling của nó là tức thời chứ không phải hạn mức ngày.

Chưa đo bao giờ thì đo: chạy 3 hộp với `workers = 3`, cộng tổng mail chia tổng
giây. Lên gần 2,4 mail/giây là trần chưa chạm, còn đẩy tiếp được; vẫn quanh 0,79
thì trần là của tenant chứ không phải của kết nối, và tăng workers chỉ tổ ăn
`Server Unavailable`.

---

## D-0 · Đêm cutover

- [ ] `postboat.py sync --resume` — vòng delta cuối, kéo nốt mail mới
- [ ] Đổi bản ghi MX sang server đích
- [ ] Chờ DNS lan (TTL đã hạ từ D-7 nên nhanh)
- [ ] Gửi thử một mail từ ngoài vào, xác nhận nó về server mới
- [ ] `postboat.py sync --resume` **một lần nữa** sau khi MX đã đổi — hứng nốt
      mail rơi vào server cũ trong lúc DNS đang lan
- [ ] `postboat.py verify` — đối chiếu ngày tháng
- [ ] Đổi mật khẩu hộp thư bên nguồn để không ai còn vào được, nếu hợp đồng có

---

## D+1 · Bàn giao

- [ ] `postboat.py verify` lại lần cuối nếu đêm qua có chạy thêm
- [ ] `postboat.py handover` — sinh biên bản
- [ ] Mở bằng trình duyệt, in ra PDF, ký
- [ ] Gửi khách kèm nhắc lại: **nâng TTL bản ghi MX trở về giá trị cũ**
- [ ] Nhắc khách tạo lại thủ công: bộ lọc, chữ ký, cấu hình chuyển tiếp

---

## Đóng hồ sơ

- [ ] Gỡ dashboard nếu có mở ra ngoài — xem [deploy/README.md](deploy/README.md)
- [ ] `shred -u users.csv` — nó chứa mật khẩu hộp thư của khách và không còn
      việc gì nữa
- [ ] Giữ lại `logs/` và biên bản: chúng không chứa mật khẩu, và là bằng chứng
      nếu sau này có tranh cãi
- [ ] Ghi lại cái gì đã chệch so với dự kiến, để job sau báo giá sát hơn

---

## Khi có sự cố lúc 2 giờ sáng

1. Đọc gợi ý ngay trong báo cáo — tool đã dịch lỗi imapsync thành việc phải làm,
   **theo đúng nhà cung cấp đang chạy**
2. Không thấy gì thì mở `logs/<mailbox>.sync.<thời-điểm>.log`, nó chứa nguyên
   văn output imapsync
3. Bảng tra nhanh theo triệu chứng: [README.md § Xử lý sự cố](README.md#xử-lý-sự-cố)

Ba điều đúng trong gần như mọi trường hợp:

- **Chạy lại không làm hỏng gì.** imapsync bỏ qua mail đã có bên đích
- **Bị chặn hạn mức không phải là hỏng.** Chờ reset rồi chạy lại
- **Giảm `workers` là cách xử lý đúng** cho phần lớn lỗi kết nối, throttling và
  "quá nhiều kết nối đồng thời"
