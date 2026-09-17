# -*- coding: utf-8 -*-
"""Doc lich/danh ba Microsoft 365 qua Graph. Token rieng, khong dung IMAP.

Cung app Entra da dang ky cho IMAP, nhung xin token o scope Graph va can them
quyen ung dung Calendars.Read + Contacts.Read (admin consent). "Lay duoc token"
KHONG co nghia la co quyen: thieu consent thi Microsoft van cap token, chi la
token khong mang role nao -- bai hoc 15/09 voi IMAP.AccessAsApp lap lai y
nguyen o day, nen kiem roles ngay sau khi lay token (oauth.token_roles).
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import replace
from typing import Dict, List, Optional

from . import oauth
from .config import Config
from .pim_dav import prepare_ics
from .users import User

GRAPH = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Quyen ung dung Graph du de doc. ReadWrite bao ham Read.
CALENDAR_ROLES = ("Calendars.Read", "Calendars.ReadWrite")
CONTACT_ROLES = ("Contacts.Read", "Contacts.ReadWrite")

# Graph tra body theo dinh dang goc (thuong la HTML) va gio theo UTC tru khi
# bao khac. Hai header nay ep ve text va UTC de ICS khong phai doan.
_PREFER = 'outlook.body-content-type="text", outlook.timezone="UTC"'

# Bi throttle (429) thi cho theo Retry-After roi thu lai; qua so lan nay thi
# bao loi cho mailbox do chu khong treo ca job.
_RETRIES = 3

_DAYS = {
    "sunday": "SU", "monday": "MO", "tuesday": "TU", "wednesday": "WE",
    "thursday": "TH", "friday": "FR", "saturday": "SA",
}
_NTH = {
    "first": "1", "second": "2", "third": "3", "fourth": "4", "last": "-1",
}
_BREAKS = re.compile(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>")
_TAGS = re.compile(r"<[^>]+>")


def missing_roles(token: str) -> List[str]:
    """Quyen Graph con thieu trong token. Rong = du, hoac token khong doc duoc
    (khi do cu goi Graph, Graph se tu tra loi)."""
    roles = oauth.token_roles(token)
    if roles is None:
        return []
    have = set(roles)
    missing = []
    for group in (CALENDAR_ROLES, CONTACT_ROLES):
        if not have.intersection(group):
            missing.append(group[0])
    return missing


def graph_token(cfg: Config) -> str:
    conf = replace(cfg.source.oauth, scope=GRAPH_SCOPE)
    token = oauth.source_for(conf).token()
    missing = missing_roles(token)
    if missing:
        raise oauth.OAuthError(
            "token Graph khong mang quyen %s. Tren app Entra da dang ky cho "
            "IMAP: API permissions > Add > Microsoft Graph > Application "
            "permissions > %s, roi bam Grant admin consent. Thieu consent thi "
            "Microsoft van cap token, chi la token khong co quyen."
            % (", ".join(missing), " va ".join(missing)))
    return token


def _get(url: str, token: str, timeout: int) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "Prefer": _PREFER,
    })
    for attempt in range(_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                body = ""
            if exc.code in (429, 503) and attempt < _RETRIES:
                time.sleep(_retry_after(exc.headers.get("Retry-After")))
                continue
            raise oauth.OAuthError(
                "Graph HTTP %s %s %s" % (exc.code, url, body))
        except urllib.error.URLError as exc:
            raise oauth.OAuthError("khong goi duoc Graph: %s" % exc.reason)
    raise oauth.OAuthError("Graph throttle qua %d lan: %s" % (_RETRIES, url))


def _retry_after(value: Optional[str]) -> float:
    try:
        return min(60.0, max(1.0, float(value or 5)))
    except ValueError:
        return 5.0


def _pages(url: str, token: str, timeout: int) -> List[dict]:
    items: List[dict] = []
    while url:
        payload = _get(url, token, timeout)
        items.extend(payload.get("value") or [])
        url = payload.get("@odata.nextLink") or ""
    return items


def wanted_calendars(calendars: List[dict]) -> List[dict]:
    """Lich mac dinh + lich user tu tao. Bo lich chi doc: ngay le, sinh nhat,
    lich nguoi khac chia se. v1 khong hua lich chia se, con ngay le thi server
    moi tu co, chep sang chi thanh hai bo."""
    return [cal for cal in calendars
            if cal.get("isDefaultCalendar") or cal.get("canEdit", True)]


def list_events(cfg: Config, user: User, token: str) -> List[dict]:
    """Series master + su kien don, KHONG bung occurrence: /events cua Graph
    tra dung nhu vay, va RRULE giu nguyen thi dich moi hieu la mot chuoi."""
    timeout = cfg.sync.timeout
    upn = urllib.parse.quote(user.src_user)
    calendars = _pages(
        "%s/users/%s/calendars" % (GRAPH, upn), token, timeout)
    events: List[dict] = []
    for cal in wanted_calendars(calendars):
        cid = urllib.parse.quote(cal.get("id") or "")
        if not cid:
            continue
        events.extend(_pages(
            "%s/users/%s/calendars/%s/events?$top=100"
            % (GRAPH, upn, cid), token, timeout))
    return events


def list_contacts(cfg: Config, user: User, token: str) -> List[dict]:
    timeout = cfg.sync.timeout
    upn = urllib.parse.quote(user.src_user)
    seen = set()
    out: List[dict] = []
    urls = [
        "%s/users/%s/contacts?$top=100" % (GRAPH, upn),
    ]
    folders = _pages(
        "%s/users/%s/contactFolders" % (GRAPH, upn), token, timeout)
    for folder in folders:
        fid = urllib.parse.quote(folder.get("id") or "")
        if fid:
            urls.append("%s/users/%s/contactFolders/%s/contacts?$top=100"
                        % (GRAPH, upn, fid))
    for url in urls:
        for item in _pages(url, token, timeout):
            cid = item.get("id")
            if cid and cid in seen:
                continue
            if cid:
                seen.add(cid)
            out.append(item)
    return out


def _esc(value: str) -> str:
    value = (value or "").replace("\\", "\\\\").replace(";", "\\;")
    value = value.replace(",", "\\,").replace("\r\n", "\n").replace("\n", "\\n")
    return value


def _graph_dt(obj, is_all_day: bool) -> tuple:
    """(param, gia tri) cho mot dateTimeTimeZone cua Graph. Nhan ca chuoi ISO
    tran (originalStart, lastModifiedDateTime la chuoi, khong phai object)."""
    if isinstance(obj, str):
        obj = {"dateTime": obj, "timeZone": "UTC"}
    raw = ((obj or {}).get("dateTime") or "").replace("Z", "")
    date, _, time_part = raw.partition("T")
    ymd = date.replace("-", "")[:8]
    if not ymd:
        return "", ""
    if is_all_day or not time_part:
        return "VALUE=DATE", ymd
    hms = time_part.split(".")[0].split("+")[0].replace(":", "")[:6]
    if len(hms) < 6:
        hms = (hms + "000000")[:6]
    tz = ((obj or {}).get("timeZone") or "").upper()
    if tz in ("UTC", "GMT", ""):
        return "", ymd + "T" + hms + "Z"
    return "", ymd + "T" + hms


def _dt_line(name: str, obj, is_all_day: bool) -> str:
    param, value = _graph_dt(obj, is_all_day)
    if not value:
        return ""
    if param:
        return "%s;%s:%s" % (name, param, value)
    return "%s:%s" % (name, value)


def _stamp(event: dict) -> str:
    """DTSTAMP la bat buoc trong VEVENT (RFC 5545); server CalDAV nghiem se
    tu choi neu thieu. Lay tu lastModifiedDateTime, khong co thi lay gio nay."""
    raw = event.get("lastModifiedDateTime") or event.get("createdDateTime") or ""
    _param, value = _graph_dt(raw, False) if raw else ("", "")
    if not value:
        value = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return "DTSTAMP:" + value


def _rrule(recurrence: Optional[dict], is_all_day: bool) -> str:
    if not recurrence:
        return ""
    pattern = recurrence.get("pattern") or {}
    rng = recurrence.get("range") or {}
    kind = (pattern.get("type") or "").lower()
    freq = {
        "daily": "DAILY",
        "weekly": "WEEKLY",
        "absolutemonthly": "MONTHLY",
        "relativemonthly": "MONTHLY",
        "absoluteyearly": "YEARLY",
        "relativeyearly": "YEARLY",
    }.get(kind)
    if not freq:
        return ""
    parts = ["FREQ=" + freq]
    interval = int(pattern.get("interval") or 1)
    parts.append("INTERVAL=%d" % interval)
    days = [_DAYS[d.lower()] for d in (pattern.get("daysOfWeek") or [])
            if d and d.lower() in _DAYS]
    nth = _NTH.get((pattern.get("index") or "").lower(), "")
    if days and nth and kind in ("relativemonthly", "relativeyearly"):
        parts.append("BYDAY=" + ",".join(nth + d for d in days))
    elif days:
        parts.append("BYDAY=" + ",".join(days))
    if kind in ("absolutemonthly", "absoluteyearly") and pattern.get("dayOfMonth"):
        parts.append("BYMONTHDAY=%s" % pattern["dayOfMonth"])
    if kind == "absoluteyearly" and pattern.get("month"):
        parts.append("BYMONTH=%s" % pattern["month"])
    rtype = (rng.get("type") or "").lower()
    if rtype == "numbered" and rng.get("numberOfOccurrences"):
        parts.append("COUNT=%s" % rng["numberOfOccurrences"])
    elif rtype == "enddate" and rng.get("endDate"):
        # RFC 5545: UNTIL phai cung kieu voi DTSTART -- DTSTART co gio thi
        # UNTIL phai co gio (UTC). Zimbra tu choi RRULE lech kieu.
        until = str(rng["endDate"]).replace("-", "")[:8]
        if not is_all_day:
            until += "T235959Z"
        parts.append("UNTIL=" + until)
    return "RRULE:" + ";".join(parts)


def _plain_body(body: Optional[dict]) -> str:
    """Prefer header da xin text; van co the nhan HTML (Graph cu, hoac body
    danh dau html tu truoc). Bo tag thi con doc duoc, de nguyen thi DESCRIPTION
    thanh mot khoi <div>."""
    body = body or {}
    text = (body.get("content") or "").strip()
    if not text:
        return ""
    if (body.get("contentType") or "").lower() == "html":
        text = html.unescape(_TAGS.sub("", _BREAKS.sub("\n", text)))
        text = "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())
    return text


def vevent_block(event: dict) -> str:
    uid = (event.get("iCalUId") or event.get("id") or "").strip()
    all_day = bool(event.get("isAllDay"))
    lines = ["BEGIN:VEVENT", "UID:" + uid, _stamp(event)]
    start = _dt_line("DTSTART", event.get("start"), all_day)
    end = _dt_line("DTEND", event.get("end"), all_day)
    if start:
        lines.append(start)
    if end:
        lines.append(end)
    summary = event.get("subject") or ""
    if summary:
        lines.append("SUMMARY:" + _esc(summary))
    loc = ((event.get("location") or {}).get("displayName") or "")
    if loc:
        lines.append("LOCATION:" + _esc(loc))
    body = _plain_body(event.get("body"))
    if body:
        lines.append("DESCRIPTION:" + _esc(body))
    org = ((event.get("organizer") or {}).get("emailAddress") or {})
    if org.get("address"):
        cn = org.get("name") or org["address"]
        lines.append("ORGANIZER;CN=%s:mailto:%s" % (_esc(cn), org["address"]))
    for att in event.get("attendees") or []:
        addr = ((att.get("emailAddress") or {}).get("address") or "")
        if not addr:
            continue
        cn = (att.get("emailAddress") or {}).get("name") or addr
        lines.append("ATTENDEE;CN=%s:mailto:%s" % (_esc(cn), addr))
    rrule = _rrule(event.get("recurrence"), all_day)
    if rrule:
        lines.append(rrule)
    if event.get("type") == "exception" and event.get("originalStart"):
        orig = _dt_line("RECURRENCE-ID", event.get("originalStart"), all_day)
        if orig:
            lines.append(orig)
    if (event.get("sensitivity") or "").lower() in ("private", "confidential"):
        lines.append("CLASS:PRIVATE")
    if (event.get("showAs") or "").lower() == "free":
        lines.append("TRANSP:TRANSPARENT")
    if event.get("isCancelled"):
        lines.append("STATUS:CANCELLED")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def event_to_ics(event: dict, keep_attendees: bool = False) -> str:
    return events_to_ics([event], keep_attendees=keep_attendees)


def events_to_ics(events: List[dict], keep_attendees: bool = False) -> str:
    """Mot resource CalDAV = mot UID: master + cac exception cung UID di chung
    (RFC 4791), nen ca nhom vao mot VCALENDAR."""
    blocks = [vevent_block(ev) for ev in events]
    cal = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Postboat//PIM//",
        "\r\n".join(blocks),
        "END:VCALENDAR",
        "",
    ]
    return prepare_ics("\r\n".join(cal), keep_attendees=keep_attendees)


def _adr(kind: str, addr: Optional[dict]) -> str:
    addr = addr or {}
    parts = [addr.get("street"), addr.get("city"), addr.get("state"),
             addr.get("postalCode"), addr.get("countryOrRegion")]
    if not any(parts):
        return ""
    return "ADR;TYPE=%s:;;%s" % (kind, ";".join(_esc(p or "") for p in parts))


def contact_to_vcard(contact: dict) -> str:
    uid = (contact.get("id") or "").strip()
    fn = contact.get("displayName") or " ".join(
        p for p in (contact.get("givenName"), contact.get("surname")) if p)
    lines = ["BEGIN:VCARD", "VERSION:3.0", "UID:" + uid, "FN:" + _esc(fn)]
    given = contact.get("givenName") or ""
    surname = contact.get("surname") or ""
    if given or surname:
        lines.append("N:%s;%s;;;" % (_esc(surname), _esc(given)))
    for email in contact.get("emailAddresses") or []:
        addr = email.get("address") or ""
        if addr:
            lines.append("EMAIL;TYPE=INTERNET:" + addr)
    for tel in contact.get("businessPhones") or []:
        if tel:
            lines.append("TEL;TYPE=WORK,VOICE:" + tel)
    for tel in contact.get("homePhones") or []:
        if tel:
            lines.append("TEL;TYPE=HOME,VOICE:" + tel)
    if contact.get("mobilePhone"):
        lines.append("TEL;TYPE=CELL:" + contact["mobilePhone"])
    for kind, key in (("WORK", "businessAddress"), ("HOME", "homeAddress")):
        line = _adr(kind, contact.get(key))
        if line:
            lines.append(line)
    if contact.get("companyName"):
        lines.append("ORG:" + _esc(contact["companyName"]))
    if contact.get("jobTitle"):
        lines.append("TITLE:" + _esc(contact["jobTitle"]))
    bday = (contact.get("birthday") or "")[:10].replace("-", "")
    if len(bday) == 8 and bday.isdigit():
        lines.append("BDAY:" + bday)
    note = contact.get("personalNotes") or ""
    if note:
        lines.append("NOTE:" + _esc(note))
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


def calendar_items(cfg: Config, user: User, token: str) -> List[tuple]:
    grouped: Dict[str, List[dict]] = {}
    for event in list_events(cfg, user, token):
        if event.get("type") == "occurrence":
            continue
        uid = (event.get("iCalUId") or event.get("id") or "").strip()
        if not uid:
            continue
        grouped.setdefault(uid, []).append(event)
    items = []
    for uid, group in grouped.items():
        items.append((uid, events_to_ics(group, cfg.pim.keep_attendees),
                      "text/calendar"))
    return items


def contact_items(cfg: Config, user: User, token: str) -> List[tuple]:
    items = []
    for contact in list_contacts(cfg, user, token):
        vcf = contact_to_vcard(contact)
        uid = (contact.get("id") or "").strip()
        if uid:
            items.append((uid, vcf, "text/vcard"))
    return items
