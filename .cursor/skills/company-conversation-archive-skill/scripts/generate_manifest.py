#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成项目文件清单 (manifest.json)，用于增量同步。
遍历项目所有文件，计算 MD5 哈希和文件大小，输出到项目根目录。

Usage:
  python scripts/generate_manifest.py
  python scripts/generate_manifest.py --root /path/to/project
  python scripts/generate_manifest.py --exclude "*.log" --exclude "tmp/"
  python scripts/generate_manifest.py --output custom_manifest.json
"""

import argparse
import hashlib
import json
import os
import fnmatch
from datetime import datetime, timezone

EXCLUDE_DIRS = {
    '.git', '__pycache__', '.pytest_cache', 'node_modules',
    '.cursor', '.vscode', '.idea', '.githooks',
}

EXCLUDE_FILES = {'manifest.json'}


def md5_file(filepath):
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def should_exclude(rel_path, extra_excludes=None):
    """检查路径是否应被排除"""
    parts = rel_path.replace('\\', '/').split('/')

    for part in parts:
        if part in EXCLUDE_DIRS:
            return True

    filename = parts[-1]
    if filename in EXCLUDE_FILES:
        return True

    if extra_excludes:
        normalized = rel_path.replace('\\', '/')
        for pattern in extra_excludes:
            if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(filename, pattern):
                return True

    return False


def generate_manifest(root_dir, output_file='manifest.json', extra_excludes=None):
    root_dir = os.path.abspath(root_dir)
    files_map = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in sorted(filenames):
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir).replace('\\', '/')

            if should_exclude(rel_path, extra_excludes):
                continue

            try:
                file_hash = md5_file(filepath)
                file_size = os.path.getsize(filepath)
                files_map[rel_path] = {
                    'hash': file_hash,
                    'size': file_size,
                }
            except (OSError, IOError) as e:
                print(f"  [WARN] 跳过无法读取的文件: {rel_path} ({e})")

    manifest = {
        'version': '1.0',
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'file_count': len(files_map),
        'files': dict(sorted(files_map.items())),
    }

    output_path = os.path.join(root_dir, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] manifest 已生成: {output_path}")
    print(f"     文件数: {len(files_map)}")
    print(f"     总大小: {sum(v['size'] for v in files_map.values()):,} bytes")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description='生成项目文件清单 (manifest.json)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/generate_manifest.py
  python scripts/generate_manifest.py --root /path/to/project
  python scripts/generate_manifest.py --exclude "*.log" --exclude "tmp/"
        """)
    parser.add_argument('--root', default='.', help='项目根目录 (默认: 当前目录)')
    parser.add_argument('--output', default='manifest.json', help='输出文件名 (默认: manifest.json)')
    parser.add_argument('--exclude', action='append', default=[], help='额外排除规则 (glob 模式，可多次指定)')

    args = parser.parse_args()
    generate_manifest(args.root, args.output, args.exclude or None)


if __name__ == '__main__':
    main()
