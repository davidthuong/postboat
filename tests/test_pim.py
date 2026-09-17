# -*- coding: utf-8 -*-
"""Ong PIM (lich/danh ba) nam ngoai duong mail.

Hop dong khoa o day: mac dinh tat; `sync` khong bao gio goi PIM; nguon khong
doc duoc thi tu choi truoc khi cham mang; --dry doc ma khong PUT; PUT giu UID
nen chay lai khong nhan ban; ket qua that ghi state/pim.json cho handover.
"""

import base64
import http.server
import io
import json
import os
import re
import shutil
import sys
import tempfile
import textwrap
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from postboat import cli, pim, runner
from postboat import providers as prov
from postboat.config import Config, Paths, PimConf, ServerConf, SyncConf, load_config
from postboat.oauth import OAuthConf, OAuthError
from postboat.users import User

from test_discover import GMAIL_EN, parse

USER = User("an@cu.com", "apppassword16chr", "an@moi.vn", "MatKhau", row=2)

CONFIG = """
[source]
host = imap.gmail.com
[dest]
host = mail.congty.vn
[paths]
imapsync = {imapsync}
logdir = logs
statedir = state
"""

USERS = """src_user,src_password,dst_user,dst_password
an@cu.com,aaaa bbbb cccc dddd,an@moi.vn,MatKhau1
"""


def make_cfg(pim_conf=None, dest_host="mail.congty.vn"):
    return Config(
        source=ServerConf("imap.gmail.com", 993, True),
        dest=ServerConf(dest_host, 993, True),
        sync=SyncConf(),
        paths=Paths(imapsync="imapsync", logdir=Path("logs"),
                    statedir=Path("state")),
        path=Path("config.ini"),
        pim=pim_conf or PimConf(),
    )


def fake_jwt(claims):
    """Token gia chi de doc claims; oauth.token_roles khong xac thuc chu ky."""
    body = base64.urlsafe_b64encode(
        json.dumps(claims).encode("utf-8")).decode("ascii").rstrip("=")
    return "h." + body + ".s"


class TestMailPathDoesNotImportPim(unittest.TestCase):
    def test_runner_module_does_not_know_pim(self):
        self.assertNotIn("pim", runner.__dict__)


class TestDestUrls(unittest.TestCase):
    def test_icewarp_default_webdav_path(self):
        cfg = make_cfg()
        cfg.dest.provider = prov.ICEWARP
        self.assertEqual(
            pim.dest_calendar_url(cfg, USER),
            "https://mail.congty.vn/webdav/an@moi.vn/Calendar/",
        )
        self.assertEqual(
            pim.dest_contacts_url(cfg, USER),
            "https://mail.congty.vn/webdav/an@moi.vn/Contacts/",
        )

    def test_written_webdav_base_wins(self):
        cfg = make_cfg(PimConf(webdav_base="https://gw.congty.vn:8443/webdav/"))
        self.assertEqual(
            pim.dest_calendar_url(cfg, USER),
            "https://gw.congty.vn:8443/webdav/an@moi.vn/Calendar/",
        )

    def test_collection_names_can_be_renamed(self):
        cfg = make_cfg(PimConf(calendar="Lich", contacts="DanhBa"))
        cfg.dest.provider = prov.ICEWARP
        self.assertTrue(pim.dest_calendar_url(cfg, USER).endswith("/Lich/"))
        self.assertTrue(pim.dest_contacts_url(cfg, USER).endswith("/DanhBa/"))

    def test_zimbra_dest_uses_dav_path(self):
        """Dich khong mac dinh la IceWarp: Postboat di bat ky nguon nao sang
        bat ky dich nao."""
        cfg = make_cfg()
        cfg.dest = ServerConf("zimbra.moi.vn", 993, True, provider=prov.ZIMBRA)
        self.assertEqual(
            pim.dest_calendar_url(cfg, USER),
            "https://zimbra.moi.vn/dav/an@moi.vn/Calendar/")

    def test_unknown_dest_has_no_guessed_base(self):
        cfg = make_cfg()   # dich = imap generic
        self.assertEqual(pim.dest_dav_base(cfg), "")
        self.assertEqual(pim.dest_kind(cfg), "")
        self.assertIn("webdav_base", pim.unsupported_dest_reason(cfg))


