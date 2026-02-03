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
# Disclaimer: provided "AS-IS"; use at your own risk and no responsibility is accepted for unintended outcomes.
"""ChatGPT export digester.

Ingests one or more ChatGPT export zip files, normalizes conversations into
human-readable transcripts, and copies referenced assets into per-conversation
folders. Supports merging overlapping exports into consolidated conversations,
and always emits unresolved asset reports.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_ASSET_STRATEGY = "copy_per_conversation"


def load_json_from_zip(zf: zipfile.ZipFile, name: str) -> Any:
    """Load JSON data from a file within a zip archive."""
    with zf.open(name) as fh:
        return json.load(fh)


def slugify(value: str) -> str:
    """Normalize a string into a filesystem-friendly slug."""
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value or "archive"


def find_zip_inputs(inputs: List[str], input_dir: Optional[str]) -> List[str]:
    """Resolve zip inputs from explicit paths and/or a directory."""
    zips = []
    for path in inputs or []:
        if os.path.isfile(path) and path.lower().endswith(".zip"):
            zips.append(path)
        else:
            raise FileNotFoundError(f"Input zip not found: {path}")
    if input_dir:
        if not os.path.isdir(input_dir):
            raise NotADirectoryError(f"Input dir not found: {input_dir}")
        for name in sorted(os.listdir(input_dir)):
            if name.lower().endswith(".zip"):
                zips.append(os.path.join(input_dir, name))
    if not zips:
        raise ValueError("No input zip files found.")
    return zips


def extract_asset_prefix(basename: str) -> Optional[str]:
    """Extract an asset id prefix from a filename."""
    match = re.match(r"^(file-[A-Za-z0-9]+)", basename)
    if match:
        return match.group(1)
    match = re.match(r"^(file_[A-Za-z0-9]+)", basename)
    if match:
        return match.group(1)
    return None


def build_zip_index(zf: zipfile.ZipFile) -> Dict[str, List[str]]:
    """Index files in a zip by basename and asset prefixes."""
    index: Dict[str, List[str]] = {}
    for path in zf.namelist():
        if path.endswith("/"):
            continue
        basename = os.path.basename(path)
        index.setdefault(basename, []).append(path)
        prefix = extract_asset_prefix(basename)
        if prefix:
            index.setdefault(prefix, []).append(path)
            if basename.startswith(prefix + "-"):
                remainder = basename[len(prefix) + 1 :]
                if remainder:
                    index.setdefault(remainder, []).append(path)
    return index


def build_global_index(
    zip_paths: List[str], stats: Dict[str, int]
) -> Tuple[Dict[str, List[Tuple[str, str]]], List[str]]:
    """Build a cross-archive asset index and list of valid zips."""
    global_index: Dict[str, List[Tuple[str, str]]] = {}
    good_zips: List[str] = []
    for zip_path in zip_paths:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                local_index = build_zip_index(zf)
                for key, paths in local_index.items():
                    for path in paths:
                        global_index.setdefault(key, []).append((zip_path, path))
            good_zips.append(zip_path)
        except zipfile.BadZipFile:
            stats["bad_archives"] += 1
            print(f"Skipping bad zip: {zip_path}", file=sys.stderr)
    return global_index, good_zips


def normalize_asset_ref(ref: str) -> str:
    """Normalize asset reference URIs to plain ids or filenames."""
    if ref.startswith("sediment://"):
        return ref.split("sediment://", 1)[1]
    if ref.startswith("file:"):
        return ref.split("file:", 1)[1]
    return ref


def resolve_asset(ref: str, index: Dict[str, List[str]]) -> Optional[str]:
    """Resolve an asset reference within a single zip index."""
    if not ref:
        return None
    normalized = normalize_asset_ref(ref)
    candidates = index.get(normalized)
    if candidates:
        return candidates[0]
    basename = os.path.basename(normalized)
    candidates = index.get(basename)
    if candidates:
        return candidates[0]
    return None


def resolve_asset_global(
    ref: str, index: Dict[str, List[Tuple[str, str]]]
) -> Optional[Tuple[str, str]]:
    """Resolve an asset reference using the global index."""
    if not ref:
        return None
    normalized = normalize_asset_ref(ref)
    candidates = index.get(normalized)
    if candidates:
        return candidates[0]
    basename = os.path.basename(normalized)
    candidates = index.get(basename)
    if candidates:
        return candidates[0]
    return None


class ZipCache:
    """Cache opened ZipFile handles for reuse."""
    def __init__(self) -> None:
        self._cache: Dict[str, zipfile.ZipFile] = {}

    def get(self, zip_path: str) -> zipfile.ZipFile:
        """Return an open ZipFile for a path, caching it."""
        if zip_path not in self._cache:
            self._cache[zip_path] = zipfile.ZipFile(zip_path)
        return self._cache[zip_path]

    def close(self) -> None:
        """Close all cached ZipFile handles."""
        for zf in self._cache.values():
            zf.close()
        self._cache.clear()


def collect_asset_refs(message: Dict[str, Any]) -> List[str]:
    """Collect asset references from message metadata and content."""
    refs: List[str] = []
    metadata = message.get("metadata")
    if isinstance(metadata, dict):
        attachments = metadata.get("attachments")
        if isinstance(attachments, list):
            for att in attachments:
                if isinstance(att, dict):
                    if isinstance(att.get("id"), str):
                        refs.append(att["id"])
                    if isinstance(att.get("name"), str):
                        refs.append(att["name"])
    content = message.get("content")
    if isinstance(content, dict):
        content_type = content.get("content_type")
        if content_type == "multimodal_text":
            parts = content.get("parts")
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict):
                        if isinstance(part.get("asset_pointer"), str):
                            refs.append(part["asset_pointer"])
                        if isinstance(part.get("video_container_asset_pointer"), str):
                            refs.append(part["video_container_asset_pointer"])
                        if isinstance(part.get("frames_asset_pointers"), list):
                            for item in part["frames_asset_pointers"]:
                                if isinstance(item, str):
                                    refs.append(item)
                        audio_asset = part.get("audio_asset_pointer")
                        if isinstance(audio_asset, dict):
                            if isinstance(audio_asset.get("asset_pointer"), str):
                                refs.append(audio_asset["asset_pointer"])
        if content_type == "computer_output":
            screenshot = content.get("screenshot")
            if isinstance(screenshot, dict):
                if isinstance(screenshot.get("asset_pointer"), str):
                    refs.append(screenshot["asset_pointer"])
    return refs


def select_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract a lightweight metadata subset for outputs."""
    if not isinstance(metadata, dict):
        return {}
    keep = [
        "attachments",
        "content_references",
        "content_references_by_file",
        "canvas",
        "citations",
        "command",
    ]
    out = {}
    for key in keep:
        if key in metadata:
            out[key] = metadata[key]
    return out


