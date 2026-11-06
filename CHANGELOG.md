# Changelog

## 1.0.0-rc2 — 2026-11-06

- Replaced the bulky utility dashboard with a compact, guided, navy-and-gold Windows wizard.
- Start screen: **Run the Patch** and conditional **Restore Backup**. Second screen: **Active mods / All mods**, optional Workshop inclusion, and explicit confirmation.
- Automatically backup during patching and show only mods that actually contain the conflicting HUD XAML on the results screen; otherwise show **No conflicts.**
- Preserve automatic profile discovery, file integrity checks, tamper-safe restore, and command-line advanced functions.


## 1.0.0-rc1 — 2026-11-06

- Staged the public companion utility with profile discovery, local and subscribed scope controls, safe F1 patching, backup ledger, Verify, Restore, GUI, and CLI dry run.
- Added synthetic tests and a pinned, isolated Windows build recipe.
- Kept the full retail-based store package outside public source pending rights and release review.
- Hardened status and ledger validation, showed missing target files in Scan, and kept explicit-profile CLI runs from enumerating other profiles.
- Auto-select the most recently updated discovered Retold profile and perform a read-only Scan on GUI launch; actual edits still require confirmation.
- Recognized the earlier F1 patch signature as already applied to avoid double patching.
