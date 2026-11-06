from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import Profile, SafetyError, discover_profiles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spectator Tooltip Fix companion patcher")
    parser.add_argument("command", nargs="?", choices=("scan", "patch", "verify", "restore"))
    parser.add_argument("--profile", type=Path, help="Profile directory containing mods/myth-mod-status.json")
    parser.add_argument("--mod-folder", help="Specific status-listed folder, such as local/MyMod")
    parser.add_argument("--scope", choices=("active", "all"), default="active")
    parser.add_argument("--include-subscribed", action="store_true", help="Opt in to subscribed mod files")
    parser.add_argument("--dry-run", action="store_true", help="Show patch/restore plan without writing")
    parser.add_argument("--state-dir", type=Path, help="Override LocalAppData state root")
    args = parser.parse_args(argv)
    if args.command is None:
        from .gui import run
        run()
        return 0
    try:
        if args.profile:
            root = args.profile
        else:
            profiles = discover_profiles()
            if len(profiles) == 1:
                root = profiles[0]
            elif not profiles:
                raise SafetyError("No profiles found; supply --profile")
            else:
                raise SafetyError("Multiple profiles found; supply --profile")
        profile = Profile(root, args.state_dir)
        if args.command == "scan":
            output = profile.plan(args.scope, args.include_subscribed, args.mod_folder)
        elif args.command == "verify":
            output = profile.verify()
        elif args.command == "patch":
            output = (profile.plan(args.scope, args.include_subscribed, args.mod_folder) if args.dry_run else
                      profile.patch(args.scope, args.include_subscribed, args.mod_folder))
        else:
            output = profile.restore_plan() if args.dry_run else profile.restore()
        print(json.dumps(output, indent=2))
        return 0
    except (SafetyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