class TestDestKind(unittest.TestCase):
    def _cfg(self, provider, pim_conf=None):
        cfg = make_cfg(pim_conf)
        cfg.dest = ServerConf("moi.vn", 993, True, provider=provider)
        return cfg

    def test_icewarp_and_zimbra_are_dav(self):
        self.assertEqual(pim.dest_kind(self._cfg(prov.ICEWARP)), "dav")
        self.assertEqual(pim.dest_kind(self._cfg(prov.ZIMBRA)), "dav")
        self.assertIn("CalDAV", pim.dest_label(self._cfg(prov.ZIMBRA)))

    def test_m365_and_gmail_dest_say_why(self):
        cfg = self._cfg(prov.M365)
        self.assertEqual(pim.dest_kind(cfg), "")
        self.assertIn("Graph", pim.unsupported_dest_reason(cfg))
        cfg = self._cfg(prov.GMAIL)
        self.assertEqual(pim.dest_kind(cfg), "")
        self.assertIn("OAuth", pim.unsupported_dest_reason(cfg))

    def test_generic_dest_with_written_base_is_dav(self):
        cfg = self._cfg(prov.IMAP, PimConf(webdav_base="https://sogo.moi.vn/dav"))
        self.assertEqual(pim.dest_kind(cfg), "dav")
        self.assertEqual(
            pim.dest_calendar_url(cfg, USER),
            "https://sogo.moi.vn/dav/an@moi.vn/Calendar/")

    def test_run_user_refuses_unsupported_dest_without_http(self):
        cfg = self._cfg(prov.M365, PimConf(enabled=True))
        cfg.source = ServerConf("mail.cu.vn", 993, True, provider=prov.ICEWARP)
        with mock.patch("urllib.request.urlopen") as urlopen:
            with mock.patch("postboat.pim.read_source", return_value=([], [])):
                result = pim.run_user(cfg, USER, dry=False)
        urlopen.assert_not_called()
        self.assertIn("Graph", result.error)

    def test_source_base_follows_provider(self):
        cfg = make_cfg()
        cfg.source = ServerConf("mail.cu.vn", 993, True, provider=prov.ICEWARP)
        self.assertEqual(pim.source_dav_base(cfg), "https://mail.cu.vn/webdav")
        cfg.source = ServerConf("zimbra.cu.vn", 993, True, provider=prov.ZIMBRA)
        self.assertEqual(pim.source_dav_base(cfg), "https://zimbra.cu.vn/dav")
        self.assertEqual(
            pim.source_calendar_url(cfg, USER),
            "https://zimbra.cu.vn/dav/an@cu.com/Calendar/")


