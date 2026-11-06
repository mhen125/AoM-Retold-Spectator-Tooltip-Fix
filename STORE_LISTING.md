# Proposed in-game store listing

**Title:** Spectator Tooltip Fix

**Short description:** Restores command-panel hover tooltips during recorded-game playback when the replay panel is collapsed.

**Description:** Collapse the replay panel during a replay to hover command-grid icons for their normal tooltips, including train, technology, and rally icons. The fix changes the collapsed replay panel's mouse hit testing. It does not add or change game commands. The game loads this as a full `HUD_MouseResources.xaml` replacement, so another UI mod replacing the same file can override it. For compatibility with another mod that supplies that file, use the separate Spectator Tooltip Patcher companion utility from the public source repository after reviewing its backups and warnings. Retold updates may require a rebuilt store package.

**Installation:** Subscribe and enable in the in-game mod manager, then restart Retold. No executable modification is needed.

**Removal:** Disable or unsubscribe in the in-game mod manager. If the companion utility was used, run its Verify and Restore actions separately for any mod files it changed.

**Media:** Pending user-provided screenshot. Do not substitute research screenshots or screenshots containing profile identifiers.

**Compatibility note:** Full-file UI replacement; check load order when using other HUD mods. The store package is pending rights and build-specific QA.
