# -*- coding: utf-8 -*-
"""Do hanh vi CalDAV/CardDAV cua mot server DICH truoc khi chay that.

Bon cau hoi, dung bon cau da do tren Zimbra 8.8.15 ngay 17/09/2026
(research/calendar-contacts.md muc 5), nhung khong con dinh vao Zimbra:

  urls     hinh URL cua collection: {base}/{email}/Calendar/ va /Contacts/
           co that khong, hay server dat ten khac.
  inm      PUT ... If-None-Match: * co tra 412 khi UID da co khong, hay van
           2xx (Zimbra: van 2xx -- "da co" phai hoi bang PROPFIND truoc).
  invites  PUT mot su kien con ORGANIZER/ATTENDEE co lam server GUI LAI LOI
           MOI khong, ca chieu hop dich la organizer lan chieu la attendee.
           Day la cho bien mot ca migrate thanh su co.
  lists    (chi IceWarp) `tool.exe file batch` voi u_type 7 + g_listfile co
           tao dung nhom va dung thanh vien khong. IceWarp hau het chay tren
           Windows va thuong khong co SSH, nen mac dinh phep nay chi sinh file
           roi in ra dung nhung dong can go trong cmd tren may do; --ssh chi
           danh cho may co bat OpenSSH.

Script khong dung zmmailbox: dem mail bang IMAP, nen chay duoc voi IceWarp,
Zimbra hay bat ky server nao khac. Chi thu vien chuan.

Chay:

  python3 testrig/pimprobe.py --provider icewarp --host mail.lab.vn \\
      --box pim-dst@lab.vn:MatKhau --peer pim-third@lab.vn:MatKhau \\
      --insecure --only urls,inm,invites

  python3 testrig/pimprobe.py --provider icewarp --host mail.lab.vn \\
      --box pim-dst@lab.vn:MatKhau --only lists

Hop --box la hop bi PUT vao (vai "pim-dst"). Hop --peer la hop thu ba: no
dong vai nguoi tham du o mot chieu va nguoi to chuc o chieu kia, va inbox cua
no la cai can dem. Hai hop phai KHAC nhau, va --peer phai doc duoc bang IMAP.
"""

from __future__ import annotations

import argparse
import imaplib
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from postboat.pim_dav import DavClient, DavError, prepare_ics  # noqa: E402

TAG = time.strftime("%Y%m%d%H%M%S")
PROBE = "postboat-probe"


# --------------------------------------------------------------------------- #
# Tien ich
# --------------------------------------------------------------------------- #

def say(line: str = "") -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def pair(value: str, what: str) -> Tuple[str, str]:
    """'user@dom:matkhau' -> (user, matkhau). Mat khau duoc phep chua ':'."""
    if ":" not in value:
        raise SystemExit("--%s phai la dang email:matkhau" % what)
    user, password = value.split(":", 1)
    if not user or not password:
        raise SystemExit("--%s thieu email hoac mat khau" % what)
    return user, password


def base_for(provider: str, host: str) -> str:
    """Cung bang suy URL voi postboat/pim.py -- de hai ben khong lech nhau."""
    if provider == "icewarp":
        return "https://%s/webdav" % host
    if provider == "zimbra":
        return "https://%s/dav" % host
    raise SystemExit("provider %r khong suy duoc goc DAV: dua --base" % provider)


def coll_url(base: str, mailbox: str, name: str) -> str:
    quoted = urllib.parse.quote(mailbox, safe="@._-")
    return "%s/%s/%s/" % (base.rstrip("/"), quoted,
                          urllib.parse.quote(name.strip("/"), safe="@._-"))


def req(client: DavClient, method: str, url: str, body: bytes = b"",
        headers: Optional[dict] = None) -> Tuple[int, bytes]:
    """Nhu client.request nhung tra ve ma HTTP tho thay vi nem: probe can
    thay 403/405 chu khong phai mot traceback."""
    try:
        return client.request(method, url, body, headers)
    except DavError as exc:
        return exc.status or 0, str(exc).encode("utf-8")


def utc(offset_hours: float) -> str:
    return time.strftime("%Y%m%dT%H%M%SZ",
                         time.gmtime(time.time() + offset_hours * 3600))


