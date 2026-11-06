# Separate release QA checklist

Status: **Windows compatibility executable published as 1.0.0-rc1; compact guided 1.0.0-rc2 prepared for prerelease after verification**. **Stable release and in-game Mods Store publication remain on HOLD** pending the checks below.

## Source and artifact review

- [x] MIT for original source and documentation, copyright mhen125; game and third-party materials are excluded. Confirm no game, third-party, profile, or research-only content in tracked files or release ZIP.
- [x] Built in project-local Python 3.14.3 / PyInstaller 6.22.3 environment from commit `3fa8239e6b611a6dd55028c9c88dea0effff48ea`; EXE SHA-256 `3F61C2F26367D47ACB459C5A422C748F6B649F68B07819A0473FC85F5D3BAC89`; ZIP SHA-256 `CFB4457C936B40A71F1142A24C436EFDA4F1DDBB0D1831D6EDC429779E5605B4`. HPZ820 GUI launch/close PASS; separate clean-machine smoke test still pending.
- [x] 16 synthetic tests run, 15 passed and 1 skipped (symlink creation unavailable), 0 failures; Windows GUI auto-detected the most-recent of two Retold profiles and auto-scanned without modifying the status files. **Still pending:** symlink/junction test under appropriate test permissions, second-machine GUI test, unsigned SmartScreen/antivirus review.
- [ ] Check GUI keyboard access, long-path display, confirmation lists, state directory, and failure messages.

## Store package

- [ ] Review rights to redistribute the full retail-based `HUD_MouseResources.xaml`; get any required permission. Keep it only in ignored private staging until approved.
- [ ] Rebuild against the intended current Retold game build and record base/patched hashes; confirm F1 is the only XAML delta, XML parses, and the game loads it.
- [ ] Set store title, version, description, and image to final reviewed values. Use the user's later screenshot after checking identifiers and rights.
- [ ] Test install, disable, uninstall, and load priority through the game mod manager. Do not ship the old research candidate as-is.

## In-game behavior

- [ ] With replay panel collapsed, hover train, technology, rally, ability, stance, and dimmed icons across 1v1 and larger replays. Check expanded panel controls remain usable.
- [ ] Test a live skirmish for unchanged hover, left click, right click, and auto-queue behavior.
- [ ] Test replay click safety, including cancel and selection paths of the age-up minor-god picker. Record whether any popup action changes simulation, replay file, or out-of-sync logs.
- [ ] Test the store mod alone and companion-patched copies of representative UI mods. Check updates replace patches safely and Verify reports them.
- [ ] Capture game build, mod list and priorities, log errors, screenshots, and exact file hashes without publishing private identifiers.

The GitHub prerelease contains only the open-source Windows patcher and documentation, not retail XAML. A stable binary and in-game store mod remain separate release decisions; do not distribute retail game XAML through GitHub.
