# -*- coding: utf-8 -*-
"""Nhom phan phoi: doc file xuat cua nguon, doi dia chi, sinh bo lenh cho dich.

Cai khoa o day: dinh dang nao cung ra cung mot lists.csv; dia chi ngoai domain
khong bi doi; bo lenh IceWarp dung u_type va tro dung file thanh vien; dich
khong phai IceWarp thi van co lists.csv chu khong im lang.
"""

import io
import shutil
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from postboat import cli, handover, lists
from postboat.users import User

M365_PAIRS = """#TYPE System.Management.Automation.PSCustomObject
"List","ListName","Member","MemberType"
"sales@cu.com","Phong Kinh Doanh","an@cu.com","UserMailbox"
"sales@cu.com","Phong Kinh Doanh","binh@cu.com","UserMailbox"
"sales@cu.com","Phong Kinh Doanh","doitac@gmail.com","MailContact"
"all@cu.com","Toan cong ty","sales@cu.com","MailUniversalDistributionGroup"
"all@cu.com","Toan cong ty","an@cu.com","UserMailbox"
"""

M365_GROUPS_ONLY = """"PrimarySmtpAddress","DisplayName","ManagedBy"
"sales@cu.com","Phong Kinh Doanh","cu.onmicrosoft.com/Users/An"
"trong@cu.com","Nhom trong","cu.onmicrosoft.com/Users/An"
"""

GAM_MEMBERS = """group,type,role,email,status
sales@cu.com,USER,OWNER,an@cu.com,ACTIVE
sales@cu.com,USER,MEMBER,binh@cu.com,ACTIVE
sales@cu.com,CUSTOMER,MEMBER,,ACTIVE
"""

GAM_GROUPS = """email,name,description,directMembersCount
sales@cu.com,Kinh doanh,Ban hang,2
trong@cu.com,Nhom trong,,0
"""

GOOGLE_EXPORT = """Email address,Nickname,Group status,Email status,Email preference,Posting permissions
an@cu.com,,Owner,,All email,Allowed
chi@cu.com,,Member,,All email,Allowed
"""

USERS = [
    User("an@cu.com", "", "an@moi.vn", "", row=2),
    User("binh@cu.com", "", "binh.le@moi.vn", "", row=3),   # doi ca local part
    User("chi@cu.com", "", "chi@moi.vn", "", row=4),
]