def normalize_content(
    content: Optional[Dict[str, Any]]
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """Normalize content into type, text, and metadata."""
    if not isinstance(content, dict):
        return ("unknown", None, {"raw_content": content})
    ctype = content.get("content_type", "unknown")
    text = None
    meta: Dict[str, Any] = {}

    if ctype == "text":
        parts = content.get("parts")
        if isinstance(parts, list):
            text = "".join([p for p in parts if isinstance(p, str)])
    elif ctype == "multimodal_text":
        parts = content.get("parts")
        text_chunks: List[str] = []
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, str):
                    text_chunks.append(part)
                elif isinstance(part, dict):
                    if isinstance(part.get("text"), str):
                        text_chunks.append(part["text"])
        text = "".join(text_chunks) if text_chunks else None
    elif ctype == "code":
        text = content.get("text")
        meta["language"] = content.get("language")
    elif ctype == "execution_output":
        text = content.get("text")
    elif ctype == "reasoning_recap":
        text = content.get("content")
    elif ctype == "tether_quote":
        text = content.get("text")
        meta["title"] = content.get("title")
        meta["url"] = content.get("url")
    elif ctype == "tether_browsing_display":
        text = content.get("summary") or content.get("result")
    elif ctype == "user_editable_context":
        text = content.get("user_instructions")
        meta["user_profile"] = content.get("user_profile")
    elif ctype == "system_error":
        text = content.get("text")
        meta["name"] = content.get("name")
    elif ctype == "computer_output":
        text = "[computer_output]"
    elif ctype == "thoughts":
        meta["thoughts"] = content.get("thoughts")
        text = None
    else:
        text = content.get("text") if isinstance(content.get("text"), str) else None
        meta["raw_content"] = content

    return (ctype, text, meta)


