#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遍历项目文件，计算 MD5 哈希，生成 manifest.json 供增量同步使用。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".cursor", "tests", ".venv", "venv"}
EXCLUDE_FILES = {"manifest.json"}
EXCLUDE_EXTENSIONS = {".pyc", ".pyo"}


def md5_file(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def should_exclude(rel_path: str, extra_excludes: list[str]) -> bool:
    parts = Path(rel_path).parts
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    filename = os.path.basename(rel_path)
    if filename in EXCLUDE_FILES:
        return True
    if os.path.splitext(filename)[1] in EXCLUDE_EXTENSIONS:
        return True
    for pattern in extra_excludes:
        if pattern in rel_path:
            return True
    return False


def generate_manifest(root: str, output: str, extra_excludes: list[str]) -> dict:
    root = os.path.abspath(root)
    files = {}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in sorted(filenames):
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root).replace("\\", "/")

            if should_exclude(rel_path, extra_excludes):
                continue

            try:
                file_hash = md5_file(filepath)
                file_size = os.path.getsize(filepath)
                files[rel_path] = {"hash": file_hash, "size": file_size}
            except (OSError, PermissionError) as e:
                print(f"[WARN] 跳过文件 {rel_path}: {e}")

    manifest = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": dict(sorted(files.items())),
    }

    output_path = os.path.join(root, output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] 已生成 {output}，共 {len(files)} 个文件")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="生成文件清单 manifest.json")
    parser.add_argument("--root", default=".", help="项目根目录（默认当前目录）")
    parser.add_argument("--output", default="manifest.json", help="输出文件名（默认 manifest.json）")
    parser.add_argument("--exclude", nargs="*", default=[], help="额外排除的路径关键字")
    args = parser.parse_args()

    generate_manifest(args.root, args.output, args.exclude)


if __name__ == "__main__":
    main()
