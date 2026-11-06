# Separate release QA checklist

Status: **HOLD for executable and in-game mod release**. The public source repository is for review; the store upload package and executable distribution still require the checks below.

## Source and artifact review

- [x] MIT for original source and documentation, copyright mhen125; game and third-party materials are excluded. Confirm no game, third-party, profile, or research-only content in tracked files or release ZIP.
- [ ] Build from a fresh project-local environment; record Python/PyInstaller versions, exact source commit, EXE and ZIP SHA-256, and clean Windows smoke-test result.
- [ ] Repeat synthetic tests, including a Windows account with permitted symlink/junction creation. Review antivirus and SmartScreen behavior for an unsigned build.
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

Source publication is separate from the release gates above. This checklist does not authorize uploading a Windows binary, distributing retail XAML, or publishing the in-game store mod.
