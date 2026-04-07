#!/usr/bin/env python3
"""Generate manifest.json for incremental file sync."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

EXCLUDE_DIRS = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.cursor', 'tests', '.githooks'}
EXCLUDE_FILES = {'manifest.json', '.DS_Store', 'Thumbs.db'}
EXCLUDE_EXTENSIONS = {'.pyc', '.pyo', '.log'}
EXCLUDE_SUFFIXES = {'.plan.md'}


def md5_file(filepath):
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def should_exclude(rel_path, extra_excludes=None):
    parts = rel_path.replace('\\', '/').split('/')
    for part in parts[:-1]:
        if part in EXCLUDE_DIRS:
            return True
    filename = parts[-1]
    if filename in EXCLUDE_FILES:
        return True
    _, ext = os.path.splitext(filename)
    if ext in EXCLUDE_EXTENSIONS:
        return True
    for suffix in EXCLUDE_SUFFIXES:
        if filename.endswith(suffix):
            return True
    if extra_excludes:
        for pattern in extra_excludes:
            if pattern in rel_path:
                return True
    return False


def generate_manifest(root, output='manifest.json', extra_excludes=None):
    files = {}
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for filename in sorted(filenames):
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root).replace('\\', '/')
            if should_exclude(rel_path, extra_excludes):
                continue
            try:
                stat = os.stat(filepath)
                files[rel_path] = {
                    'hash': md5_file(filepath),
                    'size': stat.st_size,
                }
            except (OSError, PermissionError):
                continue

    manifest = {
        'version': '1.0',
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'files': dict(sorted(files.items())),
    }

    output_path = os.path.join(root, output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f'manifest generated: {output_path}')
    print(f'  total files: {len(files)}')
    total_size = sum(v["size"] for v in files.values())
    print(f'  total size:  {total_size:,} bytes')
    return manifest


def main():
    parser = argparse.ArgumentParser(description='Generate manifest.json for incremental file sync')
    parser.add_argument('--root', default='.', help='Project root directory (default: current dir)')
    parser.add_argument('--output', default='manifest.json', help='Output filename (default: manifest.json)')
    parser.add_argument('--exclude', nargs='*', default=[], help='Additional exclude patterns')
    args = parser.parse_args()

    generate_manifest(args.root, args.output, args.exclude or None)


if __name__ == '__main__':
    main()
