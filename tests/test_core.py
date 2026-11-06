import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from spectator_tooltip_patcher.__main__ import main
from spectator_tooltip_patcher.core import OLD, NEW, Profile, SafetyError, discover_profiles, game_not_running, mod_relative, patch_bytes, preferred_profile, sha


def fixture(bom=True, newline="\r\n", anchors=1):
    block = OLD * anchors
    text = ('<Root xmlns:controls="urn:test">\n<controls:AthensPanel\n' + block +
            '</controls:AthensPanel>\n</Root>\n')
    return (b"\xef\xbb\xbf" if bom else b"") + text.replace("\n", newline).encode("utf-8")


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.profile = self.base / "Games" / "Age of Mythology Retold" / "p1"
        self.mods = self.profile / "mods"
        self.mods.mkdir(parents=True)
        self.entries = []

    def add_mod(self, name, *, enabled=True, subscribed=False, raw=None):
        category = "subscribed" if subscribed else "local"
        relative = f"{category}/{name}"
        target = self.mods / relative / "game/ui_myth/Content/InGame/HUD_MouseResources.xaml"
        target.parent.mkdir(parents=True)
        target.write_bytes(fixture() if raw is None else raw)
        self.entries.append({"Path": relative.replace("/", "\\") + "\\", "Title": name,
                             "Enabled": enabled, "Priority": len(self.entries)})
        self.write_status()
        return target

    def write_status(self):
        (self.mods / "myth-mod-status.json").write_text(json.dumps({"Mods": self.entries}), encoding="utf-8")

    def tool(self, checker=lambda: None):
        return Profile(self.profile, self.base / "state", checker)

    def test_discovery_and_scope(self):
        active = self.add_mod("active")
        inactive = self.add_mod("inactive", enabled=False)
        subscribed = self.add_mod("workshop", subscribed=True)
        original_status = (self.mods / "myth-mod-status.json").read_bytes()
        self.assertEqual(discover_profiles(self.base), [self.profile])
        p = self.tool()
        self.assertEqual(len(p.patch("active")["patched"]), 1)
        self.assertEqual(patch_bytes(active.read_bytes())[0], "patched")
        self.assertEqual(patch_bytes(inactive.read_bytes())[0], "patchable")
        self.assertEqual(patch_bytes(subscribed.read_bytes())[0], "patchable")
        self.assertEqual(len(p.patch("all")["patched"]), 1)
        self.assertEqual(len(p.patch("all", True)["patched"]), 1)
        self.assertEqual((self.mods / "myth-mod-status.json").read_bytes(), original_status)
        self.assertEqual(p.verify()["unpatched_active"], [])

    def test_preferred_profile_selects_recent_mod_status_and_ties_require_choice(self):
        self.add_mod("a")
        older = self.mods / "myth-mod-status.json"
        other = self.base / "Games" / "Age of Mythology Retold" / "p2"
        recent = other / "mods" / "myth-mod-status.json"
        recent.parent.mkdir(parents=True)
        recent.write_text('{"Mods":[]}', encoding="utf-8")
        os.utime(older, ns=(1_000_000_000, 1_000_000_000))
        os.utime(recent, ns=(2_000_000_000, 2_000_000_000))
        self.assertEqual(preferred_profile([self.profile, other]), other)
        self.assertEqual(preferred_profile([self.profile]), self.profile)
        self.assertIsNone(preferred_profile([]))
        os.utime(recent, ns=(1_000_000_000, 1_000_000_000))
        self.assertIsNone(preferred_profile([self.profile, other]))

    def test_idempotence_and_exact_restore(self):
        target = self.add_mod("a", raw=fixture(bom=False, newline="\n"))
        original = target.read_bytes()
        p = self.tool()
        self.assertEqual(len(p.patch()["patched"]), 1)
        self.assertEqual(p.patch()["patched"], [])
        self.assertEqual(patch_bytes(target.read_bytes())[0], "patched")
        self.assertEqual(len(p.restore()["results"]), 1)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(p.restore()["results"], [])

    def test_crlf_and_bom(self):
        raw = fixture()
        state, out = patch_bytes(raw)
        self.assertEqual(state, "patchable")
        self.assertTrue(out.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\n", out.replace(b"\r\n", b""))
        self.assertEqual(patch_bytes(out)[0], "patched")

    def test_earlier_f1_marker_is_recognized(self):
        earlier = fixture().replace(OLD.replace("\n", "\r\n").encode("utf-8"),
                                    NEW.replace("Spectator Tooltip Fix:", "Replay Command Tooltips:").replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(patch_bytes(earlier)[0], "patched")

    def test_reject_anchors_and_mixed_newlines(self):
        self.assertEqual(patch_bytes(fixture(anchors=0))[0], "no_anchor")
        self.assertEqual(patch_bytes(fixture(anchors=2))[0], "multiple_anchors")
        self.assertEqual(patch_bytes(fixture().replace(b"</Root>\r\n", b"</Root>\n"))[0], "mixed_newlines")
        self.assertEqual(patch_bytes(b"\xff")[0], "invalid_utf8")
        self.assertEqual(patch_bytes(fixture().replace(b"</Root>", b"</Wrong>"))[0], "invalid_xml")

    def test_changed_after_patch_and_missing(self):
        target = self.add_mod("a")
        p = self.tool()
        p.patch()
        target.write_bytes(target.read_bytes() + b"<!-- update -->")
        self.assertEqual(p.verify()["ledger"][0]["current"], "changed")
        self.assertEqual(p.restore()["results"][0]["result"], "changed_left_alone")
        self.assertTrue(target.read_bytes().endswith(b"<!-- update -->"))
        target.unlink()
        self.assertEqual(p.restore()["results"][0]["result"], "missing_left_alone")

    def test_failed_run_check(self):
        target = self.add_mod("a")
        raw = target.read_bytes()
        def unavailable():
            raise SafetyError("process detection unavailable")
        with self.assertRaises(SafetyError):
            self.tool(unavailable).patch()
        self.assertEqual(target.read_bytes(), raw)

    def test_unsafe_status_paths_and_symlinks(self):
        for value in ("../elsewhere", "local/../evil", "C:/retail", "local/a/extra",
                      "local/CON", "local/a.", "local/a*", "local/a\x00b"):
            with self.assertRaises(SafetyError):
                mod_relative(value)
        target = self.add_mod("a")
        other = self.base / "elsewhere"
        other.write_bytes(fixture())
        target.unlink()
        try:
            target.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(SafetyError):
            self.tool().scan()

    def test_explicit_mod_and_backup(self):
        first = self.add_mod("a")
        second = self.add_mod("b")
        p = self.tool()
        result = p.patch("all", mod_folder="local/a")
        self.assertEqual(len(result["patched"]), 1)
        self.assertEqual(patch_bytes(second.read_bytes())[0], "patchable")
        backup = Path(result["patched"][0]["backup"])
        self.assertEqual(sha(backup.read_bytes()), p._ledger()["entries"][0]["original_sha256"])
        self.assertEqual(patch_bytes(first.read_bytes())[0], "patched")

    def test_missing_target_is_visible_and_skipped(self):
        target = self.add_mod("gone")
        target.unlink()
        p = self.tool()
        rows = p.scan()
        self.assertEqual(rows[0]["state"], "missing")
        self.assertEqual(p.patch()["patched"], [])
        self.assertEqual(p.patch()["skipped"][0]["reason"], "missing")

    def test_invalid_and_duplicate_status_entries(self):
        self.add_mod("a")
        self.entries.append(dict(self.entries[0]))
        self.write_status()
        with self.assertRaises(SafetyError):
            self.tool().scan()
        self.entries[1] = "invalid"
        self.write_status()
        with self.assertRaises(SafetyError):
            self.tool().scan()

    def test_tampered_ledger_backup_name_is_rejected(self):
        target = self.add_mod("a")
        p = self.tool()
        p.patch()
        ledger = json.loads(p.ledger_path.read_text(encoding="utf-8"))
        ledger["entries"][0]["backup"] = "../../outside.xaml"
        p.ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
        with self.assertRaises(SafetyError):
            p.restore()
        self.assertEqual(patch_bytes(target.read_bytes())[0], "patched")

    def test_pending_entry_can_restore_after_interruption(self):
        target = self.add_mod("a")
        original = target.read_bytes()
        p = self.tool()
        p.patch()
        ledger = json.loads(p.ledger_path.read_text(encoding="utf-8"))
        ledger["entries"][0]["state"] = "pending"
        p.ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
        self.assertEqual(p.restore()["results"][0]["result"], "restored")
        self.assertEqual(target.read_bytes(), original)

    def test_cli_dry_run_is_read_only(self):
        target = self.add_mod("a")
        original = target.read_bytes()
        output = StringIO()
        with redirect_stdout(output):
            code = main(["patch", "--profile", str(self.profile), "--state-dir", str(self.base / "state"), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(output.getvalue())["to_patch"]), 1)
        self.assertEqual(target.read_bytes(), original)
        self.assertFalse((self.base / "state").exists())

    def test_restore_plan_requires_verified_backup(self):
        target = self.add_mod("a")
        tool = self.tool()
        tool.patch()
        plan = tool.restore_plan()
        self.assertEqual(plan[0]["action"], "restore")
        backup = Path(plan[0]["backup"])
        original = backup.read_bytes()
        backup.write_bytes(b"tampered")
        self.assertEqual(tool.restore_plan()[0]["action"], "skip_invalid_backup")
        self.assertEqual(patch_bytes(target.read_bytes())[0], "patched")
        backup.unlink()
        self.assertEqual(tool.restore_plan()[0]["action"], "skip_missing_backup")
        backup.write_bytes(original)
        self.assertEqual(tool.restore_plan()[0]["action"], "restore")

    def test_running_game_is_refused(self):
        if __import__("os").name != "nt":
            self.skipTest("Windows tasklist only")
        completed = __import__("subprocess").CompletedProcess([], 0, '"AoMRT.exe","123","Console","1","1 K"\n', "")
        with patch("spectator_tooltip_patcher.core.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(SafetyError, "running"):
                game_not_running()


if __name__ == "__main__":
    unittest.main()