def ics(uid: str, summary: str, organizer: str = "", attendees: Sequence[str] = (),
        partstat: str = "NEEDS-ACTION", schedule_agent: bool = False,
        hours: float = 24.0) -> str:
    """Mot VEVENT toi thieu nhung du de server coi la loi moi hop."""
    agent = ";SCHEDULE-AGENT=CLIENT" if schedule_agent else ""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Postboat//probe//VI",
        "BEGIN:VEVENT",
        "UID:" + uid,
        "DTSTAMP:" + utc(0),
        "DTSTART:" + utc(hours),
        "DTEND:" + utc(hours + 1),
        "SUMMARY:" + summary,
    ]
    if organizer:
        lines.append("ORGANIZER%s:mailto:%s" % (agent, organizer))
    for addr in attendees:
        lines.append(
            "ATTENDEE%s;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=%s;"
            "RSVP=TRUE:mailto:%s" % (agent, partstat, addr))
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


def vcard(uid: str, fn: str, email: str) -> str:
    lines = ["BEGIN:VCARD", "VERSION:3.0", "UID:" + uid, "FN:" + fn,
             "N:%s;;;;" % fn, "EMAIL;TYPE=INTERNET:" + email, "END:VCARD"]
    return "\r\n".join(lines) + "\r\n"


# --------------------------------------------------------------------------- #
# IMAP: dem mail cua hop thu ba
# --------------------------------------------------------------------------- #

