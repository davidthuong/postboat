# Triển khai Postboat lên VPS

Toàn bộ vòng đời một bản cài, từ máy trắng tới lúc gỡ đi. Không phải tra ở đâu
khác.

| Phần | Khi nào đọc |
|---|---|
| [1. Cài lần đầu](#1-cài-lần-đầu) | Máy mới |
| [2. Cập nhật](#2-cập-nhật-khi-có-bản-mới) | Có bản mới trên GitHub |
| [3. Chạy như dịch vụ](#3-chạy-như-dịch-vụ-systemd) | Muốn dashboard sống qua việc đóng SSH |
| [4. Mở ra ngoài](#4-mở-dashboard-ra-ngoài-qua-https) | Không muốn dựng SSH tunnel mỗi lần |
| [5. Gỡ bỏ](#5-gỡ-bỏ-khi-xong-việc) | Migrate xong |

File trong thư mục này: [`Caddyfile`](Caddyfile) và
[`postboat.service`](postboat.service).

Đang trực một cuộc migrate thì mở [RUNBOOK.md](../RUNBOOK.md), không phải trang
này.

---

## 1. Cài lần đầu

**Cần có:** Linux (Debian/Ubuntu hoặc RHEL/Alma), Python **3.8 trở lên**, quyền
root. Postboat chỉ dùng thư viện chuẩn của Python — không `pip install` gì cả.

```bash
git clone https://github.com/davidthuong/postboat.git /opt/postboat
```

```bash
cd /opt/postboat && chmod +x install.sh postboat.py && sudo ./install.sh
```

`install.sh` tải imapsync từ GitHub về `/usr/local/bin/imapsync` rồi cài các
module Perl nó cần — apt trên Debian/Ubuntu, dnf trên RHEL/Alma, phần thiếu bù
bằng `cpanm`.

> Script **không giữ danh sách module cứng.** Nó đọc thẳng các dòng
> `use`/`require` trong file imapsync vừa tải, nên luôn khớp với đúng bản đang
> cài. Sau đó chạy `imapsync --version` trong một vòng lặp: mỗi lần Perl báo
> `Can't locate Foo/Bar.pm` thì cài đúng module đó rồi thử lại. Danh sách viết
> tay sẽ luôn lệch theo thời gian; đọc từ nguồn thì không.

Ghim một phiên bản imapsync cụ thể:

```bash
sudo IMAPSYNC_REF=v2.290 ./install.sh
```

Kiểm môi trường — **xanh hết mới đi tiếp**:

```bash
python3 postboat.py doctor
```

Rồi tạo hai file cấu hình của riêng job này:

```bash
cp config.example.ini config.ini && cp users.example.csv users.csv && chmod 600 users.csv
```

`users.csv` chứa mật khẩu hộp thư của khách — `chmod 600` không phải thủ tục.

---

## 2. Cập nhật khi có bản mới

```bash
cd /opt/postboat && git pull
```

Với Postboat thì **thế là xong**: không build, không dependency, không migration
schema. Đọc [CHANGELOG.md](../CHANGELOG.md) xem bản mới đổi gì.

### `git pull` không đụng vào những thứ này

| File | Vì sao an toàn |
|---|---|
| `config.ini` | `.gitignore` chặn `config*.ini` (trừ file `.example`) |
| `users.csv` | `.gitignore` chặn `users*.csv` |
| `logs/`, `state/` | Cả hai thư mục đều bị chặn |

Tức là **kéo bản mới giữa chừng một cuộc migrate không làm mất tiến độ** —
`state/<mailbox>/done.marker` vẫn còn, `sync --resume` vẫn bỏ qua đúng những hộp
đã xong. Nhưng đừng pull *trong lúc* một lệnh `sync` đang chạy: file Python bị
thay dưới chân tiến trình đang chạy là chuyện không ai muốn gỡ lúc 2 giờ sáng.

### Khi nào phải chạy lại `install.sh`

Chỉ ba trường hợp, và `install.sh` chạy lại nhiều lần được:

- `doctor` báo imapsync thiếu một tuỳ chọn Postboat cần
- Muốn nâng hoặc hạ phiên bản imapsync (`IMAPSYNC_REF=...`)
- Perl báo `Can't locate Foo/Bar.pm`

```bash
sudo ./install.sh && python3 postboat.py doctor
```

Chạy như dịch vụ thì nhớ khởi động lại sau khi pull:

```bash
sudo systemctl restart postboat
```

> Restart sinh **token mới**, nên mọi phiên đăng nhập dashboard đang mở đều mất
> hiệu lực. Lấy token mới ở [phần 3](#3-chạy-như-dịch-vụ-systemd).

---

## 3. Chạy như dịch vụ (systemd)

Không có bước này thì dashboard chết theo phiên SSH.

Tạo user riêng, đừng chạy bằng root:

```bash
sudo useradd -r -s /usr/sbin/nologin postboat && sudo chown -R postboat: /opt/postboat
```

Chép unit rồi bật:

```bash
sudo cp deploy/postboat.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now postboat
```

Sửa `User=` và `WorkingDirectory=` trong unit cho khớp máy trước khi bật.

> Nếu tool nằm trong `/home/...` thì phải bỏ dòng `ProtectHome=read-only`, không
> thì `logs/` và `state/` không ghi được.

Lấy token đăng nhập:

```bash
journalctl -u postboat | grep '?t='
```

Nó in ra `http://127.0.0.1:8765/?t=<token>`. Token dùng một lần để đặt cookie rồi
biến khỏi thanh địa chỉ.

**Chưa mở ra ngoài thì vào bằng SSH tunnel** — chạy trên máy bạn:

```bash
ssh -L 8765:127.0.0.1:8765 root@<vps>
```

rồi mở đúng địa chỉ trên trong trình duyệt. Dừng ở đây là đủ an toàn và không
cần phần 4.

---

## 4. Mở dashboard ra ngoài qua HTTPS

### Đọc cái này trước

`web.py` là `http.server` của thư viện chuẩn: một token cookie duy nhất, không
HTTPS, không giới hạn số lần thử, không có khái niệm nhiều người dùng. Nó được
viết để nghe trên `127.0.0.1`.

**Và nó giữ mật khẩu hộp thư của khách hàng bạn.**

`Caddyfile` ở đây không sửa được bản chất đó. Nó dựng ba lớp đứng trước:

1. **Lọc IP** — ngoài danh sách thì bị cắt, không được mời nhập gì
2. **Mật khẩu** HTTP basic, băm bcrypt
3. **HTTPS** thật, chứng chỉ Caddy tự xin và tự gia hạn

Rủi ro còn lại, nói thẳng: ai qua được ba lớp đó thì có toàn bộ mật khẩu trong
`users.csv` và có nút `Chạy thật`. **SSH tunnel ở phần 3 vẫn an toàn hơn.** Chỉ
làm phần này khi việc phải mở tunnel mỗi lần thực sự cản trở công việc.

### 4.1 Trỏ tên miền

Tạo bản ghi `A` (và `AAAA` nếu có IPv6) cho `mm.congty.vn` về đúng IP VPS. Làm
**trước** khi khởi động Caddy: nó xin chứng chỉ bằng cách chứng minh mình giữ tên
miền đó.

```bash
dig +short mm.congty.vn
```

### 4.2 Cài Caddy

Theo [hướng dẫn chính thức](https://caddyserver.com/docs/install). Bản trong kho
apt/dnf thường quá cũ — chỉ thị `basic_auth` mới có tên này từ **Caddy 2.8**; bản
cũ hơn gọi nó là `basicauth`.

```bash
caddy version
```

### 4.3 Sinh băm mật khẩu

```bash
caddy hash-password
```

Nó hỏi hai lần rồi in chuỗi bắt đầu bằng `$2a$`. Caddy không nhận mật khẩu thô.

### 4.4 Sửa Caddyfile

```bash
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
```

Sửa ba chỗ:

- `mm.congty.vn` → tên miền thật
- `<BAM-MAT-KHAU>` → chuỗi `$2a$...` vừa sinh
- `<IP-CUA-BAN>` → dải IP được phép vào, ví dụ `14.161.0.0/16`

```bash
curl -s https://api.ipify.org
```

### 4.5 Tường lửa: chỉ mở 80 và 443

Bước dễ quên nhất, và quên thì **ba lớp trên bị đi vòng hoàn toàn** — gõ thẳng
`http://<ip-vps>:8765` là vào, không qua Caddy. Không có gì báo cả.

```bash
sudo ufw allow 80,443/tcp && sudo ufw deny 8765/tcp && sudo ufw enable
```

Cổng 80 cần cho Let's Encrypt xác thực và cho việc chuyển hướng sang HTTPS.

### 4.6 Kiểm rồi nạp

**Luôn `validate` trước `reload`.** Cấu hình sai mà reload thẳng thì Caddy giữ
bản cũ nhưng không phải lúc nào cũng nói rõ vì sao.

```bash
caddy validate --config /etc/caddy/Caddyfile
```

```bash
sudo systemctl reload caddy
```

### 4.7 Đăng nhập

Lấy token như phần 3, giữ nguyên phần `/?t=<token>`, đổi phần đầu thành tên miền:

```
https://mm.congty.vn/?t=<token>
```

Mất token thì `systemctl restart postboat` — token mới sinh mỗi lần khởi động, và
đó cũng là cách đóng cửa nhanh nhất nếu nghi có chuyện.

### Không có IP tĩnh

Mạng nhà đổi IP thì lớp 1 thành ra vướng chân chính mình. Ba lựa chọn, xếp theo
mức an toàn:

**Tốt nhất — WireGuard.** Dựng VPN trên VPS, cho phép dải IP của VPN thay vì IP
nhà. Không đổi bao giờ, và mạnh hơn cả ba lớp ở đây cộng lại.

**Chấp nhận được — dải của nhà mạng.** Cho phép cả dải `/16` của FPT hoặc Viettel
đang dùng. Rộng hơn nhiều, nhưng vẫn cắt được toàn bộ phần còn lại của thế giới.

**Cuối cùng — bỏ lớp IP.** Xoá hai dòng `@ngoai` và `abort @ngoai`. Lúc đó mật
khẩu là thứ **duy nhất** đứng giữa Internet và mật khẩu hộp thư của khách. Nếu
chọn cách này thì đặt mật khẩu 20 ký tự trở lên, sinh bằng máy.

---

## 5. Gỡ bỏ khi xong việc

Một dashboard mở ra Internet mà không ai còn dùng là một cánh cửa không ai còn
nhìn.

```bash
sudo systemctl disable --now postboat caddy
```

Xoá `users.csv` — nó chứa mật khẩu hộp thư của khách và không còn việc gì nữa:

```bash
sudo shred -u /opt/postboat/users.csv
```

Log và báo cáo giữ lại được: chúng không chứa mật khẩu, và là bằng chứng nếu sau
này có tranh cãi.
