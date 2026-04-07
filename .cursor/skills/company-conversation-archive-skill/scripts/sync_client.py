#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量同步客户端：对比服务器与本地的 manifest.json，只下载变更文件。

Usage:
  python scripts/sync_client.py --server-url http://10.0.0.1:8080 --local-dir ./local_copy
  python scripts/sync_client.py --server-url http://10.0.0.1:8080 --local-dir ./local_copy --dry-run
"""

import argparse
import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

MANIFEST_FILE = 'manifest.json'


def fetch_json(url):
    req = Request(url, headers={'User-Agent': 'sync-client/1.0'})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def download_file(base_url, rel_path, local_dir):
    url = f"{base_url.rstrip('/')}/{rel_path}"
    local_path = os.path.join(local_dir, rel_path.replace('/', os.sep))

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    req = Request(url, headers={'User-Agent': 'sync-client/1.0'})
    with urlopen(req, timeout=60) as resp:
        with open(local_path, 'wb') as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)

    return local_path


def load_local_manifest(local_dir):
    manifest_path = os.path.join(local_dir, MANIFEST_FILE)
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_local_manifest(local_dir, manifest):
    manifest_path = os.path.join(local_dir, MANIFEST_FILE)
    os.makedirs(local_dir, exist_ok=True)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def compute_diff(remote_files, local_files):
    """对比远程和本地文件清单，返回 (added, modified, deleted, unchanged)"""
    remote_set = set(remote_files.keys())
    local_set = set(local_files.keys()) if local_files else set()

    added = remote_set - local_set
    deleted = local_set - remote_set
    common = remote_set & local_set

    modified = set()
    unchanged = set()
    for path in common:
        if remote_files[path]['hash'] != local_files[path]['hash']:
            modified.add(path)
        else:
            unchanged.add(path)

    return sorted(added), sorted(modified), sorted(deleted), sorted(unchanged)


def sync(server_url, local_dir, dry_run=False, keep_deleted=False):
    server_url = server_url.rstrip('/')
    manifest_url = f"{server_url}/{MANIFEST_FILE}"

    print(f"[SYNC] 服务器: {server_url}")
    print(f"       本地目录: {os.path.abspath(local_dir)}")
    print()

    # 1. 拉取远程 manifest
    print("[1/4] 下载远程 manifest.json ...")
    try:
        remote_manifest = fetch_json(manifest_url)
    except (URLError, HTTPError) as e:
        print(f"  [ERR] 无法获取远程 manifest: {e}")
        sys.exit(1)

    remote_files = remote_manifest.get('files', {})
    print(f"       远程文件数: {remote_manifest.get('file_count', len(remote_files))}")
    print(f"       生成时间:   {remote_manifest.get('generated_at', '未知')}")

    # 2. 加载本地 manifest
    print("[2/4] 加载本地 manifest.json ...")
    local_manifest = load_local_manifest(local_dir)
    local_files = local_manifest.get('files', {}) if local_manifest else {}

    if local_manifest:
        print(f"       本地文件数: {len(local_files)}")
    else:
        print("       本地无 manifest（首次同步）")

    # 3. 计算差异
    print("[3/4] 计算文件差异 ...")
    added, modified, deleted, unchanged = compute_diff(remote_files, local_files)

    download_total = len(added) + len(modified)
    download_size = sum(remote_files[p]['size'] for p in added) + \
                    sum(remote_files[p]['size'] for p in modified)

    print(f"       新增: {len(added)}  |  修改: {len(modified)}  |  删除: {len(deleted)}  |  未变更: {len(unchanged)}")
    print(f"       需下载: {download_total} 个文件, {download_size:,} bytes")
    print()

    if added:
        print("  [新增]")
        for p in added:
            print(f"    + {p}  ({remote_files[p]['size']:,} bytes)")
    if modified:
        print("  [修改]")
        for p in modified:
            print(f"    ~ {p}  ({remote_files[p]['size']:,} bytes)")
    if deleted:
        print("  [删除]")
        for p in deleted:
            print(f"    - {p}")
    print()

    if download_total == 0 and len(deleted) == 0:
        print("[OK] 已是最新，无需同步")
        return

    if dry_run:
        print("[DRY-RUN] 仅展示差异，未执行实际操作")
        return

    # 4. 执行同步
    print(f"[4/4] 开始同步 ...")

    success_count = 0
    fail_count = 0
    for i, rel_path in enumerate(added + modified, 1):
        try:
            download_file(server_url, rel_path, local_dir)
            success_count += 1
            print(f"  [{i}/{download_total}] 下载成功: {rel_path}")
        except Exception as e:
            fail_count += 1
            print(f"  [{i}/{download_total}] 下载失败: {rel_path} ({e})")

    delete_count = 0
    if not keep_deleted:
        for rel_path in deleted:
            local_path = os.path.join(local_dir, rel_path.replace('/', os.sep))
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    delete_count += 1
                    print(f"  已删除: {rel_path}")
            except OSError as e:
                print(f"  删除失败: {rel_path} ({e})")

    # 保存新 manifest
    save_local_manifest(local_dir, remote_manifest)

    print()
    print(f"[OK] 同步完成")
    print(f"     下载成功: {success_count}  |  下载失败: {fail_count}  |  已删除: {delete_count}")

    if fail_count > 0:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='增量同步客户端 — 对比 manifest 只下载变更文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/sync_client.py --server-url http://10.0.0.1:8080 --local-dir ./local
  python scripts/sync_client.py --server-url http://10.0.0.1:8080 --local-dir ./local --dry-run
  python scripts/sync_client.py --server-url http://10.0.0.1:8080 --local-dir ./local --keep-deleted
        """)
    parser.add_argument('--server-url', required=True, help='静态文件服务器 URL')
    parser.add_argument('--local-dir', required=True, help='本地同步目录')
    parser.add_argument('--dry-run', action='store_true', help='仅显示差异，不实际下载')
    parser.add_argument('--keep-deleted', action='store_true',
                        help='保留服务器已删除的本地文件（默认会删除）')

    args = parser.parse_args()
    sync(args.server_url, args.local_dir, dry_run=args.dry_run, keep_deleted=args.keep_deleted)


if __name__ == '__main__':
    main()