def normalize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw message into a digest-friendly dict."""
    author = message.get("author") if isinstance(message.get("author"), dict) else {}
    role = author.get("role")
    author_name = author.get("name")
    content_type, text, content_meta = normalize_content(message.get("content"))
    metadata = select_metadata(message.get("metadata"))
    if content_meta:
        metadata = {**metadata, **content_meta}
    asset_refs = collect_asset_refs(message)

    return {
        "role": role,
        "author_name": author_name,
        "timestamp": message.get("create_time"),
        "content_type": content_type,
        "text": text,
        "metadata": metadata,
        "asset_refs": asset_refs,
    }


def message_fingerprint(message: Dict[str, Any], normalized: Dict[str, Any]) -> str:
    """Build a stable id for deduping messages."""
    msg_id = message.get("id")
    if isinstance(msg_id, str) and msg_id:
        return f"id:{msg_id}"
    payload = {
        "role": normalized.get("role"),
        "author_name": normalized.get("author_name"),
        "timestamp": normalized.get("timestamp"),
        "content_type": normalized.get("content_type"),
        "text": normalized.get("text"),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return "hash:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def merge_normalized_message(base: Dict[str, Any], new: Dict[str, Any]) -> None:
    """Merge fields and asset refs from another message."""
    for key in ["role", "author_name", "timestamp", "content_type", "text"]:
        if base.get(key) in (None, "", []):
            if new.get(key) not in (None, "", []):
                base[key] = new[key]

    base_meta = base.get("metadata") or {}
    new_meta = new.get("metadata") or {}
    for key, value in new_meta.items():
        if key not in base_meta or base_meta[key] in (None, "", [], {}):
            base_meta[key] = value
    base["metadata"] = base_meta

    base_refs = base.get("asset_refs") or []
    seen = {ref for ref in base_refs if isinstance(ref, str)}
    for ref in new.get("asset_refs") or []:
        if isinstance(ref, str) and ref not in seen:
            base_refs.append(ref)
            seen.add(ref)
    base["asset_refs"] = base_refs

    if new.get("order") is not None:
        base["order"] = min(base.get("order", new["order"]), new["order"])


def linearize_active_path(mapping: Dict[str, Any], current_node: Optional[str]) -> List[str]:
    """Walk parent pointers from current node to root."""
    path: List[str] = []
    node_id = current_node
    seen = set()
    while node_id and node_id in mapping and node_id not in seen:
        seen.add(node_id)
        path.append(node_id)
        node = mapping.get(node_id, {})
        node_id = node.get("parent")
    path.reverse()
    return path


def linearize_all_nodes(mapping: Dict[str, Any]) -> List[str]:
    """Linearize all message nodes by timestamp then id."""
    nodes = []
    for node_id, node in mapping.items():
        msg = node.get("message") if isinstance(node, dict) else None
        if isinstance(msg, dict):
            nodes.append((node_id, msg.get("create_time") or 0))
    nodes.sort(key=lambda item: (item[1], item[0]))
    return [node_id for node_id, _ in nodes]


def message_sort_key(message: Dict[str, Any]) -> Tuple[float, int, str]:
    """Return a stable sort key for merged messages."""
    ts = message.get("timestamp")
    ts_key = ts if isinstance(ts, (int, float)) else float("inf")
    order = message.get("order", 0)
    node_id = message.get("node_id") or ""
    return (ts_key, order, node_id)


def ensure_dir(path: str) -> None:
    """Create a directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def write_jsonl(path: str, items: Iterable[Dict[str, Any]]) -> None:
    """Write an iterable of dicts as JSONL."""
    with open(path, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=True) + "\n")


