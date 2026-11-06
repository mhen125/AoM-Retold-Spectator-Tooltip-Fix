"""Compact guided Windows GUI for the spectator tooltip compatibility patcher.

The GUI scans profiles read-only. Writing requires a deliberate confirmation
button on the scope or restore page; backups and integrity checks live in core.
"""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import Profile, SafetyError, discover_profiles, preferred_profile

BG = "#101A26"
SURFACE = "#192938"
SURFACE_ALT = "#213446"
BORDER = "#34495B"
GOLD = "#D9AF67"
GOLD_HOVER = "#EBC688"
WHITE = "#F6F2E9"
MUTED = "#B6C4D0"
GREEN = "#74D6B0"
WARNING = "#F0BE80"
RED = "#E99C94"
FONT = "Segoe UI"
SELF_MOD_NAMES = {"spectator tooltip fix", "replay command tooltips"}


def is_conflict(row: dict) -> bool:
    """Only actual HUD providers other than the installed tooltip fix."""
    folder = row.get("mod", "").replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].casefold()
    return row.get("state") != "missing" and folder not in SELF_MOD_NAMES


def visible_conflicts(rows: list[dict], scope: str) -> list[dict]:
    return [r for r in rows if is_conflict(r) and (scope == "all" or r["enabled"])]


