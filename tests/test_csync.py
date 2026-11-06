"""End-to-end tests for csync. They run the script against a fake Claude data folder,
never against the real app (CSYNC_APP_DIR / CSYNC_HOME / CSYNC_NO_APP are set)."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

CSYNC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "csync")
UUIDS = {
    "A": "aaaaaaaa-0000-0000-0000-000000000001",
    "B": "bbbbbbbb-0000-0000-0000-000000000002",
}


def load(path):
    with open(path) as f:
        return json.load(f)


def dump(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


class CsyncTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.app = os.path.join(self._tmp.name, "app")
        self.home = os.path.join(self._tmp.name, "home")
        os.makedirs(self.app)
        self.env = dict(os.environ, CSYNC_APP_DIR=self.app, CSYNC_HOME=self.home, CSYNC_NO_APP="1")

    # -- helpers --

    def run_csync(self, *args, ok=True):
        p = subprocess.run([sys.executable, "-I", CSYNC, *args], env=self.env, capture_output=True, text=True)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return p

    def sign_in(self, who, activity=100):
        """Pretend the app is signed in as account `who` (A or B)."""
        cfg_path = os.path.join(self.app, "config.json")
        cfg = load(cfg_path) if os.path.exists(cfg_path) else {"theme": "dark"}
        cfg.update({
            "oauth:tokenCache": "token-" + who,
            "oauth:tokenCacheV2": "token2-" + who,
            "lastKnownAccountUuid": UUIDS[who],
        })
        dump(cfg, cfg_path)
        ck = os.path.join(self.app, "Cookies")
        if os.path.exists(ck):
            os.remove(ck)
        con = sqlite3.connect(ck)
        con.execute("create table cookies(host_key, name, encrypted_value)")
        con.execute("insert into cookies values('.claude.ai', 'sessionKey', ?)", ("session-" + who,))
        con.execute("insert into cookies values('example.com', 'other', 'x')")
        con.commit()
        con.close()
        d = os.path.join(self.app, "claude-code-sessions", UUIDS[who], "org-" + who)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"local_chat{who}.json"), "w") as f:
            json.dump({"lastActivityAt": activity}, f)

    def config(self):
        return load(os.path.join(self.app, "config.json"))

    def session_cookie(self):
        con = sqlite3.connect(os.path.join(self.app, "Cookies"))
        try:
            row = con.execute("select encrypted_value from cookies where name='sessionKey'").fetchone()
        finally:
            con.close()
        return row[0] if row else None

    def two_accounts(self):
        self.sign_in("A")
        self.run_csync("add", "main")
        self.sign_in("B", activity=200)
        self.run_csync("add", "work")

    def chats(self, who):
        d = os.path.join(self.app, "claude-code-sessions", UUIDS[who], "org-" + who)
        return sorted(os.listdir(d))

    # -- tests --

    def test_version_and_help(self):
        self.assertIn("csync", self.run_csync("--version").stdout)
        self.assertIn("Usage", self.run_csync("--help").stdout)

    def test_unknown_command_fails(self):
        p = self.run_csync("bogus", ok=False)
        self.assertNotEqual(p.returncode, 0)

    def test_add_requires_login(self):
        p = self.run_csync("add", ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("signed in", p.stderr)

    def test_add_and_list(self):
        self.two_accounts()
        out = self.run_csync("list").stdout
        self.assertIn("[1] main", out)
        self.assertIn("[2] work", out)
        self.assertIn("* [2] work", out)  # B is the signed-in one
        self.assertIn("[2] work", self.run_csync("status").stdout)

    def test_snapshot_files_are_private(self):
        self.two_accounts()
        for path in (os.path.join(self.home, "accounts.json"),
                     os.path.join(self.home, "snapshots", UUIDS["A"], "Cookies"),
                     os.path.join(self.home, "snapshots", UUIDS["A"], "auth.json")):
            self.assertEqual(os.stat(path).st_mode & 0o077, 0, path)

    def test_switch_restores_session_and_keeps_other_settings(self):
        self.two_accounts()
        self.run_csync("switch", "main")
        cfg = self.config()
        self.assertEqual(cfg["lastKnownAccountUuid"], UUIDS["A"])
        self.assertEqual(cfg["oauth:tokenCache"], "token-A")
        self.assertEqual(cfg["theme"], "dark")  # unrelated settings survive
        self.assertEqual(self.session_cookie(), "session-A")

    def test_switch_without_argument_rotates(self):
        self.two_accounts()
        self.run_csync("switch")  # currently 2 -> wraps to 1
        self.assertEqual(self.config()["lastKnownAccountUuid"], UUIDS["A"])
        self.run_csync("switch")
        self.assertEqual(self.config()["lastKnownAccountUuid"], UUIDS["B"])

    def test_switch_saves_refreshed_tokens(self):
        self.two_accounts()
        cfg = self.config()
        cfg["oauth:tokenCache"] = "refreshed-B"
        dump(cfg, os.path.join(self.app, "config.json"))
        self.run_csync("switch", "main")
        self.run_csync("switch", "work")
        self.assertEqual(self.config()["oauth:tokenCache"], "refreshed-B")

    def test_switch_syncs_chats(self):
        self.two_accounts()
        self.run_csync("switch", "main")
        self.assertEqual(self.chats("A"), ["local_chatA.json", "local_chatB.json"])
        self.assertEqual(self.chats("B"), ["local_chatA.json", "local_chatB.json"])

    def test_sync_updates_older_copy_and_backs_it_up(self):
        self.two_accounts()
        self.run_csync()
        newer = os.path.join(self.app, "claude-code-sessions", UUIDS["A"], "org-A", "local_chatA.json")
        dump({"lastActivityAt": 999, "edited": True}, newer)
        self.run_csync()
        other = os.path.join(self.app, "claude-code-sessions", UUIDS["B"], "org-B", "local_chatA.json")
        self.assertTrue(load(other).get("edited"))
        backups = [os.path.join(r, f) for r, _, fs in os.walk(os.path.join(self.home, "backup")) for f in fs]
        self.assertTrue(any(b.endswith("local_chatA.json") for b in backups))

    def test_dry_run_changes_nothing(self):
        self.two_accounts()
        before_cfg = self.config()
        out = self.run_csync("switch", "main", "--dry-run").stdout
        self.assertIn("[dry run]", out)
        self.assertEqual(self.config(), before_cfg)
        self.assertEqual(self.chats("A"), ["local_chatA.json"])
        self.assertIn("[dry run]", self.run_csync("--dry-run").stdout)
        self.assertEqual(self.chats("A"), ["local_chatA.json"])

    def test_login_signs_out_but_keeps_saved_accounts(self):
        self.two_accounts()
        self.run_csync("login")
        self.assertNotIn("oauth:tokenCache", self.config())
        self.assertIsNone(self.session_cookie())
        self.assertIn("No account", self.run_csync("status").stdout)
        self.assertIn("[1] main", self.run_csync("list").stdout)

    def test_login_refuses_when_current_account_unsaved(self):
        self.sign_in("A")
        p = self.run_csync("login", ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.config()["oauth:tokenCache"], "token-A")  # nothing was cleared

    def test_slot_management(self):
        self.two_accounts()
        self.run_csync("swap", "1", "2")
        self.assertIn("[1] work", self.run_csync("list").stdout)
        self.run_csync("move", "work", "5")
        self.assertIn("[5] work", self.run_csync("list").stdout)
        self.run_csync("label", "5", "job")
        self.assertIn("[5] job", self.run_csync("list").stdout)
        self.run_csync("remove", "job")
        self.assertNotIn("job", self.run_csync("list").stdout)
        self.assertEqual(self.chats("B"), ["local_chatB.json"])  # chats untouched

    def test_resolve_by_uuid_prefix(self):
        self.two_accounts()
        self.run_csync("switch", "aaaaaaaa")
        self.assertEqual(self.config()["lastKnownAccountUuid"], UUIDS["A"])

    def test_unknown_account_fails(self):
        self.two_accounts()
        self.assertNotEqual(self.run_csync("switch", "nope", ok=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