def write_json(path: str, data: Any) -> None:
    """Write JSON to disk with indentation."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=True)


def format_timestamp(ts: Optional[float]) -> str:
    """Format epoch seconds as a UTC ISO string."""
    if not ts:
        return "unknown"
    try:
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    except (ValueError, OSError):
        return "unknown"


def render_message_markdown(message: Dict[str, Any]) -> str:
    """Render a normalized message into Markdown."""
    role = (message.get("role") or "unknown").upper()
    timestamp = format_timestamp(message.get("timestamp"))
    header = f"[{message.get('seq')}] {role} ({timestamp})"
    content_type = message.get("content_type")
    text = message.get("text") or ""
    assets = message.get("assets") or []

    if content_type == "code":
        lang = message.get("metadata", {}).get("language") or ""
        body = f"```{lang}\n{text}\n```" if text else "```\n```"
    elif content_type == "execution_output":
        body = f"```output\n{text}\n```" if text else "```output\n```"
    else:
        body = text if text else f"[{content_type}]"

    asset_lines = ""
    if assets:
        lines = []
        for item in assets:
            if isinstance(item, dict):
                lines.append(f"- {item.get('path', item.get('ref', 'unknown'))}")
            else:
                lines.append(f"- {item}")
        asset_lines = "\n\nAssets:\n" + "\n".join(lines)

    return f"{header}\n{body}{asset_lines}\n"


def write_unresolved_report(output_root: str) -> None:
    """Write unresolved asset report and summary files."""
    conv_root = os.path.join(output_root, "conversations")
    report_path = os.path.join(output_root, "unresolved_assets_report.jsonl")
    summary_path = os.path.join(output_root, "unresolved_assets_summary.json")
    entries = 0
    conv_counts: Dict[str, int] = {}
    archive_counts: Dict[str, int] = {}
    role_counts: Dict[str, int] = {}
    content_counts: Dict[str, int] = {}

    with open(report_path, "w", encoding="utf-8") as out:
        for dirpath, _, filenames in os.walk(conv_root):
            for name in filenames:
                if name != "messages.jsonl":
                    continue
                msg_path = os.path.join(dirpath, name)
                conv_id = os.path.basename(os.path.dirname(msg_path))
                parent_dir = os.path.dirname(os.path.dirname(msg_path))
                archive = None
                if os.path.basename(parent_dir) != "conversations":
                    archive = os.path.basename(parent_dir)
                with open(msg_path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        msg = json.loads(line)
                        assets = msg.get("assets") or []
                        for asset in assets:
                            if (
                                isinstance(asset, dict)
                                and asset.get("status") == "unresolved"
                            ):
                                entry = {
                                    "conversation_id": conv_id,
                                    "archive": archive,
                                    "seq": msg.get("seq"),
                                    "node_id": msg.get("node_id"),
                                    "role": msg.get("role"),
                                    "content_type": msg.get("content_type"),
                                    "ref": asset.get("ref"),
                                    "text_snippet": (msg.get("text") or "")[:160],
                                }
                                out.write(json.dumps(entry, ensure_ascii=True) + "\n")
                                entries += 1
                                conv_counts[conv_id] = conv_counts.get(conv_id, 0) + 1
                                if archive:
                                    archive_counts[archive] = (
                                        archive_counts.get(archive, 0) + 1
                                    )
                                role = msg.get("role")
                                if role:
                                    role_counts[role] = role_counts.get(role, 0) + 1
                                content_type = msg.get("content_type")
                                if content_type:
                                    content_counts[content_type] = (
                                        content_counts.get(content_type, 0) + 1
                                    )

    summary = {
        "total_unresolved": entries,
        "conversations_with_unresolved": len(conv_counts),
        "archives": sorted(
            archive_counts.items(), key=lambda item: item[1], reverse=True
        ),
        "roles": sorted(role_counts.items(), key=lambda item: item[1], reverse=True),
        "content_types": sorted(
            content_counts.items(), key=lambda item: item[1], reverse=True
        ),
        "top_conversations": sorted(
            conv_counts.items(), key=lambda item: item[1], reverse=True
        )[:50],
    }
    write_json(summary_path, summary)


def copy_assets_local(
    zf: zipfile.ZipFile,
    index: Dict[str, List[str]],
    asset_refs: List[str],
    assets_dir: str,
    asset_name_counts: Dict[str, int],
    asset_cache: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Resolve and copy assets from a single zip archive."""
    resolved_assets = []
    assets_manifest = []

    for ref in asset_refs:
        zip_path = resolve_asset(ref, index)
        if zip_path:
            if zip_path in asset_cache:
                rel_path = asset_cache[zip_path]
                entry = {
                    "ref": ref,
                    "path": rel_path,
                    "status": "resolved",
                    "zip_path": zip_path,
                }
            else:
                base_name = os.path.basename(zip_path)
                count = asset_name_counts.get(base_name, 0)
                asset_name_counts[base_name] = count + 1
                target_name = base_name if count == 0 else f"{count}_{base_name}"
                target_path = os.path.join(assets_dir, target_name)
                with zf.open(zip_path) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                rel_path = os.path.join("assets", target_name)
                asset_cache[zip_path] = rel_path
                entry = {
                    "ref": ref,
                    "path": rel_path,
                    "status": "resolved",
                    "zip_path": zip_path,
                }
        else:
            entry = {"ref": ref, "status": "unresolved"}
        resolved_assets.append(entry)
        assets_manifest.append(entry)

    return resolved_assets, assets_manifest


