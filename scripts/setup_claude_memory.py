#!/usr/bin/env python3
"""
Setup Claude Code project memory for this project.

Copies .claude/memory/ files to the correct Claude Code memory directory on
the current machine. Works on macOS, Linux, and Windows.

Usage:
    python scripts/setup_claude_memory.py           # install memory → Claude
    python scripts/setup_claude_memory.py --sync-back  # pull live memory → repo

After cloning on a new machine, run once:
    python scripts/setup_claude_memory.py
"""

import argparse
import shutil
import sys
from pathlib import Path


def get_claude_home() -> Path:
    """Return Claude Code's config home directory for the current platform."""
    if sys.platform == "win32":
        # Claude Code on Windows uses %APPDATA%\Claude
        import os
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidate = Path(appdata) / "Claude"
            if candidate.exists():
                return candidate
        # Fallback to ~/.claude (WSL-style or older installs)
        return Path.home() / ".claude"
    else:
        # macOS and Linux
        return Path.home() / ".claude"


def project_path_to_dir_name(project_root: Path) -> str:
    """
    Convert an absolute project path to Claude Code's directory naming convention.

    Claude encodes the project path by replacing path separators with '-':
      /Users/alice/myproject  →  -Users-alice-myproject
      C:\\Users\\alice\\proj  →  C-Users-alice-proj  (Windows)
    """
    path_str = str(project_root.resolve())

    if sys.platform == "win32":
        # Normalize backslashes and strip the drive colon (C: → C)
        path_str = path_str.replace("\\", "/").replace(":", "")

    # Replace '/' and '_' with '-'  (the leading '/' becomes a leading '-')
    return path_str.replace("/", "-").replace("_", "-")


def get_target_memory_dir(project_root: Path) -> Path:
    claude_home = get_claude_home()
    dir_name = project_path_to_dir_name(project_root)
    return claude_home / "projects" / dir_name / "memory"


def install(project_root: Path) -> None:
    """Copy .claude/memory/ from the repo → Claude's memory directory."""
    source_dir = project_root / ".claude" / "memory"
    if not source_dir.exists():
        print(f"Error: {source_dir} not found. Nothing to install.")
        sys.exit(1)

    target_dir = get_target_memory_dir(project_root)
    target_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(source_dir.glob("*.md"))
    if not files:
        print("No .md files found in .claude/memory/ — nothing to install.")
        sys.exit(1)

    print(f"Installing Claude memory files to:\n  {target_dir}\n")
    for f in files:
        dest = target_dir / f.name
        shutil.copy2(f, dest)
        print(f"  Copied: {f.name}")

    print(f"\nDone. {len(files)} file(s) installed.")
    print("Claude Code will pick them up automatically in the next conversation.")


def sync_back(project_root: Path) -> None:
    """Copy live Claude memory → .claude/memory/ in the repo (to commit updates)."""
    source_dir = get_target_memory_dir(project_root)
    if not source_dir.exists():
        print(f"Error: Claude memory directory not found:\n  {source_dir}")
        sys.exit(1)

    target_dir = project_root / ".claude" / "memory"
    target_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(source_dir.glob("*.md"))
    if not files:
        print("No .md files found in Claude memory directory.")
        sys.exit(1)

    print(f"Syncing Claude memory files to repo:\n  {target_dir}\n")
    for f in files:
        dest = target_dir / f.name
        shutil.copy2(f, dest)
        print(f"  Copied: {f.name}")

    print(f"\nDone. {len(files)} file(s) synced.")
    print("Review changes with `git diff .claude/memory/` then commit.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--sync-back",
        action="store_true",
        help="Pull live Claude memory back into the repo (for committing updates)",
    )
    args = parser.parse_args()

    # Project root is one directory up from this script
    project_root = Path(__file__).resolve().parent.parent

    print(f"Project root: {project_root}")
    print(f"Claude home:  {get_claude_home()}")
    print()

    if args.sync_back:
        sync_back(project_root)
    else:
        install(project_root)


if __name__ == "__main__":
    main()