class TestParse(unittest.TestCase):
    def test_m365_pairs_with_type_line(self):
        p = lists.parse(M365_PAIRS)
        self.assertEqual(p.fmt, "cap nhom-thanh vien")
        self.assertEqual(sorted(p.lists), ["all@cu.com", "sales@cu.com"])
        sales = p.lists["sales@cu.com"]
        self.assertEqual(sales.name, "Phong Kinh Doanh")
        self.assertEqual(sales.members, ["an@cu.com", "binh@cu.com", "doitac@gmail.com"])
        # Nhom long nhau: nhom la thanh vien cua nhom, giu nguyen.
        self.assertIn("sales@cu.com", p.lists["all@cu.com"].members)
        self.assertEqual(p.rows_read, 5)

    def test_m365_groups_only_adds_empty_lists(self):
        p = lists.parse(M365_GROUPS_ONLY)
        self.assertEqual(p.fmt, "chi danh sach nhom")
        self.assertEqual(p.lists["trong@cu.com"].members, [])
        self.assertEqual(p.lists["trong@cu.com"].name, "Nhom trong")
        # ManagedBy cua PowerShell la ten canonical, khong phai email: khong doan.
        self.assertEqual(p.lists["sales@cu.com"].owner, "")

    def test_gam_members_owner_and_customer_row(self):
        p = lists.parse(GAM_MEMBERS)
        sales = p.lists["sales@cu.com"]
        self.assertEqual(sales.members, ["an@cu.com", "binh@cu.com"])
        self.assertEqual(sales.owner, "an@cu.com")
        self.assertEqual(len(p.warnings), 1)
        self.assertIn("CUSTOMER", p.warnings[0])

    def test_gam_groups_then_members_merge(self):
        p = lists.merge(lists.parse(GAM_GROUPS), lists.parse(GAM_MEMBERS))
        self.assertEqual(sorted(p.lists), ["sales@cu.com", "trong@cu.com"])
        self.assertEqual(p.lists["sales@cu.com"].name, "Kinh doanh")
        self.assertEqual(len(p.lists["sales@cu.com"].members), 2)

    def test_google_export_needs_list_flag(self):
        with self.assertRaises(lists.ListsError) as ctx:
            lists.parse(GOOGLE_EXPORT)
        self.assertIn("--list", str(ctx.exception))
        p = lists.parse(GOOGLE_EXPORT, members_of="sales@cu.com")
        self.assertEqual(p.lists["sales@cu.com"].members, ["an@cu.com", "chi@cu.com"])

    def test_neutral_csv_round_trip(self):
        p = lists.parse("list,name,member\nsales@cu.com,Sales,an@cu.com\n")
        self.assertEqual(p.lists["sales@cu.com"].members, ["an@cu.com"])
        self.assertEqual(p.lists["sales@cu.com"].name, "Sales")

    def test_bare_two_columns_without_header(self):
        p = lists.parse("sales@cu.com,an@cu.com\nsales@cu.com,binh@cu.com\n")
        self.assertEqual(p.lists["sales@cu.com"].members, ["an@cu.com", "binh@cu.com"])

    def test_bare_one_column_is_lists_only(self):
        p = lists.parse("sales@cu.com\nhr@cu.com\n")
        self.assertEqual(sorted(p.lists), ["hr@cu.com", "sales@cu.com"])

    def test_utf16_and_semicolon_via_decode(self):
        raw = ("List;Member\r\nsales@cu.com;an@cu.com\r\n").encode("utf-16")
        p = lists.parse(lists.decode(raw))
        self.assertEqual(p.lists["sales@cu.com"].members, ["an@cu.com"])

    def test_garbage_is_an_error_not_a_crash(self):
        with self.assertRaises(lists.ListsError):
            lists.parse("khong,co,gi\nca,het,day\n")
        with self.assertRaises(lists.ListsError):
            lists.parse("\n\n")


class TestMapping(unittest.TestCase):
    def test_users_win_then_domain_then_external_untouched(self):
        p = lists.parse(M365_PAIRS)
        m = lists.mapping_from(USERS, p.lists.values())
        self.assertEqual(m.domains, {"cu.com": "moi.vn"})
        out = {l.address: l for l in lists.translate_all(p, m)}
        self.assertEqual(sorted(out), ["all@moi.vn", "sales@moi.vn"])
        sales = out["sales@moi.vn"]
        self.assertEqual(sales.members, ["an@moi.vn", "binh.le@moi.vn", "doitac@gmail.com"])
        self.assertEqual(sales.external, 1)
        self.assertIn("sales@moi.vn", out["all@moi.vn"].members)

    def test_dst_domain_only_rewrites_source_domains(self):
        p = lists.parse(M365_PAIRS)
        m = lists.mapping_from([], p.lists.values(), dst_domain="@moi.vn")
        out = {l.address: l for l in lists.translate_all(p, m)}
        self.assertEqual(out["sales@moi.vn"].members,
                         ["an@moi.vn", "binh@moi.vn", "doitac@gmail.com"])

    def test_no_users_no_domain_keeps_everything(self):
        p = lists.parse(M365_PAIRS)
        m = lists.mapping_from([], p.lists.values())
        out = {l.address: l for l in lists.translate_all(p, m)}
        self.assertIn("sales@cu.com", out)
        self.assertEqual(out["sales@cu.com"].external, 1)

    def test_conflicting_domain_map_is_not_guessed(self):
        users = [User("a@cu.com", "", "a@x.vn", "", 2), User("b@cu.com", "", "b@y.vn", "", 3)]
        m = lists.mapping_from(users, [])
        self.assertEqual(m.domains, {})
        self.assertEqual(m.translate("a@cu.com"), "a@x.vn")
        self.assertEqual(m.translate("c@cu.com"), "c@cu.com")


