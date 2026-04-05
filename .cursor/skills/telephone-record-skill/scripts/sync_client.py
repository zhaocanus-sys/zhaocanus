#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户端增量同步脚本 — 对比远端与本地 manifest.json，只下载变更文件。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def fetch_json(url: str) -> dict:
    with urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_file(url: str) -> bytes:
    with urlopen(url, timeout=60) as resp:
        return resp.read()


def load_local_manifest(local_dir: str) -> dict:
    manifest_path = os.path.join(local_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return {"version": "1.0", "files": {}}
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_local_manifest(local_dir: str, manifest: dict):
    manifest_path = os.path.join(local_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def compute_diff(remote_files: dict, local_files: dict) -> tuple[list, list, list]:
    """返回 (to_download, unchanged, to_delete) 三个文件路径列表。"""
    to_download = []
    unchanged = []
    to_delete = []

    for path, info in remote_files.items():
        if path not in local_files:
            to_download.append(path)
        elif local_files[path]["hash"] != info["hash"]:
            to_download.append(path)
        else:
            unchanged.append(path)

    for path in local_files:
        if path not in remote_files:
            to_delete.append(path)

    return to_download, unchanged, to_delete


def print_diff_summary(to_download: list, unchanged: list, to_delete: list, remote_files: dict):
    download_size = sum(remote_files[p]["size"] for p in to_download)

    print(f"\n{'='*50}")
    print(f"  新增/修改: {len(to_download)} 个文件 ({download_size:,} bytes)")
    print(f"  未变更:    {len(unchanged)} 个文件")
    print(f"  待删除:    {len(to_delete)} 个文件")
    print(f"{'='*50}")

    if to_download:
        print("\n[下载]")
        for p in sorted(to_download):
            print(f"  + {p}  ({remote_files[p]['size']:,} bytes)")

    if to_delete:
        print("\n[删除]")
        for p in sorted(to_delete):
            print(f"  - {p}")

    if not to_download and not to_delete:
        print("\n本地已是最新，无需同步。")


def sync(server_url: str, local_dir: str, dry_run: bool = False):
    server_url = server_url.rstrip("/")
    os.makedirs(local_dir, exist_ok=True)

    print(f"从 {server_url}/manifest.json 获取远端清单...")
    try:
        remote_manifest = fetch_json(f"{server_url}/manifest.json")
    except (URLError, OSError) as e:
        print(f"[ERROR] 无法获取远端 manifest: {e}", file=sys.stderr)
        sys.exit(1)

    local_manifest = load_local_manifest(local_dir)

    remote_files = remote_manifest.get("files", {})
    local_files = local_manifest.get("files", {})
    to_download, unchanged, to_delete = compute_diff(remote_files, local_files)

    print_diff_summary(to_download, unchanged, to_delete, remote_files)

    if dry_run:
        print("\n[DRY-RUN] 仅预览，未执行任何操作。")
        return

    if not to_download and not to_delete:
        return

    errors = 0

    for i, rel_path in enumerate(sorted(to_download), 1):
        file_url = f"{server_url}/{rel_path}"
        local_path = os.path.join(local_dir, rel_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            print(f"  [{i}/{len(to_download)}] 下载 {rel_path} ...", end=" ")
            data = fetch_file(file_url)
            with open(local_path, "wb") as f:
                f.write(data)
            print("OK")
        except (URLError, OSError) as e:
            print(f"FAILED: {e}")
            errors += 1

    for rel_path in sorted(to_delete):
        local_path = os.path.join(local_dir, rel_path)
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"  [删除] {rel_path}")
                parent = os.path.dirname(local_path)
                while parent != local_dir and os.path.isdir(parent) and not os.listdir(parent):
                    os.rmdir(parent)
                    parent = os.path.dirname(parent)
        except OSError as e:
            print(f"  [删除失败] {rel_path}: {e}")
            errors += 1

    save_local_manifest(local_dir, remote_manifest)
    print(f"\n同步完成。下载 {len(to_download)} / 删除 {len(to_delete)} / 错误 {errors}")


def main():
    parser = argparse.ArgumentParser(description="客户端增量文件同步")
    parser.add_argument("--server-url", required=True, help="远端静态服务器 URL（如 http://example.com/project）")
    parser.add_argument("--local-dir", default=".", help="本地同步目录（默认当前目录）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览差异，不执行下载/删除")
    args = parser.parse_args()

    sync(args.server_url, args.local_dir, args.dry_run)


if __name__ == "__main__":
    main()
