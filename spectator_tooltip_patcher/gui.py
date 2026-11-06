"""Small keyboard-operable Tk GUI. Opening it is read-only."""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import Profile, SafetyError, discover_profiles, preferred_profile


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Spectator Tooltip Fix — Compatibility Patcher")
        root.geometry("1000x600")
        self.profile = tk.StringVar()
        self.mod_folder = tk.StringVar()
        self.subscribed = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Choose a profile, then Scan. No files are changed on open.")
        self.profiles = discover_profiles()
        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Profile").grid(row=0, column=0, sticky="w")
        self.combo = ttk.Combobox(outer, textvariable=self.profile, values=[str(p) for p in self.profiles], width=85)
        self.combo.grid(row=0, column=1, sticky="ew")
        ttk.Button(outer, text="Browse…", command=self.browse).grid(row=0, column=2)
        ttk.Label(outer, text="Mod folder (optional: local/Name)").grid(row=1, column=0, sticky="w")
        ttk.Entry(outer, textvariable=self.mod_folder).grid(row=1, column=1, sticky="ew")
        ttk.Checkbutton(outer, text="Include subscribed mods (updates may overwrite changes)",
                        variable=self.subscribed).grid(row=2, column=0, columnspan=3, sticky="w")
        controls = ttk.Frame(outer)
        controls.grid(row=3, column=0, columnspan=3, sticky="w", pady=8)
        for label, action in (("Scan", self.scan), ("Patch Active", lambda: self.patch("active")),
                              ("Patch All", lambda: self.patch("all")), ("Verify", self.verify),
                              ("Restore", self.restore)):
            ttk.Button(controls, text=label, command=action).pack(side="left", padx=(0, 8))
        columns = ("mod", "enabled", "subscribed", "effective", "state", "selected")
        self.tree = ttk.Treeview(outer, columns=columns, show="headings", height=15)
        for col, width in (("mod", 300), ("enabled", 75), ("subscribed", 90),
                           ("effective", 80), ("state", 150), ("selected", 80)):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=4, column=0, columnspan=3, sticky="nsew")
        scroll = ttk.Scrollbar(outer, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=4, column=3, sticky="ns")
        ttk.Label(outer, textvariable=self.status, wraplength=950).grid(row=5, column=0, columnspan=3, sticky="w", pady=5)
        self.detail = tk.Text(outer, height=8, wrap="word", state="disabled")
        self.detail.grid(row=6, column=0, columnspan=3, sticky="nsew")
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(4, weight=3)
        outer.rowconfigure(6, weight=1)
        selected = preferred_profile(self.profiles)
        if selected is not None:
            self.profile.set(str(selected))
            # Show the detected mods without requiring a Scan click.
            # No file is modified until the user confirms Patch or Restore.
            root.after_idle(self.scan)
        elif self.profiles:
            self.status.set("Multiple equally recent profiles found. Choose one, then Scan.")
        else:
            self.status.set("No Retold profile found automatically. Use Browse to select a profile.")

    def browse(self):
        chosen = filedialog.askdirectory(title="Select a Retold profile folder")
        if chosen:
            self.profile.set(chosen)

    def selected(self) -> Profile:
        if not self.profile.get().strip():
            raise SafetyError("Choose a profile directory first")
        return Profile(Path(self.profile.get().strip()))

    def mod(self) -> str | None:
        return self.mod_folder.get().strip() or None

    def show(self, value):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", json.dumps(value, indent=2))
        self.detail.configure(state="disabled")

    def rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=(row["mod"], row["enabled"], row["subscribed"],
                                                   row["in_effect"], row["state"], row.get("selected", "")))

    def guarded(self, callback):
        try:
            callback()
        except (SafetyError, OSError, ValueError, json.JSONDecodeError) as exc:
            self.status.set(str(exc))
            messagebox.showerror("Spectator Tooltip Fix", str(exc), parent=self.root)

    def scan(self):
        def work():
            plan = self.selected().plan("all", self.subscribed.get(), self.mod())
            self.rows(plan["rows"])
            self.show({"profile": plan["profile"], "backup_root": plan["state_dir"]})
            providers = sum(row["state"] != "missing" for row in plan["rows"])
            patchable = sum(row["state"] == "patchable" for row in plan["rows"])
            self.status.set(
                f"Found {providers} HUD resource provider(s) among {len(plan['rows'])} mods; "
                f"{patchable} patchable. Scan made no changes."
            )
        self.guarded(work)

    def patch(self, scope: str):
        def work():
            profile = self.selected()
            plan = profile.plan(scope, self.subscribed.get(), self.mod())
            self.rows(plan["rows"])
            if not plan["to_patch"]:
                self.status.set("No selected files are patchable.")
                return
            paths = "\n".join(r["path"] for r in plan["to_patch"])
            warning = "\nSubscribed mods may be replaced at game update.\n" if any(r["subscribed"] for r in plan["to_patch"]) else ""
            if not messagebox.askyesno("Confirm patch", f"Patch these files?\n\n{paths}\n\nBackups: {profile.state / 'backups'}{warning}", parent=self.root):
                return
            result = profile.patch(scope, self.subscribed.get(), self.mod())
            self.show(result)
            self.status.set(f"Patched {len(result['patched'])} file(s). Review skips in details.")
            self.rows(profile.scan("all", self.subscribed.get(), self.mod()))
        self.guarded(work)

    def verify(self):
        def work():
            result = self.selected().verify()
            self.show(result)
            self.rows(result["rows"])
            self.status.set(f"Verification complete; {len(result['unpatched_active'])} enabled provider(s) unpatched.")
        self.guarded(work)

    def restore(self):
        def work():
            profile = self.selected()
            plan = profile.restore_plan()
            actionable = [r for r in plan if r["action"] == "restore"]
            if not actionable:
                self.status.set("No unmodified patched files to restore.")
                self.show(plan)
                return
            lines = "\n".join(f"{r['path']}\n  from {r['backup']}" for r in actionable)
            if not messagebox.askyesno("Confirm restore", f"Restore exact backups for:\n\n{lines}", parent=self.root):
                return
            result = profile.restore()
            self.show(result)
            self.status.set("Restore complete. Changed or missing files were left alone.")
            self.rows(profile.scan("all", self.subscribed.get(), self.mod()))
        self.guarded(work)


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
