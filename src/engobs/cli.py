from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from engobs.ai.claude import read_hook_session_id
from engobs.commands.ai_session import run_ai_session
from engobs.commands.doctor import run_doctor
from engobs.commands.install import run_install
from engobs.commands.snapshot import run_snapshot
from engobs.commands.uninstall import run_uninstall
from engobs.commands.verify import run_verify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engobs")
    parser.add_argument("--profile", dest="profile", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install")
    subparsers.add_parser("doctor")

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--trigger", default="manual")
    snapshot_parser.add_argument("--force", action="store_true")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("verify_command", nargs=argparse.REMAINDER)

    subparsers.add_parser("uninstall")

    ai_parser = subparsers.add_parser("ai-session")
    ai_subparsers = ai_parser.add_subparsers(dest="ai_command", required=True)
    for action in ("start", "end"):
        action_parser = ai_subparsers.add_parser(action)
        action_parser.add_argument("--tool", required=True)
        action_parser.add_argument("--session-id", help="defaults to the hook stdin JSON")
        action_parser.add_argument("--model")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cwd = Path.cwd()

    if args.command == "install":
        return run_install(cwd, profile=args.profile)
    if args.command == "doctor":
        return run_doctor(cwd, profile=args.profile)[0]
    if args.command == "snapshot":
        return run_snapshot(cwd, profile=args.profile, trigger=args.trigger, force=args.force)
    if args.command == "verify":
        command = [item for item in list(args.verify_command) if item != "--"]
        if not command:
            parser.error("engobs verify requires a command after --")
        return run_verify(cwd, profile=args.profile, command=command)
    if args.command == "uninstall":
        return run_uninstall(cwd, profile=args.profile)
    if args.command == "ai-session":
        return run_ai_session(
            cwd,
            profile=args.profile,
            action=args.ai_command,
            tool=args.tool,
            session_id=args.session_id or read_hook_session_id(sys.stdin) or "unknown",
            model=args.model,
        )
    parser.error(f"Unsupported command: {args.command}")
    return 2
