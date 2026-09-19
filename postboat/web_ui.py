# -*- coding: utf-8 -*-
"""Trang HTML cua dashboard. Tu chua tat ca, khong tai gi tu ben ngoai."""

# Logo nhung thang vao trang duoi dang data: URI chu khong phai mot duong dan
# /logo.png. Ly do: trang nay tu chua tat ca -- khong goi ra ngoai thi khong co
# gi de chan, va khong phai them mot route phuc vu file tinh nao vao web.py.
# Doi lai, CSP phai cho phep img-src data: (xem _send trong web.py).
#
# Anh goc: brand/postboat-icon.png, cat sat noi dung roi thu ve 64px. O 16px no
# chi con la mot vet xanh-navy; favicon that van can mot ban ve rieng don gian
# hon -- xem brand/README.md.
ICON = "data:image/png;base64,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"

PAGE = r"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Postboat</title>
<link rel="icon" type="image/png" href="__ICON__">
<style>
 :root{
   --bg:#f6f7f9; --panel:#fff; --ink:#16191d; --muted:#6b7280; --line:#e3e6ea;
   --accent:#2563eb; --ok:#137333; --err:#c5221f; --warn:#a16207; --warnbg:#fffbe6;
   --code:#0f172a; --codeink:#d7dde8;
 }
 @media (prefers-color-scheme:dark){
   :root{
     --bg:#0f1216; --panel:#171b21; --ink:#e6e9ee; --muted:#98a2b3; --line:#262c35;
     --accent:#60a5fa; --ok:#4ade80; --err:#f87171; --warn:#fbbf24; --warnbg:#2a2410;
     --code:#0b0e12; --codeink:#c8d2e0;
   }
 }
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--ink);
      font:14px/1.5 system-ui,"Segoe UI",Roboto,Arial,sans-serif}
 header{background:var(--panel);border-bottom:1px solid var(--line);
        padding:.85rem 1.25rem;display:flex;gap:1.25rem;align-items:baseline;flex-wrap:wrap}
 header h1{font-size:1rem;margin:0;font-weight:650;letter-spacing:-.01em}
 header .route{color:var(--muted);font-size:13px}
 header .route b{color:var(--ink);font-weight:600}
 main{padding:1.25rem;max-width:1400px;margin:0 auto;display:grid;gap:1.25rem}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
 .card > h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;
            color:var(--muted);margin:0;padding:.7rem 1rem;border-bottom:1px solid var(--line)}
 .pad{padding:1rem}
 .bar{display:flex;gap:.45rem;flex-wrap:wrap;align-items:center;padding:1rem;
      border-bottom:1px solid var(--line)}
 button{font:inherit;padding:.42rem .8rem;border-radius:7px;border:1px solid var(--line);
        background:var(--bg);color:var(--ink);cursor:pointer}
 button:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
 button:disabled{opacity:.45;cursor:not-allowed}
 button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
 button.primary:hover:not(:disabled){filter:brightness(1.08);color:#fff}
 button.danger{border-color:var(--err);color:var(--err)}
 .sep{width:1px;height:22px;background:var(--line);margin:0 .35rem}
 .scope{color:var(--muted);font-size:13px;margin-left:auto}
 /* 10 cot khong bop vua man hep duoc. Khong co khung cuon nay thi
    .card{overflow:hidden} cat cut tu cot "Ket qua" tro di -- ke ca nut xoa
    va dau chi sang muc "Can xu ly" -- ma khong con cach nao voi toi. */
 .tablewrap{overflow-x:auto}
 table{width:100%;min-width:880px;border-collapse:collapse;font-size:13px}
 th,td{padding:.5rem .7rem;text-align:left;border-bottom:1px solid var(--line);
       vertical-align:top}
 th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;
    letter-spacing:.04em;white-space:nowrap}
 tbody tr:last-child td{border-bottom:none}
 tbody tr:hover{background:color-mix(in srgb,var(--accent) 6%,transparent)}
 td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
 .badge{display:inline-block;padding:.1rem .45rem;border-radius:999px;font-size:11.5px;
        font-weight:600;border:1px solid transparent;white-space:nowrap}
 .b-ok{color:var(--ok);border-color:var(--ok)}
 .b-err{color:var(--err);border-color:var(--err)}
 .b-idle{color:var(--muted);border-color:var(--line)}
 /* Goi y sua loi la van xuoi dai. De trong o "Ghi chu" thi dong bang bi keo
    cao va cac cot ben trai bo trong ca mang; o man hep thi cot bi bop lai den
    muc khong doc duoc. Cho no card rieng ben duoi bang. */
 .more{font-size:11.5px;color:var(--warn);white-space:nowrap}
 #fixcount,#pimcount{text-transform:none;font-weight:400;color:var(--muted);
                     margin-left:.4rem}
 /* Bang lich/danh ba chi co sau cot nen hep hon bang chinh (880px), nhung van
    phai co min-width: bo han thi tren dien thoai cac cot bi bop den muc dia
    chi xuong hai dong, ma dong nao co cau loi thi keo cao ca hang len trong
    khi cot loi nam ngoai man hinh -- nguoi xem thay mot o trong cao ngoang.
    Cho no cuon ngang nhu bang chinh. */
 #pimtable{min-width:760px}
 #pimnote{padding-top:.8rem}
 #pimnote .pair{margin-top:.25rem}
 #pimnote .pair b{color:var(--ink);font-weight:600;word-break:break-all}
 /* Loi cua mot dong lich/danh ba la cau van, khong phai nhan -- phai cho
    xuong dong, khac voi .more. */
 .tip{font-size:11.5px;color:var(--err);white-space:normal;max-width:34ch;
      margin-top:.2rem}
 .fix{padding:.7rem 1rem;border-left:3px solid var(--err);
      border-bottom:1px solid var(--line)}
 .fix:last-child{border-bottom:none}
 .fix .who{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
 .fix .who b{font-weight:600}
 .fix p{margin:.4rem 0 0;font-size:13px;line-height:1.6;max-width:74ch;
        color:var(--muted)}
 pre{margin:0;padding:1rem;background:var(--code);color:var(--codeink);
     font:12.5px/1.55 ui-monospace,"SFMono-Regular",Consolas,monospace;
     overflow:auto;max-height:26rem;white-space:pre-wrap;word-break:break-word}
 .job{display:flex;gap:.7rem;align-items:center;padding:.7rem 1rem;
      border-bottom:1px solid var(--line);flex-wrap:wrap}
 .dot{width:9px;height:9px;border-radius:50%;background:var(--muted);flex:none}
 .dot.run{background:var(--accent);animation:pulse 1.1s ease-in-out infinite}
 .dot.ok{background:var(--ok)} .dot.err{background:var(--err)}
 @keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
 form.add{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
          gap:.6rem;padding:1rem;align-items:end}
 label{display:block;font-size:12px;color:var(--muted);margin-bottom:.25rem}
 input{font:inherit;width:100%;padding:.42rem .6rem;border-radius:7px;
       border:1px solid var(--line);background:var(--bg);color:var(--ink)}
 input:focus{outline:2px solid color-mix(in srgb,var(--accent) 45%,transparent);
             outline-offset:1px;border-color:var(--accent)}
 .note{color:var(--muted);font-size:12.5px;padding:0 1rem 1rem}
 .err{color:var(--err)}
 .empty{padding:2rem 1rem;text-align:center;color:var(--muted)}
 button.rm{padding:.1rem .4rem;font-size:12px;line-height:1.3;color:var(--muted);
           border-color:transparent;background:transparent}
 button.rm:hover:not(:disabled){color:var(--err);border-color:var(--err)}
 td.act{text-align:right;white-space:nowrap}
 .brand{display:flex;align-items:center;gap:.5rem}
 .logo{width:26px;height:26px;flex:none}
 /* Danh sach tep: mot dem chay 200 hop sinh ra 200 log, nen phai co khung
    cuon rieng thay vi keo trang dai ra vo tan. */
 .files{max-height:20rem;overflow:auto}
 .file{display:flex;gap:.6rem;align-items:baseline;padding:.45rem 1rem;
       border-bottom:1px solid var(--line);font-size:13px}
 .file:last-child{border-bottom:none}
 .file a{color:var(--accent);font-weight:500;word-break:break-all}
 .file .size,.file .when{color:var(--muted);font-size:12px;white-space:nowrap}
 .file .when{margin-left:auto}
</style>
</head>
<body>
<header>
  <div class="brand">
    <img class="logo" src="__ICON__" alt="" width="26" height="26">
    <h1>Postboat</h1>
  </div>
  <div class="route">
    <b id="src">…</b> &rarr; <b id="dst">…</b>
  </div>
  <div class="route" id="meta"></div>
</header>

<main>
  <section class="card">
    <div class="bar">
      <button data-act="preflight">Kiểm tra đăng nhập</button>
      <button data-act="discover">Kế hoạch folder</button>
      <button data-act="dest" id="btn-dest">Folder bên đích</button>
      <button data-act="sizes">Đo dung lượng</button>
      <span class="sep"></span>
      <button data-act="folders">Tạo cây folder</button>
      <button data-act="dry">Chạy khan</button>
      <button data-act="sync" class="primary">Chạy thật</button>
      <button data-act="resume" title="Bỏ qua mailbox đã chạy xong trước đó">Chạy tiếp</button>
      <span class="sep"></span>
      <button data-act="verify">Đối chiếu ngày</button>
      <span class="scope" id="scope"></span>
    </div>
    <div class="tablewrap">
    <table>
      <thead><tr>
        <th style="width:28px"><input type="checkbox" id="all" title="Chọn tất cả"></th>
        <th>Nguồn</th><th>Đích</th><th>Kết quả</th>
        <th class="num">Folder</th><th class="num">Mail</th>
        <th class="num">Dung lượng</th><th class="num">Thời gian</th>
        <th>Ghi chú</th><th></th>
      </tr></thead>
      <tbody id="rows"><tr><td colspan="10" class="empty">Đang tải…</td></tr></tbody>
    </table>
    </div>
  </section>

  <section class="card" id="fix" hidden>
    <h2>Cần xử lý <span id="fixcount"></span></h2>
    <div id="fixlist"></div>
  </section>

  <!-- Lịch và danh bạ đi ống riêng: không qua imapsync mà đọc CalDAV/CardDAV
       (hoặc Microsoft Graph) bên nguồn rồi PUT CalDAV/CardDAV bên đích. Để
       chung thanh nút với "Chạy thật" ở trên thì dễ bấm nhầm, mà nhầm ở đây
       là ghi thẳng vào lịch người ta -- nên nó có thẻ riêng. -->
  <section class="card">
    <h2>Lịch &amp; danh bạ <span id="pimcount"></span></h2>
    <div class="bar" id="pimbar">
      <button data-act="pim-dry" title="Đọc nguồn, đếm mục, không ghi gì">Đọc thử</button>
      <button data-act="pim" class="primary">Chuyển lịch &amp; danh bạ</button>
      <span class="scope" id="pimscope"></span>
    </div>
    <div class="note" id="pimnote"></div>
    <div class="tablewrap" id="pimwrap" hidden>
    <table id="pimtable">
      <thead><tr>
        <th>Nguồn</th><th>Đích</th>
        <th class="num">Sự kiện lịch</th><th class="num">Danh bạ</th>
        <th>Kết quả</th><th>Lúc</th>
      </tr></thead>
      <tbody id="pimrows"></tbody>
    </table>
    </div>
  </section>

  <section class="card">
    <div class="job">
      <span class="dot" id="dot"></span>
      <b id="jobname">Chưa chạy tác vụ nào</b>
      <span class="route" id="jobinfo"></span>
    </div>
    <pre id="log">Kết quả sẽ hiện ở đây.</pre>
  </section>

  <section class="card">
    <h2>Công cụ &amp; tệp</h2>
    <div class="bar">
      <button data-act="doctor" data-global="1">Kiểm tra môi trường</button>
      <button data-act="providers" data-global="1">Nguồn được hỗ trợ</button>
      <span class="sep"></span>
      <button data-act="report" data-global="1">Xuất báo cáo</button>
      <button data-act="handover" data-global="1"
              title="Biên bản để in ra PDF và ký với khách">Biên bản bàn giao</button>
      <span class="scope">Áp dụng cho cả cuộc migrate, không theo lựa chọn ở trên</span>
    </div>
    <div class="files" id="files"><div class="empty">Đang tải…</div></div>
    <div class="note">
      Tệp nằm trong <code id="logdir">logs/</code> trên máy chủ này. Bấm để tải
      về; trình duyệt không mở tại chỗ. Mở từ ổ đĩa rồi in ra PDF để ký.
    </div>
  </section>

  <section class="card">
    <h2>Thêm mailbox</h2>
    <form class="add" id="addform" autocomplete="off">
      <div><label id="lb-src">Địa chỉ nguồn</label>
           <input name="src_user" placeholder="an@congty-cu.com" required></div>
      <div id="wrap-srcpass"><label id="lb-srcpass">Mật khẩu nguồn</label>
           <input name="src_password" type="password"></div>
      <div><label id="lb-dst">Địa chỉ đích</label>
           <input name="dst_user" placeholder="an@congty.vn" required></div>
      <div id="wrap-dstpass"><label id="lb-dstpass">Mật khẩu đích</label>
           <input name="dst_password" type="password" required></div>
      <div><button type="submit" class="primary">Thêm vào danh sách</button></div>
    </form>
    <!-- Chỗ báo kết quả thêm mailbox phải là một thẻ RIÊNG, không được viết
         đè lên khối ghi chú: khối đó chứa <code id="usersfile">, mà gán
         textContent lên cha thì xoá sạch con. Sau đó refresh() chạm vào
         $("usersfile") đã biến mất, ném lỗi trước khi kịp gọi schedule(),
         và cả vòng cập nhật chết hẳn -- dashboard đứng hình không một lời
         báo cho tới khi tải lại trang. -->
    <div class="note" id="addstatus"></div>
    <div class="note" id="addnote">
      Ghi thẳng vào <code id="usersfile">users.csv</code> trên máy chủ này.
      Mật khẩu không bao giờ được gửi ngược về trình duyệt.
      Muốn sửa một dòng thì xoá bằng dấu ✕ ở cuối dòng rồi thêm lại.
    </div>
  </section>
</main>

<script>
"use strict";
const $ = (id) => document.getElementById(id);
// Dat chu vao mot o, bo qua neu o do khong con. Xem ghi chu trong refresh().
const text = (id, value) => { const el = $(id); if (el) el.textContent = value; };
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g,
  (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

let state = null, selected = new Set(), timer = null, stick = true;

function scope() {
  return selected.size ? Array.from(selected) : [];
}

function renderScope() {
  const n = selected.size;
  // Cùng một lựa chọn chi phối cả hai thẻ có nút chạy theo mailbox, nên cả
  // hai phải nói ra nó. Thẻ lịch/danh bạ nằm xa bảng chọn hơn, ai kéo thẳng
  // xuống đó bấm mà không thấy dòng này sẽ tưởng nó chạy cho tất cả.
  const s = n
    ? n + " mailbox được chọn"
    : (state && state.mailboxes.length
        ? "Áp dụng cho tất cả " + state.mailboxes.length + " mailbox"
        : "");
  text("scope", s);
  text("pimscope", s ? s + " (chọn ở bảng trên)" : "");
}

function badge(m) {
  if (m.ket_qua === "OK")  return '<span class="badge b-ok">OK</span>';
  if (m.ket_qua === "LOI") return '<span class="badge b-err">LỖI</span>';
  // Chua chay sync, nhung co the da kiem dang nhap. Noi ra thay vi de "chua
  // chay": voi 200 mailbox thi cot nay la cho duy nhat nhin mot phat ra 15
  // hop sai mat khau, khong ai di cuon log tim.
  // Ket qua sync co roi thi no thang -- no moi la viec that su da lam.
  const p = m.preflight;
  if (p) {
    return p.ok ? '<span class="badge b-ok">đăng nhập OK</span>'
                : '<span class="badge b-err">đăng nhập LỖI</span>';
  }
  return '<span class="badge b-idle">chưa chạy</span>';
}

function renderRows() {
  const box = $("rows");
  if (!state.mailboxes.length) {
    box.innerHTML = '<tr><td colspan="10" class="empty">' +
      'Chưa có mailbox nào. Thêm ở khung bên dưới.</td></tr>';
    return;
  }
  box.innerHTML = state.mailboxes.map((m) => {
    // Goi y day du nam o card "Can xu ly"; trong bang chi de mot dau chi cho.
    const more = fixTips(m).length
      ? ' <span class="more">↓ cần xử lý</span>' : "";
    const warn = (!m.has_src_password || !m.has_dst_password)
      ? ' <span class="badge b-err">thiếu mật khẩu</span>' : "";
    return '<tr><td><input type="checkbox" data-u="' + esc(m.src_user) + '"' +
      (selected.has(m.src_user) ? " checked" : "") + "></td>" +
      "<td>" + esc(m.src_user) + (m.done ? ' <span class="badge b-ok">đã xong</span>' : "") + "</td>" +
      "<td>" + esc(m.dst_user) + "</td>" +
      "<td>" + badge(m) + "</td>" +
      '<td class="num">' + esc(m.folder) + "</td>" +
      '<td class="num">' + esc(m.mail) + "</td>" +
      '<td class="num">' + esc(m.dung_luong) + "</td>" +
      '<td class="num">' + esc(m.thoi_gian) + "</td>" +
      "<td>" + esc(m.ghi_chu) + warn + more + "</td>" +
      '<td class="act"><button class="rm" data-rm="' + esc(m.src_user) +
      '" title="Xoá khỏi danh sách">✕</button></td></tr>';
  }).join("");

  box.querySelectorAll("input[data-u]").forEach((cb) => {
    cb.onchange = () => {
      cb.checked ? selected.add(cb.dataset.u) : selected.delete(cb.dataset.u);
      renderScope();
    };
  });

  box.querySelectorAll("button[data-rm]").forEach((btn) => {
    btn.disabled = !!(state.job && state.job.running);
    btn.onclick = () => removeUser(btn.dataset.rm);
  });
}

// Mailbox nao co goi_y thi gom ca vao day, kem dong loi ngan de biet loi
// nao ung voi loi khuyen nao. Khong co mailbox nao loi thi an luon card.
function fixTips(m) {
  // Preflight hong thi lan sync sau CHAC CHAN hong, nen no phai len day ke ca
  // khi lan sync truoc da OK -- do la canh bao som, khong phai tin cu.
  const pf = (m.preflight && !m.preflight.ok) ? m.preflight.goi_y || [] : [];
  return pf.concat(m.goi_y || []);
}

// Ten dau viet co dau cho khop voi phan con lai cua trang; may chu tra ve
// "nguon"/"dich" khong dau vi ma nguon Python trong repo viet vay.
const SIDE_VI = { nguon: "nguồn", dich: "đích" };

function fixLabel(m) {
  if (m.preflight && !m.preflight.ok) {
    const sides = (m.preflight.hong || []).map((s) => SIDE_VI[s] || s);
    return "đăng nhập hỏng ở " + sides.join(" và ");
  }
  return m.ghi_chu;
}

function bytes(n) {
  if (!(n >= 0)) return "";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return (i === 0 ? n : n.toFixed(1)) + " " + u[i];
}

function when(ts) {
  const d = new Date(ts * 1000), p = (x) => ("0" + x).slice(-2);
  return p(d.getDate()) + "/" + p(d.getMonth() + 1) + " " +
         p(d.getHours()) + ":" + p(d.getMinutes());
}

function renderFiles() {
  const box = $("files"), list = (state && state.files) || [];
  if (!list.length) {
    box.innerHTML = '<div class="empty">Chưa có tệp nào. ' +
      "Chạy một tác vụ rồi quay lại đây.</div>";
    return;
  }
  // Link tai ve la thẻ <a> thường chứ không phải fetch(): cookie đăng nhập đi
  // kèm sẵn vì cùng gốc, và máy chủ trả Content-Disposition nên trình duyệt
  // tải xuống chứ không rời trang.
  box.innerHTML = list.map((f) =>
    '<div class="file">' +
    (f.kind === "bao-cao" ? '<span class="badge b-ok">báo cáo</span>' : "") +
    '<a href="/api/file?name=' + encodeURIComponent(f.name) + '" download>' +
    esc(f.name) + "</a>" +
    '<span class="size">' + bytes(f.size) + "</span>" +
    '<span class="when">' + when(f.mtime) + "</span>" +
    "</div>").join("");
}

function renderFix() {
  const bad = state.mailboxes.filter((m) => fixTips(m).length);
  $("fix").hidden = !bad.length;
  if (!bad.length) return;
  $("fixcount").textContent = "(" + bad.length + " mailbox)";
  $("fixlist").innerHTML = bad.map((m) =>
    '<div class="fix"><div class="who"><b>' + esc(m.src_user) + "</b>" +
    (fixLabel(m) ? '<span class="badge b-err">' + esc(fixLabel(m)) + "</span>" : "") +
    "</div>" +
    fixTips(m).map((t) => "<p>" + esc(t) + "</p>").join("") +
    "</div>").join("");
}

// Thẻ lịch & danh bạ. Chạy SAU renderJob(): renderJob mở khoá mọi nút
// data-act khi job vừa xong, mà hai nút ở đây còn phải khoá tiếp nếu cấu hình
// chưa chạy được ống PIM.
function renderPim() {
  const p = (state && state.pim) || {};
  const running = !!(state && state.job && state.job.running);
  document.querySelectorAll("#pimbar button[data-act]").forEach((b) => {
    b.disabled = running || !p.ready;
  });

  const note = $("pimnote");
  if (!p.ready) {
    // Lý do lấy nguyên văn của máy chủ -- đúng câu mà `postboat.py pim` in ra,
    // để người đọc tra trong README thấy cùng một dòng.
    note.innerHTML =
      '<span class="err">Chưa chạy được.</span> ' + esc(p.reason || "") +
      (p.enabled ? "" :
        " Bật bằng <code>[pim] enabled = true</code> rồi tải lại trang.");
  } else {
    // Hai đầu đặt trên hai dòng riêng chứ không nhét vào giữa câu: nhãn lấy
    // nguyên văn của tool (không dấu, có ngoặc đơn kiểu "(mat khau hop thu)"),
    // ghép vào văn xuôi có dấu thì đọc ra một câu gãy.
    note.innerHTML =
      "Không đi qua IMAP, và giữ nguyên UID nên chạy lại không tạo bản trùng." +
      '<div class="pair">Đọc từ <b>' + esc(p.source) + "</b></div>" +
      '<div class="pair">Ghi vào <b>' + esc(p.dest) + "</b></div>";
  }

  const rows = (state.mailboxes || []).filter((m) => m.pim);
  $("pimwrap").hidden = !rows.length;
  text("pimcount", rows.length
    ? "(" + rows.length + " mailbox đã chuyển)"
    : (p.ready ? "(chưa chạy lần nào)" : ""));
  if (!rows.length) return;

  $("pimrows").innerHTML = rows.map((m) => {
    const q = m.pim;
    let verdict;
    if (q.error)     verdict = '<span class="badge b-err">không chuyển được</span>';
    else if (q.loi)  verdict = '<span class="badge b-err">thiếu ' + q.loi + " mục</span>";
    else             verdict = '<span class="badge b-ok">xong</span>';
    return "<tr><td>" + esc(m.src_user) + "</td><td>" + esc(m.dst_user) + "</td>" +
      '<td class="num">' + q.calendar + "</td>" +
      '<td class="num">' + q.contacts + "</td>" +
      "<td>" + verdict +
      (q.error ? '<div class="tip">' + esc(q.error) + "</div>" : "") + "</td>" +
      "<td>" + esc(q.at) + "</td></tr>";
  }).join("");
}

function renderJob() {
  const j = state.job, dot = $("dot"), log = $("log");
  dot.className = "dot";
  if (!j) {
    $("jobname").textContent = "Chưa chạy tác vụ nào";
    $("jobinfo").textContent = "";
    return;
  }
  const secs = Math.round(j.elapsed);
  const time = secs >= 60 ? Math.floor(secs / 60) + "m" + ("0" + (secs % 60)).slice(-2) + "s"
                          : secs + "s";
  if (j.running)      { dot.classList.add("run"); }
  else if (j.error || (j.exit_code !== null && j.exit_code !== 0)) { dot.classList.add("err"); }
  else                { dot.classList.add("ok"); }

  $("jobname").textContent = j.action_label + (j.running ? " — đang chạy" : " — xong");
  const who = j.only.length ? j.only.join(", ") : "tất cả mailbox";
  $("jobinfo").textContent = who + " · " + time +
    (j.running || j.exit_code === null ? "" : " · mã thoát " + j.exit_code);

  const text = (j.lines || []).join("\n") || "(chưa có output)";
  if (log.textContent !== text) {
    const atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
    log.textContent = text;
    if (stick && atEnd) log.scrollTop = log.scrollHeight;
  }
  document.querySelectorAll("button[data-act]").forEach((b) => { b.disabled = j.running; });
}

async function removeUser(user) {
  const msg = "Xoá " + user + " khỏi danh sách?\n\n" +
    "Chỉ xoá dòng trong users.csv. Mail đã chuyển và log vẫn còn nguyên.";
  if (!confirm(msg)) return;
  try {
    const res = await fetch("/api/users/remove", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ src_user: user }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.error || "Không xoá được"); return; }
    selected.delete(user);
  } catch (e) {
    alert("Không gọi được máy chủ: " + e.message);
  }
  refresh();
}