def copy_assets_global(
    asset_refs: List[str],
    global_index: Dict[str, List[Tuple[str, str]]],
    zip_cache: ZipCache,
    assets_dir: str,
    asset_name_counts: Dict[str, int],
    asset_cache: Dict[Tuple[str, str], str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Resolve and copy assets across multiple zip archives."""
    resolved_assets = []
    assets_manifest = []

    for ref in asset_refs:
        resolved = resolve_asset_global(ref, global_index)
        if resolved:
            zip_file, zip_path = resolved
            cache_key = (zip_file, zip_path)
            if cache_key in asset_cache:
                rel_path = asset_cache[cache_key]
                entry = {
                    "ref": ref,
                    "path": rel_path,
                    "status": "resolved",
                    "zip_file": zip_file,
                    "zip_path": zip_path,
                }
            else:
                base_name = os.path.basename(zip_path)
                count = asset_name_counts.get(base_name, 0)
                asset_name_counts[base_name] = count + 1
                target_name = base_name if count == 0 else f"{count}_{base_name}"
                target_path = os.path.join(assets_dir, target_name)
                zf = zip_cache.get(zip_file)
                with zf.open(zip_path) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                rel_path = os.path.join("assets", target_name)
                asset_cache[cache_key] = rel_path
                entry = {
                    "ref": ref,
                    "path": rel_path,
                    "status": "resolved",
                    "zip_file": zip_file,
                    "zip_path": zip_path,
                }
        else:
            entry = {"ref": ref, "status": "unresolved"}
        resolved_assets.append(entry)
        assets_manifest.append(entry)

    return resolved_assets, assets_manifest


def process_conversation(
    zf: zipfile.ZipFile,
    archive_slug: str,
    index: Dict[str, List[str]],
    conv: Dict[str, Any],
    output_root: str,
    include_all_branches: bool,
    asset_strategy: str,
    use_archive_scope: bool,
    stats: Dict[str, int],
) -> Optional[Dict[str, Any]]:
    """Process one conversation into normalized outputs."""
    conv_id = conv.get("conversation_id") or conv.get("id")
    if not isinstance(conv_id, str):
        return None

    if use_archive_scope:
        conv_dir = os.path.join(output_root, "conversations", archive_slug, conv_id)
    else:
        conv_dir = os.path.join(output_root, "conversations", conv_id)

    if os.path.isdir(conv_dir):
        shutil.rmtree(conv_dir)
    ensure_dir(conv_dir)
    assets_dir = os.path.join(conv_dir, "assets")
    ensure_dir(assets_dir)

    mapping = conv.get("mapping") if isinstance(conv.get("mapping"), dict) else {}
    if include_all_branches:
        node_ids = linearize_all_nodes(mapping)
    else:
        node_ids = linearize_active_path(mapping, conv.get("current_node"))
        if not node_ids:
            node_ids = linearize_all_nodes(mapping)

    messages = []
    assets_manifest = []
    asset_name_counts: Dict[str, int] = {}
    asset_cache: Dict[str, str] = {}

    for seq, node_id in enumerate(node_ids, start=1):
        node = mapping.get(node_id, {})
        msg = node.get("message") if isinstance(node, dict) else None
        if not isinstance(msg, dict):
            continue

        normalized = normalize_message(msg)
        asset_refs = normalized.pop("asset_refs", [])

        resolved_assets = []
        if asset_strategy == DEFAULT_ASSET_STRATEGY:
            resolved_assets, manifest = copy_assets_local(
                zf,
                index,
                asset_refs,
                assets_dir,
                asset_name_counts,
                asset_cache,
            )
            assets_manifest.extend(manifest)
        else:
            resolved_assets = [{"ref": ref, "status": "skipped"} for ref in asset_refs]

        messages.append(
            {
                "seq": seq,
                "node_id": node_id,
                "role": normalized.get("role"),
                "author_name": normalized.get("author_name"),
                "timestamp": normalized.get("timestamp"),
                "content_type": normalized.get("content_type"),
                "text": normalized.get("text"),
                "assets": resolved_assets,
                "metadata": normalized.get("metadata"),
            }
        )

    write_jsonl(os.path.join(conv_dir, "messages.jsonl"), messages)
    write_json(os.path.join(conv_dir, "assets_manifest.json"), assets_manifest)

    participant_roles = sorted({m.get("role") for m in messages if m.get("role")})
    header_lines = [
        f"# {conv.get('title') or 'Untitled'}",
        f"- id: {conv_id}",
        f"- created_at: {format_timestamp(conv.get('create_time'))}",
        f"- updated_at: {format_timestamp(conv.get('update_time'))}",
        f"- model: {conv.get('default_model_slug') or 'unknown'}",
        f"- message_count: {len(messages)}",
        f"- participant_roles: {', '.join(participant_roles) if participant_roles else 'unknown'}",
        f"- archived: {conv.get('is_archived')}",
        f"- starred: {conv.get('is_starred')}",
        f"- do_not_remember: {conv.get('is_do_not_remember')}",
        f"- study_mode: {conv.get('is_study_mode')}",
        "",
        "## Messages",
        "",
    ]

    md_path = os.path.join(conv_dir, "conversation.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header_lines))
        for message in messages:
            fh.write(render_message_markdown(message))
            fh.write("\n")

    stats["conversations"] += 1
    stats["messages"] += len(messages)
    stats["assets"] += sum(1 for item in assets_manifest if item.get("status") == "resolved")
    stats["unresolved_assets"] += sum(
        1 for item in assets_manifest if item.get("status") == "unresolved"
    )

    return {
        "conversation_id": conv_id,
        "title": conv.get("title"),
        "create_time": conv.get("create_time"),
        "update_time": conv.get("update_time"),
        "model_slug": conv.get("default_model_slug"),
        "message_count": len(messages),
        "participant_roles": participant_roles,
        "output_path": os.path.relpath(conv_dir, output_root),
        "archive": archive_slug,
        "has_assets": bool(assets_manifest),
    }


def update_conversation_meta(
    agg: Dict[str, Any], conv: Dict[str, Any], archive_slug: str
) -> None:
    """Update consolidated conversation metadata across archives."""
    agg["archives"].add(archive_slug)

    create_time = conv.get("create_time")
    if create_time is not None:
        if agg["create_time"] is None or create_time < agg["create_time"]:
            agg["create_time"] = create_time

    update_time = conv.get("update_time")
    if update_time is not None:
        if agg["update_time"] is None or update_time > agg["update_time"]:
            agg["update_time"] = update_time

    latest = agg.get("latest_update_time")
    if update_time is not None and (latest is None or update_time >= latest):
        agg["latest_update_time"] = update_time
        for key in [
            "title",
            "default_model_slug",
            "is_archived",
            "is_starred",
            "is_do_not_remember",
            "is_study_mode",
        ]:
            if key in conv:
                agg[key] = conv.get(key)
    else:
        for key in [
            "title",
            "default_model_slug",
            "is_archived",
            "is_starred",
            "is_do_not_remember",
            "is_study_mode",
        ]:
            if agg.get(key) is None and key in conv:
                agg[key] = conv.get(key)


def process_archives_merge(
    zip_paths: List[str],
    output_root: str,
    asset_strategy: str,
    stats: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Merge overlapping exports into consolidated conversations."""
    global_index, good_zips = build_global_index(zip_paths, stats)
    zip_cache = ZipCache()
    merged: Dict[str, Any] = {}

    for zip_path in good_zips:
        archive_slug = slugify(os.path.splitext(os.path.basename(zip_path))[0])
        try:
            with zipfile.ZipFile(zip_path) as zf:
                if "conversations.json" not in zf.namelist():
                    continue
                conversations = load_json_from_zip(zf, "conversations.json")
                if not isinstance(conversations, list):
                    continue

                for conv in conversations:
                    if not isinstance(conv, dict):
                        continue
                    conv_id = conv.get("conversation_id") or conv.get("id")
                    if not isinstance(conv_id, str):
                        continue

                    if conv_id not in merged:
                        merged[conv_id] = {
                            "conversation_id": conv_id,
                            "title": None,
                            "default_model_slug": None,
                            "create_time": None,
                            "update_time": None,
                            "is_archived": None,
                            "is_starred": None,
                            "is_do_not_remember": None,
                            "is_study_mode": None,
                            "latest_update_time": None,
                            "archives": set(),
                            "messages": {},
                            "order_counter": 0,
                        }

                    agg = merged[conv_id]
                    update_conversation_meta(agg, conv, archive_slug)

                    mapping = (
                        conv.get("mapping") if isinstance(conv.get("mapping"), dict) else {}
                    )
                    for node in mapping.values():
                        msg = node.get("message") if isinstance(node, dict) else None
                        if not isinstance(msg, dict):
                            continue
                        normalized = normalize_message(msg)
                        key = message_fingerprint(msg, normalized)
                        if key in agg["messages"]:
                            merge_normalized_message(agg["messages"][key], normalized)
                            stats["merged_messages"] += 1
                            continue

                        normalized["node_id"] = msg.get("id") or key
                        normalized["order"] = agg["order_counter"]
                        agg["order_counter"] += 1
                        agg["messages"][key] = normalized
        except zipfile.BadZipFile:
            continue

    index_entries: List[Dict[str, Any]] = []

    for conv_id, agg in merged.items():
        conv_dir = os.path.join(output_root, "conversations", conv_id)
        if os.path.isdir(conv_dir):
            shutil.rmtree(conv_dir)
        ensure_dir(conv_dir)
        assets_dir = os.path.join(conv_dir, "assets")
        ensure_dir(assets_dir)

        messages_raw = list(agg["messages"].values())
        messages_raw.sort(key=message_sort_key)

        messages = []
        assets_manifest = []
        asset_name_counts: Dict[str, int] = {}
        asset_cache: Dict[Tuple[str, str], str] = {}

        for seq, msg in enumerate(messages_raw, start=1):
            asset_refs = msg.get("asset_refs") or []
            resolved_assets = []
            if asset_strategy == DEFAULT_ASSET_STRATEGY:
                resolved_assets, manifest = copy_assets_global(
                    asset_refs,
                    global_index,
                    zip_cache,
                    assets_dir,
                    asset_name_counts,
                    asset_cache,
                )
                assets_manifest.extend(manifest)
            else:
                resolved_assets = [{"ref": ref, "status": "skipped"} for ref in asset_refs]

            messages.append(
                {
                    "seq": seq,
                    "node_id": msg.get("node_id"),
                    "role": msg.get("role"),
                    "author_name": msg.get("author_name"),
                    "timestamp": msg.get("timestamp"),
                    "content_type": msg.get("content_type"),
                    "text": msg.get("text"),
                    "assets": resolved_assets,
                    "metadata": msg.get("metadata"),
                }
            )

        write_jsonl(os.path.join(conv_dir, "messages.jsonl"), messages)
        write_json(os.path.join(conv_dir, "assets_manifest.json"), assets_manifest)

        participant_roles = sorted({m.get("role") for m in messages if m.get("role")})
        header_lines = [
            f"# {agg.get('title') or 'Untitled'}",
            f"- id: {conv_id}",
            f"- created_at: {format_timestamp(agg.get('create_time'))}",
            f"- updated_at: {format_timestamp(agg.get('update_time'))}",
            f"- model: {agg.get('default_model_slug') or 'unknown'}",
            f"- message_count: {len(messages)}",
            f"- participant_roles: {', '.join(participant_roles) if participant_roles else 'unknown'}",
            f"- archived: {agg.get('is_archived')}",
            f"- starred: {agg.get('is_starred')}",
            f"- do_not_remember: {agg.get('is_do_not_remember')}",
            f"- study_mode: {agg.get('is_study_mode')}",
            f"- archives: {', '.join(sorted(agg.get('archives', [])))}",
            "",
            "## Messages",
            "",
        ]

        md_path = os.path.join(conv_dir, "conversation.md")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(header_lines))
            for message in messages:
                fh.write(render_message_markdown(message))
                fh.write("\n")

        stats["conversations"] += 1
        stats["messages"] += len(messages)
        stats["assets"] += sum(
            1 for item in assets_manifest if item.get("status") == "resolved"
        )
        stats["unresolved_assets"] += sum(
            1 for item in assets_manifest if item.get("status") == "unresolved"
        )

        index_entries.append(
            {
                "conversation_id": conv_id,
                "title": agg.get("title"),
                "create_time": agg.get("create_time"),
                "update_time": agg.get("update_time"),
                "model_slug": agg.get("default_model_slug"),
                "message_count": len(messages),
                "participant_roles": participant_roles,
                "output_path": os.path.relpath(conv_dir, output_root),
                "archives": sorted(agg.get("archives", [])),
                "has_assets": bool(assets_manifest),
            }
        )

    zip_cache.close()
    return index_entries


def process_archive(
    zip_path: str,
    output_root: str,
    include_all_branches: bool,
    asset_strategy: str,
    dedupe: bool,
    registry: Dict[str, Dict[str, Any]],
    index_entries: List[Dict[str, Any]],
    stats: Dict[str, int],
) -> None:
    """Process a single zip in non-merge mode."""
    archive_slug = slugify(os.path.splitext(os.path.basename(zip_path))[0])
    use_archive_scope = not dedupe
    try:
        with zipfile.ZipFile(zip_path) as zf:
            if "conversations.json" not in zf.namelist():
                raise ValueError(f"Missing conversations.json in {zip_path}")
            conversations = load_json_from_zip(zf, "conversations.json")
            if not isinstance(conversations, list):
                raise ValueError(f"Unexpected conversations.json format in {zip_path}")
            index = build_zip_index(zf)

            for conv in conversations:
                if not isinstance(conv, dict):
                    continue
                conv_id = conv.get("conversation_id") or conv.get("id")
                if not isinstance(conv_id, str):
                    continue
                update_time = conv.get("update_time") or 0
                registry_key = f"{archive_slug}:{conv_id}" if not dedupe else conv_id
                if registry_key in registry:
                    if update_time <= registry[registry_key].get("update_time", 0):
                        stats["deduped"] += 1
                        continue
                registry[registry_key] = {"update_time": update_time}

                summary = process_conversation(
                    zf,
                    archive_slug,
                    index,
                    conv,
                    output_root,
                    include_all_branches,
                    asset_strategy,
                    use_archive_scope,
                    stats,
                )
                if summary:
                    index_entries.append(summary)
    except zipfile.BadZipFile:
        stats["bad_archives"] += 1
        print(f"Skipping bad zip: {zip_path}", file=sys.stderr)


EPILOG_TEXT = """Detailed option reference (what each flag means, why it exists, and what it does):
- `--input / --input-dir`: pick individual zips when you only need specific exports, or point at an exports directory to process every download automatically.
- `--output-dir`: required output tree for normalized conversations, asset manifests, indexes, and unresolved-asset reports; keeping it outside the raw zips prevents accidental overwrites.
- `--asset-strategy copy_per_conversation`: the sole strategy; copies every referenced file into each conversation's `assets/` directory and logs resolution metadata so you can inspect which assets were found or missing.
- `--include-all-branches`: include every node in the conversation graph rather than only the active path, letting you capture abandoned branches that may still contain replies or reasoning.
- `--dedupe` (default) / `--no-dedupe`: dedupe mode keeps a single folder per conversation ID even if multiple archives contain it, while `--no-dedupe` retains one copy per archive so you can compare exports side-by-side.
- `--merge-overlaps`: merge overlapping exports by conversation ID, deduplicate messages, and save one consolidated conversation per ID—recommended when you ingest exports over time.
- `index.json` plus `unresolved_assets_report.jsonl` / `unresolved_assets_summary.json` expose stats for archives, conversations, messages, resolved/unresolved assets, deduped entries, merged messages, and bad archives so you can verify the run afterwards.

Reason & what it does:
The digester builds a human-friendly transcript tree from raw ChatGPT exports: it normalizes messages, linearizes branches, copies referenced assets, merges overlaps, and writes per-conversation folders plus global reports. The options let you control how much history to include (active path vs every branch), whether multiple archives collapse or stack, and how assets are bundled.

Examples:
  # Default merge mode over an exports directory (produce consolidated conversations)
  python3 chatgpt_export_digester.py --input-dir ChatGPT_Exports --output-dir ChatGPT_Digested --merge-overlaps

  # Keep separate folders per archive and include every branch
  python3 chatgpt_export_digester.py --input-dir ChatGPT_Exports --output-dir ChatGPT_Digested --no-dedupe --include-all-branches
"""


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="ChatGPT export digester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG_TEXT,
    )
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        default=[],
        help="Path to a ChatGPT export zip (can be repeated)",
    )
    parser.add_argument(
        "--input-dir",
        dest="input_dir",
        help="Directory containing ChatGPT export zips",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for normalized conversations",
    )
    parser.add_argument(
        "--asset-strategy",
        default=DEFAULT_ASSET_STRATEGY,
        choices=[DEFAULT_ASSET_STRATEGY],
        help="Asset handling strategy",
    )
    parser.add_argument(
        "--include-all-branches",
        action="store_true",
        help="Include all branches instead of only the active path",
    )
    parser.add_argument(
        "--dedupe",
        dest="dedupe",
        action="store_true",
        default=True,
        help="Deduplicate conversations across archives (default)",
    )
    parser.add_argument(
        "--no-dedupe",
        dest="dedupe",
        action="store_false",
        help="Do not deduplicate conversations across archives",
    )
    parser.add_argument(
        "--merge-overlaps",
        action="store_true",
        help="Merge overlapping exports into consolidated conversations",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    """CLI entry point."""
    if not argv:
        print(
            "No options provided; here is the detailed option reference and how the digester behaves:\n"
        )
        print(EPILOG_TEXT)
        return 0

    args = parse_args(argv)
    output_root = args.output_dir
    ensure_dir(output_root)

    inputs = find_zip_inputs(args.inputs, args.input_dir)
    stats = {
        "archives": 0,
        "conversations": 0,
        "messages": 0,
        "assets": 0,
        "unresolved_assets": 0,
        "deduped": 0,
        "merged_messages": 0,
        "bad_archives": 0,
    }

    index_entries: List[Dict[str, Any]] = []

    if args.merge_overlaps:
        stats["archives"] = len(inputs)
        index_entries = process_archives_merge(
            inputs,
            output_root,
            args.asset_strategy,
            stats,
        )
    else:
        registry: Dict[str, Dict[str, Any]] = {}
        for zip_path in inputs:
            stats["archives"] += 1
            process_archive(
                zip_path,
                output_root,
                args.include_all_branches,
                args.asset_strategy,
                args.dedupe,
                registry,
                index_entries,
                stats,
            )

    index = {
        "generated_at": dt.datetime.now(dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "archives": stats["archives"],
        "conversations": stats["conversations"],
        "messages": stats["messages"],
        "assets": stats["assets"],
        "unresolved_assets": stats["unresolved_assets"],
        "deduped": stats["deduped"],
        "merged_messages": stats["merged_messages"],
        "bad_archives": stats["bad_archives"],
        "items": index_entries,
    }
    write_json(os.path.join(output_root, "index.json"), index)
    write_unresolved_report(output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
