#!/usr/bin/env python3
"""Incremental file sync client — download only changed files by comparing manifests."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def load_local_manifest(local_dir):
    path = os.path.join(local_dir, 'manifest.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('files', {})


def fetch_remote_manifest(server_url):
    url = server_url.rstrip('/') + '/manifest.json'
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data
    except urllib.error.URLError as e:
        print(f'error: cannot fetch remote manifest from {url}: {e}', file=sys.stderr)
        sys.exit(1)


def compute_diff(local_files, remote_files):
    to_download = []
    to_delete = []
    unchanged = []

    for path, info in remote_files.items():
        local_info = local_files.get(path)
        if local_info is None or local_info.get('hash') != info['hash']:
            to_download.append(path)
        else:
            unchanged.append(path)

    for path in local_files:
        if path not in remote_files:
            to_delete.append(path)

    return to_download, to_delete, unchanged


def download_file(server_url, rel_path, local_dir):
    url = server_url.rstrip('/') + '/' + rel_path
    dest = os.path.join(local_dir, rel_path.replace('/', os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except urllib.error.URLError as e:
        print(f'  failed to download {rel_path}: {e}', file=sys.stderr)
        return False


def delete_file(local_dir, rel_path):
    dest = os.path.join(local_dir, rel_path.replace('/', os.sep))
    try:
        os.remove(dest)
        parent = os.path.dirname(dest)
        while parent != local_dir:
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
                parent = os.path.dirname(parent)
            else:
                break
    except OSError:
        pass


def sync(server_url, local_dir, dry_run=False):
    remote_manifest = fetch_remote_manifest(server_url)
    remote_files = remote_manifest.get('files', {})
    local_files = load_local_manifest(local_dir)

    to_download, to_delete, unchanged = compute_diff(local_files, remote_files)

    print(f'remote manifest generated at: {remote_manifest.get("generated_at", "unknown")}')
    print(f'  to download: {len(to_download)}')
    print(f'  to delete:   {len(to_delete)}')
    print(f'  unchanged:   {len(unchanged)}')

    if not to_download and not to_delete:
        print('already up to date.')
        return

    if dry_run:
        if to_download:
            print('\nfiles to download:')
            for p in sorted(to_download):
                size = remote_files[p].get('size', 0)
                print(f'  + {p} ({size:,} bytes)')
        if to_delete:
            print('\nfiles to delete:')
            for p in sorted(to_delete):
                print(f'  - {p}')
        return

    success = 0
    fail = 0
    for p in to_download:
        if download_file(server_url, p, local_dir):
            success += 1
            print(f'  downloaded: {p}')
        else:
            fail += 1

    for p in to_delete:
        delete_file(local_dir, p)
        print(f'  deleted: {p}')

    manifest_path = os.path.join(local_dir, 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(remote_manifest, f, indent=2, ensure_ascii=False)

    print(f'\nsync complete: {success} downloaded, {fail} failed, {len(to_delete)} deleted')


def main():
    parser = argparse.ArgumentParser(description='Incremental file sync client')
    parser.add_argument('--server-url', required=True, help='Base URL of the file server')
    parser.add_argument('--local-dir', default='.', help='Local directory to sync into (default: current dir)')
    parser.add_argument('--dry-run', action='store_true', help='Only show diff, do not download/delete')
    args = parser.parse_args()

    sync(args.server_url, args.local_dir, args.dry_run)


if __name__ == '__main__':
    main()