async function refresh() {
  try {
    const res = await fetch("/api/state", { credentials: "same-origin" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    state = await res.json();
  } catch (e) {
    $("jobinfo").innerHTML = '<span class="err">Mất kết nối tới máy chủ</span>';
    return schedule();
  }
  // schedule() phai chay DU phia tren co hong. Truoc day mot phan tu thieu
  // nem TypeError ngay tai day, va vi schedule() nam sau cung nen vong cap
  // nhat chet han: dashboard dung hinh, khong mot loi bao, cho toi khi tai
  // lai trang. Mot o hien sai con hon ca man hinh dong bang.
  try {
    text("src", state.source_provider + " · " + state.source);
    text("dst", state.dest_provider + " · " + state.dest);
    text("meta", "config: " + state.config +
                 " · song song: " + state.workers + " mailbox");
    text("usersfile", state.users_file);
    text("logdir", state.logdir);
    renderLabels();
    renderRows(); renderFix(); renderScope(); renderJob(); renderPim();
    renderFiles();
  } catch (e) {
    console.error("refresh hong:", e);
  }
  schedule();
}

// Nhan trong giao dien lay tu config chu khong viet cung: mot ban cai chay
// Gmail -> IceWarp, ban khac chay Microsoft 365 -> Zimbra.
function passField(id, needed) {
  const wrap = $(id), input = wrap.querySelector("input");
  wrap.style.display = needed ? "" : "none";
  // Bỏ required cùng lúc với ẩn: một ô input required mà đang ẩn sẽ chặn
  // submit vĩnh viễn, và trình duyệt không chỉ được ra chỗ nào sai.
  input.required = !!needed;
}

function renderLabels() {
  const src = state.source_provider, dst = state.dest_provider;
  $("btn-dest").textContent = "Folder bên " + dst;
  // "nguon"/"dich" phai nam TRONG nhan, khong duoc chi dua vao ten provider:
  // ca migrate hay gap nhat cua mot nha cung cap la cPanel -> cPanel, luc do
  // ca ba nhan ra chuoi giong het nhau va khong con gi phan biet o nao la dau
  // nao. Dat nham thi chay nguoc -- chep tu server moi ve server cu.
  $("lb-src").textContent = "Địa chỉ nguồn · " + src;
  $("lb-dst").textContent = "Địa chỉ đích · " + dst;
  $("lb-dstpass").textContent = "Mật khẩu đích · " + dst;
  // OAuth2 và master: không ai có mật khẩu của từng user, nên không hỏi.
  passField("wrap-srcpass", state.needs_src_password);
  passField("wrap-dstpass", state.needs_dst_password);
  $("lb-srcpass").textContent =
    state.source_provider.indexOf("Gmail") === 0
      ? "App Password nguồn (16 ký tự)"
      : "Mật khẩu nguồn · " + src;
}

function schedule() {
  clearTimeout(timer);
  const fast = state && state.job && state.job.running;
  timer = setTimeout(refresh, fast ? 1200 : 6000);
}

document.querySelectorAll("button[data-act]").forEach((btn) => {
  btn.onclick = async () => {
    const act = btn.dataset.act;
    // Tác vụ toàn cục (doctor, providers, report, handover) làm việc trên cả
    // cuộc migrate. Gửi kèm lựa chọn ở bảng trên thì người bấm sẽ tưởng báo
    // cáo đã lọc theo lựa chọn đó, trong khi nó không hề.
    const only = btn.dataset.global ? [] : scope();
    const who = only.length ? only.length + " mailbox đã chọn" : "TẤT CẢ mailbox";
    if (act === "sync" || act === "resume" || act === "pim") {
      // "pim" ghi thẳng vào lịch và danh bạ bên đích, không phải vào mail --
      // hỏng ở đây là hỏng thứ người ta nhìn hằng ngày, nên cũng phải hỏi
      // lại như "Chạy thật".
      const msg = act === "resume"
        ? "Chạy tiếp cho " + who + "?\n\nMail sẽ được ghi vào "
          + state.dest_provider
          + ". Mailbox đã chạy xong trước đó sẽ bị bỏ qua."
        : act === "pim"
        ? "Chuyển lịch & danh bạ cho " + who + "?\n\nCác mục sẽ được ghi vào "
          + state.dest_provider + " bằng CalDAV/CardDAV. Mail không đụng tới."
        : "Chạy thật cho " + who + "?\n\nMail sẽ được ghi vào "
          + state.dest_provider + ".";
      if (!confirm(msg)) return;
    }
    document.querySelectorAll("button[data-act]").forEach((b) => { b.disabled = true; });
    stick = true;
    try {
      const res = await fetch("/api/run", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: act, only: only }),
      });
      const data = await res.json();
      if (!res.ok) alert(data.error || "Không chạy được");
    } catch (e) {
      alert("Không gọi được máy chủ: " + e.message);
    }
    refresh();
  };
});

$("all").onchange = (e) => {
  selected = e.target.checked
    ? new Set(state.mailboxes.map((m) => m.src_user)) : new Set();
  renderRows(); renderScope();
};

$("addform").onsubmit = async (e) => {
  e.preventDefault();
  const form = e.target;
  const body = Object.fromEntries(new FormData(form).entries());
  const note = $("addstatus");
  try {
    const res = await fetch("/api/users", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      note.innerHTML = '<span class="err">' + esc(data.error) + "</span>";
      return;
    }
    form.reset();
    note.textContent = "Đã thêm " + data.src_user + " vào danh sách.";
    refresh();
  } catch (err) {
    note.innerHTML = '<span class="err">Không gọi được máy chủ.</span>';
  }
};

$("log").onscroll = () => {
  const el = $("log");
  stick = el.scrollTop + el.clientHeight >= el.scrollHeight - 24;
};

refresh();
</script>
</body>
</html>
""".replace("__ICON__", ICON)