class TestWriters(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-lists-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = lists.parse(M365_PAIRS)
        m = lists.mapping_from(USERS, p.lists.values())
        self.dest = lists.translate_all(p, m)
        self.dest.append(lists.MailList("trong@moi.vn", name='Nhom "trong"'))

    def test_csv_has_one_row_per_member_and_empty_list_kept(self):
        path = lists.write_csv(self.tmp / "lists.csv", self.dest)
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("list,name,member\n"))
        self.assertIn("sales@moi.vn,Phong Kinh Doanh,doitac@gmail.com\n", text)
        self.assertIn('trong@moi.vn,"Nhom ""trong""",\n', text)
        back = lists.parse(text)
        self.assertEqual(sorted(back.lists), ["all@moi.vn", "sales@moi.vn", "trong@moi.vn"])
        self.assertEqual(back.lists["trong@moi.vn"].members, [])

    def test_icewarp_group_batch_and_member_files(self):
        batch, files = lists.write_icewarp(
            self.tmp, self.dest, listdir="/opt/icewarp/postboat-lists", kind="group")
        lines = batch.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn(
            'create account sales@moi.vn u_type 7 u_name "Phong Kinh Doanh" '
            'g_listfile "/opt/icewarp/postboat-lists/members/sales@moi.vn.txt"',
            lines)
        # Ngoac kep trong ten khong duoc pha dong lenh.
        self.assertIn("u_name \"Nhom 'trong'\"", "\n".join(lines))
        members = (self.tmp / "members" / "sales@moi.vn.txt").read_text(encoding="utf-8")
        self.assertEqual(members, "an@moi.vn\nbinh.le@moi.vn\ndoitac@gmail.com\n")
        self.assertEqual((self.tmp / "members" / "trong@moi.vn.txt").read_text(), "")
        self.assertEqual(len(files), 3)
        self.assertIn("tool file batch", (self.tmp / "README.txt").read_text(encoding="utf-8"))

    def test_icewarp_mailinglist_needs_owner(self):
        lines = lists.icewarp_lines(self.dest, "C:\\IceWarp\\lists", kind="mailinglist",
                                    default_owner="admin@moi.vn")
        self.assertIn(
            'create account sales@moi.vn u_type 1 u_name "Phong Kinh Doanh" '
            'm_owneraddress "admin@moi.vn" m_sendalllists 0 '
            'm_listfile "C:\\IceWarp\\lists/members/sales@moi.vn.txt"',
            lines)
        # Khong co --owner thi postmaster cua domain nhom, khong de trong.
        lines = lists.icewarp_lines(self.dest, "/x", kind="mailinglist")
        self.assertIn('m_owneraddress "postmaster@moi.vn"', lines[0])

    def test_state_round_trip(self):
        path = lists.save_state(self.tmp, self.dest, "icewarp", self.tmp)
        data = lists.load_state(self.tmp)
        self.assertEqual(data["dest"], "icewarp")
        self.assertEqual(data["lists"]["sales@moi.vn"]["members"], 3)
        self.assertEqual(data["lists"]["sales@moi.vn"]["external"], 1)
        self.assertEqual(data["lists"]["trong@moi.vn"]["members"], 0)
        path.write_text("{hong", encoding="utf-8")
        self.assertEqual(lists.load_state(self.tmp), {})


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-listscli-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "users.csv").write_text(
            "src_user,src_password,dst_user,dst_password\n"
            "an@cu.com,,an@moi.vn,\n"
            "binh@cu.com,,binh@moi.vn,\n",
            encoding="utf-8")
        (self.tmp / "export.csv").write_text(M365_PAIRS, encoding="utf-8")

    def config(self, dest_provider):
        (self.tmp / "config.ini").write_text(textwrap.dedent("""
            [source]
            provider = m365
            auth = password
            [dest]
            provider = %s
            host = mail.moi.vn
            [paths]
            logdir = logs
            statedir = state
            """ % dest_provider), encoding="utf-8")

    def run_cli(self, *args):
        base = ["--config", str(self.tmp / "config.ini"),
                "--users", str(self.tmp / "users.csv")]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(base + list(args))
        return code, buf.getvalue()

    def test_icewarp_dest_writes_batch_and_state(self):
        self.config("icewarp")
        out = self.tmp / "lists"
        code, text = self.run_cli("lists", str(self.tmp / "export.csv"), "--out", str(out))
        self.assertEqual(code, 0, text)
        self.assertTrue((out / "lists.csv").exists())
        self.assertTrue((out / "icewarp.batch").exists())
        self.assertTrue((out / "members" / "sales@moi.vn.txt").exists())
        self.assertIn("cu.com -> moi.vn", text)
        self.assertIn("tool file batch", text)
        self.assertIn("1 ngoai domain", text)
        state = lists.load_state(self.tmp / "state")
        self.assertEqual(sorted(state["lists"]), ["all@moi.vn", "sales@moi.vn"])

    def test_other_dest_gets_csv_and_a_plain_sentence(self):
        self.config("zimbra")
        out = self.tmp / "lists"
        code, text = self.run_cli("lists", str(self.tmp / "export.csv"), "--out", str(out))
        self.assertEqual(code, 0, text)
        self.assertTrue((out / "lists.csv").exists())
        self.assertFalse((out / "icewarp.batch").exists())
        self.assertIn("chua co bo lenh", text)
        self.assertIn("Zimbra", text)

    def test_refuses_to_overwrite_without_force(self):
        self.config("icewarp")
        out = self.tmp / "lists"
        out.mkdir()
        (out / "lists.csv").write_text("x", encoding="utf-8")
        code, text = self.run_cli("lists", str(self.tmp / "export.csv"), "--out", str(out))
        self.assertEqual(code, 2, text)
        self.assertIn("--force", text)

    def test_google_export_with_list_flag(self):
        self.config("icewarp")
        (self.tmp / "members.csv").write_text(GOOGLE_EXPORT, encoding="utf-8")
        out = self.tmp / "lists"
        code, text = self.run_cli("lists", str(self.tmp / "members.csv"),
                                  "--list", "sales@cu.com", "--out", str(out))
        self.assertEqual(code, 0, text)
        self.assertIn("sales@moi.vn", (out / "lists.csv").read_text(encoding="utf-8"))

    def test_missing_users_csv_is_a_warning_not_a_stop(self):
        self.config("icewarp")
        (self.tmp / "users.csv").unlink()
        out = self.tmp / "lists"
        code, text = self.run_cli("lists", str(self.tmp / "export.csv"),
                                  "--out", str(out), "--dst-domain", "moi.vn")
        self.assertEqual(code, 0, text)
        self.assertIn("sales@moi.vn", (out / "lists.csv").read_text(encoding="utf-8"))


