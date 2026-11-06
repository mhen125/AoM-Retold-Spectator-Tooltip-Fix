"""Conservative, file-only F1 patcher. No game or status-file writes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

REL = Path("game/ui_myth/Content/InGame/HUD_MouseResources.xaml")
MARKER = "Spectator Tooltip Fix: collapsed replay panel releases command-grid hover"
OLD = '''                    Focusable="False"
                    Style="{StaticResource CommandPanel}"
                    Visibility="{Binding ReplayCommandPanel, Converter={StaticResource NotNullToVisibility}}">
'''
NEW = f'''                    Focusable="False"
                    Visibility="{{Binding ReplayCommandPanel, Converter={{StaticResource NotNullToVisibility}}}}">
                    <!--  {MARKER}  -->
                    <controls:AthensPanel.Style>
                        <Style
                            BasedOn="{{StaticResource CommandPanel}}"
                            TargetType="controls:AthensPanel">
                            <Style.Triggers>
                                <DataTrigger
                                    Binding="{{Binding ReplayCommandPanel.IsCollapsed}}"
                                    Value="True">
                                    <Setter Property="IsHitTestVisible" Value="False" />
                                </DataTrigger>
                            </Style.Triggers>
                        </Style>
                    </controls:AthensPanel.Style>
'''
FIX_SIGNATURE = (
    "<controls:AthensPanel.Style>",
    'BasedOn="{StaticResource CommandPanel}"',
    'Binding="{Binding ReplayCommandPanel.IsCollapsed}"',
    '<Setter Property="IsHitTestVisible" Value="False" />',
)


class SafetyError(Exception):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unsafe_component(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.stat(follow_symlinks=False).st_file_attributes & 0x400)
    except AttributeError:
        return False


def safe_path(root: Path, target: Path) -> Path:
    """Require a lexical descendant and no symlink/junction in the existing path."""
    root = Path(os.path.abspath(root))
    target = Path(os.path.abspath(target))
    try:
        rel = target.relative_to(root)
    except ValueError as exc:
        raise SafetyError("Path escapes selected profile") from exc
    for part in (root, *(root / Path(*rel.parts[:i]) for i in range(1, len(rel.parts) + 1))):
        if part.exists() and _unsafe_component(part):
            raise SafetyError(f"Symlink or reparse point: {part}")
    return target


def mod_relative(value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise SafetyError("Invalid mod Path in status JSON")
    normalized = value.replace("\\", "/")
    if normalized.startswith("/"):
        raise SafetyError(f"Unsafe mod Path in status JSON: {value!r}")
    parts = normalized.rstrip("/").split("/")
    if len(parts) != 2 or parts[0].lower() not in ("local", "subscribed") or any(
        p in ("", ".", "..") or p.rstrip(" .") != p or
        any(ord(char) < 32 or char in '<>:"|?*' for char in p) for p in parts
    ):
        raise SafetyError(f"Unsafe mod Path in status JSON: {value!r}")
    if parts[1].split(".", 1)[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        raise SafetyError(f"Unsafe mod Path in status JSON: {value!r}")
    return Path(*parts)


def patch_bytes(raw: bytes) -> tuple[str, bytes | None]:
    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    try:
        content = raw[len(bom):].decode("utf-8")
    except UnicodeDecodeError:
        return "invalid_utf8", None
    if "\r" in content.replace("\r\n", "") or ("\r\n" in content and "\n" in content.replace("\r\n", "")):
        return "mixed_newlines", None
    newline = "\r\n" if "\r\n" in content else "\n"
    normalized = content.replace("\r\n", "\n")
    if normalized.count(OLD) == 0 and all(part in normalized for part in FIX_SIGNATURE):
        try:
            ET.fromstring(raw)
        except ET.ParseError:
            return "invalid_xml", None
        return "patched", None
    count = normalized.count(OLD)
    if count != 1:
        return ("no_anchor" if count == 0 else "multiple_anchors"), None
    try:
        ET.fromstring(raw)
    except ET.ParseError:
        return "invalid_xml", None
    out = bom + normalized.replace(OLD, NEW).replace("\n", newline).encode("utf-8")
    try:
        ET.fromstring(out)
    except ET.ParseError:
        return "invalid_patched_xml", None
    return "patchable", out


def game_not_running() -> None:
    if os.name != "nt":
        raise SafetyError("Retold process detection unavailable on this platform")
    try:
        result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SafetyError("Retold process detection unavailable") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise SafetyError("Retold process detection unavailable")
    import csv
    try:
        names = [row[0].casefold() for row in csv.reader(result.stdout.splitlines()) if row]
    except (csv.Error, IndexError) as exc:
        raise SafetyError("Retold process detection unavailable") from exc
    if any(name in ("aomrt.exe", "age of mythology retold.exe") or name.startswith("aomrt") for name in names):
        raise SafetyError("Age of Mythology: Retold is running; close it first")


def profile_root(home: Path | None = None) -> Path:
    return (home or Path.home()) / "Games" / "Age of Mythology Retold"


def discover_profiles(home: Path | None = None) -> list[Path]:
    base = profile_root(home)
    if not base.is_dir() or _unsafe_component(base):
        return []
    return sorted((p for p in base.iterdir() if p.is_dir() and not _unsafe_component(p)
                   and (p / "mods" / "myth-mod-status.json").is_file()), key=lambda p: p.name.casefold())


def default_store() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise SafetyError("LOCALAPPDATA is unavailable; specify --state-dir")
    return Path(local) / "SpectatorTooltipPatcher"


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class Profile:
    def __init__(self, root: Path, state_base: Path | None = None,
                 check_game: Callable[[], None] = game_not_running):
        self.root = Path(os.path.abspath(root))
        self.mods = safe_path(self.root, self.root / "mods")
        self.status = safe_path(self.root, self.mods / "myth-mod-status.json")
        if not self.status.is_file():
            raise SafetyError(f"Status JSON missing: {self.status}")
        self.state_base = Path(os.path.abspath(state_base if state_base is not None else default_store()))
        self.state = self.state_base / sha(str(self.root).casefold().encode("utf-8"))[:20]
        self.ledger_path = self.state / "ledger.json"
        self.check_game = check_game

    def _ledger(self) -> dict:
        safe_path(self.state_base, self.ledger_path)
        if not self.ledger_path.exists():
            return {"schema": 1, "profile": str(self.root), "entries": []}
        data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or data.get("profile") != str(self.root) or not isinstance(data.get("entries"), list):
            raise SafetyError("Ledger does not match selected profile")
        for entry in data["entries"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("mod"), str):
                raise SafetyError("Invalid ledger entry")
            mod_relative(entry["mod"])
            if not isinstance(entry.get("backup"), str) or not re.fullmatch(r"[0-9a-f]{32}\.xaml", entry["backup"]):
                raise SafetyError("Invalid ledger backup name")
            if any(not isinstance(entry.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", entry[key])
                   for key in ("original_sha256", "patched_sha256")):
                raise SafetyError("Invalid ledger hash")
            if entry.get("state") not in ("pending", "patched", "restored", "aborted_changed"):
                raise SafetyError("Invalid ledger state")
        return data

    def _save(self, data: dict) -> None:
        safe_path(self.state_base, self.ledger_path)
        atomic_write(self.ledger_path, (json.dumps(data, indent=2) + "\n").encode("utf-8"))

    def _backup(self, name: str) -> Path:
        return safe_path(self.state_base, self.state / "backups" / name)

    def _target(self, relative: str) -> Path:
        mod = mod_relative(relative)
        return safe_path(self.root, self.mods / mod / REL)

    def scan(self, scope: str = "active", include_subscribed: bool = False,
             mod_folder: str | None = None) -> list[dict]:
        if scope not in ("active", "all"):
            raise SafetyError("Scope must be active or all")
        status = json.loads(self.status.read_text(encoding="utf-8-sig"))
        mods = status.get("Mods")
        if not isinstance(mods, list):
            raise SafetyError("Status JSON has no Mods array")
        selected = mod_relative(mod_folder).as_posix().casefold() if mod_folder else None
        found = False
        seen = set()
        rows = []
        for item in mods:
            if not isinstance(item, dict):
                raise SafetyError("Status JSON contains an invalid mod entry")
            rel = mod_relative(item.get("Path", "")).as_posix()
            if rel.casefold() in seen:
                raise SafetyError(f"Status JSON lists a mod folder more than once: {rel}")
            seen.add(rel.casefold())
            target = self._target(rel)
            if selected and rel.casefold() != selected:
                continue
            found = True
            raw = target.read_bytes() if target.is_file() else None
            state = patch_bytes(raw)[0] if raw is not None else "missing"
            subscribed = rel.casefold().startswith("subscribed/")
            enabled = item.get("Enabled") is True
            rows.append({"title": str(item.get("Title", rel)), "mod": rel, "path": str(target),
                         "enabled": enabled, "priority": item.get("Priority"), "subscribed": subscribed,
                         "state": state, "sha256": sha(raw) if raw is not None else None,
                         "selected": (scope == "all" or enabled) and (include_subscribed or not subscribed)})
        if selected and not found:
            raise SafetyError(f"Mod folder not listed in status JSON: {mod_folder}")
        enabled_rows = [r for r in rows if r["enabled"] and isinstance(r["priority"], int)]
        effective = min(enabled_rows, key=lambda r: r["priority"], default=None)
        for row in rows:
            row["in_effect"] = row is effective
        return rows

    def plan(self, scope: str = "active", include_subscribed: bool = False,
             mod_folder: str | None = None) -> dict:
        rows = self.scan(scope, include_subscribed, mod_folder)
        return {"profile": str(self.root), "state_dir": str(self.state), "scope": scope,
                "rows": rows, "to_patch": [r for r in rows if r["selected"] and r["state"] == "patchable"]}

    def patch(self, scope: str = "active", include_subscribed: bool = False,
              mod_folder: str | None = None) -> dict:
        self.check_game()
        plan = self.plan(scope, include_subscribed, mod_folder)
        ledger = self._ledger()
        result = {"patched": [], "skipped": []}
        for row in plan["rows"]:
            if not row["selected"] or row["state"] != "patchable":
                result["skipped"].append({"mod": row["mod"], "reason": "out_of_scope" if not row["selected"] else row["state"]})
                continue
            self.check_game()
            target = self._target(row["mod"])
            original = target.read_bytes()
            if sha(original) != row["sha256"]:
                result["skipped"].append({"mod": row["mod"], "reason": "changed_since_scan"})
                continue
            state, patched = patch_bytes(original)
            if state != "patchable" or patched is None:
                result["skipped"].append({"mod": row["mod"], "reason": state})
                continue
            backup_name = uuid.uuid4().hex + ".xaml"
            backup = self._backup(backup_name)
            backup.parent.mkdir(parents=True, exist_ok=True)
            with backup.open("xb") as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
            if sha(backup.read_bytes()) != sha(original):
                raise SafetyError("Backup verification failed")
            entry = {"mod": row["mod"], "backup": backup_name,
                     "original_sha256": sha(original), "patched_sha256": sha(patched), "state": "pending"}
            ledger["entries"].append(entry)
            self._save(ledger)
            self.check_game()
            safe_path(self.root, target)
            if sha(target.read_bytes()) != entry["original_sha256"]:
                entry["state"] = "aborted_changed"
                self._save(ledger)
                result["skipped"].append({"mod": row["mod"], "reason": "changed_before_write"})
                continue
            try:
                atomic_write(target, patched)
                if sha(target.read_bytes()) != entry["patched_sha256"]:
                    raise SafetyError("Post-write verification failed")
            except Exception:
                if target.is_file() and sha(target.read_bytes()) == entry["patched_sha256"]:
                    atomic_write(target, original)
                raise
            entry["state"] = "patched"
            self._save(ledger)
            result["patched"].append({"mod": row["mod"], "path": str(target), "backup": str(backup)})
        return result

    def verify(self) -> dict:
        rows = self.scan("all", True)
        entries = []
        for entry in self._ledger()["entries"]:
            target = self._target(entry["mod"])
            if not target.is_file():
                current = "missing"
            else:
                digest = sha(target.read_bytes())
                current = ("patched" if digest == entry["patched_sha256"] else
                           "original" if digest == entry["original_sha256"] else "changed")
            entries.append({"mod": entry["mod"], "ledger_state": entry["state"], "current": current})
        return {"rows": rows, "ledger": entries,
                "unpatched_active": [r["mod"] for r in rows if r["enabled"] and r["state"] != "patched"]}

    def restore_plan(self) -> list[dict]:
        result = []
        for entry in reversed(self._ledger()["entries"]):
            if entry["state"] in ("restored", "aborted_changed"):
                continue
            target = self._target(entry["mod"])
            current = sha(target.read_bytes()) if target.is_file() else None
            result.append({"mod": entry["mod"], "path": str(target),
                           "backup": str(self._backup(entry["backup"])),
                           "action": "restore" if current == entry["patched_sha256"] else "skip_changed"})
        return result

    def restore(self) -> dict:
        self.check_game()
        ledger = self._ledger()
        results = []
        for entry in reversed(ledger["entries"]):
            if entry["state"] in ("restored", "aborted_changed"):
                continue
            self.check_game()
            target = self._target(entry["mod"])
            if not target.is_file():
                results.append({"mod": entry["mod"], "result": "missing_left_alone"})
                continue
            current = sha(target.read_bytes())
            if current == entry["original_sha256"]:
                entry["state"] = "restored"
                self._save(ledger)
                results.append({"mod": entry["mod"], "result": "already_original"})
                continue
            if current != entry["patched_sha256"]:
                results.append({"mod": entry["mod"], "result": "changed_left_alone"})
                continue
            backup = self._backup(entry["backup"])
            if not backup.is_file():
                results.append({"mod": entry["mod"], "result": "backup_missing_left_alone"})
                continue
            original = backup.read_bytes()
            if sha(original) != entry["original_sha256"]:
                results.append({"mod": entry["mod"], "result": "backup_changed_left_alone"})
                continue
            self.check_game()
            if sha(target.read_bytes()) != entry["patched_sha256"]:
                results.append({"mod": entry["mod"], "result": "changed_before_restore"})
                continue
            atomic_write(target, original)
            if sha(target.read_bytes()) != entry["original_sha256"]:
                raise SafetyError("Restore verification failed")
            entry["state"] = "restored"
            self._save(ledger)
            results.append({"mod": entry["mod"], "result": "restored"})
        return {"results": results}
