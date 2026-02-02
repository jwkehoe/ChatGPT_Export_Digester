#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Project: ChatGPT Archive Digester
# Author: John Kehoe
# Created: 2026-01-24
# Version: 0.1.0
# Changelog:
#   - 0.1.0 (2026-01-24): initial setup
# MIT License
#
# Copyright (c) 2026 John Kehoe, Exotic Problems
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ----------------------------------------------------------------------------
"""Rename conversation folders using titles from conversation.md.

Scans conversation folders, slugifies the title, and renames the directory
to a readable title-based name. Emits rename and id-to-title maps for traceability.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def slugify_title(title: str, max_len: int = 120) -> Optional[str]:
    """Convert a title into a safe directory name."""
    cleaned = re.sub(r"\s+", " ", title.strip())
    cleaned = re.sub(r"[^A-Za-z0-9 ._-]", "_", cleaned)
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    if not cleaned:
        return None
    return cleaned[:max_len]


def parse_title(conversation_md: Path) -> Optional[str]:
    """Read the conversation title from conversation.md."""
    try:
        with conversation_md.open("r", encoding="utf-8") as fh:
            first_line = fh.readline().strip()
    except OSError:
        return None
    if first_line.startswith("# "):
        return first_line[2:].strip()
    return None


def parse_conversation_id(conversation_md: Path) -> Optional[str]:
    """Read the conversation id from conversation.md."""
    try:
        with conversation_md.open("r", encoding="utf-8") as fh:
            for _ in range(5):
                line = fh.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("- id: "):
                    return line.split("- id: ", 1)[1].strip()
    except OSError:
        return None
    return None


def find_conversation_files(root: Path) -> List[Path]:
    """Find all conversation.md files under the root."""
    return list(root.rglob("conversation.md"))


def unique_path(parent: Path, base_name: str) -> Path:
    """Return a unique path by suffixing if needed."""
    candidate = parent / base_name
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = parent / f"{base_name}_{index}"
        if not candidate.exists():
            return candidate
        index += 1


def rename_conversations(
    root: Path, dry_run: bool, include_id: bool
) -> List[Dict[str, str]]:
    """Rename conversation directories and return change records."""
    changes = []
    for md_path in find_conversation_files(root):
        conv_dir = md_path.parent
        title = parse_title(md_path)
        if not title:
            continue
        conversation_id = parse_conversation_id(md_path) or conv_dir.name
        slug = slugify_title(title)
        if not slug:
            continue
        if include_id:
            slug = f"{slug}__{conv_dir.name}"
        target = unique_path(conv_dir.parent, slug)
        if target == conv_dir:
            continue
        changes.append(
            {
                "from": str(conv_dir),
                "to": str(target),
                "title": title,
                "conversation_id": conversation_id,
            }
        )
        if not dry_run:
            conv_dir.rename(target)
    return changes


EPILOG_TEXT = """Detailed option reference and reasons:
- `--root`: starting point for the scan; defaults to `ChatGPT_Digested/conversations` so you can work from the standard output of the digester.
- `--dry-run`: gathers proposed renames without touching the filesystem, useful to preview collisions or slug results before committing.
- `--include-id`: appends `__<original_id>` to the slugified title so multiple conversations with the same title stay unique; slugification replaces unsafe characters and truncates at 120 chars.
- `--map-path` / `--id-title-path`: controls where the rename map and ID→title map are emitted (default files sit under `ChatGPT_Digested` to keep them near the renamed folders).
- `--no-map` / `--no-id-title`: skip writing the corresponding JSON artifacts if you don't need the audit trail.

Reason & what it does:
The renamer reads each `conversation.md`, slugifies the title into a filesystem-safe name, optionally appends the original ID, and moves the directory (unless `--dry-run`). Rename maps and ID→title maps are published so you can trace what changed.

Examples:
  # rename every conversation folder under the default digested output
  python3 rename_conversation_dirs.py

  # preview changes without renaming
  python3 rename_conversation_dirs.py --dry-run

  # include source ID in the slug to avoid multi-title collisions
  python3 rename_conversation_dirs.py --include-id --map-path ~/maps/rename_map.json
"""


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Rename conversation directories using conversation titles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG_TEXT,
    )
    parser.add_argument(
        "--root",
        default="ChatGPT_Digested/conversations",
        help="Root conversations directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without renaming",
    )
    parser.add_argument(
        "--include-id",
        action="store_true",
        help="Append the original directory name to avoid collisions",
    )
    parser.add_argument(
        "--map-path",
        default="ChatGPT_Digested/rename_map.json",
        help="Path to write rename mapping JSON",
    )
    parser.add_argument(
        "--id-title-path",
        default="ChatGPT_Digested/id_title_map.json",
        help="Path to write conversation id to title JSON",
    )
    parser.add_argument(
        "--no-map",
        action="store_true",
        help="Do not write the rename mapping JSON",
    )
    parser.add_argument(
        "--no-id-title",
        action="store_true",
        help="Do not write the id to title JSON map",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    """CLI entry point."""
    if not argv:
        print(
            "No options provided; here is the renamer option reference and what it does:\n"
        )
        print(EPILOG_TEXT)
        return 0
    args = parse_args(argv)
    root = Path(args.root).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Root not found: {root}")
    changes = rename_conversations(root, args.dry_run, args.include_id)
    if not args.no_map:
        map_path = Path(args.map_path).expanduser()
        map_path.parent.mkdir(parents=True, exist_ok=True)
        with map_path.open("w", encoding="utf-8") as fh:
            json.dump(changes, fh, indent=2, ensure_ascii=True)
    if not args.no_id_title:
        id_title_path = Path(args.id_title_path).expanduser()
        id_title_path.parent.mkdir(parents=True, exist_ok=True)
        id_title = {}
        for entry in changes:
            conv_id = entry.get("conversation_id")
            title = entry.get("title")
            if conv_id and title:
                id_title[conv_id] = title
        with id_title_path.open("w", encoding="utf-8") as fh:
            json.dump(id_title, fh, indent=2, ensure_ascii=True)
    print(f"Renamed {len(changes)} conversation folders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(os.sys.argv[1:]))
