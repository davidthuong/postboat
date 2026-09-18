# Lịch và danh bạ: vì sao IMAP không chở được, và làm sao lấy được

Nghiên cứu cho Postboat, 16/09/2026. Mỗi khẳng định kỹ thuật trỏ về tài liệu gốc của nhà cung cấp hoặc RFC.

**Kết luận ngắn:** lịch và danh bạ không đi qua IMAP. Tool ngoài thị trường làm được vì chúng **không dùng IMAP cho hai thứ đó** — chúng đọc Graph / Calendar API / People API / EWS / CalDAV, rồi ghi vào đích bằng CalDAV/CardDAV hoặc API PIM. Postboat hiện đang skip folder `Calendar`/`Contacts` trên Zimbra và IceWarp là **đúng**, không phải thiếu sót của imapsync.

---

## 1. Cái Postboat đang làm, và vì sao nó dừng ở mail

Postboat dựng trên [imapsync](https://github.com/imapsync/imapsync). Tác giả imapsync ghi thẳng:

> “No, Imapsync can't migrate Contacts, Calendars, Tasks nor Chat messages. […] messages synced by imapsync from Contacts/Calendars/Tasks/Chat folders are not used by email servers to set or get the contacts, calendars, tasks, or chat messages. **No way via IMAP, no way via imapsync.**”
>
> — [imapsync FAQ.Contacts_Calendars.txt](https://imapsync.lamiral.info/FAQ.d/FAQ.Contacts_Calendars.txt)

Microsoft nói cùng một câu cho sản phẩm migrate IMAP của chính họ:

> “You can only migrate items in a user's inbox or other mail folders. This type of migration doesn't migrate contacts, calendar items, or tasks.”
>
> — [Migrating IMAP mailboxes to Microsoft 365](https://learn.microsoft.com/en-us/exchange/mailbox-migration/migrating-imap-mailboxes/migrating-imap-mailboxes)

Và IMAP trên Exchange Online “don't offer rich email, **calendaring, and contact management**”:
[POP3 and IMAP4 in Exchange Online](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/pop3-and-imap4/pop3-and-imap4).

Hai chỗ Postboat đã xử lý đúng:

| Chỗ | Việc đã làm | Vì sao đúng |
|---|---|---|
| `postboat/providers.py` Zimbra/IceWarp `skip_names` | Bỏ `Calendar`, `Contacts`, `Tasks`, `Notes` | Đó là folder PIM giả trên đường IMAP, không phải mail |
| `postboat/handover.py` `OUT_OF_SCOPE` | Ghi rõ lịch và danh bạ không đi qua IMAP | Nói trước thì là phạm vi; để khách tự phát hiện sau cutover thì là sự cố |
| `README.md` mục M365 | “Calendar, Contacts, Tasks, Notes — Exchange không bày các folder này ra đường IMAP” | Đúng với tài liệu Microsoft |

Token OAuth hiện tại của Postboat chỉ xin `IMAP.AccessAsApp` (`postboat/oauth.py`). Quyền đó **không** đọc được lịch hay danh bạ — Microsoft cấp nó cho IMAP/POP/SMTP, không cho Graph calendar/contacts ([Authenticate IMAP/POP/SMTP with OAuth](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth)).

---

## 2. Tool ngoài thị trường làm gì, thật ra

Không có “bạc đạn”. Mỗi hãng gắn thêm một ống PIM bên cạnh ống mail.

| Tool | Mail | Lịch | Danh bạ | IMAP cho PIM? |
|---|---|---|---|---|
| **BitTitan MigrationWiz** | EWS (sắp chuyển Graph) hoặc Gmail API / IMAP | EWS `IPM.Appointment` hoặc [Google Calendar API](https://developers.google.com/workspace/calendar/api/guides/overview) | EWS `IPM.Contact` hoặc [People API](https://developers.google.com/people/api/rest) | **Không.** Endpoint “G Suite (IMAP)” vẫn xin scope Calendar + Contacts riêng. [Migrated items](https://help.bittitan.com/hc/en-us/articles/360041736314-MigrationWiz-Migrated-and-Not-Migrated-Items), [Google API setup](https://help.bittitan.com/hc/en-us/articles/360038939774-Google-API-Set-up-to-Migrate-Google-Workspace-Products) |
| **CloudM Migrate** | EWS / Gmail API | Calendar API / EWS | People API / EWS | **Không.** “IMAP will not migrate contacts and calendars this is expected behavior.” [Generic IMAP](https://support.cloudm.io/hc/en-us/articles/11507654470684-Generic-IMAP-to-Microsoft-365-Migration) |
| **IceWarp M365 Migrator** | Graph `Mail.Read` | Graph `Calendars.Read` | Graph `Contacts.Read` | Không. [Pre-migration](https://docs.icewarp.com/Content/M365_Migrator/Pre-migration.htm) |
| **IceWarp Exchange Migrator** | **EWS** | EWS | EWS | Không. [Introduction](https://docs.icewarp.com/Content/Exchange_Migrator/New_Introduction.htm) |
| **Microsoft native GWS → M365** | Gmail API | Calendar API | Contacts + People API | Wizard IMAP của Microsoft **chỉ mail**. PIM đi đường MRS riêng. [IMAP Gmail](https://learn.microsoft.com/en-us/exchange/mailbox-migration/migrating-imap-mailboxes/migrate-g-suite-mailboxes), [G Suite migration](https://learn.microsoft.com/en-us/exchange/mailbox-migration/perform-g-suite-migration) |
| **GWMME** | MAPI/Outlook hoặc IMAP | Outlook MAPI (Exchange nguồn) | Outlook MAPI | IMAP = mail only. [How GWMME works](https://knowledge.workspace.google.com/admin/migrate/how-a-gwmme-migration-works) |
| **imapsync** | IMAP | — | — | Không làm được. |

Cùng một ma trận IceWarp tự công bố: từ Google / M365 / Exchange họ chuyển **Contacts = Yes, Calendars = Yes**; từ Zimbra/MDaemon họ khuyên imapsync — tức mail only. [IceWarp migrator matrix](https://docs.icewarp.com/Content/Exchange_Migrator/New_Introduction.htm).

Những thứ tool lớn **cũng thường bỏ**: lịch chia sẻ và ACL, phòng họp, ảnh danh thiếp, ngoại lệ chuỗi họp (đổi người tham dự trên một lần), đính kèm trên sự kiện Google, “Other Contacts”. Microsoft tắt copy quyền lịch GWS→M365 trên toàn cầu từ tháng 6/2024 ([manual migration](https://learn.microsoft.com/en-us/exchange/mailbox-migration/manual-migration)). Đừng hứa những thứ mà MigrationWiz còn ghi “not migrated”.

---

## 3. Đường đi đúng: hai ống, không một ống

```
Nguồn                         Trung gian              Đích (IceWarp mặc định)
─────                         ────────                ──────────────────────
Google Workspace  ──Calendar API / People API──┐
Microsoft 365     ──Graph Calendars+Contacts──┤
Exchange on-prem  ──EWS────────────────────────┼──►  ICS (RFC 5545)
Zimbra            ──CalDAV / REST ?fmt=ics────┤      vCard (RFC 6352)
IceWarp nguồn     ──CalDAV / CardDAV──────────┤
iCloud / Yahoo / Zoho ──CalDAV / CardDAV──────┘
                                              │
                                              └──►  PUT CalDAV  /webdav/user@domain/Calendar/
                                                    PUT CardDAV /webdav/user@domain/  (Contacts)
```

Định dạng trung gian là iCalendar và vCard — RFC, không phải JSON của một hãng.

- CalDAV: [RFC 4791](https://www.rfc-editor.org/rfc/rfc4791.html) — mỗi sự kiện (kèm ngoại lệ cùng UID) là một resource `text/calendar`.
- CardDAV: [RFC 6352](https://www.rfc-editor.org/rfc/rfc6352.html) — mỗi danh bạ là một vCard.
- Dữ liệu: [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545.html) (iCalendar), vCard 3.0 ([RFC 2426](https://www.rfc-editor.org/rfc/rfc2426.html)).

imapsync đề xuất Outlook CalDav Synchronizer cho đúng đường này ([FAQ](https://imapsync.lamiral.info/FAQ.d/FAQ.Contacts_Calendars.txt)). Zimbra khuyên [vdirsyncer](https://blog.zimbra.com/2024/03/introducing-vdirsyncer-for-migrating-calendars-and-addressbooks/) cho cùng việc. Cả hai là **sync client**, không phải migrate tenant — nhưng protocol thì đúng.

---

## 4. Đọc từ từng nguồn Postboat đã hỗ trợ

### 4.1 Gmail / Google Workspace — job thương mại hay gặp nhất

App password dùng cho IMAP **không** đăng nhập được CalDAV/CardDAV của Google. Google trả `401` nếu Basic Auth:

> “The CalDAV server refuses to authenticate a request unless it arrives over HTTPS with OAuth 2.0 […]. Attempting to connect over HTTP or using Basic Authentication results in an HTTP `401 Unauthorized`.”
>
> — [CalDAV API Developer's Guide](https://developers.google.com/workspace/calendar/caldav)

CardDAV: “Google does not support any other authentication method.” [People CardDAV](https://developers.google.com/people/carddav). Workspace tắt password-based CalDAV/CardDAV từ 14/03/2025 ([LSA → OAuth](https://knowledge.workspace.google.com/admin/sync/transition-from-less-secure-apps-to-oauth)).

**Workspace (cả tổ chức, không xin từng user):** service account + [domain-wide delegation](https://knowledge.workspace.google.com/admin/apps/control-api-access-with-domain-wide-delegation). Google liệt kê “Migration and sync tools” là use case của DWD. Impersonate từng user qua JWT `sub`.

**Gmail cá nhân (`@gmail.com`):** không có DWD. Phải OAuth consent từng account — không scale cho job 200 hộp.

API nên dùng (REST, không phải DAV), vì MigrationWiz/CloudM/Microsoft đều đi đường này:

| Việc | API | Scope đọc |
|---|---|---|
| Liệt kê lịch user đang thấy | `GET …/users/me/calendarList` | `calendar.readonly` |
| Sự kiện (giữ RRULE, không bung occurrence) | `GET …/calendars/{id}/events` (`singleEvents=false`) | `calendar.readonly` / `calendar.events.readonly` |
| Danh bạ đã lưu | `people.connections.list` | `contacts.readonly` |
| “Other contacts” (tự tạo từ mail) | `otherContacts.list` | `contacts.other.readonly` — **chỉ** trả tên/email/SĐT |

- Calendar API: [overview](https://developers.google.com/workspace/calendar/api/guides/overview), [scopes](https://developers.google.com/workspace/calendar/api/auth), [events.list](https://developers.google.com/workspace/calendar/api/v3/reference/events/list), [quota 600 req/phút/user](https://developers.google.com/workspace/calendar/api/guides/quota).
- People API: [REST](https://developers.google.com/people/api/rest). Contacts API tắt ngày 19/01/2022 ([migration](https://developers.google.com/people/contacts-api-migration)).
- CalDAV Google không hỗ trợ `VTODO`/`VJOURNAL`; CardDAV dùng vCard 3.0.

**Không lấy được nếu chỉ đọc lịch chính:** lịch được share, lịch ẩn, quyền ACL, phòng họp Google. MigrationWiz mặc định chỉ lịch **owned**; phải bật `MigrateGmailAllCalendar=1` mới lấy thêm.

### 4.2 Microsoft 365 / Exchange Online

IMAP.AccessAsApp **không đủ**. Thêm Graph application permissions trên **cùng app Entra** Postboat đã đăng ký:

| Quyền Graph | Việc |
|---|---|
| `Calendars.Read` | Đọc mọi lịch mailbox, không cần user đăng nhập |
| `Contacts.Read` | Đọc danh bạ cá nhân trong mailbox |

[Permissions reference](https://learn.microsoft.com/en-us/graph/permissions-reference): `Calendars.Read` application = “read events of all calendars without a signed-in user.” Admin consent bắt buộc.

Gọi:

```
GET /users/{upn}/calendars
GET /users/{upn}/calendars/{id}/events          ← series master + single, không bung
GET /users/{upn}/calendarView?startDateTime&endDateTime  ← nếu đích không hiểu RRULE
GET /users/{upn}/contactFolders
GET /users/{upn}/contacts
```

[calendar resource](https://learn.microsoft.com/en-us/graph/api/resources/calendar?view=graph-rest-1.0), [contact resource](https://learn.microsoft.com/en-us/graph/api/resources/contact?view=graph-rest-1.0), [calendar overview](https://learn.microsoft.com/en-us/graph/outlook-calendar-concept-overview).

Graph **không** vào In-Place Archive — cùng hạn chế mail Postboat đã ghi trong README.

**Phạm vi mailbox:** đừng cấp `Calendars.Read` tenant-wide rồi quên. Dùng [RBAC for Applications](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac) (`Application Calendars.Read` + `Application Contacts.Read` trên management scope). Nếu vừa để quyền Graph không scoped ở Entra vừa scoped ở Exchange thì union = không scoped. IceWarp M365 Migrator xin đúng `Calendars.Read` + `Contacts.Read` ([Pre-migration](https://docs.icewarp.com/Content/M365_Migrator/Pre-migration.htm)) — họ không scoped, Postboat nên scoped vì đã làm vậy với IMAP.

Sự kiện đánh dấu private: app-only Graph trả “object was not found” trừ khi mailbox có FullAccess hoặc delegate CanViewPrivateItems ([list events](https://learn.microsoft.com/en-us/graph/api/calendar-list-events?view=graph-rest-1.0)).

Throttle Outlook: **10.000 request / 10 phút / (app, mailbox)** và **4 request đồng thời** trên một mailbox ([throttling limits](https://learn.microsoft.com/en-us/graph/throttling-limits)). Song song theo **nhiều mailbox**, không đào sâu một hộp.

GAL (`orgContact`) là directory, quyền `OrgContact.Read.All` — **không** phải danh bạ cá nhân. Đừng trộn hai thứ.

### 4.3 Exchange tự dựng

Graph không còn nói chuyện với mailbox on-prem (hybrid REST tắt 07/2023). Đường còn lại: **EWS** + `ApplicationImpersonation`. IceWarp Exchange Migrator đi đúng đường này. EWS trên Exchange Online bị tắt dần 10/2026–04/2027; on-prem thì vẫn sống. Job nguồn là Exchange 2016/2019 tự dựng thì EWS, không Graph.

### 4.4 Zimbra

IMAP folder `Calendar`/`Contacts` **không** chứa iCalendar/vCard dùng được. Zimbra tự nói IMAP migration không cover PIM; phải REST hoặc CalDAV ([Calendar and Contacts Migration](https://wiki.zimbra.com/wiki/Calendar_and_Contacts_Migration)).

Đọc:

```
GET https://zimbra/home/{user}/calendar?fmt=ics
GET https://zimbra/home/{user}/contacts?fmt=vcf
```

hoặc CalDAV `https://zimbra/dav/{user}/Calendar` ([CalDAV Support](https://wiki.zimbra.com/wiki/CalDav_Support), Thunderbird: `/dav/<user>/Calendar` và `/dav/<user>/Contacts`).

PUT lên Zimbra: tên file phải `{UID}.ics`, không thì fail; POST (RFC 5995) cho server đặt tên. CalDAV Zimbra **không** chuyển attachment.

### 4.5 IceWarp nguồn

Cùng URL dùng khi IceWarp là đích. GroupWare là kho thật; folder IMAP chỉ là mặt nạ ([Shared Items](https://docs.icewarp.com/Content/IceWarp-Server/Administration-Nodes/GroupWare/Sharing%20Concepts/Shared%20Items.htm), [Databases](https://docs.icewarp.com/Content/IceWarp-Server/Related-Topics/IceWarp%20ServerDatabases.htm)).

### 4.6 iCloud, Yahoo, Zoho

| Nguồn | Lịch | Danh bạ | Auth |
|---|---|---|---|
| iCloud | CalDAV, discovery `caldav.icloud.com` (RFC 6764) | CardDAV `contacts.icloud.com` | App-specific password ([Apple](https://support.apple.com/en-us/102654)) |
| Yahoo | `https://caldav.calendar.yahoo.com` ([SLN4704](https://help.yahoo.com/kb/SLN4704.html)) | CardDAV (ít tài liệu URL cố định) | App password |
| Zoho | `https://calendar.zoho.com/` (DC `.eu` / `.in` / …) [CalDAV help](https://www.zoho.com/calendar/help/setup-caldav-sync.html) | `https://contacts.zoho.com/carddav` [CardDAV](https://help.zoho.com/portal/en/kb/zoho-contacts/articles/carddav) | App password |

### 4.7 Dovecot / cPanel / Courier

Hosting Maildir thường **không có** lịch/danh bạ phía server. Cái khách gọi là “danh bạ” nằm trong Outlook/Thunderbird local. Không có API để lấy. Nói trước trong handover, đừng hứa.

---

## 5. Ghi vào IceWarp (đích mặc định)

IceWarp nhận lịch/danh bạ qua **WebDAV**, không qua IMAP APPEND.

```
https://mail.{domain}/webdav/{email}              ← gốc, CardDAV Contacts nằm dưới này
https://mail.{domain}/webdav/{email}/Calendar/    ← CalDAV
https://mail.{domain}/webdav/{email}/Tasks/       ← VTODO
```

Nguồn IceWarp:

- Desktop Client: [add calendars and contacts manually](https://docs.icewarp.com/Content/Desktop_Client/Settings/How%20to_settings/How%20to%20add%20calendars%20and%20contacts%20manually.htm) — `https://mail.{domain}/webdav/{email}`, user = email, password = mật khẩu hộp.
- Thunderbird: `http://hostname/webdav/user@domain.com/Calendar/` ([KB](https://support.icewarp.co.in/hc/en-us/articles/20847462364057-How-To-Sync-Calendars-In-Thunderbird-Using-CalDav)).
- WebDAV module: CalDAV + CardDAV + GroupDAV; **WebFolders không cần license GroupWare**, nhưng object lịch/contact thật sống trong database GroupWare ([WebDAV](https://docs.icewarp.com/Content/IceWarp-Server/Administration-Nodes/GroupWare/Reference/WebDAV.htm)).

Auth: HTTP Basic, username = địa chỉ đầy đủ. Bật dịch vụ WebDAV (System → Services) và GroupWare phải sống.

Ghi từng object:

1. `PROPFIND` để tìm collection Calendar / Contacts.
2. Tách ICS nguồn thành **một resource / UID** (master + `RECURRENCE-ID` đi cùng).
3. `PUT` `text/calendar` với `If-None-Match: *`. Giữ UID gốc để chạy lại không nhân bản (`no-uid-conflict` trong RFC 4791).
4. `PUT` `text/vcard` từng contact.

Đường phụ trên chính server IceWarp: `importcontacts.php` (vCard hàng loạt, [Contacts Migration Script](https://docs.icewarp.com/Content/IceWarp-Server/Administration-Nodes/System%20Node/Tools/Server%20Migration/Contacts%20Migration%20Script.htm)) và GroupWare API `AddvCalendar()` (nhiều VEVENT một lần). Chỉ dùng khi agent chạy **trên** máy IceWarp; từ VPS Postboat thì CalDAV PUT là đường đúng.

**Cạm bẫy lịch họp:** server CalDAV có [RFC 6638](https://www.rfc-editor.org/rfc/rfc6638.html) (Zimbra có, IceWarp có SRV `_ischedule`). PUT một VEVENT còn `ORGANIZER`/`ATTENDEE` có thể **gửi lại lời mời cho cả công ty**. Trước khi PUT: bỏ `METHOD`, hoặc đặt `SCHEDULE-AGENT=CLIENT`/`NONE` nếu server nhận. Đây là chỗ dễ biến migrate thành sự cố.

**Đo thật 17/09/2026, Zimbra 8.8.15 FOSS (lab VPS, Zimbra → Zimbra qua CalDAV):**

| Thử | Kết quả |
|---|---|
| PUT bởi hộp đích, hộp đích **là ORGANIZER**, có `SCHEDULE-AGENT=CLIENT` | Zimbra **gửi lời mời** cho attendee, y như không có tham số |
| PUT bởi hộp đích, hộp đích **là ATTENDEE** (PARTSTAT=ACCEPTED) | Zimbra **gửi "Accept:" reply** cho organizer |
| PUT bởi hộp đích, hộp đích không phải organizer lẫn attendee | Không gửi gì |
| `zmprov mcf zimbraCalendarCalDavDisableScheduling TRUE` + `zmprov fc -a all` (global config; đặt ở account bị LDAP từ chối) | **Chặn cả hai chiều**, không cần restart mailboxd |
| PUT đè lên UID đã có với `If-None-Match: *` | Trả 2xx chứ không 412 — "đã có" phải hỏi bằng PROPFIND trước |
| Tên file `{UID}.ics` với `@` trong UID, RRULE `UNTIL` dạng UTC, vCard 3.0 | Nhận nguyên vẹn; href trả về mã hoá `%40` cho `@` |
| Cùng phép `If-None-Match: *` nhưng trên **CardDAV** (18/09, `testrig/pimprobe.py`) | Trả **412** — Zimbra chỉ phớt lờ ở đường lịch. "Server này có tôn trọng `If-None-Match` không" là câu hỏi theo từng collection, không phải theo server |

Kết luận cho Postboat: `SCHEDULE-AGENT=CLIENT` không đủ làm mặc định. Mặc định phải bỏ `ORGANIZER`/`ATTENDEE` khỏi sự kiện có người tham dự (giữ dưới dạng `X-POSTBOAT-*`, ghi danh sách vào `DESCRIPTION`); chỉ giữ nguyên khi admin đích đã tắt scheduling CalDAV — với Zimbra là lệnh trên, với IceWarp **chưa đo**.

---

## 6. Việc “làm được” trông như thế nào, và việc không hứa

### Làm được ở mức khách nhận hộp mới và thấy lịch/danh bạ

- Lịch chính của từng user: sự kiện một lần + chuỗi RRULE.
- Danh bạ đã lưu (My Contacts / mailbox Contacts): tên, email, SĐT, công ty, địa chỉ.
- Chạy lại không nhân bản (UID giữ nguyên).
- Báo cáo: N sự kiện / N danh bạ đã PUT, N bỏ vì đã có, N lỗi.

### Không hứa ở v1 — tool lớn cũng thường miss

| Hạng mục | Vì sao |
|---|---|
| Lịch chia sẻ + ACL | Microsoft native không migrate shared calendars; quyền lịch GWS→M365 tắt 06/2024 |
| Phòng họp / resource mailbox | API riêng, thường job thứ hai |
| Ảnh danh thiếp | Mất trên nhiều cặp nguồn–đích |
| “Other Contacts” / GAL | Khác store, khác quyền; Other Contacts Google chỉ 3 field |
| Ngoại lệ chuỗi họp (đổi attendee trên một lần) | CloudM/MigrationWiz cùng ghi không hết |
| Đính kèm trên sự kiện Google | Calendar API trỏ Drive, không nhét file vào ICS |
| Tasks / Notes | Làm được sau (VTODO → `/Tasks/`), không gói chung v1 |
| Bộ lọc, chữ ký, OOO | Vẫn ngoài phạm vi — IceWarp migrator cũng No |

---

## 7. Gợi ý cho Postboat (chưa implement)

Giữ nguyên ống imapsync. Thêm ống PIM chạy **sau** mail (hoặc song song, khác worker). Không `pip install`: CalDAV là HTTP+XML (`http.client` + `xml.etree`), Graph/Google REST là HTTP+JSON — cùng kiểu `oauth.py` hiện tại.

Thứ tự nên làm, vì khớp job thật (đích IceWarp):

1. **Ghi IceWarp CalDAV/CardDAV** — một lần, dùng cho mọi nguồn. Không có bước này thì đọc nguồn xong cũng không đổ được.
2. **Đọc Google Workspace** (DWD + Calendar API + People API) — nguồn hay gặp, auth khác hẳn app password IMAP.
3. **Đọc M365 Graph** trên app Entra đã có, thêm `Calendars.Read` + `Contacts.Read`, scoped bằng RBAC. Cùng `users.csv`.
4. **Đọc Zimbra REST ICS/VCF** — rẻ, không OAuth.
5. Mới tính Exchange on-prem EWS, iCloud/Yahoo/Zoho DAV, VTODO.

Prep mới (in ra bởi `providers`):

- Google Workspace: tạo service account, bật Calendar API + People API, DWD các scope `calendar.readonly`, `contacts.readonly` (và `contacts.other.readonly` nếu khách muốn Other Contacts).
- M365: trên app hiện có, thêm Graph application `Calendars.Read` + `Contacts.Read`, admin consent, `New-ManagementRoleAssignment` scoped — **gỡ** quyền Graph tenant-wide nếu đã lỡ add.
- IceWarp đích: WebDAV + GroupWare bật, thử `PROPFIND` một hộp trước khi chạy hàng loạt.

Handover: đổi câu “IMAP chỉ chở thư” thành “thư đi IMAP; lịch/danh bạ đi ống riêng nếu hợp đồng có”. Không xóa mục out-of-scope cho ACL / phòng họp / filter.

Ước lượng trung thực với khách: ống PIM nhỏ hơn mail rất nhiều (vài nghìn object, không phải GB), nhưng **auth và mapping** mới là công. Một job Google Workspace → IceWarp có lịch/danh bạ là DWD + CalDAV PUT, không phải “bật thêm flag imapsync”.

---

## Nguồn (đã mở trang)

### Vì sao IMAP không đủ
- https://imapsync.lamiral.info/FAQ.d/FAQ.Contacts_Calendars.txt
- https://learn.microsoft.com/en-us/exchange/mailbox-migration/migrating-imap-mailboxes/migrating-imap-mailboxes
- https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/pop3-and-imap4/pop3-and-imap4

### Google
- https://developers.google.com/workspace/calendar/api/guides/overview
- https://developers.google.com/workspace/calendar/api/auth
- https://developers.google.com/workspace/calendar/caldav
- https://developers.google.com/people/api/rest
- https://developers.google.com/people/carddav
- https://developers.google.com/people/contacts-api-migration
- https://knowledge.workspace.google.com/admin/apps/control-api-access-with-domain-wide-delegation
- https://knowledge.workspace.google.com/admin/sync/transition-from-less-secure-apps-to-oauth

### Microsoft
- https://learn.microsoft.com/en-us/graph/api/resources/calendar?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/resources/contact?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/outlook-calendar-concept-overview
- https://learn.microsoft.com/en-us/graph/permissions-reference
- https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac
- https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth
- https://learn.microsoft.com/en-us/graph/throttling-limits
- https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/deprecation-of-ews-exchange-online

### IceWarp
- https://docs.icewarp.com/Content/Desktop_Client/Settings/How%20to_settings/How%20to%20add%20calendars%20and%20contacts%20manually.htm
- https://docs.icewarp.com/Content/IceWarp-Server/Administration-Nodes/GroupWare/Reference/WebDAV.htm
- https://docs.icewarp.com/Content/M365_Migrator/Pre-migration.htm
- https://docs.icewarp.com/Content/Exchange_Migrator/New_Introduction.htm
- https://docs.icewarp.com/Content/IceWarp-Server/Administration-Nodes/System%20Node/Tools/Server%20Migration/Contacts%20Migration%20Script.htm

### Zimbra / RFC / đối thủ
- https://wiki.zimbra.com/wiki/CalDav_Support
- https://wiki.zimbra.com/wiki/Calendar_and_Contacts_Migration
- https://www.rfc-editor.org/rfc/rfc4791.html
- https://www.rfc-editor.org/rfc/rfc6352.html
- https://www.rfc-editor.org/rfc/rfc5545.html
- https://help.bittitan.com/hc/en-us/articles/360041736314-MigrationWiz-Migrated-and-Not-Migrated-Items
- https://support.cloudm.io/hc/en-us/articles/11507654470684-Generic-IMAP-to-Microsoft-365-Migration
- https://learn.microsoft.com/en-us/exchange/mailbox-migration/perform-g-suite-migration
