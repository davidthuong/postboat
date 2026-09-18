# Chuẩn bị phía nguồn, theo từng nhà cung cấp

Mỗi nhà cung cấp mail mở IMAP ra theo cách riêng của nó: chỗ đòi App Password,
chỗ tắt hẳn basic auth, chỗ giấu mất một phần dữ liệu không đi qua IMAP được.
File này là phần phải đọc **trước khi chạy**, tra đúng mục của nguồn đang gặp
rồi thôi — không cần đọc hết.

Phần khai báo `provider` trong `config.ini` và vị trí của bước này trong cả quy
trình nằm ở [README.md § Chuẩn bị phía nguồn](../README.md#chuẩn-bị-phía-nguồn).
Bản tóm tắt ngắn hơn cũng in ra được từ dòng lệnh:

```bash
python3 postboat.py providers          # danh sách nguồn và việc phải chuẩn bị
python3 postboat.py providers m365     # chi tiết một nguồn
```

---

## Gmail / Google Workspace

Mỗi mailbox cần một **App Password 16 ký tự** — không dùng được mật khẩu đăng nhập.

1. Bật xác thực 2 bước cho account (bắt buộc, không bật thì mục App Password
   không hiện ra).
2. Vào <https://myaccount.google.com/apppasswords>, tạo password mới, copy 16 ký tự.
3. Nếu là Google Workspace: admin phải bật IMAP cho tổ chức —
   **Admin console → Apps → Google Workspace → Gmail → End User Access → IMAP**.
   Tắt ở cấp tổ chức thì không App Password nào cứu được.

Google hiển thị password dạng `abcd efgh ijkl mnop`. Dán vào CSV kèm khoảng trắng
cũng được, tool tự bỏ.

**Nhóm (Google Groups)** không đi qua IMAP. `postboat.py lists` đọc file của
[GAM](https://github.com/GAM-team/GAM) chạy bằng tài khoản admin Workspace:

```bash
gam print groups > groups.csv
gam print group-members > members.csv
python3 postboat.py lists groups.csv members.csv
```

Không có GAM thì mở từng group ở groups.google.com → Members → Export members,
rồi chạy `postboat.py lists members.csv --list ten-nhom@domain` cho mỗi file.
Thành viên kiểu "cả domain" GAM ghi là `CUSTOMER`, không có địa chỉ — tool báo
và bỏ qua, thêm tay bên đích.

## Microsoft 365 / Exchange Online

Phần lớn tenant đã tắt basic auth. Ở đó **không có mật khẩu nào đăng nhập IMAP
được** — kể cả mật khẩu đúng. Đường còn lại là OAuth2 app-only: đăng ký một ứng
dụng, cho nó quyền đọc mailbox toàn tenant, rồi tool dùng token của ứng dụng đó
để đăng nhập thay từng mailbox. **Không cần thu mật khẩu của nhân viên khách
hàng** — thực tế đây mới là thứ làm việc migrate khả thi.

Khách hàng (admin của tenant nguồn) làm bốn bước:

1. **Entra ID → App registrations → New registration.** Ghi lại
   *Application (client) ID* và *Directory (tenant) ID*.
2. **API permissions → APIs my organization uses → Office 365 Exchange Online →
   Application permissions → `IMAP.AccessAsApp` → Add**, rồi bấm
   **Grant admin consent**.
3. **Certificates & secrets → New client secret.** Copy giá trị ngay, sau này
   không xem lại được.
4. Trong **Exchange Online PowerShell**, đăng ký service principal cho app đó:

   ```powershell
   New-ServicePrincipal -AppId <client-id> -ServiceId <object-id-cua-service-principal>
   ```

   Thiếu bước này thì token lấy về vẫn hợp lệ nhưng IMAP trả `AUTHENTICATE failed`
   — đây là chỗ hay tắc nhất.

Ngoài ra IMAP phải được bật cho từng mailbox:

```powershell
Set-CASMailbox -Identity user@contoso.com -ImapEnabled $true
```

Rồi khai vào `config.ini`:

```ini
[source]
provider = m365
auth = oauth2
oauth_tenant    = contoso.onmicrosoft.com
oauth_client_id = 00000000-0000-0000-0000-000000000000
oauth_client_secret_file = oauth-secret.txt
```

Để secret ra file riêng (`chmod 600`) thì `config.ini` vẫn còn backup/gửi đi
được. Cột `src_password` trong `users.csv` khi đó **để trống**.

`python3 postboat.py doctor` sẽ thật sự gọi Microsoft xin token và in mã `AADSTS` nếu
bị từ chối — đó là cách nhanh nhất biết secret hết hạn hay thiếu consent.

> OAuth2 cần **imapsync 2.251 trở lên**. Tuỳ chọn `--oauthaccesstoken1` có
> từ 2.113, nhưng trước 2.251 imapsync vẫn đòi có `--password1` đi kèm nên
> không dùng một mình được. `doctor` kiểm tra và báo nếu bản đang cài quá cũ.
>
> Tool ghi token ra file rồi truyền đường dẫn file đó (không truyền token
> thẳng trên dòng lệnh). imapsync đọc lại file mỗi lần nó kết nối lại giữa
> chừng, nên trong suốt lần chạy tool giữ cho file đó luôn còn hạn — hộp thư
> chạy mười mấy tiếng cũng không đứt vì token hết hạn.

Tenant nào còn bật basic auth thì cứ để `auth = password` và điền mật khẩu như
bình thường.

Bật IMAP cho cả tenant một lượt, thay vì từng mailbox:

```powershell
Get-Mailbox -ResultSize Unlimited | Set-CASMailbox -ImapEnabled $true
```

**Nhóm phân phối** không đi qua IMAP. Xuất bằng PowerShell rồi đưa cho
`postboat.py lists` — không cần thêm quyền nào cho app:

```powershell
Get-DistributionGroup -ResultSize Unlimited | ForEach-Object {
  $g = $_
  Get-DistributionGroupMember -Identity $g.Identity -ResultSize Unlimited |
    Select-Object @{n='List';e={$g.PrimarySmtpAddress}},
                  @{n='ListName';e={$g.DisplayName}},
                  @{n='Member';e={$_.PrimarySmtpAddress}},
                  @{n='MemberType';e={$_.RecipientTypeDetails}}
} | Export-Csv -NoTypeInformation -Encoding UTF8 lists.csv
```

Nhóm chưa có thành viên không sinh dòng nào. Muốn giữ cả nhóm rỗng thì xuất
thêm `Get-DistributionGroup | Select-Object PrimarySmtpAddress,DisplayName |
Export-Csv groups.csv` và đưa cả hai file. Microsoft 365 Group
(`Get-UnifiedGroup` + `Get-UnifiedGroupLinks -LinkType Members`) xuất ra cùng
bốn cột thì đọc được y vậy — nhưng chỉ có thành viên; hộp thư chung của nhóm
IMAP không vào được.

Cả ba việc trên gom trong [docs/m365-lists-export.ps1](m365-lists-export.ps1):
chạy bằng admin tenant, đăng nhập qua trình duyệt, ra ba file `.csv` đưa thẳng
cho `postboat.py lists`. Chạy thật trên một tenant test 18/09/2026 thấy ba
điều đáng biết trước: tenant có thể **không có distribution group nào** (chỉ có
Microsoft 365 Group) — file tương ứng chỉ còn BOM và tool hiểu là 0 nhóm;
`Get-UnifiedGroupLinks` trả cả **user không có mailbox** (cột `Member` rỗng,
`MemberType` = `User`) — tool bỏ và báo từng dòng; và tên nhóm có dấu tiếng
Việt — đưa qua tham số `u_name` của `tool.exe` thì mất dấu ("THƯƠNG MẠI" thành
"THUONG M?I", `chcp` không cứu được vì tham số đi qua bảng mã ANSI), nên script
sinh ra chỉ đặt tên không dấu lúc `create`, rồi nạp tên đầy đủ bằng
`tool.exe import account names.csv u_name` (CSV UTF-8, đo là giữ đủ dấu và
không đụng thuộc tính khác).
Chạy từ tiến trình không có cửa sổ thì `Connect-ExchangeOnline` phải có
`-DisableWAM`, không thì chết với "A window handle must be configured".

## Microsoft 365: cái gì không đi qua IMAP

Tool này chuyển **mail**. Với một tenant Microsoft 365 thì "mail" ít hơn thứ
khách hàng hình dung khi họ nói *"chuyển hết Microsoft 365 sang"*. Đây là danh
sách để nói trước khi nhận việc — không phải để giải thích sau cutover.

**Đi qua được:** toàn bộ mail trong mailbox chính của user mailbox và shared
mailbox — cấu trúc folder lồng nhau, ngày tháng, trạng thái đã đọc, cờ, thư đã
trả lời. Shared mailbox chỉ là một dòng như mọi dòng khác trong `users.csv`,
miễn là đã bật IMAP cho nó.

**Không đi qua được:**

| Không lấy được | Vì sao |
|---|---|
| Calendar, Contacts, Tasks, Notes | Exchange không bày các folder này ra đường IMAP (khác Zimbra và IceWarp) |
| **Online Archive** (In-Place Archive) | Là một mailbox riêng, không có endpoint IMAP |
| Public folder | Không truy cập được bằng IMAP |
| Rule, chữ ký, out-of-office, category, quyền delegate | Nằm ở tầng Exchange, không ở tầng message |
| Recoverable Items (thùng rác cấp hai) | Không nhìn thấy qua IMAP |
| Room / Equipment mailbox | Chỉ có lịch, không có mail — `mkusers` tự bỏ qua |
| Microsoft 365 Group, Team site mailbox | IMAP không vào được |
| OneDrive, SharePoint, Teams | Khác hệ hoàn toàn |

**Online Archive là cái hay bị quên nhất**, vì nó không hiện ra ở bất kỳ bước
nào của tool: mailbox archive không nằm trên đường IMAP nên `discover` cũng
không thấy. Đếm xem có bao nhiêu mailbox bị ảnh hưởng *trước* khi chạy:

```powershell
Get-Mailbox -ResultSize Unlimited | Where-Object { $_.ArchiveStatus -eq "Active" } | Select-Object PrimarySmtpAddress, ArchiveStatus
```

Cách xử lý là kéo nội dung archive về hộp thư chính trước khi sync (nếu quota
bên đích đủ chỗ) — sau đó nó là mail bình thường và đi theo lần sync như mọi
folder khác. Nếu không kéo về được thì phải export riêng bằng Outlook hoặc
Graph API, và nói rõ với khách rằng phần đó nằm ngoài lần migrate này.

Nếu để `mkusers` sinh `users.csv` từ output `Get-Mailbox` (xem
[Cấu hình](../README.md#cấu-hình)) thì cột `ArchiveStatus` được đọc luôn và số mailbox có
archive được in ra ngay lúc đó.

## cPanel / DirectAdmin / Plesk (Dovecot), Courier

Hosting kiểu Maildir++ để mọi folder dưới tiền tố `INBOX.` với dấu phân cách là
`.`. Tool đọc lệnh `NAMESPACE` của **cả hai đầu**: tiền tố bên nguồn bị cắt đi,
tiền tố bên đích được thêm vào, và dấu phân cách được đổi theo. Không làm thế
thì hoặc hộp thư mới mọc ra một folder `INBOX` chứa tất cả, hoặc mọi folder bị
kéo ra ngoài INBOX.

Đây là việc **không thể phó mặc cho imapsync**: nó chỉ tự đổi tiền tố và dấu
phân cách cho những folder nó tự suy ra tên. Tên nào đi qua `--f1f2` thì nó lấy
nguyên văn (`sub imap2_folder_name` trả về trước khi gọi
`prefix_seperator_invertion`) — mà tool này ánh xạ tường minh gần như mọi folder.

Muốn ghi đè thì đặt `prefix` trong `[source]` hoặc `[dest]`: `auto` (mặc định),
`none`, hoặc một tiền tố viết cứng như `INBOX.` cho server trả về `NAMESPACE` sai.

Cái chặn thường gặp là `mail_max_userip_connections` của Dovecot (mặc định 10):
vượt là server từ chối kết nối mới. Giảm `workers` hoặc nâng giới hạn đó.

Courier không quảng bá SPECIAL-USE, nên folder đặc biệt được nhận ra **theo
tên**. Chạy `discover` kiểm lại trước khi sync thật.

## Zimbra

Bật IMAP trong COS (`zimbraImapEnabled = TRUE`). Zimbra bày cả `Contacts`,
`Emailed Contacts`, `Calendar`, `Tasks`, `Chats`, `Briefcase` ra đường IMAP —
tool tự bỏ qua chúng.

## Yahoo / Zoho / iCloud

Đều bắt buộc app-specific password, tạo trong phần bảo mật của account. Zoho còn
phải bật IMAP trong **Settings → Mail Accounts → IMAP Access**, và account ở
châu Âu dùng `imap.zoho.eu`.

## Nguồn không có trong danh sách

```ini
[source]
provider = imap
host = mail.khachhang.vn
```

Tool vẫn đọc cờ SPECIAL-USE và đối chiếu bảng tên tiếng Anh + tiếng Việt. Chạy
`discover` để xem nó phân loại đúng chưa trước khi chạy thật.

## Đăng nhập bằng tài khoản quản trị (`auth = master`)

Cách mặc định là xin mật khẩu của **từng hộp thư** rồi điền vào `users.csv`. Với
một cuộc migrate 200 mailbox thì đó là 200 lần đi hỏi, và mỗi mật khẩu thu về
đều là một thứ phải giữ rồi phải xoá. Nếu bạn làm chủ server — đầu nguồn tự
dựng, hoặc đầu đích là hệ thống của chính bạn — thì đi đường này thay thế:

```ini
[source]
provider = dovecot
host     = mail.congty-cu.vn
auth     = master

master_user          = migrate
master_password_file = master-pass.txt
```

Cột mật khẩu tương ứng trong `users.csv` (`src_password` cho nguồn,
`dst_password` cho đích) khi đó **để trống** — tool không đọc tới nữa.

Hỗ trợ với `provider` là `dovecot`, `zimbra`, hoặc `imap`. Đặt cho đầu nào cũng
được, và đặt cho **cả hai** đầu cũng được.

**Đã kiểm chứng tới đâu.** Nói thẳng để bạn biết chỗ nào đứng vững, chỗ nào nên
thử trước:

| | Trạng thái |
|---|---|
| **Dovecot** | Chạy thật đầu-cuối, cả hai `master_style`, cả hai đầu — Ubuntu 24.04 / Dovecot 2.3.19.1 / imapsync 2.314. Dựng lại bằng [`testrig/`](../testrig/) |
| **Zimbra** | **Chưa chạy thật lần nào.** Phần dưới là suy ra từ tài liệu Zimbra và imapsync, không phải từ quan sát |
| **IMAP chung** | Để ngỏ, không phải lời hứa — tuỳ server |
| Kết nối TLS | Rig mặc định chạy 993 có đối chiếu chứng chỉ, và `auth = master` chạy trọn trên đó — preflight, sync, `verify` lệch 0 ngày. Gỡ CA khỏi trust store thì **cả hai** nửa dừng lại, đúng như phải thế |
| Kiểm tên host trong chứng chỉ | Rig không trả lời được (chứng chỉ của nó cấp đúng tên), nên có phép thử riêng: [`testrig/tlsprobe.sh`](../testrig/tlsprobe.sh), 10/10 ô khớp trên VPS thật và trên máy dev |

Với Zimbra hoặc một server lạ, chạy `preflight` trên **một** hộp thư trước đã.

**Hai kiểu gửi tài khoản quản trị lên server.** Khác nhau ở giao thức chứ không
phải ở sở thích, nên chọn theo cái server chấp nhận:

| `master_style` | Cách hoạt động | Dùng khi |
|---|---|---|
| `authzid` (mặc định) | SASL PLAIN mang ba trường: hộp thư cần mở, tài khoản quản trị, mật khẩu quản trị (RFC 4616) | Dovecot có passdb `master = yes`; Zimbra với tài khoản admin (chưa kiểm chứng) |
| `separator` | Ghép thành một tên đăng nhập `hopthu*quantri` rồi LOGIN như thường | Dovecot có bật `auth_master_user_separator`, hoặc server không cho SASL PLAIN |

Đổi dấu phân cách bằng `master_separator` nếu server bạn không dùng `*`.

**Phía Dovecot** cần thêm một passdb quản trị vào
`/etc/dovecot/conf.d/10-auth.conf` rồi reload:

```
passdb {
  driver = passwd-file
  args = /etc/dovecot/master-users
  master = yes
}
```

Đúng bốn dòng đó là đủ trên Dovecot 2.3.19 — đã chạy thật. Vài bản khác cần
thêm `result_success = continue` trong khối này; nếu `doveadm auth login` không
qua thì đó là dòng đầu tiên nên thử.

File `/etc/dovecot/master-users` chứa dòng `migrate:{SHA512-CRYPT}$6$...` —
sinh hash bằng `doveadm pw -s SHA512-CRYPT`. Tên tài khoản quản trị thường là
tên trần (`migrate`), **không** phải `user@domain`.

Kiểm bằng **hai** lệnh trước khi động tới tool, đừng bỏ lệnh thứ hai:

```bash
doveadm auth login 'an@congty-cu.vn*migrate' 'MatKhauMaster'   # passdb
doveadm user an@congty-cu.vn                                    # userdb
```

`doveadm auth login` chỉ kiểm passdb. userdb hỏng thì nó vẫn báo
`auth succeeded`, trong khi mọi lần đăng nhập IMAP thật đều chết với
`[UNAVAILABLE] Internal error occurred` — một câu không hề nhắc tới userdb.

**Phía Zimbra** — *chưa kiểm chứng, xem bảng ở trên.* Theo tài liệu thì không
phải đổi cấu hình gì: đặt `master_user` là một tài khoản admin đầy đủ
(`admin@domain`) và giữ `master_style = authzid`. Chạy `preflight` trên một hộp
thư để biết chắc, và nếu nó không nhận thì `master_style = separator` là thứ
đáng thử tiếp.

> `master_password` là mật khẩu mở được **mọi** hộp thư trên server đó. Để nó ra
> file riêng bằng `master_password_file` rồi `chmod 600`, đừng để thẳng trong
> `config.ini` — file này hay bị copy đi copy lại giữa các cuộc migrate.

Chạy `preflight` trên **một** hộp thư trước khi tin cả danh sách: đây là chỗ
duy nhất biết chắc server có chấp nhận hay không.
