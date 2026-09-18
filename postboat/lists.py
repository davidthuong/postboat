# -*- coding: utf-8 -*-
"""Nhom phan phoi (distribution group / mailing list / Google Group).

Khong co du lieu de chuyen, chi co ten nhom va thanh vien -- nhung moi he
thong mot cach xuat, moi he thong mot cach tao. Cung mot hinh voi hai ong kia
(imapsync cho thu, ICS/vCard cho lich): mot dinh dang trung gian lists.csv
(list, member) doc tu file xuat cua nguon, roi mot bo ghi cho tung dich.

Nguon doc duoc (theo cot, khong theo ten file):
  - Microsoft 365: file PowerShell Get-DistributionGroup + Get-DistributionGroupMember
    (cot List/Member), hoac chi Get-DistributionGroup (nhom chua co thanh vien).
  - Google Workspace: `gam print group-members` (group/role/email) va
    `gam print groups` (email/name); file "Export members" cua mot Google Group
    thi chay voi --list <dia chi nhom> vi file do khong co cot nhom.
  - Chinh lists.csv (list, name, member).

Dich ghi duoc: IceWarp -- bo lenh cho `tool file batch` va file thanh vien moi
dia chi mot dong (u_type 7 = User group, u_type 1 = Mailing list; API
Variables > Accounts, Shared). Dich khac chi co lists.csv de tao tay.

Dia chi doi theo users.csv: hop thu co trong do thi lay dst_user; con lai doi
domain theo cap src -> dst suy tu users.csv (hoac --dst-domain). Thanh vien
ngoai domain giu nguyen va duoc dem rieng.
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

# Dung lai bo doc CSV chiu loi cua mkusers: UTF-16 khong BOM, dong #TYPE,
# dau phan cach ';'... cung mot nguon PowerShell, cung mot kieu hong.
from .mailboxes import _email, _rows, decode  # noqa: F401  (decode dung o cli)
from .providers import fold
from .users import User

STATE_FILE = "lists.json"

# Ten cot da fold, theo thu tu uu tien.
LIST_COLUMNS = ("list", "group", "groupemail", "groupaddress", "listaddress",
                "distributiongroup", "nhom")
MEMBER_COLUMNS = ("member", "memberemail", "memberaddress", "email",
                  "emailaddress", "primarysmtpaddress", "address", "thanhvien")
NAME_COLUMNS = ("listname", "displayname", "groupname", "name", "description",
                "ten")
ROLE_COLUMNS = ("role", "membertype", "recipienttypedetails", "type")
# Kieu thanh vien (GAM: type = USER/GROUP/CUSTOMER), de bao dung khi khong co dia chi.
KIND_COLUMNS = ("type", "membertype", "recipienttypedetails")
OWNER_COLUMNS = ("owner", "managedby", "manager")
OWNER_ROLES = ("owner", "manager")
# Cot chi co trong file "Export members" cua Google Groups: khong co cot nhom.
GOOGLE_EXPORT_MARKS = ("groupstatus", "postingpermissions", "nickname")

# IceWarp U_Type (API Variables > Accounts, Shared): 1 Mailing list, 7 User group.
ICEWARP_KINDS = {"group": 7, "mailinglist": 1}

HOWTO = (
    "File can co cot nhom va cot thanh vien (List/Member, hoac group/email cua "
    "GAM), hoac chi cot dia chi nhom. Xem README muc 'lists'.")


class ListsError(ValueError):
    """File khong doc duoc. Ke thua ValueError de main() in mot cau."""


@dataclass
class MailList:
    address: str
    name: str = ""
    owner: str = ""
    members: List[str] = field(default_factory=list)
    external: int = 0       # thanh vien ngoai domain nguon/dich, sau khi doi

    def add(self, member: str) -> None:
        key = member.strip().lower()
        if key and key not in (m.lower() for m in self.members):
            self.members.append(member.strip())


@dataclass
class Parsed:
    lists: Dict[str, MailList] = field(default_factory=dict)   # key: dia chi thuong
    fmt: str = ""
    rows_read: int = 0
    warnings: List[str] = field(default_factory=list)

    def get(self, address: str, name: str = "") -> MailList:
        key = address.lower()
        item = self.lists.get(key)
        if item is None:
            item = MailList(address=address, name=name)
            self.lists[key] = item
        elif name and not item.name:
            item.name = name
        return item

    @property
    def members_total(self) -> int:
        return sum(len(l.members) for l in self.lists.values())


# --------------------------------------------------------------------------- #
# Doc
# --------------------------------------------------------------------------- #

def _pick(folded: Sequence[str], names: Sequence[str],
          taken: Iterable[int] = ()) -> Optional[int]:
    taken = set(taken)
    best: Optional[Tuple[int, int]] = None
    for i, cell in enumerate(folded):
        if i in taken or cell not in names:
            continue
        rank = names.index(cell)
        if best is None or rank < best[0]:
            best = (rank, i)
    return best[1] if best else None


def _columns(header: Sequence[str]) -> Dict[str, int]:
    """Nhan dien cot theo ten. 'list' luon la cot dia chi nhom; co 'member'
    thi file la cap nhom-thanh vien, khong thi file chi liet ke nhom."""
    folded = [fold(c) for c in header]
    idx: Dict[str, int] = {}
    li = _pick(folded, LIST_COLUMNS)
    if li is not None:
        idx["list"] = li
        mi = _pick(folded, MEMBER_COLUMNS, taken=(li,))
        if mi is not None:
            idx["member"] = mi
    else:
        ai = _pick(folded, MEMBER_COLUMNS)
        if ai is not None:
            idx["list"] = ai
    for key, names in (("name", NAME_COLUMNS), ("role", ROLE_COLUMNS),
                       ("owner", OWNER_COLUMNS)):
        i = _pick(folded, names, taken=idx.values())
        if i is not None:
            idx[key] = i
    # Cot kieu thanh vien co the trung voi cot role (M365 MemberType); khong
    # loai tru nhau.
    i = _pick(folded, KIND_COLUMNS, taken=(idx.get("list"), idx.get("member"),
                                          idx.get("name"), idx.get("owner")))
    if i is not None:
        idx["kind"] = i
    return idx


def _cell(row: Sequence[str], index: Optional[int]) -> str:
    if index is None or index < 0 or index >= len(row):
        return ""
    return (row[index] or "").strip()


def parse(text: str, members_of: str = "") -> Parsed:
    """Mot file -> cac nhom. `members_of`: file chi la thanh vien cua nhom do."""
    out = Parsed()
    rows = _rows(text)
    if not rows:
        raise ListsError("file rong. " + HOWTO)
    header = rows[0]
    folded = [fold(c) for c in header]
    idx = _columns(header)
    body = rows[1:]

    if not idx:
        # Khong co header: chap nhan dia chi tho -- hai cot (nhom, thanh vien)
        # hoac mot cot (chi nhom).
        body = rows
        widths = {len([c for c in r if _email(c)]) for r in body}
        if widths <= {2}:
            idx = {"list": 0, "member": 1}
        elif widths <= {1}:
            idx = {"list": 0}
        else:
            raise ListsError("khong nhan ra cot nao. " + HOWTO)
        header = []

    if members_of:
        col = idx.get("member", idx.get("list"))
        target = out.get(members_of)
        out.fmt = "thanh vien cua %s" % members_of
        for n, row in enumerate(body, start=2 if header else 1):
            out.rows_read += 1
            addr = _email(_cell(row, col))
            if not addr:
                out.warnings.append("dong %d: khong co dia chi, bo" % n)
                continue
            target.add(addr)
            if fold(_cell(row, idx.get("role"))) in OWNER_ROLES and not target.owner:
                target.owner = addr
        return out

    if "list" in idx and "member" not in idx and any(
            m in folded for m in GOOGLE_EXPORT_MARKS):
        raise ListsError(
            "day la file 'Export members' cua mot Google Group, khong co cot "
            "nhom -- chay lai voi --list <dia chi nhom>")

    pairs = "member" in idx
    out.fmt = "cap nhom-thanh vien" if pairs else "chi danh sach nhom"
    for n, row in enumerate(body, start=2 if header else 1):
        out.rows_read += 1
        list_addr = _email(_cell(row, idx["list"]))
        if not list_addr:
            out.warnings.append("dong %d: cot nhom khong co dia chi, bo" % n)
            continue
        item = out.get(list_addr, _cell(row, idx.get("name")))
        owner = _email(_cell(row, idx.get("owner")))
        if owner and not item.owner:
            item.owner = owner
        if not pairs:
            continue
        member = _email(_cell(row, idx["member"]))
        if not member:
            out.warnings.append(
                "dong %d: nhom %s co thanh vien khong phai dia chi (%s) -- "
                "IceWarp khong co kieu 'ca domain', them tay neu can"
                % (n, list_addr, _cell(row, idx["member"]) or
                   _cell(row, idx.get("kind")) or "?"))
            continue
        item.add(member)
        if fold(_cell(row, idx.get("role"))) in OWNER_ROLES and not item.owner:
            item.owner = member
    return out


def merge(into: Parsed, part: Parsed) -> Parsed:
    for key, item in part.lists.items():
        target = into.get(item.address, item.name)
        if item.owner and not target.owner:
            target.owner = item.owner
        for m in item.members:
            target.add(m)
    into.rows_read += part.rows_read
    into.warnings.extend(part.warnings)
    return into


# --------------------------------------------------------------------------- #
# Doi dia chi
# --------------------------------------------------------------------------- #

def _domain(addr: str) -> str:
    return addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""


@dataclass
class Mapping:
    users: Dict[str, str] = field(default_factory=dict)      # src_user -> dst_user
    domains: Dict[str, str] = field(default_factory=dict)    # src domain -> dst domain
    source_domains: Set[str] = field(default_factory=set)
    dst_domain: str = ""

    def translate(self, addr: str) -> str:
        key = addr.lower()
        if key in self.users:
            return self.users[key]
        local, _, dom = addr.rpartition("@")
        dom = dom.lower()
        if dom in self.source_domains:
            if self.dst_domain:
                return "%s@%s" % (local, self.dst_domain)
            if dom in self.domains:
                return "%s@%s" % (local, self.domains[dom])
        return addr

    def is_external(self, addr: str) -> bool:
        dom = _domain(addr)
        known = set(self.source_domains) | set(self.domains.values())
        if self.dst_domain:
            known.add(self.dst_domain)
        return bool(dom) and dom not in known


def mapping_from(users: Sequence[User], lists: Iterable[MailList],
                 dst_domain: str = "") -> Mapping:
    """Suy cach doi dia chi tu users.csv. Domain nguon nao map sang hai domain
    dich khac nhau thi khong doi domain do (chi doi tung hop thu co trong file)."""
    m = Mapping(dst_domain=dst_domain.strip().lstrip("@").lower())
    conflicts: Set[str] = set()
    for u in users:
        m.users[u.src_user.lower()] = u.dst_user
        s, d = _domain(u.src_user), _domain(u.dst_user)
        if s:
            m.source_domains.add(s)
            if s in m.domains and m.domains[s] != d:
                conflicts.add(s)
            m.domains[s] = d
    for s in conflicts:
        m.domains.pop(s, None)
    for item in lists:
        dom = _domain(item.address)
        if dom:
            m.source_domains.add(dom)
    return m


def translate_all(parsed: Parsed, mapping: Mapping) -> List[MailList]:
    out: List[MailList] = []
    for item in parsed.lists.values():
        dest = MailList(address=mapping.translate(item.address), name=item.name,
                        owner=mapping.translate(item.owner) if item.owner else "")
        for member in item.members:
            dest.add(mapping.translate(member))
        dest.external = sum(1 for x in dest.members if mapping.is_external(x))
        out.append(dest)
    return out


# --------------------------------------------------------------------------- #
# Ghi
# --------------------------------------------------------------------------- #

def write_csv(path: Path, lists: Sequence[MailList]) -> Path:
    """lists.csv trung gian: list, name, member. Nhom rong van co mot dong."""
    path = Path(path)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["list", "name", "member"])
        for item in lists:
            if not item.members:
                w.writerow([item.address, item.name, ""])
            for member in item.members:
                w.writerow([item.address, item.name, member])
    return path


def _q(value: str) -> str:
    """Gia tri cho tool.exe: mot dong, trong ngoac kep, khong chua ngoac kep."""
    return '"%s"' % " ".join((value or "").replace('"', "'").split())


def member_filename(address: str) -> str:
    return address.lower() + ".txt"


def windows_path(path: str) -> bool:
    """IceWarp chay ca tren Windows lan Linux, va ban Windows la ban hay gap.
    Duong dan quyet dinh ba thu: dau tach thu muc, ket thuc dong trong file
    thanh vien, va ten file thuc thi (`tool.exe` hay `tool.sh`, ca hai nam
    ngay trong <InstallDirectory>)."""
    p = (path or "").strip()
    if p.startswith("\\\\"):          # UNC \\server\share
        return True
    if len(p) >= 3 and p[0].isalpha() and p[1] == ":" and p[2] in "\\/":
        return True
    return "\\" in p


def tool_name(listdir: str) -> str:
    return "tool.exe" if windows_path(listdir) else "tool.sh"


def remote_join(listdir: str, *parts: str) -> str:
    """Noi duong dan theo kieu cua chinh `listdir`, khong theo kieu cua may
    dang chay tool nay: file sinh tren Windows co the la cho mot IceWarp
    Linux va nguoc lai."""
    sep = "\\" if windows_path(listdir) else "/"
    return sep.join([listdir.rstrip("/\\")] + [p.strip("/\\") for p in parts])


def default_tooldir(listdir: str) -> str:
    """Thu muc cai IceWarp, noi co tool.exe / tool.sh."""
    return "C:\\Program Files\\IceWarp" if windows_path(listdir) else "/opt/icewarp"


def icewarp_script_name(listdir: str) -> str:
    return "icewarp.cmd" if windows_path(listdir) else "icewarp.sh"


def _cmd_line(line: str) -> str:
    """Dong trong file .cmd: % la bien moi truong ke ca trong ngoac kep."""
    return line.replace("%", "%%")


def _sh_line(line: str) -> str:
    """Dong trong file .sh: trong ngoac kep, $ va ` van duoc shell hieu."""
    return line.replace("$", "\\$").replace("`", "\\`")


def icewarp_script_lines(lists: Sequence[MailList], listdir: str,
                         kind: str = "group", default_owner: str = "",
                         tooldir: str = "") -> List[str]:
    """Script goi thang tool.exe / tool.sh tung dong, thay cho `file batch`.

    Do 18/09/2026 tren IceWarp Windows: `tool.exe file batch <file>` im lang
    va KHONG tao gi, con go thang `tool.exe create account ...` thi tao ngay
    va in "Account ... created.". Nen script la duong chinh; sau moi nhom co
    mot dong display de doc ket qua ngay tai cho, khong phai tin.
    """
    windows = windows_path(listdir)
    tool = tool_name(listdir)
    tooldir = tooldir or default_tooldir(listdir)
    field = "g_listfile" if kind == "group" else "m_listfile"
    creates = icewarp_lines(lists, listdir, kind, default_owner)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    out: List[str] = []
    if windows:
        out += ["@echo off",
                "rem Sinh boi postboat.py lists luc %s. Chay trong cmd (Administrator)." % stamp,
                "rem Sai thu muc cai IceWarp thi sua dong cd duoi day, hoac sinh lai voi --tooldir.",
                'cd /d "%s"' % tooldir]
        for item, create in zip(lists, creates):
            out.append(_cmd_line("%s %s" % (tool, create)))
            out.append("%s display account %s u_type %s" % (tool, item.address, field))
        out.append("echo Xong: %d nhom." % len(lists))
    else:
        out += ["#!/bin/sh",
                "# Sinh boi postboat.py lists luc %s." % stamp,
                '# Sai thu muc cai IceWarp thi sua dong cd duoi day, hoac sinh lai voi --tooldir.',
                'cd "%s" || exit 1' % tooldir]
        for item, create in zip(lists, creates):
            out.append(_sh_line("./%s %s" % (tool, create)))
            out.append("./%s display account %s u_type %s" % (tool, item.address, field))
        out.append('echo "Xong: %d nhom."' % len(lists))
    return out


def icewarp_lines(lists: Sequence[MailList], listdir: str, kind: str = "group",
                  default_owner: str = "") -> List[str]:
    """Moi nhom mot dong `create account ...` cho `tool file batch`.

    Khong co dong ghi chu: tai lieu chi noi "moi dong mot lenh", khong noi
    gi ve comment, nen khong danh cuoc.
    """
    if kind not in ICEWARP_KINDS:
        raise ListsError("kind phai la group hoac mailinglist")
    utype = ICEWARP_KINDS[kind]
    lines: List[str] = []
    for item in lists:
        path = remote_join(listdir, "members", member_filename(item.address))
        name = item.name or item.address.split("@", 1)[0]
        if kind == "group":
            lines.append("create account %s u_type %d u_name %s g_listfile %s"
                         % (item.address, utype, _q(name), _q(path)))
        else:
            owner = item.owner or default_owner or (
                "postmaster@" + _domain(item.address))
            lines.append(
                "create account %s u_type %d u_name %s m_owneraddress %s "
                "m_sendalllists 0 m_listfile %s"
                % (item.address, utype, _q(name), _q(owner), _q(path)))
    return lines


def write_icewarp(outdir: Path, lists: Sequence[MailList], listdir: str,
                  kind: str = "group", default_owner: str = "",
                  tooldir: str = "") -> Tuple[Path, List[Path]]:
    """Ghi script (icewarp.cmd / icewarp.sh), file batch tham khao, file thanh
    vien va README. Tra ve (duong dan script, cac file thanh vien)."""
    outdir = Path(outdir)
    members_dir = outdir / "members"
    members_dir.mkdir(parents=True, exist_ok=True)
    # File nay do IceWarp doc, khong phai git hay shell: ket thuc dong theo
    # may dich. Ban Windows tu ghi file thanh vien bang CRLF (nut Text file
    # trong admin console), nen gui LF sang do la tu chuoc rui ro.
    eol = "\r\n" if windows_path(listdir) else "\n"
    files: List[Path] = []
    for item in lists:
        path = members_dir / member_filename(item.address)
        with path.open("w", encoding="utf-8", newline="") as fh:
            for member in item.members:
                fh.write(member + eol)
        files.append(path)
    batch = outdir / "icewarp.batch"
    lines = icewarp_lines(lists, listdir, kind, default_owner)
    with batch.open("w", encoding="utf-8", newline="") as fh:
        fh.write(eol.join(lines) + eol)
    script = outdir / icewarp_script_name(listdir)
    with script.open("w", encoding="utf-8", newline="") as fh:
        fh.write(eol.join(icewarp_script_lines(
            lists, listdir, kind, default_owner, tooldir)) + eol)
    tool = tool_name(listdir)
    field = "g_listfile" if kind == "group" else "m_listfile"
    readme = outdir / "README.txt"
    with readme.open("w", encoding="utf-8", newline="") as fh:
        fh.write(eol.join([
            "Sinh boi postboat.py lists luc %s." % time.strftime("%Y-%m-%d %H:%M"),
            "Copy nguyen thu muc nay len may IceWarp tai: %s" % listdir,
            "Roi chay:  %s" % remote_join(listdir, script.name),
            "  (script cd vao %s roi goi %s create + display cho tung nhom;"
            % (tooldir or default_tooldir(listdir), tool),
            "   moi nhom phai in 'Account ... created.' va u_type: %d)" % ICEWARP_KINDS[kind],
            "Kiem lai: %s display account <nhom> u_type u_name %s" % (tool, field),
            "%d nhom, %d thanh vien. Loai tai khoan: %s (u_type %d)." % (
                len(lists), sum(len(l.members) for l in lists),
                kind, ICEWARP_KINDS[kind]),
            "icewarp.batch la cung noi dung cho `%s file batch` -- tren may test "
            "18/09/2026 lenh do im lang va khong tao gi, chi de tham khao." % tool,
            ""]))
    return script, files


# --------------------------------------------------------------------------- #
# Trang thai cho handover
# --------------------------------------------------------------------------- #

def state_path(statedir) -> Path:
    return Path(statedir) / STATE_FILE


def load_state(statedir) -> dict:
    path = state_path(statedir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) and data.get("lists") else {}


def save_state(statedir, lists: Sequence[MailList], dest_key: str,
               out_dir) -> Path:
    path = state_path(statedir)
    data = {
        "at": time.strftime("%Y-%m-%d %H:%M"),
        "dest": dest_key,
        "out": str(out_dir),
        "lists": {
            item.address: {
                "name": item.name,
                "members": len(item.members),
                "external": item.external,
            } for item in lists
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True),
                    encoding="utf-8")
    return path
