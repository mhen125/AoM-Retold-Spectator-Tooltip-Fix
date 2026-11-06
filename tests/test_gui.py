"""Guided Tk UI regression checks using synthetic Retold profiles only."""
import json
import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from spectator_tooltip_patcher import gui
from spectator_tooltip_patcher.core import OLD, Profile, REL, patch_bytes


def fixture():
    text = ('<Root xmlns:controls="urn:test">\n'
            '<controls:AthensPanel\n' + OLD +
            '</controls:AthensPanel>\n</Root>\n')
    return b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8")


class GuidedGuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.profile = self.base / "Games" / "Age of Mythology Retold" / "synthetic"
        self.mods = self.profile / "mods"
        self.mods.mkdir(parents=True)
        self.entries = []

        def add_mod(name, category="local", enabled=True, with_file=True):
            rel = f"{category}/{name}"
            target = self.mods / rel / REL
            if with_file:
                target.parent.mkdir(parents=True)
                target.write_bytes(fixture())
            self.entries.append({
                "Path": rel.replace("/", "\\") + "\\",
                "Title": name, "Enabled": enabled, "Priority": len(self.entries)
            })
            return target

        self.primary = add_mod("Synthetic HUD")
        self.secondary = add_mod("Dormant HUD", enabled=False)
        self.workshop = add_mod("Subscribed HUD", category="subscribed")
        add_mod("No HUD File", with_file=False)
        self.status = self.mods / "myth-mod-status.json"
        self.status.write_text(json.dumps({"Mods": self.entries}), encoding="utf-8")
        self.original_bytes = self.primary.read_bytes()
        self.original_status = self.status.read_bytes()

        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.base / "localdata")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.profiles_patch = patch.object(gui, "discover_profiles", return_value=[self.profile])
        self.profiles_patch.start()
        self.addCleanup(self.profiles_patch.stop)
        self.class_patch = patch.object(
            gui, "Profile", side_effect=lambda root: Profile(
                root, self.base / "localdata", check_game=lambda: None
            )
        )
        self.class_patch.start()
        self.addCleanup(self.class_patch.stop)

    def test_home_scope_results_restore(self):
        app = gui.App(self.root)
        self.root.update_idletasks()
        self.assertEqual(app.page, "home")
        self.assertEqual(app.profile_path, str(self.profile))
        self.assertFalse(app.restore_available)
        app.scope_page()
        self.assertEqual(app.page, "scope")
        self.assertEqual(len(app._cards), 2)
        self.assertEqual(app.scope.get(), "active")
        app.scope.set("all")
        app._recolor_choices()
        app.home()
        app.scope_page()
        self.assertEqual(len(app._cards), 2, "revisiting scope must not use destroyed cards")
        app.scope.set("active")
        app.run_patch()
        self.assertEqual(app.page, "result")
        self.assertEqual(patch_bytes(self.primary.read_bytes())[0], "patched")
        self.assertEqual(patch_bytes(self.secondary.read_bytes())[0], "patchable")
        self.assertEqual(patch_bytes(self.workshop.read_bytes())[0], "patchable")
        self.assertEqual(self.original_status, self.status.read_bytes())
        app.home()
        self.assertTrue(app.restore_available)
        app.restore_page()
        self.assertEqual(app.page, "restore")
        app.run_restore()
        self.assertEqual(app.page, "result")
        self.assertEqual(self.primary.read_bytes(), self.original_bytes)
        self.assertEqual(self.original_status, self.status.read_bytes())

    def test_result_filters_missing_and_fix_mod(self):
        rows = [
            {"mod": "local/Spectator Tooltip Fix", "state": "patched", "enabled": True},
            {"mod": "local/A", "state": "missing", "enabled": True},
            {"mod": "local/HUD One", "state": "patchable", "enabled": True},
            {"mod": "local/HUD Two", "state": "patchable", "enabled": False},
        ]
        self.assertEqual([r["mod"] for r in gui.visible_conflicts(rows, "active")],
                         ["local/HUD One"])
        self.assertEqual([r["mod"] for r in gui.visible_conflicts(rows, "all")],
                         ["local/HUD One", "local/HUD Two"])
        self.assertEqual(gui.visible_conflicts(rows[:2], "all"), [])


if __name__ == "__main__":
    unittest.main()