def valid_restore_rows(plan: list[dict]) -> list[dict]:
    return [r for r in plan if r.get("action") == "restore"]


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Spectator Tooltip Fix")
        root.geometry("580x450")
        root.minsize(540, 430)
        root.configure(bg=BG)

        self.profiles = discover_profiles()
        detected = preferred_profile(self.profiles)
        self.profile_path = str(detected) if detected else ""
        self.scope = tk.StringVar(value="active")
        self.include_subscribed = tk.BooleanVar(value=False)
        self.page = "home"
        self.restore_available = False
        self.profile_picker_open = False

        self.outer = tk.Frame(root, bg=BG)
        self.outer.pack(fill="both", expand=True, padx=25, pady=(19, 15))

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(
            "Profile.TCombobox",
            fieldbackground=SURFACE,
            background=SURFACE,
            foreground=WHITE,
            bordercolor=BORDER,
            arrowcolor=GOLD,
            selectbackground=SURFACE_ALT,
            selectforeground=WHITE,
            padding=5,
        )
        self.home()

    def _clear(self):
        for child in self.outer.winfo_children():
            child.destroy()

    def _text(self, parent, value, *, size=10, color=WHITE, bold=False,
              wrap=515, pady=0, **kwargs):
        widget = tk.Label(
            parent, text=value, bg=parent.cget("bg"), fg=color,
            font=(FONT, size, "bold" if bold else "normal"),
            justify="left", anchor="w", wraplength=wrap, **kwargs
        )
        widget.pack(anchor="w", pady=pady)
        return widget

    def _header(self, heading: str, subheading: str, back=None):
        if back is not None:
            self._button(self.outer, "‹  Back", back, outline=True, small=True,
                         width=100, pady=(0, 13))
        self._text(self.outer, "SPECTATOR TOOLTIP FIX", size=9, color=GOLD, bold=True,
                   pady=(0, 5))
        self._text(self.outer, heading, size=20, bold=True, wrap=520, pady=(0, 5))
        self._text(self.outer, subheading, size=10, color=MUTED, pady=(0, 16))

    def _button(self, parent, label: str, callback, *, primary=False,
                outline=False, small=False, width=None, pady=(0, 10)):
        bg = GOLD if primary else (BG if outline else SURFACE_ALT)
        fg = BG if primary else (MUTED if outline else WHITE)
        active = GOLD_HOVER if primary else SURFACE
        w = tk.Button(
            parent, text=label, command=callback, bg=bg, fg=fg,
            activebackground=active, activeforeground=BG if primary else WHITE,
            highlightthickness=1 if outline else 0, highlightbackground=BORDER,
            bd=0, relief="flat", font=(FONT, 10 if small else 11, "bold"),
            padx=16, pady=8 if small else 12, cursor="hand2",
            width=width, anchor="center",
        )
        w.pack(fill="x" if width is None else "none", anchor="w", pady=pady)
        return w

    def _line(self):
        tk.Frame(self.outer, height=1, bg=BORDER).pack(fill="x", pady=(6, 12))

    def _foot(self, text: str):
        self._text(self.outer, text, color=MUTED, size=9, wrap=510)

    def _selected(self) -> Profile:
        if not self.profile_path:
            raise SafetyError("No Retold profile found. Choose your game folder first.")
        return Profile(Path(self.profile_path))

    def _guard(self, callback):
        try:
            return callback()
        except (SafetyError, OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Spectator Tooltip Fix", str(exc), parent=self.root)
            return None

    def _profile_control(self):
        if not self.profile_path:
            self._text(self.outer, "Game folder not detected", color=WARNING, bold=True,
                       pady=(5, 8))
            self._button(self.outer, "Choose Game Folder", self.browse,
                         small=True, width=25)
            return

        footer = tk.Frame(self.outer, bg=BG)
        footer.pack(fill="x", pady=(9, 3))
        tk.Label(
            footer, text="✓  Game profile detected automatically", bg=BG, fg=GREEN,
            font=(FONT, 9), anchor="w"
        ).pack(side="left")
        tk.Button(
            footer, text="Change", command=self.toggle_profile_picker,
            bg=BG, fg=GOLD, activebackground=BG, activeforeground=GOLD_HOVER,
            relief="flat", borderwidth=0, cursor="hand2",
            font=(FONT, 9, "underline")
        ).pack(side="right")
        if self.profile_picker_open:
            pick = tk.Frame(self.outer, bg=BG)
            pick.pack(fill="x", pady=6)
            selection = tk.StringVar(value=self.profile_path)
            combo = ttk.Combobox(
                pick, values=[str(x) for x in self.profiles],
                textvariable=selection, style="Profile.TCombobox",
                state="readonly", width=52
            )
            combo.pack(side="left", fill="x", expand=True, padx=(0, 7))
            def changed(_event=None):
                self.profile_path = selection.get()
                self.profile_picker_open = False
                self.home()
            combo.bind("<<ComboboxSelected>>", changed)
            tk.Button(
                pick, text="Browse…", command=self.browse, bg=SURFACE_ALT,
                fg=WHITE, activebackground=BORDER, activeforeground=WHITE,
                relief="flat", bd=0, font=(FONT, 9), cursor="hand2"
            ).pack(side="right")

    def toggle_profile_picker(self):
        self.profile_picker_open = not self.profile_picker_open
        self.home()

    def browse(self):
        selected = filedialog.askdirectory(
            title="Choose your Age of Mythology: Retold game profile",
            parent=self.root
        )
        if selected:
            self.profile_path = selected
            self.profile_picker_open = False
            self.home()

    def home(self):
        self.page = "home"
        self._clear()
        self._header(
            "Compatibility Patcher",
            "Keep your other HUD mods and restore command-panel tooltips in replays."
        )
        self._button(self.outer, "Run the Patch   ›", self.scope_page, primary=True)
        self.restore_available = False
        if self.profile_path:
            def check():
                plan = self._selected().restore_plan()
                return bool(valid_restore_rows(plan))
            checked = self._guard(check)
            self.restore_available = bool(checked)
        if self.restore_available:
            self._button(self.outer, "Restore Backup", self.restore_page)
        self._line()
        self._profile_control()
        if not self.restore_available:
            self._foot("No restorable backups found. Backups are created when you run the patch.")
        else:
            self._foot("Changes are never made automatically. Original files are backed up before patching.")

    def scope_page(self):
        def work():
            self._selected().scan("all", True)
            self.page = "scope"
            self._clear()
            self._cards = []
            self._header(
                "Choose your mods",
                "Pick which installed mods should receive the compatibility fix.",
                back=self.home,
            )
            self._choice_card(
                "active", "Active mods", "Only enabled mods (recommended)."
            )
            self._choice_card(
                "all", "All mods", "Enabled and disabled mods."
            )
            all_rows = self._selected().scan("all", True)
            workshop = [r for r in all_rows if r["subscribed"] and is_conflict(r)]
            if workshop:
                check = tk.Checkbutton(
                    self.outer, text="Include subscribed / Workshop mods",
                    variable=self.include_subscribed, onvalue=True, offvalue=False,
                    bg=BG, fg=MUTED, selectcolor=SURFACE_ALT,
                    activebackground=BG, activeforeground=WHITE,
                    font=(FONT, 9), cursor="hand2"
                )
                check.pack(anchor="w", pady=(5, 1))
                self._text(self.outer, "Workshop updates may overwrite compatibility changes.",
                           color=MUTED, size=8, pady=(0, 8))
            else:
                self._text(self.outer, "Workshop mods are excluded unless explicitly selected.",
                           color=MUTED, size=8, pady=(1, 9))
            self._button(self.outer, "Confirm & Run Patch", self.run_patch,
                         primary=True, pady=(4, 4))
            self._foot("Original files are backed up automatically. Retold must be closed.")
        self._guard(work)

    def _choice_card(self, value: str, title: str, description: str):
        frame = tk.Frame(
            self.outer, bg=SURFACE,
            highlightthickness=1,
            highlightbackground=GOLD if self.scope.get() == value else BORDER
        )
        frame.pack(fill="x", pady=(0, 10))
        radio = tk.Radiobutton(
            frame, text=title, variable=self.scope, value=value,
            command=self._recolor_choices,
            bg=SURFACE, fg=WHITE, activebackground=SURFACE,
            activeforeground=WHITE, selectcolor=SURFACE_ALT,
            font=(FONT, 11, "bold"), anchor="w", cursor="hand2",
            padx=12, pady=7
        )
        radio.pack(anchor="w", fill="x")
        lbl = tk.Label(frame, text=description, bg=SURFACE, fg=MUTED,
                       font=(FONT, 9), anchor="w", padx=32, pady=0)
        lbl.pack(anchor="w", pady=(0, 9))
        self._cards.append((value, frame))

    def _recolor_choices(self):
        for value, frame in getattr(self, "_cards", []):
            frame.configure(highlightbackground=GOLD if value == self.scope.get() else BORDER)

    def run_patch(self):
        def work():
            profile = self._selected()
            scope = self.scope.get()
            include = self.include_subscribed.get()
            plan = profile.plan(scope, include)
            if not plan["to_patch"]:
                self.result_page(profile, scope, include, patched=[], skipped=[],
                                 operation="patch")
                return
            # This button is the explicit confirmation; Profile.patch always
            # writes each verified original to the backup ledger before editing.
            result = profile.patch(scope, include)
            self.result_page(profile, scope, include, patched=result["patched"],
                             skipped=result["skipped"], operation="patch")
        self._guard(work)

    def restore_page(self):
        def work():
            plan = valid_restore_rows(self._selected().restore_plan())
            if not plan:
                self.home()
                return
            self.page = "restore"
            self._clear()
            self._header(
                "Restore your backup",
                "Return your patched mods to their exact saved originals.",
                back=self.home
            )
            self._text(self.outer, f"{len(plan)} mod backup(s) ready to restore.",
                       color=GREEN, bold=True, pady=(3, 12))
            self._text(self.outer, "Modified or missing files will never be overwritten.",
                       color=MUTED, size=10, pady=(0, 20))
            self._button(self.outer, "Confirm & Restore Backup",
                         self.run_restore, primary=True, pady=(0, 8))
            self._foot("Retold must be closed. Backups are checked before restoration.")
        self._guard(work)

    def run_restore(self):
        def work():
            profile = self._selected()
            result = profile.restore()
            self.result_page(profile, "all", True, patched=[], skipped=[],
                             operation="restore", restored=result["results"])
        self._guard(work)

    def result_page(self, profile: Profile, scope: str, include: bool, *,
                    patched: list[dict], skipped: list[dict],
                    operation: str, restored: list[dict] | None = None):
        self.page = "result"
        rows = visible_conflicts(profile.scan("all", True), scope)
        self._clear()
        self._header(
            "Backup restored" if operation == "restore" else "Compatibility check complete",
            ("Your saved originals were checked and restored where valid."
             if operation == "restore" else
             "The compatibility check has finished. Original files were backed up automatically."),
            back=None
        )
        if operation == "patch":
            number = len(patched)
            if not rows:
                self._text(self.outer, "No conflicts.", color=GREEN, bold=True,
                           size=18, pady=(8, 12))
                self._text(self.outer, "No other installed mods replace the relevant HUD file.",
                           color=MUTED, size=10, pady=(0, 15))
            else:
                self._text(self.outer,
                           f"{number} mod(s) updated" if number else "No changes needed",
                           color=GREEN if number else GOLD, size=14, bold=True, pady=(2, 9))
        else:
            restored = restored or []
            count = sum(r.get("result") in ("restored", "already_original") for r in restored)
            self._text(self.outer, f"{count} mod(s) restored",
                       color=GREEN, size=14, bold=True, pady=(2, 9))

        if rows:
            self._text(self.outer, "MODS USING THE HUD FILE", size=8,
                       color=GOLD, bold=True, pady=(4, 7))
            holder = tk.Frame(self.outer, bg=SURFACE, highlightthickness=1,
                              highlightbackground=BORDER)
            holder.pack(fill="both", expand=True, pady=(0, 10))
            canvas = tk.Canvas(holder, bg=SURFACE, highlightthickness=0,
                               borderwidth=0)
            scrollbar = tk.Scrollbar(holder, orient="vertical", command=canvas.yview,
                                     bg=SURFACE_ALT, troughcolor=SURFACE,
                                     activebackground=BORDER)
            content = tk.Frame(canvas, bg=SURFACE)
            content.bind("<Configure>",
                         lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            window = canvas.create_window((0, 0), window=content, anchor="nw")
            canvas.bind("<Configure>",
                        lambda e: canvas.itemconfigure(window, width=e.width))
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            patched_set = {r["mod"] for r in patched}
            restored_lookup = {r["mod"]: r["result"] for r in (restored or [])}
            for row in rows:
                if operation == "restore":
                    outcome = restored_lookup.get(row["mod"], "unchanged")
                    if outcome in ("restored", "already_original"):
                        status, color = "Restored", GREEN
                    elif outcome in ("changed_left_alone", "missing_left_alone",
                                     "backup_missing_left_alone", "backup_changed_left_alone"):
                        status, color = "Left unchanged", WARNING
                    else:
                        status, color = "Not restored", MUTED
                elif row["mod"] in patched_set:
                    status, color = "Updated", GREEN
                elif row["state"] == "patched":
                    status, color = "Already fixed", GREEN
                elif row["subscribed"] and not include:
                    status, color = "Workshop excluded", WARNING
                elif row["state"] == "patchable" and scope == "active" and not row["enabled"]:
                    status, color = "Not selected", MUTED
                elif row["state"] == "patchable":
                    status, color = "Needs attention", WARNING
                else:
                    status, color = "Unsupported file", WARNING
                line = tk.Frame(content, bg=SURFACE, height=36)
                line.pack(fill="x", padx=12, pady=1)
                line.pack_propagate(False)
                label = row["mod"].replace("\\", "/").split("/", 1)[-1]
                tk.Label(line, text=label, bg=SURFACE, fg=WHITE,
                         font=(FONT, 9), anchor="w").pack(
                             side="left", fill="x", expand=True)
                tk.Label(line, text=status, bg=SURFACE, fg=color,
                         font=(FONT, 9, "bold"), anchor="e").pack(side="right")
        else:
            tk.Frame(self.outer, bg=BG, height=35).pack()

        bottom = tk.Frame(self.outer, bg=BG)
        bottom.pack(fill="x", side="bottom", pady=(9, 0))
        close = tk.Button(
            bottom, text="Exit", command=self.root.destroy, bg=GOLD, fg=BG,
            activebackground=GOLD_HOVER, activeforeground=BG,
            bd=0, font=(FONT, 11, "bold"), cursor="hand2", padx=23, pady=11
        )
        close.pack(side="right")
        tk.Button(
            bottom, text="Back to Start", command=self.home,
            bg=SURFACE_ALT, fg=WHITE, activebackground=SURFACE,
            activeforeground=WHITE, bd=0, font=(FONT, 9),
            cursor="hand2", padx=13, pady=12
        ).pack(side="left")


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