class TestConfigDefaults(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-pim-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def load(self, text):
        path = self.tmp / "config.ini"
        path.write_text(textwrap.dedent(text), encoding="utf-8")
        return load_config(path)

    def test_missing_section_means_disabled(self):
        cfg = self.load("""
            [source]
            host = imap.gmail.com
            [dest]
            host = mail.congty.vn
            """)
        self.assertFalse(cfg.pim.enabled)
        self.assertEqual(cfg.pim.webdav_base, "")

    def test_enabled_must_be_written_true(self):
        cfg = self.load("""
            [source]
            host = imap.gmail.com
            [dest]
            host = mail.congty.vn
            [pim]
            enabled = true
            webdav_base = https://mail.congty.vn/webdav
            """)
        self.assertTrue(cfg.pim.enabled)
        self.assertEqual(cfg.pim.webdav_base, "https://mail.congty.vn/webdav")
        self.assertFalse(cfg.pim.keep_attendees)

    def test_keep_attendees_is_opt_in(self):
        cfg = self.load("""
            [source]
            host = imap.gmail.com
            [dest]
            host = mail.congty.vn
            [pim]
            enabled = true
            keep_attendees = true
            """)
        self.assertTrue(cfg.pim.keep_attendees)

    def test_constructor_without_pim_stays_disabled(self):
        """Test cu goi Config(...) khong truyen pim van chay."""
        cfg = Config(
            source=ServerConf("imap.gmail.com", 993, True),
            dest=ServerConf("mail.congty.vn", 993, True),
            sync=SyncConf(),
            paths=Paths(),
            path=Path("config.ini"),
        )
        self.assertFalse(cfg.pim.enabled)


class TestCliGate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-pimcli-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fake = HERE / "fake_imapsync.py"
        imapsync = '"%s" "%s"' % (sys.executable, fake)
        (self.tmp / "config.ini").write_text(
            textwrap.dedent(CONFIG).format(imapsync=imapsync), encoding="utf-8")
        (self.tmp / "users.csv").write_text(USERS, encoding="utf-8")

    def run_cli(self, *args):
        base = ["--config", str(self.tmp / "config.ini"),
                "--users", str(self.tmp / "users.csv")]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(base + list(args))
        return code, buf.getvalue()

    def enable_pim(self):
        path = self.tmp / "config.ini"
        path.write_text(path.read_text(encoding="utf-8") + "\n[pim]\nenabled = true\n",
                        encoding="utf-8")

    def test_disabled_by_default_and_does_not_write(self):
        code, out = self.run_cli("pim")
        self.assertEqual(code, 2, out)
        self.assertIn("enabled = false", out)
        self.assertIn("sync", out)

    def test_gmail_source_is_refused_without_http(self):
        """App password IMAP khong dang nhap CalDAV Google. Khong duoc doa PUT."""
        self.enable_pim()
        with mock.patch("urllib.request.urlopen") as urlopen:
            code, out = self.run_cli("pim")
        self.assertEqual(code, 2, out)
        urlopen.assert_not_called()
        self.assertIn("gmail", out.lower())

    def test_unsupported_dest_is_refused_without_http(self):
        """Nguon doc duoc nhung dich khong ghi duoc: noi ro, khong cham mang."""
        (self.tmp / "config.ini").write_text(textwrap.dedent("""
            [source]
            provider = icewarp
            host = mail.cu.vn
            [dest]
            provider = m365
            [pim]
            enabled = true
            """), encoding="utf-8")
        with mock.patch("urllib.request.urlopen") as urlopen:
            code, out = self.run_cli("pim", "--dry")
        self.assertEqual(code, 2, out)
        urlopen.assert_not_called()
        self.assertIn("Graph", out)

    def test_sync_does_not_call_pim_even_when_pim_is_enabled(self):
        self.enable_pim()

        def fake_folders(cfg, user, timeout=60):
            return parse(GMAIL_EN)

        with mock.patch("postboat.cli.cmd_pim") as cmd_pim, \
                mock.patch("postboat.cli.list_folders", side_effect=fake_folders), \
                mock.patch("postboat.discover.server_layout") as layout:
            from postboat.discover import Layout
            layout.return_value = Layout()
            code, out = self.run_cli("sync", "--dry")
        cmd_pim.assert_not_called()
        self.assertEqual(code, 0, out)


# --------------------------------------------------------------------------- #
# ICS / vCard
# --------------------------------------------------------------------------- #

ICS_MEETING = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//src//
METHOD:REQUEST
BEGIN:VEVENT
UID:hop-tuan-1
DTSTAMP:20260101T000000Z
DTSTART:20260115T030000Z
DTEND:20260115T040000Z
SUMMARY:Hop tuan
ORGANIZER:mailto:an@cu.com
ATTENDEE;CN=Binh;PARTSTAT=ACCEPTED:mailto:binh@cu.com
END:VEVENT
END:VCALENDAR
"""

VCF_BINH = """BEGIN:VCARD
VERSION:3.0
UID:contact-binh
FN:Binh Le
EMAIL:binh@cu.com
TEL:0901234567
END:VCARD
"""


class TestIcsHelpers(unittest.TestCase):
    def test_uid_from_ics(self):
        from postboat.pim_dav import uid_from_ics
        self.assertEqual(uid_from_ics(ICS_MEETING), "hop-tuan-1")

    def test_uid_from_vcard(self):
        from postboat.pim_dav import uid_from_vcard
        self.assertEqual(uid_from_vcard(VCF_BINH), "contact-binh")

    def test_default_neutralizes_scheduling(self):
        """Zimbra 8.8 that (lab 17/09): bo qua SCHEDULE-AGENT=CLIENT, gui loi
        moi khi nguoi PUT la organizer va gui reply khi la attendee. Mac dinh
        phai bo ORGANIZER/ATTENDEE khoi VEVENT, giu X-POSTBOAT-*, ghi mo ta."""
        from postboat.pim_dav import prepare_ics
        out = prepare_ics(ICS_MEETING)
        self.assertNotIn("METHOD:", out)
        self.assertNotIn("\r\nATTENDEE", out)
        self.assertNotIn("\r\nORGANIZER", out)
        self.assertIn(
            "X-POSTBOAT-ATTENDEE;CN=Binh;PARTSTAT=ACCEPTED:mailto:binh@cu.com", out)
        self.assertIn("X-POSTBOAT-ORGANIZER:mailto:an@cu.com", out)
        self.assertIn(
            "DESCRIPTION:Nguoi to chuc: an@cu.com. Nguoi tham du (loi moi khong "
            "gui lai khi chuyen): Binh <binh@cu.com>", out)
        self.assertIn("UID:hop-tuan-1", out)

    def test_keep_attendees_marks_schedule_agent(self):
        from postboat.pim_dav import prepare_ics
        out = prepare_ics(ICS_MEETING, keep_attendees=True)
        self.assertIn("ORGANIZER;SCHEDULE-AGENT=CLIENT:mailto:an@cu.com", out)
        # Tham so co san thi chen them, khong pha tham so cu.
        self.assertIn(
            "ATTENDEE;SCHEDULE-AGENT=CLIENT;CN=Binh;PARTSTAT=ACCEPTED:mailto:binh@cu.com",
            out)
        self.assertNotIn("X-POSTBOAT", out)

    def test_existing_description_gets_the_note_appended(self):
        from postboat.pim_dav import prepare_ics
        ics = ICS_MEETING.replace("SUMMARY:Hop tuan\n",
                                  "SUMMARY:Hop tuan\nDESCRIPTION:Agenda, muc 1\n")
        out = prepare_ics(ics)
        self.assertIn("DESCRIPTION:Agenda, muc 1\\n\\nNguoi to chuc", out)
        self.assertEqual(out.count("DESCRIPTION:"), 1)

    def test_event_without_attendees_keeps_organizer(self):
        """Khong co ai de moi thi ORGANIZER vo hai, va bo di chi mat thong tin."""
        from postboat.pim_dav import prepare_ics
        ics = ("BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:x\nORGANIZER:mailto:an@cu.com\n"
               "SUMMARY:Rieng\nEND:VEVENT\nEND:VCALENDAR\n")
        out = prepare_ics(ics)
        self.assertIn("\r\nORGANIZER:mailto:an@cu.com\r\n", out)
        self.assertNotIn("X-POSTBOAT", out)
        self.assertNotIn("DESCRIPTION", out)

    def test_looks_like_rejects_html(self):
        from postboat.pim_dav import looks_like
        self.assertTrue(looks_like(ICS_MEETING, "calendar"))
        self.assertTrue(looks_like("﻿" + VCF_BINH, "contacts"))
        self.assertFalse(looks_like("<html><body>Calendar</body></html>", "calendar"))
        self.assertFalse(looks_like(VCF_BINH, "calendar"))

    def test_filename_keeps_uid_for_zimbra(self):
        from postboat.pim_dav import filename_for
        self.assertEqual(filename_for("hop-tuan-1", "ics"), "hop-tuan-1.ics")
        self.assertEqual(filename_for("a/b c", "vcf"), "a%2Fb%20c.vcf")


MULTISTATUS_ENCODED = b"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
<D:response><D:href>/webdav/an%40cu.com/Calendar/</D:href>
<D:propstat><D:prop><D:resourcetype><D:collection/><C:calendar/></D:resourcetype>
</D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat></D:response>
<D:response><D:href>/webdav/an%40cu.com/Calendar/Sub/</D:href>
<D:propstat><D:prop><D:resourcetype><D:collection/></D:resourcetype>
</D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat></D:response>
<D:response><D:href>/webdav/an%40cu.com/Calendar/hop-tuan-1.ics</D:href>
<D:propstat><D:prop><D:resourcetype/><D:getcontenttype>text/calendar</D:getcontenttype>
</D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat></D:response>
</D:multistatus>"""

MULTISTATUS_BARE = b"""<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
<d:response><d:href>http://h/webdav/an@cu.com/Calendar</d:href>
<d:propstat><d:prop><d:resourcetype/></d:prop></d:propstat></d:response>
<d:response><d:href>/webdav/an@cu.com/Calendar/x.ics</d:href>
<d:propstat><d:prop><d:resourcetype/></d:prop></d:propstat></d:response>
</d:multistatus>"""


class TestMultistatus(unittest.TestCase):
    """PROPFIND tra ve ca chinh collection (thuong voi %40 thay @) va cac
    collection con. Giu nham thi buoc GET nhan trang HTML roi PUT sang dich."""

    def test_skips_self_and_subcollections_even_when_percent_encoded(self):
        from postboat.pim_dav import _hrefs_from_multistatus
        hrefs = _hrefs_from_multistatus(
            "http://h/webdav/an@cu.com/Calendar/", MULTISTATUS_ENCODED)
        self.assertEqual(
            hrefs, ["http://h/webdav/an%40cu.com/Calendar/hop-tuan-1.ics"])

    def test_skips_self_without_trailing_slash_or_resourcetype(self):
        from postboat.pim_dav import _hrefs_from_multistatus
        hrefs = _hrefs_from_multistatus(
            "http://h/webdav/an@cu.com/Calendar/", MULTISTATUS_BARE)
        self.assertEqual(hrefs, ["http://h/webdav/an@cu.com/Calendar/x.ics"])

    def test_broken_xml_is_a_dav_error(self):
        from postboat.pim_dav import DavError, _hrefs_from_multistatus
        with self.assertRaises(DavError):
            _hrefs_from_multistatus("http://h/c/", b"<html>login</html")


class TestGraphConvert(unittest.TestCase):
    def test_event_to_ics_has_uid_and_no_method(self):
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({
            "id": "AAMk",
            "iCalUId": "04000000ABC",
            "subject": "Hop tuan",
            "type": "singleInstance",
            "isAllDay": False,
            "lastModifiedDateTime": "2026-01-10T08:00:00Z",
            "start": {"dateTime": "2026-01-15T10:00:00.0000000",
                      "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-15T11:00:00.0000000",
                    "timeZone": "UTC"},
            "location": {"displayName": "Phong A"},
            "body": {"content": "Agenda", "contentType": "text"},
            "organizer": {"emailAddress": {
                "name": "An", "address": "an@cu.com"}},
            "attendees": [{"emailAddress": {
                "name": "Binh", "address": "binh@cu.com"},
                "type": "required"}],
        })
        self.assertIn("UID:04000000ABC", ics)
        self.assertIn("DTSTAMP:20260110T080000Z", ics)
        self.assertIn("SUMMARY:Hop tuan", ics)
        self.assertIn("DTSTART:20260115T100000Z", ics)
        self.assertNotIn("METHOD:", ics)
        # Mac dinh: nguoi tham du roi khoi ATTENDEE, vao X-POSTBOAT-* va mo ta.
        self.assertNotIn("\r\nATTENDEE", ics)
        self.assertIn("X-POSTBOAT-ATTENDEE;CN=Binh:mailto:binh@cu.com", ics)
        self.assertIn("Binh <binh@cu.com>", ics)

    def test_event_to_ics_keep_attendees(self):
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({
            "id": "k", "subject": "x",
            "organizer": {"emailAddress": {"name": "An", "address": "an@cu.com"}},
            "attendees": [{"emailAddress": {"name": "Binh", "address": "binh@cu.com"}}],
        }, keep_attendees=True)
        self.assertIn("ATTENDEE;SCHEDULE-AGENT=CLIENT;CN=Binh:mailto:binh@cu.com", ics)
        self.assertNotIn("X-POSTBOAT", ics)

    def test_dtstamp_is_always_present(self):
        """RFC 5545 bat buoc DTSTAMP; server CalDAV nghiem tu choi neu thieu."""
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({"id": "x", "subject": "Khong co lastModified"})
        self.assertRegex(ics, r"DTSTAMP:\d{8}T\d{6}Z")

    def test_all_day_uses_date_value(self):
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({
            "id": "x",
            "subject": "Quoc khanh",
            "isAllDay": True,
            "start": {"dateTime": "2026-09-02T00:00:00.0000000"},
            "end": {"dateTime": "2026-09-03T00:00:00.0000000"},
        })
        self.assertIn("DTSTART;VALUE=DATE:20260902", ics)
        self.assertIn("DTEND;VALUE=DATE:20260903", ics)

    def test_contact_to_vcard(self):
        from postboat.pim_graph import contact_to_vcard
        vcf = contact_to_vcard({
            "id": "c1",
            "displayName": "Binh Le",
            "givenName": "Binh",
            "surname": "Le",
            "emailAddresses": [{"address": "binh@cu.com"}],
            "businessPhones": ["0901234567"],
            "mobilePhone": "0912345678",
            "companyName": "BizMac",
            "jobTitle": "KT",
            "businessAddress": {"street": "1 Le Loi", "city": "HCM",
                                "countryOrRegion": "VN"},
            "birthday": "1990-05-10T00:00:00Z",
        })
        self.assertIn("UID:c1", vcf)
        self.assertIn("FN:Binh Le", vcf)
        self.assertIn("N:Le;Binh;;;", vcf)
        self.assertIn("EMAIL;TYPE=INTERNET:binh@cu.com", vcf)
        self.assertIn("TEL;TYPE=WORK,VOICE:0901234567", vcf)
        self.assertIn("TEL;TYPE=CELL:0912345678", vcf)
        self.assertIn("ORG:BizMac", vcf)
        self.assertIn("ADR;TYPE=WORK:;;1 Le Loi;HCM;;;VN", vcf)
        self.assertIn("BDAY:19900510", vcf)

    def test_weekly_rrule_until_matches_dtstart_type(self):
        """RFC 5545: DTSTART co gio thi UNTIL phai co gio (UTC)."""
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({
            "id": "r1",
            "subject": "Standup",
            "start": {"dateTime": "2026-01-05T09:00:00.0000000",
                      "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-05T09:15:00.0000000",
                    "timeZone": "UTC"},
            "recurrence": {
                "pattern": {"type": "weekly", "interval": 1,
                            "daysOfWeek": ["monday", "wednesday"]},
                "range": {"type": "endDate", "endDate": "2026-06-01"},
            },
        })
        self.assertIn(
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE;UNTIL=20260601T235959Z", ics)

    def test_all_day_series_until_is_a_date(self):
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({
            "id": "r2", "subject": "Ngay le", "isAllDay": True,
            "start": {"dateTime": "2026-01-01T00:00:00.0000000"},
            "end": {"dateTime": "2026-01-02T00:00:00.0000000"},
            "recurrence": {
                "pattern": {"type": "absoluteYearly", "interval": 1,
                            "month": 1, "dayOfMonth": 1},
                "range": {"type": "endDate", "endDate": "2030-01-01"},
            },
        })
        self.assertIn("UNTIL=20300101", ics)
        self.assertNotIn("UNTIL=20300101T", ics)
        self.assertIn("BYMONTHDAY=1", ics)
        self.assertIn("BYMONTH=1", ics)

    def test_html_body_is_flattened(self):
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({
            "id": "b1", "subject": "x",
            "body": {"contentType": "html",
                     "content": "<div>Agenda<br>1. A &amp; B</div>"},
        })
        self.assertIn("DESCRIPTION:Agenda\\n1. A & B", ics)
        self.assertNotIn("<div>", ics)

    def test_exception_with_string_original_start(self):
        """originalStart cua Graph la chuoi, khong phai {dateTime, timeZone}."""
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({
            "id": "e1", "iCalUId": "SERIES", "subject": "Doi gio",
            "type": "exception",
            "originalStart": "2026-01-15T10:00:00Z",
            "start": {"dateTime": "2026-01-15T11:00:00.0000000",
                      "timeZone": "UTC"},
        })
        self.assertIn("RECURRENCE-ID:20260115T100000Z", ics)

    def test_private_free_cancelled_flags(self):
        from postboat.pim_graph import event_to_ics
        ics = event_to_ics({"id": "f", "subject": "x", "sensitivity": "private",
                            "showAs": "free", "isCancelled": True})
        self.assertIn("CLASS:PRIVATE", ics)
        self.assertIn("TRANSP:TRANSPARENT", ics)
        self.assertIn("STATUS:CANCELLED", ics)

    def test_wanted_calendars_skips_read_only(self):
        """Ngay le, sinh nhat, lich nguoi khac chia se: canEdit = false. Chep
        sang chi thanh hai bo ngay le tren cung mot hop."""
        from postboat.pim_graph import wanted_calendars
        cals = wanted_calendars([
            {"id": "1", "name": "Calendar", "isDefaultCalendar": True, "canEdit": True},
            {"id": "2", "name": "Vietnam holidays", "isDefaultCalendar": False,
             "canEdit": False},
            {"id": "3", "name": "Du an", "isDefaultCalendar": False, "canEdit": True},
            {"id": "4", "name": "Khong noi gi"},
        ])
        self.assertEqual([c["id"] for c in cals], ["1", "3", "4"])


class TestGraphRoles(unittest.TestCase):
    """Bai hoc 15/09 voi IMAP: Microsoft cap token ke ca khi chua admin consent.
    Ong PIM phai kiem roles truoc khi goi Graph, va noi ten quyen con thieu."""

    def test_missing_roles_names_what_consent_lacks(self):
        from postboat import pim_graph
        self.assertEqual(
            pim_graph.missing_roles(fake_jwt({"roles": ["Calendars.Read"]})),
            ["Contacts.Read"])
        self.assertEqual(
            pim_graph.missing_roles(fake_jwt(
                {"roles": ["Calendars.ReadWrite", "Contacts.ReadWrite"]})),
            [])
        self.assertEqual(
            pim_graph.missing_roles(fake_jwt({"aud": "graph"})),
            ["Calendars.Read", "Contacts.Read"])
        # Khong doc duoc thi khong doan: de Graph tu tra loi.
        self.assertEqual(pim_graph.missing_roles("khong-phai-jwt"), [])

    def _m365_cfg(self, tenant):
        cfg = make_cfg()
        cfg.source = ServerConf(
            "outlook.office365.com", 993, True, provider=prov.M365,
            auth="oauth2",
            oauth=OAuthConf(tenant=tenant, client_id="cid", client_secret="s"))
        return cfg

    def test_graph_token_refuses_token_without_consent(self):
        from postboat import pim_graph
        cfg = self._m365_cfg("pim-test-thieu-consent")
        token = fake_jwt({"roles": ["IMAP.AccessAsApp"]})
        with mock.patch("postboat.oauth.request_token", return_value=(token, 3600)):
            with self.assertRaises(OAuthError) as ctx:
                pim_graph.graph_token(cfg)
        msg = str(ctx.exception)
        self.assertIn("Calendars.Read", msg)
        self.assertIn("Contacts.Read", msg)
        self.assertIn("admin consent", msg)

    def test_graph_token_uses_graph_scope_not_imap_scope(self):
        from postboat import pim_graph
        cfg = self._m365_cfg("pim-test-du-quyen")
        token = fake_jwt({"roles": ["Calendars.Read", "Contacts.Read"]})
        seen = []

        def fetch(conf, timeout=30):
            seen.append(conf.scope)
            return token, 3600

        with mock.patch("postboat.oauth.request_token", side_effect=fetch):
            self.assertEqual(pim_graph.graph_token(cfg), token)
        self.assertEqual(seen, [pim_graph.GRAPH_SCOPE])


class TestSourceKind(unittest.TestCase):
    def test_icewarp_and_zimbra_are_dav(self):
        cfg = make_cfg()
        cfg.source.provider = prov.ICEWARP
        self.assertEqual(pim.source_kind(cfg), "dav")
        cfg.source.provider = prov.ZIMBRA
        self.assertEqual(pim.source_kind(cfg), "dav")

    def test_m365_is_graph(self):
        cfg = make_cfg()
        cfg.source.provider = prov.M365
        self.assertEqual(pim.source_kind(cfg), "graph")
        self.assertIn("Graph", pim.source_label(cfg))

    def test_gmail_is_unsupported(self):
        cfg = make_cfg()
        cfg.source.provider = prov.GMAIL
        self.assertEqual(pim.source_kind(cfg), "")
        self.assertIn("gmail", pim.unsupported_reason(cfg).lower())

    def test_manual_dav_sources_need_a_written_base(self):
        cfg = make_cfg()
        cfg.source.provider = prov.YAHOO
        self.assertEqual(pim.source_kind(cfg), "")
        self.assertIn("source_webdav_base", pim.unsupported_reason(cfg))
        cfg = make_cfg(PimConf(source_webdav_base="https://caldav.calendar.yahoo.com"))
        cfg.source.provider = prov.YAHOO
        self.assertEqual(pim.source_kind(cfg), "dav")

    def test_dav_source_without_password_is_an_error_not_a_crash(self):
        cfg = make_cfg(PimConf(enabled=True))
        cfg.source = ServerConf("mail.cu.vn", 993, True, provider=prov.ICEWARP)
        user = User("an@cu.com", "", "an@moi.vn", "x", row=2)
        result = pim.run_user(cfg, user, dry=True)
        self.assertIn("src_password", result.error)
        self.assertTrue(result.failed)


# --------------------------------------------------------------------------- #
# CalDAV that (server gia trong tien trinh)
# --------------------------------------------------------------------------- #

class FakeDavHandler(http.server.BaseHTTPRequestHandler):
    """CalDAV/CardDAV toi gian: PROPFIND + GET + PUT, Basic auth."""

    store = None   # type: dict
    puts = None    # type: list
    user = "an@cu.com"
    password = "srcpass"
    # Zimbra 8.8 that: PUT de len su kien da co van tra 2xx du co
    # If-None-Match: *. Tat co nay de gia lap.
    honor_if_none_match = True

    def log_message(self, fmt, *args):
        return

    def _auth_ok(self):
        header = self.headers.get("Authorization") or ""
        if not header.startswith("Basic "):
            return False
        raw = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        user, _, password = raw.partition(":")
        return password == self.password and (
            user == self.user or "@" in user)

    def _path(self):
        from urllib.parse import unquote
        return unquote(self.path.split("?", 1)[0])

    def _read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _send(self, code, body=b"", content_type="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def do_PROPFIND(self):
        # Doc het body truoc khi tra loi, ke ca 401: khong thi Windows dong
        # socket giua chung va client thay "connection aborted" thay vi 401.
        self._read_body()
        if not self._auth_ok():
            self._send(401, b"auth")
            return
        path = self._path()
        if not path.endswith("/"):
            path += "/"
        items = []
        for href, (_ctype, _data) in sorted(self.store.items()):
            if href.startswith(path) and href != path:
                rest = href[len(path):]
                if "/" not in rest.rstrip("/"):
                    items.append(href)
        chunks = ['<?xml version="1.0" encoding="utf-8"?>',
                  '<d:multistatus xmlns:d="DAV:">',
                  # Chinh collection, voi @ ma hoa -- nhu IceWarp that lam.
                  "<d:response><d:href>%s</d:href><d:propstat><d:prop>"
                  "<d:resourcetype><d:collection/></d:resourcetype></d:prop>"
                  "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
                  % path.replace("@", "%40")]
        for href in items:
            chunks.append("<d:response><d:href>%s</d:href>"
                          "<d:propstat><d:prop><d:resourcetype/></d:prop>"
                          "<d:status>HTTP/1.1 200 OK</d:status>"
                          "</d:propstat></d:response>" % href)
        chunks.append("</d:multistatus>")
        xml = "".join(chunks).encode("utf-8")
        self._send(207, xml, "application/xml; charset=utf-8")

    def do_GET(self):
        if not self._auth_ok():
            self._send(401, b"auth")
            return
        path = self._path()
        item = self.store.get(path)
        if item is None:
            self._send(404, b"missing")
            return
        self._send(200, item[1], item[0])

    def do_PUT(self):
        body = self._read_body()
        if not self._auth_ok():
            self._send(401, b"auth")
            return
        path = self._path()
        match = self.headers.get("If-None-Match")
        if match == "*" and path in self.store and self.honor_if_none_match:
            self._send(412, b"exists")
            return
        ctype = self.headers.get("Content-Type") or "application/octet-stream"
        self.store[path] = (ctype.split(";")[0].strip(), body)
        self.puts.append(path)
        self._send(201, b"created")


def start_fake_dav(store, user="an@cu.com", password="srcpass"):
    FakeDavHandler.store = store
    FakeDavHandler.puts = []
    FakeDavHandler.user = user
    FakeDavHandler.password = password
    FakeDavHandler.honor_if_none_match = True
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeDavHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()
    return httpd, thread


def sample_store():
    return {
        "/webdav/an@cu.com/Calendar/hop-tuan-1.ics":
            ("text/calendar", ICS_MEETING.encode("utf-8")),
        # Trang HTML nam chung collection: server that co the tra ve; khong
        # duoc bien no thanh mot .ics ben dich.
        "/webdav/an@cu.com/Calendar/index.html":
            ("text/html", b"<html><body>Calendar</body></html>"),
        "/webdav/an@cu.com/Contacts/contact-binh.vcf":
            ("text/vcard", VCF_BINH.encode("utf-8")),
    }


class TestDavCopy(unittest.TestCase):
    def setUp(self):
        self.store = sample_store()
        self.httpd, _thread = start_fake_dav(self.store)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        port = self.httpd.server_address[1]
        base = "http://127.0.0.1:%d/webdav" % port
        self.cfg = make_cfg(PimConf(
            enabled=True,
            webdav_base=base,
            source_webdav_base=base,
        ), dest_host="127.0.0.1")
        self.cfg.source = ServerConf(
            "127.0.0.1", 993, True, provider=prov.ICEWARP)
        self.cfg.dest = ServerConf(
            "127.0.0.1", 993, True, provider=prov.ICEWARP)
        self.src = User("an@cu.com", "srcpass", "an@moi.vn", "srcpass", row=2)

    def test_dry_reads_but_does_not_put(self):
        result = pim.run_user(self.cfg, self.src, dry=True)
        self.assertEqual(result.error, "")
        self.assertEqual(result.calendar_ok, 1)
        self.assertEqual(result.contacts_ok, 1)
        self.assertEqual(FakeDavHandler.puts, [])
        dest_cal = "/webdav/an@moi.vn/Calendar/hop-tuan-1.ics"
        self.assertNotIn(dest_cal, self.store)

    def test_put_copies_calendar_and_contacts(self):
        result = pim.run_user(self.cfg, self.src, dry=False)
        self.assertEqual(result.error, "")
        self.assertEqual(result.calendar_ok, 1)
        self.assertEqual(result.contacts_ok, 1)
        dest_cal = "/webdav/an@moi.vn/Calendar/hop-tuan-1.ics"
        dest_vcf = "/webdav/an@moi.vn/Contacts/contact-binh.vcf"
        self.assertIn(dest_cal, self.store)
        self.assertIn(dest_vcf, self.store)
        body = self.store[dest_cal][1].decode("utf-8")
        self.assertNotIn("METHOD:", body)
        self.assertNotIn("\r\nATTENDEE", body)
        self.assertIn("X-POSTBOAT-ATTENDEE", body)
        self.assertEqual(result.calendar_neutralized, 1)

    def test_keep_attendees_from_config_reaches_the_put(self):
        self.cfg.pim.keep_attendees = True
        result = pim.run_user(self.cfg, self.src, dry=False)
        body = self.store["/webdav/an@moi.vn/Calendar/hop-tuan-1.ics"][1].decode("utf-8")
        self.assertIn("SCHEDULE-AGENT=CLIENT", body)
        self.assertEqual(result.calendar_neutralized, 0)

    def test_html_and_the_collection_itself_are_not_copied(self):
        pim.run_user(self.cfg, self.src, dry=False)
        for path in FakeDavHandler.puts:
            self.assertNotIn("index", path)
            self.assertNotIn("Calendar.ics", path)
            self.assertNotIn("cal-", path)   # khong co fallback uid tu HTML

    def test_second_put_skips_existing_uid(self):
        pim.run_user(self.cfg, self.src, dry=False)
        FakeDavHandler.puts = []
        result = pim.run_user(self.cfg, self.src, dry=False)
        self.assertEqual(result.calendar_skip, 1)
        self.assertEqual(result.contacts_skip, 1)
        self.assertEqual(result.calendar_ok, 0)
        self.assertEqual(FakeDavHandler.puts, [])

    def test_second_run_skips_even_when_server_ignores_if_none_match(self):
        """Zimbra 8.8 that (lab, 17/09): PUT de van 2xx. Van phai dem 'da co'
        va khong PUT lai -- hoi PROPFIND truoc, khong tin ma PUT."""
        pim.run_user(self.cfg, self.src, dry=False)
        FakeDavHandler.honor_if_none_match = False
        FakeDavHandler.puts = []
        result = pim.run_user(self.cfg, self.src, dry=False)
        self.assertEqual(result.calendar_skip, 1)
        self.assertEqual(result.contacts_skip, 1)
        self.assertEqual(result.calendar_ok, 0)
        self.assertEqual(FakeDavHandler.puts, [])

    def test_wrong_password_is_an_error_with_a_hint(self):
        bad = User("an@cu.com", "sai", "an@moi.vn", "srcpass", row=2)
        result = pim.run_user(self.cfg, bad, dry=True)
        self.assertIn("401", result.error)
        self.assertIn("mat khau", result.error)
        self.assertTrue(result.failed)


class TestState(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-pimstate-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_save_merges_by_user_and_load_reads_back(self):
        a = pim.PimResult("an@cu.com", "an@moi.vn", calendar_ok=3, contacts_ok=5)
        b = pim.PimResult("binh@cu.com", "binh@moi.vn", error="HTTP 401")
        pim.save_results(self.tmp, [a, b])
        a2 = pim.PimResult("an@cu.com", "an@moi.vn", calendar_skip=3, contacts_skip=5)
        pim.save_results(self.tmp, [a2])
        data = pim.load_results(self.tmp)
        self.assertEqual(sorted(data), ["an@cu.com", "binh@cu.com"])
        self.assertEqual(data["an@cu.com"]["calendar_skip"], 3)
        self.assertEqual(data["an@cu.com"]["calendar_ok"], 0)
        self.assertEqual(data["binh@cu.com"]["error"], "HTTP 401")
        self.assertIn("at", data["an@cu.com"])

    def test_missing_or_broken_file_is_empty(self):
        self.assertEqual(pim.load_results(self.tmp), {})
        pim.state_path(self.tmp).write_text("{hong", encoding="utf-8")
        self.assertEqual(pim.load_results(self.tmp), {})

    def test_totals(self):
        t = pim.totals([
            pim.PimResult("a", calendar_ok=2, contacts_err=1),
            pim.PimResult("b", error="x"),
        ])
        self.assertEqual(t["users"], 2)
        self.assertEqual(t["errors"], 1)
        self.assertEqual(t["calendar_ok"], 2)
        self.assertEqual(t["contacts_err"], 1)


class TestCliDavCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-pimdav-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.store = sample_store()
        self.httpd, _thread = start_fake_dav(self.store)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        port = self.httpd.server_address[1]
        self.base = "http://127.0.0.1:%d/webdav" % port
        fake = HERE / "fake_imapsync.py"
        imapsync = '"%s" "%s"' % (sys.executable, fake)
        (self.tmp / "config.ini").write_text(textwrap.dedent("""
            [source]
            provider = icewarp
            host = 127.0.0.1
            [dest]
            provider = icewarp
            host = 127.0.0.1
            [pim]
            enabled = true
            webdav_base = {base}
            source_webdav_base = {base}
            [paths]
            imapsync = {imapsync}
            logdir = logs
            statedir = state
            """).format(base=self.base, imapsync=imapsync), encoding="utf-8")
        (self.tmp / "users.csv").write_text(
            "src_user,src_password,dst_user,dst_password\n"
            "an@cu.com,srcpass,an@moi.vn,srcpass\n",
            encoding="utf-8")

    def run_cli(self, *args):
        base = ["--config", str(self.tmp / "config.ini"),
                "--users", str(self.tmp / "users.csv")]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(base + list(args))
        return code, buf.getvalue()

    def test_dry_does_not_put_and_saves_nothing(self):
        code, out = self.run_cli("pim", "--dry")
        self.assertEqual(code, 0, out)
        self.assertEqual(FakeDavHandler.puts, [])
        self.assertIn("hop-tuan-1", out)
        self.assertIn("se ghi", out)
        self.assertFalse(pim.state_path(self.tmp / "state").exists())

    def test_pim_puts_without_calling_imapsync_and_saves_state(self):
        code, out = self.run_cli("pim")
        self.assertEqual(code, 0, out)
        self.assertIn("/webdav/an@moi.vn/Calendar/hop-tuan-1.ics",
                      FakeDavHandler.puts)
        self.assertNotIn("imapsync", out.lower())
        self.assertIn("Tong 1 mailbox", out)
        data = pim.load_results(self.tmp / "state")
        self.assertEqual(data["an@cu.com"]["dst_user"], "an@moi.vn")
        self.assertEqual(data["an@cu.com"]["calendar_ok"], 1)
        self.assertEqual(data["an@cu.com"]["contacts_ok"], 1)

    def test_failed_mailbox_gives_exit_1(self):
        (self.tmp / "users.csv").write_text(
            "src_user,src_password,dst_user,dst_password\n"
            "an@cu.com,sai,an@moi.vn,srcpass\n",
            encoding="utf-8")
        code, out = self.run_cli("pim")
        self.assertEqual(code, 1, out)
        self.assertIn("LOI", out)
        self.assertIn("401", out)


if __name__ == "__main__":
    unittest.main()
