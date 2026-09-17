# -*- coding: utf-8 -*-
"""CalDAV/CardDAV bang HTTP stdlib. Khong dung imapsync, khong import runner.

Chi ba dong tac: PROPFIND (liet ke object trong collection), GET (doc mot
object), PUT voi If-None-Match: * (ghi neu chua co). Khong co pip install:
CalDAV la HTTP + XML, stdlib du.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

_UNFOLD = re.compile(r"\n[ \t]")


class DavError(Exception):
    def __init__(self, message: str, status: int = 0) -> None:
        Exception.__init__(self, message)
        self.status = status


def unfold(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return _UNFOLD.sub("", text)


def _prop(line: str) -> str:
    return line.split(";", 1)[0].split(":", 1)[0].strip().upper()


def uid_from_ics(text: str) -> str:
    for line in unfold(text).split("\n"):
        if _prop(line) == "UID" and ":" in line:
            return line.split(":", 1)[1].strip()
    return ""


def uid_from_vcard(text: str) -> str:
    for line in unfold(text).split("\n"):
        if _prop(line) == "UID" and ":" in line:
            return line.split(":", 1)[1].strip()
    return ""


def fallback_uid(body: str, prefix: str) -> str:
    digest = hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]
    return "%s-%s" % (prefix, digest)


def looks_like(body: str, kind: str) -> bool:
    """GET mot href co the tra ve trang HTML (index cua folder) chu khong phai
    object -- IceWarp lam vay voi collection con, va vai server tra 200 kem
    trang loi. Chi nhan cai mo dau bang BEGIN:VCALENDAR / BEGIN:VCARD, khong
    thi PUT sang dich mot cuc HTML mang ten .ics."""
    head = (body or "").lstrip("﻿ \t\r\n")[:32].upper()
    want = "BEGIN:VCALENDAR" if kind == "calendar" else "BEGIN:VCARD"
    return head.startswith(want)


def _with_schedule_agent(line: str) -> str:
    if "SCHEDULE-AGENT=" in line.upper():
        return line
    name, _, rest = line.partition(":")
    if ";" in name:
        head, params = name.split(";", 1)
        return "%s;SCHEDULE-AGENT=CLIENT;%s:%s" % (head, params, rest)
    return "%s;SCHEDULE-AGENT=CLIENT:%s" % (name, rest)


def _esc_text(value: str) -> str:
    """Gia tri TEXT cua RFC 5545: \\ ; , va xuong dong phai escape."""
    value = (value or "").replace("\\", "\\\\").replace(";", "\\;")
    return value.replace(",", "\\,").replace("\r\n", "\n").replace("\n", "\\n")


def _cal_address(line: str) -> str:
    """'ATTENDEE;CN=Binh;PARTSTAT=...:mailto:b@x' -> 'Binh <b@x>'."""
    head, _, value = line.partition(":")
    addr = value.strip()
    if addr.lower().startswith("mailto:"):
        addr = addr[7:]
    cn = ""
    for param in head.split(";")[1:]:
        name, _, pval = param.partition("=")
        if name.strip().upper() == "CN":
            cn = pval.strip().strip('"')
    if cn and cn.lower() != addr.lower():
        return "%s <%s>" % (cn, addr)
    return addr


def prepare_ics(text: str, keep_attendees: bool = False) -> str:
    """Bo METHOD (iTIP) va vo hieu hoa scheduling truoc khi PUT.

    Day la cho de bien migrate thanh su co nhat: server CalDAV co RFC 6638 se
    GUI LAI LOI MOI cho ca cong ty khi nhan mot VEVENT ma nguoi PUT la
    ORGANIZER, va gui REPLY cho organizer khi nguoi PUT la ATTENDEE. Do that
    17/09/2026 tren Zimbra 8.8.15: SCHEDULE-AGENT=CLIENT (RFC 6638) bi BO QUA,
    ca hai chieu deu gui mail. Nen mac dinh:

      - Su kien co ATTENDEE: bo ORGANIZER va ATTENDEE khoi VEVENT, giu chung
        duoi dang X-POSTBOAT-ORGANIZER / X-POSTBOAT-ATTENDEE (khong mat du
        lieu, import lai duoc), va ghi danh sach nguoi tham du vao DESCRIPTION
        de nguoi dung van thay.
      - keep_attendees=True: giu nguyen va gan SCHEDULE-AGENT=CLIENT. Chi bat
        khi admin da tat scheduling CalDAV tren server dich va da thu tren
        mot hop.
    """
    out: List[str] = []
    vevent_at = -1          # vi tri BEGIN:VEVENT dang mo trong `out`
    organizer_at = -1       # vi tri dong ORGANIZER cua VEVENT do
    attendees: List[str] = []
    organizer = ""
    for line in unfold(text).split("\n"):
        if not line:
            continue
        key = _prop(line)
        if key == "METHOD":
            continue
        upper = line.upper()
        if upper.startswith("BEGIN:VEVENT"):
            vevent_at, organizer_at = len(out), -1
            attendees, organizer = [], ""
        if key in ("ATTENDEE", "ORGANIZER") and vevent_at >= 0:
            if keep_attendees:
                out.append(_with_schedule_agent(line))
            else:
                if key == "ATTENDEE":
                    attendees.append(_cal_address(line))
                else:
                    organizer, organizer_at = _cal_address(line), len(out)
                out.append("X-POSTBOAT-" + line)
            continue
        if upper.startswith("END:VEVENT") and vevent_at >= 0:
            if not keep_attendees:
                if attendees:
                    _note_attendees(out, vevent_at, organizer, attendees)
                elif organizer_at >= 0:
                    # Khong co ai de moi thi ORGANIZER vo hai: tra lai nguyen.
                    out[organizer_at] = out[organizer_at][len("X-POSTBOAT-"):]
            vevent_at = -1
        out.append(line)
    return "\r\n".join(out) + "\r\n"


def _note_attendees(out: List[str], start: int, organizer: str,
                    attendees: List[str]) -> None:
    """Ghi 'nguoi to chuc / nguoi tham du' vao DESCRIPTION cua VEVENT dang mo."""
    note = "Nguoi tham du (loi moi khong gui lai khi chuyen): " + ", ".join(attendees)
    if organizer:
        note = "Nguoi to chuc: %s. %s" % (organizer, note)
    for i in range(start, len(out)):
        if _prop(out[i]) == "DESCRIPTION":
            out[i] = out[i] + "\\n\\n" + _esc_text(note)
            return
    out.append("DESCRIPTION:" + _esc_text(note))


def filename_for(uid: str, ext: str) -> str:
    """Zimbra bat ten file phai la {UID}.ics; IceWarp khong quan tam. Dat
    theo Zimbra thi ca hai deu nhan."""
    safe = urllib.parse.quote(uid.strip() or "item", safe="-._@")
    return "%s.%s" % (safe, ext)


def _local(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _norm(url: str) -> str:
    """Dang de so sanh hai URL: %40 va @ la mot, bo / cuoi, khong phan biet
    hoa thuong. Chi dung de so sanh, khong dung de goi."""
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(parsed.path).rstrip("/")
    return (parsed.netloc + path).lower()


class DavClient:
    def __init__(self, username: str, password: str, timeout: int = 60,
                 tls_verify: bool = True) -> None:
        self.username = username
        self.password = password
        self.timeout = timeout
        self.tls_verify = tls_verify

    def _headers(self, extra: Optional[dict] = None) -> dict:
        raw = ("%s:%s" % (self.username, self.password)).encode("utf-8")
        token = base64.b64encode(raw).decode("ascii")
        headers = {
            "Authorization": "Basic " + token,
            "User-Agent": "Postboat-PIM",
        }
        if extra:
            headers.update(extra)
        return headers

    def _ssl(self, url: str):
        if not url.lower().startswith("https://"):
            return None
        ctx = ssl.create_default_context()
        if not self.tls_verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def request(self, method: str, url: str, body: bytes = b"",
                headers: Optional[dict] = None) -> Tuple[int, bytes]:
        req = urllib.request.Request(
            url, data=body or None, method=method,
            headers=self._headers(headers))
        ctx = self._ssl(url)
        try:
            if ctx is None:
                resp = urllib.request.urlopen(req, timeout=self.timeout)
            else:
                resp = urllib.request.urlopen(req, timeout=self.timeout,
                                             context=ctx)
            with resp:
                return resp.getcode() or 200, resp.read()
        except urllib.error.HTTPError as exc:
            payload = b""
            try:
                payload = exc.read()
            except Exception:
                payload = b""
            if exc.code in (412, 409, 404, 207, 201, 204, 200):
                return exc.code, payload
            raise DavError("HTTP %s %s %s%s" % (
                exc.code, method, url, _hint(exc.code)), exc.code)
        except urllib.error.URLError as exc:
            raise DavError("khong noi duoc %s: %s" % (url, exc.reason))
        except (OSError, http.client.HTTPException) as exc:
            # Server dong ket noi giua chung (reset, timeout doc, tra loi hong).
            # Mot mailbox hong khong duoc keo ca job xuong bang traceback.
            raise DavError("ket noi %s bi ngat: %s" % (url, exc))

    def list_hrefs(self, collection_url: str) -> List[str]:
        url = collection_url if collection_url.endswith("/") else collection_url + "/"
        body = (
            b'<?xml version="1.0" encoding="utf-8"?>'
            b'<d:propfind xmlns:d="DAV:">'
            b"<d:prop><d:getcontenttype/><d:resourcetype/><d:getetag/>"
            b"</d:prop></d:propfind>"
        )
        status, data = self.request(
            "PROPFIND", url, body,
            {"Content-Type": "application/xml; charset=utf-8", "Depth": "1"})
        if status == 404:
            return []
        if status not in (207, 200):
            raise DavError("PROPFIND %s -> HTTP %s" % (url, status), status)
        return _hrefs_from_multistatus(url, data)

    def get(self, url: str) -> str:
        status, data = self.request("GET", url)
        if status != 200:
            raise DavError("GET %s -> HTTP %s" % (url, status), status)
        return data.decode("utf-8", "replace")

    def put(self, url: str, body: str, content_type: str) -> str:
        """'created' hoac 'exists'. If-None-Match: * la cach RFC 4791 giu cho
        chay lai khong nhan ban: cung UID thi server tra 412, ta dem la da co."""
        status, _data = self.request(
            "PUT", url, body.encode("utf-8"),
            {"Content-Type": content_type + "; charset=utf-8",
             "If-None-Match": "*"})
        if status in (412, 409):
            return "exists"
        if status in (200, 201, 204):
            return "created"
        raise DavError("PUT %s -> HTTP %s" % (url, status), status)


def _hint(code: int) -> str:
    """Ma HTTP tran trui khong noi duoc phai lam gi; ba ma hay gap thi noi."""
    if code == 401:
        return " -- sai mat khau hop thu, hoac WebDAV/GroupWare chua bat"
    if code == 403:
        return " -- tai khoan dang nhap duoc nhung khong co quyen tren collection nay"
    if code == 405:
        return " -- URL nay khong phai collection CalDAV/CardDAV (kiem webdav_base)"
    return ""


def _hrefs_from_multistatus(collection_url: str, data: bytes) -> List[str]:
    """Href cua tung object trong collection.

    Bo chinh collection va moi collection con. Khong so sanh chuoi tho: server
    hay tra `%40` cho `@` trong href, va neu vi the ma giu nham collection lai
    thi buoc GET sau do nhan mot trang HTML roi PUT no sang dich.
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise DavError("PROPFIND XML hong: %s" % exc)
    coll = _norm(collection_url)
    found: List[str] = []
    for resp in root.iter():
        if _local(resp.tag) != "response":
            continue
        href_el = next((el for el in resp if _local(el.tag) == "href"), None)
        if href_el is None or not (href_el.text or "").strip():
            continue
        if any(_local(el.tag) == "collection" for el in resp.iter()):
            continue
        href = urllib.parse.urljoin(collection_url, href_el.text.strip())
        if _norm(href) == coll:
            continue
        found.append(href)
    return found