class Mailbox:
    """Dem thu trong mot folder. Khong xoa gi, khong danh dau da doc."""

    def __init__(self, host: str, port: int, user: str, password: str,
                 insecure: bool) -> None:
        self.host, self.port = host, port
        self.user, self.password = user, password
        self.insecure = insecure

    def _ctx(self):
        ctx = ssl.create_default_context()
        if self.insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def count(self, folder: str = "INBOX") -> int:
        try:
            imap = imaplib.IMAP4_SSL(self.host, self.port,
                                     ssl_context=self._ctx())
        except Exception as exc:
            raise SystemExit("IMAP %s:%s khong noi duoc: %s"
                             % (self.host, self.port, exc))
        try:
            imap.login(self.user, self.password)
            typ, _ = imap.select('"%s"' % folder, readonly=True)
            if typ != "OK":
                return -1
            typ, data = imap.search(None, "ALL")
            if typ != "OK":
                return -1
            return len(data[0].split())
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    def subjects(self, folder: str = "INBOX", last: int = 3) -> List[str]:
        imap = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=self._ctx())
        out: List[str] = []
        try:
            imap.login(self.user, self.password)
            typ, _ = imap.select('"%s"' % folder, readonly=True)
            if typ != "OK":
                return out
            typ, data = imap.search(None, "ALL")
            if typ != "OK":
                return out
            for num in data[0].split()[-last:]:
                typ, payload = imap.fetch(
                    num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
                if typ != "OK" or not payload or not payload[0]:
                    continue
                raw = payload[0][1] or b""
                text = raw.decode("utf-8", "replace")
                out.append(" | ".join(
                    part.strip() for part in text.splitlines() if part.strip()))
        finally:
            try:
                imap.logout()
            except Exception:
                pass
        return out


def wait_for_mail(box: Mailbox, folder: str, before: int, seconds: int) -> int:
    """Doi toi `seconds` giay xem so mail co tang khong. Tra ve so cuoi cung.

    Doi that chu khong sleep mot cuc: server gui cham thi ket luan 'khong gui'
    la ket luan sai, va no la ket luan nguy hiem nhat trong ca bo do nay."""
    deadline = time.time() + seconds
    now = before
    while time.time() < deadline:
        time.sleep(4)
        now = box.count(folder)
        if now > before:
            return now
    return now


# --------------------------------------------------------------------------- #
# 1. Hinh URL
# --------------------------------------------------------------------------- #

CANDIDATES = ("Calendar", "calendar", "Contacts", "contacts", "Danh bạ",
              "Default", "addressbook")


def probe_urls(client: DavClient, base: str, mailbox: str) -> None:
    say("### 1. Hinh URL duoi %s" % base)
    root = "%s/%s/" % (base.rstrip("/"), urllib.parse.quote(mailbox, safe="@._-"))
    status, data = req(client, "PROPFIND", root,
                       b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:">'
                       b"<d:prop><d:resourcetype/><d:displayname/></d:prop>"
                       b"</d:propfind>",
                       {"Content-Type": "application/xml; charset=utf-8",
                        "Depth": "1"})
    say("  PROPFIND %-52s -> %s" % (root, status))
    if status in (207, 200):
        try:
            for href in client.list_hrefs(root):
                say("      con: %s" % urllib.parse.unquote(href))
        except DavError as exc:
            say("      (khong doc duoc danh sach con: %s)" % exc)
        for line in data.decode("utf-8", "replace").splitlines():
            if "displayname" in line.lower():
                say("      %s" % line.strip()[:120])
                break
    for name in CANDIDATES:
        url = coll_url(base, mailbox, name)
        status, data = req(client, "PROPFIND", url,
                           b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:">'
                           b"<d:prop><d:resourcetype/></d:prop></d:propfind>",
                           {"Content-Type": "application/xml; charset=utf-8",
                            "Depth": "0"})
        kind = ""
        if status in (207, 200):
            body = data.decode("utf-8", "replace").lower()
            if "calendar-collection" in body or "calendar" in body:
                kind = "calendar-collection"
            if "addressbook" in body:
                kind = (kind + " addressbook").strip()
            if not kind:
                kind = "collection (khong khai kieu)"
        say("  PROPFIND %-52s -> %-4s %s" % (url, status, kind))
    say()


# --------------------------------------------------------------------------- #
# 2. If-None-Match
# --------------------------------------------------------------------------- #

def probe_inm(client: DavClient, base: str, mailbox: str, calendar: str,
              contacts: str, cleanup: List[Tuple[DavClient, str]]) -> None:
    say("### 2. If-None-Match: * co duoc ton trong khong")
    uid = "%s-inm-%s@probe" % (PROBE, TAG)
    url = coll_url(base, mailbox, calendar) + uid + ".ics"
    body = ics(uid, "Probe If-None-Match")

    status, _ = req(client, "PUT", url, body.encode("utf-8"),
                    {"Content-Type": "text/calendar; charset=utf-8"})
    say("  PUT lan 1 (khong co header)        -> %s" % status)
    if status not in (200, 201, 204):
        say("  Khong ghi duoc, bo qua phan con lai cua phep do nay.")
        say()
        return
    cleanup.append((client, url))

    status, _ = req(client, "PUT", url, body.encode("utf-8"),
                    {"Content-Type": "text/calendar; charset=utf-8",
                     "If-None-Match": "*"})
    honours = status in (412, 409)
    say("  PUT lan 2 (If-None-Match: *)       -> %s   %s"
        % (status, "412 = ton trong" if honours
           else "2xx = PHOT LO, phai PROPFIND truoc khi PUT"))

    changed = ics(uid, "Probe If-None-Match (da sua)")
    status, _ = req(client, "PUT", url, changed.encode("utf-8"),
                    {"Content-Type": "text/calendar; charset=utf-8",
                     "If-None-Match": "*"})
    after = ""
    try:
        after = client.get(url)
    except DavError as exc:
        after = str(exc)
    overwritten = "da sua" in after
    say("  PUT lan 3 (noi dung khac, INM: *)  -> %s   %s"
        % (status, "ban cu bi ghi de" if overwritten else "ban cu con nguyen"))

    hrefs = []
    try:
        hrefs = [h for h in client.list_hrefs(coll_url(base, mailbox, calendar))
                 if uid.split("@")[0] in urllib.parse.unquote(h)]
    except DavError as exc:
        say("  PROPFIND loi: %s" % exc)
    say("  PROPFIND thay lai object           -> %s"
        % ("co (%s)" % urllib.parse.unquote(hrefs[0]) if hrefs else "KHONG"))

    vuid = "%s-inm-%s@probe" % (PROBE, TAG)
    vurl = coll_url(base, mailbox, contacts) + vuid + ".vcf"
    status, _ = req(client, "PUT", vurl,
                    vcard(vuid, "Probe Contact", "probe@example.test").encode("utf-8"),
                    {"Content-Type": "text/vcard; charset=utf-8"})
    if status in (200, 201, 204):
        cleanup.append((client, vurl))
    status2, _ = req(client, "PUT", vurl,
                     vcard(vuid, "Probe Contact", "probe@example.test").encode("utf-8"),
                     {"Content-Type": "text/vcard; charset=utf-8",
                      "If-None-Match": "*"})
    say("  vCard: PUT lan 1 -> %s, lan 2 (INM: *) -> %s" % (status, status2))
    say()


# --------------------------------------------------------------------------- #
# 3. Loi moi hop
# --------------------------------------------------------------------------- #

def probe_invites(client: DavClient, base: str, mailbox: str, calendar: str,
                  peer: str, peerbox: Mailbox, boxbox: Optional[Mailbox],
                  wait: int, cleanup: List[Tuple[DavClient, str]]) -> None:
    say("### 3. Server co gui lai loi moi khi PUT khong  (doi toi %ds moi ca)"
        % wait)
    say("  Hop bi PUT vao : %s" % mailbox)
    say("  Hop thu ba     : %s  (dem INBOX qua IMAP)" % peer)

    cases = [
        ("A. dich la ORGANIZER, co SCHEDULE-AGENT=CLIENT",
         ics("%s-orgagent-%s@probe" % (PROBE, TAG), "Probe organizer + agent",
             organizer=mailbox, attendees=[peer], schedule_agent=True)),
        ("B. dich la ORGANIZER, khong co tham so nao",
         ics("%s-orgplain-%s@probe" % (PROBE, TAG), "Probe organizer tran",
             organizer=mailbox, attendees=[peer])),
        ("C. dich la ATTENDEE da ACCEPTED, organizer la hop thu ba",
         ics("%s-attendee-%s@probe" % (PROBE, TAG), "Probe attendee",
             organizer=peer, attendees=[mailbox], partstat="ACCEPTED")),
        ("D. qua prepare_ics() mac dinh cua Postboat",
         prepare_ics(ics("%s-neutral-%s@probe" % (PROBE, TAG),
                         "Probe da trung hoa",
                         organizer=mailbox, attendees=[peer]))),
    ]

    verdicts = []
    for label, payload in cases:
        uid = ""
        for line in payload.splitlines():
            if line.upper().startswith("UID:"):
                uid = line.split(":", 1)[1].strip()
                break
        url = coll_url(base, mailbox, calendar) + uid + ".ics"
        before = peerbox.count("INBOX")
        sent_before = boxbox.count("Sent") if boxbox else -1
        status, _ = req(client, "PUT", url, payload.encode("utf-8"),
                        {"Content-Type": "text/calendar; charset=utf-8"})
        if status in (200, 201, 204):
            cleanup.append((client, url))
        after = wait_for_mail(peerbox, "INBOX", before, wait)
        sent_after = boxbox.count("Sent") if boxbox else -1
        delta = after - before
        sent_delta = (sent_after - sent_before) if sent_before >= 0 else -1
        verdicts.append((label, status, delta, sent_delta))
        say("  %-52s PUT %-4s inbox %+d%s"
            % (label, status, delta,
               ("  sent %+d" % sent_delta) if sent_delta >= 0 else ""))
        if delta > 0:
            for subject in peerbox.subjects("INBOX", delta):
                say("        moi: %s" % subject[:110])

    say()
    gui = [v for v in verdicts if v[2] > 0]
    if gui:
        say("  => Server NAY CO gui lai loi moi: %s"
            % ", ".join(v[0].split(".")[0] for v in gui))
        say("     Giu mac dinh keep_attendees = false.")
    else:
        say("  => Khong ca nao gui mail. Neu ca B cung im thi server khong co")
        say("     RFC 6638 tren duong CalDAV, keep_attendees = true la an toan.")
    say()


# --------------------------------------------------------------------------- #
# 4. tool file batch (IceWarp)
# --------------------------------------------------------------------------- #

def probe_lists(domain: str, members: Sequence[str], ssh: str,
                remote_dir: str, kind: str, tool: str = "") -> None:
    """Cai gi da chac va cai gi con phai do:

      chac  `tool file batch <file>`, moi dong mot lenh, KHONG co chu 'tool'
            o dau dong (Command Line Tool, docs.icewarp.com).
      chac  U_Type 7 = Group, 1 = Mailing list; G_ListFile = 'List file',
            M_ListFile = 'Path to list file' (hang so API IceWarp, file
            APIconst.pas nam trong <InstallDirectory>\\API\\Delphi\\ ngay tren
            may IceWarp -- doi chieu tai cho duoc).
      do    dinh dang file thanh vien -- moi dia chi mot dong la suy tu
            'members file content', tai lieu khong viet ra. Buoc doc lai bang
            g_listfile_contents duoi day la de tra loi dung cho nay.

    IceWarp ban Windows la ban hay gap, va no doi ba thu: duong dan Windows,
    `tool.exe` thay cho `tool.sh`, va thuong khong co SSH. Khong co --ssh thi
    phep do nay in ra dung nhung dong can go trong cmd tren may do.
    """
    from postboat.lists import (MailList, remote_join, tool_name,
                                windows_path, write_icewarp)

    is_win = windows_path(remote_dir)
    tool = tool or tool_name(remote_dir)
    field = "g_listfile" if kind == "group" else "m_listfile"
    say("### 4. `%s file batch`: u_type %s + %s   (may dich: %s)"
        % (tool, "7 (User group)" if kind == "group" else "1 (Mailing list)",
           field, "Windows" if is_win else "Linux"))
    address = "probe-nhom-%s@%s" % (TAG, domain)
    group = MailList(address=address, name="Probe nhom %s" % TAG,
                     members=list(members))
    outdir = Path(tempfile.mkdtemp(prefix="pimprobe-lists-"))
    batch, files = write_icewarp(outdir, [group], remote_dir, kind=kind)
    say("  Sinh tai %s" % outdir)
    for path in [batch] + list(files):
        raw = path.read_bytes()
        say("  --- %s  (%s)" % (path.name,
                                "CRLF" if b"\r\n" in raw else "LF"))
        for line in raw.decode("utf-8").splitlines():
            say("      %s" % line)

    batch_remote = remote_join(remote_dir, batch.name)
    if not ssh:
        say()
        say("  Khong co --ssh. Tren may IceWarp, copy thu muc tren vao %s"
            % remote_dir)
        say("  roi go (%s):" % ("cmd, chay nhu Administrator" if is_win
                                else "shell"))
        say('      cd "%s"' % ("<InstallDirectory>" if is_win else "/opt/icewarp"))
        say("      %s file batch %s" % (tool, batch_remote))
        say("      %s display account %s u_name u_type %s" % (tool, address, field))
        say("      %s display account %s %s_contents" % (tool, address, field))
        say("  Thanh vien phai dung %d dia chi: %s"
            % (len(members), ", ".join(members)))
        say("  Xong thi xoa: %s delete account %s" % (tool, address))
        say()
        return

    say()
    say("  Day len %s:%s" % (ssh, remote_dir))
    if is_win:
        # OpenSSH tren Windows Server: shell mac dinh co the la cmd hoac
        # PowerShell, nen tranh cu phap rieng cua shell -- chi mot lenh mot lan.
        run(["ssh", ssh, 'mkdir "%s"' % remote_join(remote_dir, "members")])
    else:
        run(["ssh", ssh, "mkdir -p %s" % remote_join(remote_dir, "members")])
    run(["scp", str(batch), "%s:%s" % (ssh, batch_remote)])
    for path in files:
        run(["scp", str(path),
             "%s:%s" % (ssh, remote_join(remote_dir, "members", path.name))])
    say("  Chay `file batch`  (moi dong mot lenh, khong co chu 'tool'):")
    run(["ssh", ssh, '"%s" file batch "%s"' % (tool, batch_remote)], show=True)
    say("  Doc lai nhom vua tao (u_type phai la %d):" % (7 if kind == "group" else 1))
    run(["ssh", ssh, '"%s" display account %s u_name u_type %s'
         % (tool, address, field)], show=True)
    say("  Noi dung danh sach thanh vien server doc duoc (%s_contents):" % field)
    run(["ssh", ssh, '"%s" display account %s %s_contents'
         % (tool, address, field)], show=True)
    say("  Thanh vien phai dung %d dia chi: %s" % (len(members), ", ".join(members)))
    say("  Don dep khi da xem xong:")
    say('      ssh %s \'"%s" delete account %s\'' % (ssh, tool, address))
    say()


def run(cmd: Sequence[str], show: bool = False) -> None:
    try:
        proc = subprocess.run(list(cmd), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=120)
    except Exception as exc:
        say("      (loi chay %s: %s)" % (" ".join(cmd), exc))
        return
    text = proc.stdout.decode("utf-8", "replace").strip()
    if show or proc.returncode != 0:
        for line in text.splitlines():
            say("      %s" % line)
        if proc.returncode != 0:
            say("      (exit %s)" % proc.returncode)


# --------------------------------------------------------------------------- #

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Do CalDAV/CardDAV cua mot server dich (IceWarp, Zimbra, ...)")
    ap.add_argument("--provider", default="", help="icewarp | zimbra (de suy --base)")
    ap.add_argument("--host", default="", help="host web cua server dich")
    ap.add_argument("--base", default="", help="goc DAV, vd https://host/webdav")
    ap.add_argument("--box", required=True, metavar="EMAIL:MATKHAU",
                    help="hop thu bi PUT vao")
    ap.add_argument("--peer", default="", metavar="EMAIL:MATKHAU",
                    help="hop thu ba lam attendee/organizer (can cho 'invites')")
    ap.add_argument("--imap-host", default="", help="mac dinh = --host")
    ap.add_argument("--imap-port", type=int, default=993)
    ap.add_argument("--calendar", default="Calendar")
    ap.add_argument("--contacts", default="Contacts")
    ap.add_argument("--insecure", action="store_true",
                    help="chap nhan cert tu ky (lab)")
    ap.add_argument("--wait", type=int, default=24,
                    help="giay doi mail moi ca cua phep do invites")
    ap.add_argument("--only", default="urls,inm,invites",
                    help="urls,inm,invites,lists")
    ap.add_argument("--keep", action="store_true",
                    help="giu lai object da tao (mac dinh: xoa)")
    ap.add_argument("--ssh", default="",
                    help="user@host cua may IceWarp neu may do co SSH; khong "
                         "co thi phep do lists chi in ra lenh de go tay")
    ap.add_argument("--remote-dir", default="C:\\pimprobe-lists",
                    help="thu muc tren may IceWarp (mac dinh kieu Windows); "
                         "ban Linux thi dua /tmp/pimprobe-lists")
    ap.add_argument("--tool", default="",
                    help="duong dan toi tool.exe/tool.sh tren may IceWarp; "
                         "mac dinh suy tu --remote-dir")
    ap.add_argument("--list-kind", default="group", choices=("group", "mailinglist"))
    ap.add_argument("--list-members", default="",
                    help="dia chi thanh vien, phan cach bang dau phay")
    args = ap.parse_args(argv)

    want = [part.strip() for part in args.only.split(",") if part.strip()]
    box, box_password = pair(args.box, "box")
    base = args.base.rstrip("/") or base_for(args.provider, args.host)
    if not base:
        raise SystemExit("phai co --base hoac --provider + --host")

    say("Postboat pimprobe  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    say("  goc DAV : %s" % base)
    say("  hop dich: %s" % box)
    say("  TLS     : %s" % ("khong kiem cert (--insecure)" if args.insecure
                            else "kiem cert"))
    say()

    client = DavClient(box, box_password, timeout=40,
                       tls_verify=not args.insecure)
    cleanup: List[Tuple[DavClient, str]] = []

    try:
        if "urls" in want:
            probe_urls(client, base, box)
        if "inm" in want:
            probe_inm(client, base, box, args.calendar, args.contacts, cleanup)
        if "invites" in want:
            if not args.peer:
                say("### 3. Bo qua: chua co --peer (hop thu ba)\n")
            else:
                peer, peer_password = pair(args.peer, "peer")
                imap_host = args.imap_host or args.host or urllib.parse.urlsplit(
                    base).hostname or ""
                peerbox = Mailbox(imap_host, args.imap_port, peer,
                                  peer_password, args.insecure)
                boxbox = Mailbox(imap_host, args.imap_port, box, box_password,
                                 args.insecure)
                if boxbox.count("Sent") < 0:
                    boxbox = None
                probe_invites(client, base, box, args.calendar, peer, peerbox,
                              boxbox, args.wait, cleanup)
        if "lists" in want:
            members = [m.strip() for m in args.list_members.split(",") if m.strip()]
            domain = box.split("@", 1)[1] if "@" in box else "example.test"
            if not members:
                members = [box] + ([args.peer.split(":", 1)[0]] if args.peer else [])
            probe_lists(domain, members, args.ssh, args.remote_dir,
                        args.list_kind, args.tool)
    finally:
        if cleanup and not args.keep:
            say("### Don dep %d object da tao" % len(cleanup))
            for cli, url in cleanup:
                status, _ = req(cli, "DELETE", url)
                say("  DELETE %-70s -> %s" % (urllib.parse.unquote(url), status))
        elif cleanup:
            say("### Giu lai %d object (--keep)" % len(cleanup))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