class TestHandover(unittest.TestCase):
    STATE = {"at": "2026-09-17 10:00", "dest": "icewarp", "out": "lists",
             "lists": {"sales@moi.vn": {"name": "Kinh doanh", "members": 12, "external": 2},
                       "all@moi.vn": {"name": "", "members": 40, "external": 0}}}

    def row(self):
        return {"src_user": "an@cu.com", "dst_user": "an@moi.vn", "ket_qua": "OK",
                "mail_chuyen": 10, "bytes": 1024, "folder": "3/3"}

    def test_section_and_out_of_scope_wording(self):
        doc = handover.build_html([self.row()], lists_state=self.STATE)
        self.assertIn("Nhóm phân phối", doc)
        self.assertIn("sales@moi.vn", doc)
        self.assertIn("Kinh doanh", doc)
        self.assertNotIn("Quyền chia sẻ hộp thư và nhóm phân phối", doc)
        self.assertIn("kiểm duyệt", doc)
        self.assertIn("2 nhóm phân phối", doc)

    def test_absent_state_keeps_old_wording(self):
        doc = handover.build_html([self.row()])
        self.assertNotIn("<h2>Nhóm phân phối</h2>", doc)
        self.assertIn("Quyền chia sẻ hộp thư và nhóm phân phối", doc)


if __name__ == "__main__":
    unittest.main()
