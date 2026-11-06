# Spectator Tooltip Fix

This repository contains the source for the **1.0.0-rc2 compatibility patcher**. The compact guided Windows executable is available in the [GitHub prerelease](https://github.com/mhen125/AoM-Retold-Spectator-Tooltip-Fix/releases/tag/v1.0.0-rc2). The **in-game mod is not yet published**; the executable only patches HUD files supplied by other installed mods. Public source is provided for review and testing.

Spectator Tooltip Fix restores hover tooltips on command-grid icons during Age of Mythology: Retold replay playback when the replay panel is collapsed. The confirmed F1 change makes that collapsed panel stop catching the mouse. It does not change command bindings or gameplay. The public source contains only the companion patcher and synthetic fixtures; it contains no retail or third-party HUD XAML.

## Two parts

1. **In-game store mod:** install and enable **Spectator Tooltip Fix** through the game's mod manager once its separate package has passed rights and release review. The game replaces the entire `HUD_MouseResources.xaml` resource for a mod, so this package needs a build-specific full file and may conflict with other UI mods.
2. **Companion utility:** `SpectatorTooltipPatcher.exe` patches the one F1 anchor in status-listed mod copies of `HUD_MouseResources.xaml`. Use it when another installed UI mod supplies that file. It never installs the store mod, edits the game executable or game install, or writes `myth-mod-status.json`.

The companion cannot fix the retail file by itself. If no enabled mod supplies the target XAML, use the store mod. A mod update can overwrite a companion patch; use **Verify** afterward and patch again only after reviewing compatibility. Scan also shows status-listed mods whose target file is missing.

## Windows use

Close Retold and launch `SpectatorTooltipPatcher.exe`. The compact wizard automatically finds your game profile; no paths or manual scanning are required. Choose **Run the Patch**, select **Active mods** (recommended) or **All mods**, optionally include subscribed Workshop mods, and press **Confirm & Run Patch**. Originals are automatically backed up before writing. The result screen shows only other installed mods containing `HUD_MouseResources.xaml`, with clear per-mod outcomes, or **No conflicts.** when none are found. Choose **Restore Backup** on the first screen whenever a valid patcher backup can be restored. The GUI is intentionally compact and hides advanced file paths; the CLI retains detailed Scan/Verify and dry-run commands.

Subscribed mods are excluded by default. Check **Include subscribed mods** to opt in; their updates may replace patched files. The game must be closed for Patch and Restore. If process detection fails, writes are refused. Scan, Verify, and the CLI dry run are read-only. The utility does not request elevation or update itself.

Backups and a per-profile ledger live under `%LOCALAPPDATA%\SpectatorTooltipPatcher\<profile-hash>`. Keep that folder until you no longer need to restore. A missing or changed mod file is left alone. If an operation is interrupted, the ledger records a pending entry and Verify reports the current hash state; Restore can finish when the file still matches the recorded patched hash.

## CLI from source

Python 3.11+ with Tkinter is required. From this directory:

```powershell
python -m spectator_tooltip_patcher scan --profile "<profile folder>" --scope all
python -m spectator_tooltip_patcher patch --profile "<profile folder>" --scope active --dry-run
python -m spectator_tooltip_patcher patch --profile "<profile folder>" --scope active
python -m spectator_tooltip_patcher verify --profile "<profile folder>"
python -m spectator_tooltip_patcher restore --profile "<profile folder>" --dry-run
```

The GUI automatically chooses the most recently updated profile when multiple profiles are detected. For CLI commands, omit `--profile` only if exactly one profile is discovered under `%USERPROFILE%\Games\Age of Mythology Retold\*\mods\myth-mod-status.json`; CLI writes require an explicit profile when multiple are present. Use `--mod-folder local/Name` to select one status-listed folder and `--include-subscribed` for subscribed copies. `--state-dir` is for isolated testing or portable state; retain its contents for Restore. The executable is a GUI build; CLI use is through Python source.

Restore checks every recorded patch for the selected profile, regardless of the optional mod-folder filter. The first screen offers **Restore Backup** only when a matching, verified backup exists; changed files are left alone.

## Compatibility and limits

The patcher changes only the existing replay-panel F1 anchor: `Style="{StaticResource CommandPanel}"` becomes an inline style whose `ReplayCommandPanel.IsCollapsed=True` trigger sets `IsHitTestVisible=False`. It requires exactly one anchor and well-formed UTF-8 XML. It recognizes earlier F1 builds as already patched. It preserves the original BOM choice and newline style, and skips files with no anchor, multiple anchors, mixed newlines, invalid UTF-8, or invalid XML. It never forces a best-effort rewrite. Other UI changes within the same XAML are kept byte-for-byte except that block.

The research build confirmed hover tooltips for train, rally, military unit, and age-up technology icons in replay; broader icon and game-build coverage remains a release QA item. In a replay, clicking the age-up icon opened a local minor-god picker; choosing a god there was not tested. The companion utility does not add a click blocker. Live games were observed unchanged in the research session. See [release QA](RELEASE_QA.md) before public release.

## Build and tests

Run `python -m unittest discover -s tests -v`. The project-local Windows build script is [scripts/build.ps1](scripts/build.ps1); run it with `powershell -File scripts/build.ps1` or pass `-Python` with a Python 3.11+ executable path. It installs pinned build packages in `.build-venv` and creates a GUI `.exe` and ZIP under ignored `dist/`. Build temp and caches also stay inside this directory. Windows builds should be smoke-tested on a clean Windows machine. The build does not bundle any game XAML.

The private, Git-ignored `private_stage/store_upload/Spectator Tooltip Fix` directory holds the separately staged game-derived mod package. It must never be included in public GitHub source or patcher EXE. Direct website distribution remains subject to the game-content redistribution review.

## Rights

The original patcher source code and documentation in this repository are licensed under the [MIT License](LICENSE). This license does **not** grant rights to Age of Mythology: Retold files, UI XAML, third-party mods, game artwork, screenshots, or trademarks. Those remain under their respective owners' terms and are excluded from this source repository. The in-game store package is separate.
