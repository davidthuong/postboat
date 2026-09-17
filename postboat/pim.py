# -*- coding: utf-8 -*-
"""Ong lich va danh ba -- nam ngoai duong IMAP.

Mail van di imapsync (runner.py). Module nay khong duoc import tu runner hay
discover: token IMAP va skip_names Calendar/Contacts giu nguyen. Ly do o
research/calendar-contacts.md: IMAP khong cho lich/danh ba, moi tool tren thi
truong deu gan them mot ong rieng ben canh ong mail.

Mac dinh tat ([pim] enabled = false). Bat roi chay `postboat.py pim`.
--dry: doc nguon, khong PUT. Khong --dry: PUT CalDAV/CardDAV ben dich, roi
ghi ket qua vao state/pim.json de `handover` dua vao bien ban.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import unquote

from .config import Config
from .oauth import OAuthError
from .pim_dav import (DavClient, DavError, fallback_uid, filename_for,
                      looks_like, prepare_ics, uid_from_ics, uid_from_vcard)
from .users import User

Emit = Callable[[str], None]

DAV_PROVIDERS = ("icewarp", "zimbra")
GRAPH_PROVIDERS = ("m365",)
# Nguon co CalDAV/CardDAV nhung URL khong suy duoc tu host IMAP -> phai dien
# source_webdav_base (bang URL o research/calendar-contacts.md 4.6).
MANUAL_DAV_PROVIDERS = ("yahoo", "zoho", "icloud", "imap")

STATE_FILE = "pim.json"


@dataclass
class PimResult:
    user: str
    dst_user: str = ""
    calendar_ok: int = 0
    calendar_skip: int = 0
    calendar_err: int = 0
    contacts_ok: int = 0
    contacts_skip: int = 0
    contacts_err: int = 0
    # Su kien co nguoi tham du da bo ORGANIZER/ATTENDEE (keep_attendees=false).
    calendar_neutralized: int = 0
    error: str = ""
    dry_uids: List[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return bool(self.error or self.calendar_err or self.contacts_err)


# --------------------------------------------------------------------------- #
# URL
# --------------------------------------------------------------------------- #

def _dav_base_for(key: str, host: str) -> str:
    """Goc CalDAV/CardDAV suy tu provider. Chi hai server co hinh URL biet
    truoc; con lai phai khai tay -- Postboat di bat ky nguon nao sang bat ky
    dich nao, khong duoc mac dinh dich la IceWarp."""
    if key == "icewarp":
        return "https://%s/webdav" % host
    if key == "zimbra":
        return "https://%s/dav" % host
    return ""


def dest_dav_base(cfg: Config) -> str:
    written = (cfg.pim.webdav_base or "").strip().rstrip("/")
    if written:
        return written
    return _dav_base_for(cfg.dest.provider.key, cfg.dest.host)


def source_dav_base(cfg: Config) -> str:
    written = (cfg.pim.source_webdav_base or "").strip().rstrip("/")
    if written:
        return written
    return _dav_base_for(cfg.source.provider.key, cfg.source.host)


def _collection_url(base: str, mailbox: str, collection: str) -> str:
    from urllib.parse import quote
    user = quote(mailbox, safe="@._-")
    name = quote(collection.strip().strip("/"), safe="@._-")
    return "%s/%s/%s/" % (base.rstrip("/"), user, name)


def dest_calendar_url(cfg: Config, user: User) -> str:
    return _collection_url(dest_dav_base(cfg), user.dst_user, cfg.pim.calendar)


def dest_contacts_url(cfg: Config, user: User) -> str:
    return _collection_url(dest_dav_base(cfg), user.dst_user, cfg.pim.contacts)


def source_calendar_url(cfg: Config, user: User) -> str:
    return _collection_url(source_dav_base(cfg), user.src_user, cfg.pim.calendar)


def source_contacts_url(cfg: Config, user: User) -> str:
    return _collection_url(source_dav_base(cfg), user.src_user, cfg.pim.contacts)


def plan_lines(cfg: Config, users: List[User]) -> List[str]:
    lines: List[str] = []
    for user in users:
        lines.append("%s  calendar %s" % (
            user.src_user, dest_calendar_url(cfg, user)))
        lines.append("%s  contacts %s" % (
            user.src_user, dest_contacts_url(cfg, user)))
    return lines


# --------------------------------------------------------------------------- #
# Nguon nao doc duoc
# --------------------------------------------------------------------------- #

def source_kind(cfg: Config) -> str:
    key = cfg.source.provider.key
    if key in GRAPH_PROVIDERS:
        return "graph"
    if key in DAV_PROVIDERS:
        return "dav"
    if (cfg.pim.source_webdav_base or "").strip() and key in MANUAL_DAV_PROVIDERS:
        return "dav"
    return ""


def source_label(cfg: Config) -> str:
    """Mot dong noi ong PIM se doc nguon bang gi, in truoc khi chay."""
    kind = source_kind(cfg)
    if kind == "graph":
        return "Microsoft Graph, tenant %s (Calendars.Read + Contacts.Read)" % (
            cfg.source.oauth.tenant or "?")
    if kind == "dav":
        return "CalDAV/CardDAV %s (mat khau hop thu)" % source_dav_base(cfg)
    return unsupported_reason(cfg)


def unsupported_reason(cfg: Config) -> str:
    key = cfg.source.provider.key
    if key == "gmail":
        return (
            "Nguon gmail chua ho tro ong PIM: app password IMAP khong dang "
            "nhap duoc CalDAV/Calendar API (Google bat OAuth). Mail van di "
            "`postboat.py sync` nhu cu."
        )
    if key == "exchange":
        return (
            "Nguon exchange (tu dung) chua ho tro ong PIM: can EWS, khong "
            "phai IMAP hay Graph. Mail van di `postboat.py sync` nhu cu."
        )
    if key in ("dovecot", "courier"):
        return (
            "Nguon %s thuong khong co lich/danh ba phia server. Ong PIM "
            "khong co gi de doc." % key
        )
    if key in MANUAL_DAV_PROVIDERS:
        return (
            "Nguon %s: dat [pim] source_webdav_base bang URL CalDAV/CardDAV "
            "(xem research/calendar-contacts.md), roi chay lai." % key
        )
    return "Nguon %s chua ho tro ong PIM." % key


# --------------------------------------------------------------------------- #
# Dich nao ghi duoc
# --------------------------------------------------------------------------- #
# Ghi bang CalDAV/CardDAV PUT. IceWarp va Zimbra suy duoc URL; server CalDAV
# khac (SOGo, Kerio, Nextcloud...) thi khai webdav_base toi thu muc cha cua
# hop thu, vi hinh {base}/{email}/{Calendar}/ la cua IceWarp/Zimbra. M365 va
# Gmail lam dich khong co CalDAV mo cho mat khau: phai ghi bang Graph/OAuth,
# chua lam.

def dest_kind(cfg: Config) -> str:
    key = cfg.dest.provider.key
    if key in DAV_PROVIDERS:
        return "dav"
    if (cfg.pim.webdav_base or "").strip() and key in MANUAL_DAV_PROVIDERS:
        return "dav"
    return ""


def dest_label(cfg: Config) -> str:
    if dest_kind(cfg) == "dav":
        return "CalDAV/CardDAV %s (mat khau hop thu)" % dest_dav_base(cfg)
    return unsupported_dest_reason(cfg)


def unsupported_dest_reason(cfg: Config) -> str:
    key = cfg.dest.provider.key
    if key == "gmail":
        return (
            "Dich gmail chua ho tro ong PIM: CalDAV/CardDAV Google chi nhan "
            "OAuth, app password khong dang nhap duoc. Mail van di "
            "`postboat.py sync` nhu cu."
        )
    if key == "m365":
        return (
            "Dich m365 chua ho tro ong PIM: Exchange Online khong co CalDAV, "
            "phai ghi bang Graph (Calendars.ReadWrite + Contacts.ReadWrite) "
            "-- chua lam. Mail van di `postboat.py sync` nhu cu."
        )
    if key == "exchange":
        return (
            "Dich exchange (tu dung) chua ho tro ong PIM: can EWS, chua lam. "
            "Mail van di `postboat.py sync` nhu cu."
        )
    if key in ("dovecot", "courier"):
        return (
            "Dich %s khong co lich/danh ba phia server; ong PIM khong co cho "
            "de ghi." % key
        )
    if key in MANUAL_DAV_PROVIDERS:
        return (
            "Dich %s: dat [pim] webdav_base bang URL CalDAV/CardDAV cua dich "
            "(xem research/calendar-contacts.md), roi chay lai." % key
        )
    return "Dich %s chua ho tro ong PIM." % key


# --------------------------------------------------------------------------- #
# Doc nguon
# --------------------------------------------------------------------------- #

def _timeout(cfg: Config) -> int:
    return max(30, int(cfg.sync.timeout or 60))


def _dav_client(mailbox: str, password: str, cfg: Config, side: str) -> DavClient:
    server = cfg.source if side == "source" else cfg.dest
    return DavClient(
        mailbox, password, timeout=_timeout(cfg),
        tls_verify=server.tls_verify)


def _read_dav_collection(client: DavClient, url: str, kind: str,
                         keep_attendees: bool = False) -> List[tuple]:
    items: List[tuple] = []
    for href in client.list_hrefs(url):
        body = client.get(href)
        if not looks_like(body, kind):
            # Trang HTML hay object khac loai: bo, khong dem la loi. Neu dem
            # la loi thi mot folder con trong Calendar lam ca mailbox "chua dat".
            continue
        if kind == "calendar":
            body = prepare_ics(body, keep_attendees=keep_attendees)
            uid = uid_from_ics(body) or fallback_uid(body, "cal")
            items.append((uid, body, "text/calendar"))
        else:
            uid = uid_from_vcard(body) or fallback_uid(body, "card")
            items.append((uid, body, "text/vcard"))
    return items


def read_source(cfg: Config, user: User) -> Tuple[List[tuple], List[tuple]]:
    kind = source_kind(cfg)
    if kind == "dav":
        if not user.src_password:
            raise DavError(
                "CalDAV nguon can mat khau hop thu (cot src_password); "
                "auth = master/oauth2 khong dung duoc cho WebDAV")
        client = _dav_client(user.src_user, user.src_password, cfg, "source")
        calendar = _read_dav_collection(
            client, source_calendar_url(cfg, user), "calendar",
            keep_attendees=cfg.pim.keep_attendees)
        contacts = _read_dav_collection(
            client, source_contacts_url(cfg, user), "contacts")
        return calendar, contacts
    if kind == "graph":
        from . import pim_graph
        token = pim_graph.graph_token(cfg)
        return (pim_graph.calendar_items(cfg, user, token),
                pim_graph.contact_items(cfg, user, token))
    raise DavError(unsupported_reason(cfg))


# --------------------------------------------------------------------------- #
# Ghi dich
# --------------------------------------------------------------------------- #

def existing_names(client: DavClient, collection_url: str) -> set:
    """Ten file (da unquote, chu thuong) dang co trong collection dich."""
    names = set()
    for href in client.list_hrefs(collection_url):
        name = unquote(href.rstrip("/").rsplit("/", 1)[-1]).lower()
        if name:
            names.add(name)
    return names


def _put_items(client: DavClient, collection_url: str, items: List[tuple],
               ext: str, result: PimResult, field_name: str) -> None:
    base = collection_url if collection_url.endswith("/") else collection_url + "/"
    # "Da co" phai hoi truoc bang PROPFIND, khong tin ma tra ve cua PUT: Zimbra
    # 8.8 tra 2xx cho PUT de len su kien da co du gui If-None-Match: * (do that
    # 17/09 tren lab) -- khong nhan ban vi cung ten file, nhung dem sai. Van giu
    # If-None-Match cho server tuan RFC, va 409 (no-uid-conflict) cung la da co.
    try:
        existing = existing_names(client, base)
    except DavError:
        existing = set()
    for uid, body, ctype in items:
        name = filename_for(uid, ext)
        if unquote(name).lower() in existing:
            _bump(result, field_name + "_skip")
            continue
        try:
            outcome = client.put(base + name, body, ctype)
        except DavError:
            _bump(result, field_name + "_err")
            continue
        _bump(result, field_name + ("_skip" if outcome == "exists" else "_ok"))


def _bump(result: PimResult, attr: str) -> None:
    setattr(result, attr, getattr(result, attr) + 1)


def run_user(cfg: Config, user: User, dry: bool = False) -> PimResult:
    result = PimResult(user=user.src_user, dst_user=user.dst_user)
    if not source_kind(cfg):
        result.error = unsupported_reason(cfg)
        return result
    try:
        calendar, contacts = read_source(cfg, user)
    except (DavError, OAuthError) as exc:
        result.error = str(exc)
        return result
    result.calendar_neutralized = sum(
        1 for _uid, body, _t in calendar if "X-POSTBOAT-ATTENDEE" in body)
    if dry:
        result.calendar_ok = len(calendar)
        result.contacts_ok = len(contacts)
        result.dry_uids = [uid for uid, _body, _t in calendar + contacts]
        return result
    if not dest_kind(cfg):
        result.error = unsupported_dest_reason(cfg)
        return result
    if not user.dst_password:
        result.error = ("CalDAV dich can mat khau hop thu (cot dst_password); "
                        "auth = master khong dung duoc cho WebDAV")
        return result
    dest = _dav_client(user.dst_user, user.dst_password, cfg, "dest")
    try:
        _put_items(dest, dest_calendar_url(cfg, user), calendar, "ics",
                   result, "calendar")
        _put_items(dest, dest_contacts_url(cfg, user), contacts, "vcf",
                   result, "contacts")
    except DavError as exc:
        result.error = str(exc)
    return result


def run_all(cfg: Config, users: List[User], dry: bool = False,
            emit: Optional[Emit] = None) -> List[PimResult]:
    say = emit or (lambda _m: None)
    results: List[PimResult] = []
    for user in users:
        result = run_user(cfg, user, dry=dry)
        results.append(result)
        if result.error:
            say("%s  LOI %s" % (user.src_user, result.error))
            continue
        verb = "se ghi" if dry else "ghi"
        say("%s  calendar %d %s, %d da co, %d loi" % (
            user.src_user, result.calendar_ok, verb,
            result.calendar_skip, result.calendar_err))
        if result.calendar_neutralized:
            say("%s  %d su kien co nguoi tham du: bo ORGANIZER/ATTENDEE, ghi "
                "vao mo ta -- dich khong gui lai loi moi (keep_attendees = false)"
                % (user.src_user, result.calendar_neutralized))
        say("%s  contacts %d %s, %d da co, %d loi" % (
            user.src_user, result.contacts_ok, verb,
            result.contacts_skip, result.contacts_err))
        if dry:
            for uid in result.dry_uids:
                say("  %s" % uid)
    return results


def totals(results: List[PimResult]) -> Dict[str, int]:
    out = {"users": len(results), "errors": 0}
    for key in ("calendar_ok", "calendar_skip", "calendar_err",
                "contacts_ok", "contacts_skip", "contacts_err"):
        out[key] = sum(getattr(r, key) for r in results)
    out["errors"] = sum(1 for r in results if r.error)
    return out


# --------------------------------------------------------------------------- #
# Trang thai cho handover
# --------------------------------------------------------------------------- #
# Bien ban ban giao la to giay duy nhat con lai sau khi minh roi di. Neu hop
# dong co lich/danh ba ma bien ban van ghi "khong thuoc pham vi" thi to giay
# sai; nen moi lan chay that ghi lai ket qua theo tung mailbox de handover doc.

def state_path(statedir) -> Path:
    return Path(statedir) / STATE_FILE


def load_results(statedir) -> Dict[str, dict]:
    path = state_path(statedir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_results(statedir, results: List[PimResult]) -> Path:
    """Gop vao file cu theo src_user: chay lai mot mailbox thi ghi de dong do,
    cac mailbox khac giu nguyen -- cung cach handover gop cac lan sync."""
    path = state_path(statedir)
    data = load_results(statedir)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    for r in results:
        data[r.user] = {
            "src_user": r.user,
            "dst_user": r.dst_user,
            "calendar_ok": r.calendar_ok,
            "calendar_skip": r.calendar_skip,
            "calendar_err": r.calendar_err,
            "contacts_ok": r.contacts_ok,
            "contacts_skip": r.contacts_skip,
            "contacts_err": r.contacts_err,
            "calendar_neutralized": r.calendar_neutralized,
            "error": r.error,
            "at": stamp,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True),
                    encoding="utf-8")
    return path
