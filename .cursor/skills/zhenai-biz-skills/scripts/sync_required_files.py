#!/usr/bin/env python3
"""Synchronize required files for a remote skill using manifest-based updates."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 30.0
DEFAULT_RETRIES = 1
DEFAULT_MAX_WORKERS = 4
DEFAULT_USER_AGENT = "zhenai-biz-skills-sync/1.0"

SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class SyncError(RuntimeError):
    """Raised when synchronization fails."""


def validate_skill_name(skill_name: str) -> str:
    if not skill_name or not SKILL_NAME_RE.fullmatch(skill_name):
        raise SyncError(
            "Invalid skill name. Only letters, digits, dot, underscore, and hyphen are allowed."
        )
    return skill_name


def normalize_relative_path(path_str: str) -> str:
    raw = path_str.strip()
    if not raw:
        raise SyncError("File path must not be empty.")
    if "\\" in raw:
        raise SyncError(f"Backslash is not allowed in relative path: {path_str}")
    normalized = PurePosixPath(raw)
    if normalized.is_absolute():
        raise SyncError(f"Absolute path is not allowed: {path_str}")
    parts = normalized.parts
    if any(part in ("", ".", "..") for part in parts):
        raise SyncError(f"Unsafe relative path: {path_str}")
    return normalized.as_posix()


def dedupe_preserve_order(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path_str in paths:
        normalized = normalize_relative_path(path_str)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def build_file_url(base_url: str, skill_name: str, relative_path: str) -> str:
    base = base_url.rstrip("/")
    safe_skill = quote(validate_skill_name(skill_name), safe="")
    safe_path = "/".join(quote(part, safe="") for part in PurePosixPath(relative_path).parts)
    return f"{base}/{safe_skill}/{safe_path}"


def build_local_target_path(local_skill_dir: Path, relative_path: str) -> Path:
    normalized = normalize_relative_path(relative_path)
    base_dir = local_skill_dir.resolve()
    target_path = (base_dir / Path(*PurePosixPath(normalized).parts)).resolve()
    if os.path.commonpath([str(base_dir), str(target_path)]) != str(base_dir):
        raise SyncError(f"Resolved path escapes cache directory: {relative_path}")
    return target_path


def fetch_bytes(
    url: str,
    connect_timeout: float,
    read_timeout: float,
    retries: int,
    user_agent: str = DEFAULT_USER_AGENT,
) -> bytes:
    attempts = retries + 1
    last_error: Optional[Exception] = None
    request_timeout = max(connect_timeout, read_timeout)

    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": user_agent})
            with urlopen(request, timeout=request_timeout) as response:
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code < 500 or attempt == attempts:
                break
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == attempts:
                break

        time.sleep(min(0.5 * attempt, 2.0))

    raise SyncError(f"Failed to fetch {url}: {last_error}")


def atomic_write(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp_handle:
        temp_handle.write(data)
        temp_name = temp_handle.name
    os.replace(temp_name, target)


@contextlib.contextmanager
def skill_manifest_lock(
    local_skill_dir: Path,
    *,
    acquire_timeout: float = 30.0,
    poll_interval: float = 0.1,
    stale_after: float = 300.0,
):
    lock_dir = local_skill_dir / ".manifest.lock"
    owner_file = lock_dir / "owner.json"
    local_skill_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + acquire_timeout

    while True:
        try:
            lock_dir.mkdir()
            owner_payload = {
                "pid": os.getpid(),
                "acquired_at": time.time(),
            }
            atomic_write(owner_file, json.dumps(owner_payload, ensure_ascii=False).encode("utf-8"))
            break
        except FileExistsError:
            try:
                age = time.time() - lock_dir.stat().st_mtime
            except FileNotFoundError:
                continue

            if age > stale_after:
                try:
                    owner_file.unlink(missing_ok=True)
                    lock_dir.rmdir()
                    continue
                except OSError:
                    pass

            if time.monotonic() >= deadline:
                raise SyncError(f"Timed out waiting for manifest lock: {lock_dir}")
            time.sleep(poll_interval)

    try:
        yield
    finally:
        try:
            owner_file.unlink(missing_ok=True)
            lock_dir.rmdir()
        except OSError:
            pass


def parse_manifest(manifest_bytes: bytes) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncError(f"Invalid manifest.json: {exc}") from exc

    files = payload.get("files")
    if isinstance(files, dict):
        parsed: dict[str, dict[str, Any]] = {}
        for raw_path, metadata in files.items():
            normalized = normalize_relative_path(str(raw_path))
            if not isinstance(metadata, dict):
                raise SyncError(f"Invalid manifest entry for {normalized}: expected object.")
            file_hash = metadata.get("hash") or metadata.get("md5")
            if not isinstance(file_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{32}", file_hash):
                raise SyncError(f"Manifest entry for {normalized} is missing a valid MD5 hash.")
            size = metadata.get("size")
            if size is not None and (not isinstance(size, int) or size < 0):
                raise SyncError(f"Manifest entry for {normalized} has invalid size.")
            parsed[normalized] = {"hash": file_hash.lower(), "size": size}
        return parsed

    raise SyncError("Invalid manifest.json: 'files' must be an object.")


def load_local_manifest(local_manifest_path: Path) -> Tuple[Optional[bytes], Dict[str, Dict[str, Any]]]:
    if not local_manifest_path.exists():
        return None, {}
    raw = local_manifest_path.read_bytes()
    try:
        return raw, parse_manifest(raw)
    except SyncError:
        return raw, {}


def should_download_file(
    *,
    local_path: Path,
    local_manifest: dict[str, dict[str, Any]],
    remote_manifest: dict[str, dict[str, Any]],
    relative_path: str,
) -> bool:
    if not local_path.is_file():
        return True

    local_metadata = local_manifest.get(relative_path)
    remote_metadata = remote_manifest[relative_path]
    if local_metadata is None:
        return True

    return str(local_metadata.get("hash")) != str(remote_metadata.get("hash"))


def download_and_store_file(
    *,
    base_url: str,
    skill_name: str,
    relative_path: str,
    local_skill_dir: Path,
    connect_timeout: float,
    read_timeout: float,
    retries: int,
) -> None:
    url = build_file_url(base_url, skill_name, relative_path)
    data = fetch_bytes(url, connect_timeout=connect_timeout, read_timeout=read_timeout, retries=retries)

    target_path = build_local_target_path(local_skill_dir, relative_path)
    atomic_write(target_path, data)


def synchronize_required_files(
    *,
    skill_name: str,
    base_url: str,
    local_dir: str,
    required_files: list[str],
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    read_timeout: float = DEFAULT_READ_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict[str, Any]:
    safe_skill_name = validate_skill_name(skill_name)
    normalized_files = dedupe_preserve_order(required_files)
    if not normalized_files:
        raise SyncError("At least one required file must be provided.")

    local_skill_dir = Path(local_dir).expanduser().resolve() / safe_skill_name
    local_manifest_path = local_skill_dir / "manifest.json"

    remote_manifest_bytes = fetch_bytes(
        build_file_url(base_url, safe_skill_name, "manifest.json"),
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        retries=retries,
    )
    remote_manifest = parse_manifest(remote_manifest_bytes)

    existing_manifest_bytes, local_manifest = load_local_manifest(local_manifest_path)
    manifest_updated = existing_manifest_bytes != remote_manifest_bytes

    missing_in_manifest: list[str] = []
    to_download: list[str] = []
    reused: list[str] = []
    downloaded: list[str] = []
    errors: list[str] = []

    for relative_path in normalized_files:
        metadata = remote_manifest.get(relative_path)
        if metadata is None:
            missing_in_manifest.append(relative_path)
            continue

        local_path = build_local_target_path(local_skill_dir, relative_path)
        if should_download_file(
            local_path=local_path,
            local_manifest=local_manifest,
            remote_manifest=remote_manifest,
            relative_path=relative_path,
        ):
            to_download.append(relative_path)
        else:
            reused.append(relative_path)

    if to_download:
        worker_count = max(1, min(max_workers, len(to_download)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(
                    download_and_store_file,
                    base_url=base_url,
                    skill_name=safe_skill_name,
                    relative_path=relative_path,
                    local_skill_dir=local_skill_dir,
                    connect_timeout=connect_timeout,
                    read_timeout=read_timeout,
                    retries=retries,
                ): relative_path
                for relative_path in to_download
            }
            for future in as_completed(future_map):
                relative_path = future_map[future]
                try:
                    future.result()
                    downloaded.append(relative_path)
                except Exception as exc:
                    errors.append(f"{relative_path}: {exc}")

    downloaded.sort(key=normalized_files.index)
    reused.sort(key=normalized_files.index)
    missing_in_manifest.sort(key=normalized_files.index)

    with skill_manifest_lock(local_skill_dir):
        _, latest_local_manifest = load_local_manifest(local_manifest_path)
        next_local_manifest = dict(latest_local_manifest)
        for relative_path in reused:
            next_local_manifest[relative_path] = remote_manifest[relative_path]
        for relative_path in downloaded:
            next_local_manifest[relative_path] = remote_manifest[relative_path]
        for relative_path in missing_in_manifest:
            next_local_manifest.pop(relative_path, None)
        manifest_payload = {"version": "1.0", "files": next_local_manifest}
        atomic_write(
            local_manifest_path,
            json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
        )

    status = "ok" if not missing_in_manifest and not errors else "error"
    return {
        "status": status,
        "skill_name": safe_skill_name,
        "cache_dir": str(local_skill_dir),
        "manifest_updated": manifest_updated,
        "downloaded": downloaded,
        "reused": reused,
        "missing_in_manifest": missing_in_manifest,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Synchronize required files for a remote skill using manifest-based updates."
    )
    parser.add_argument("--skill-name", required=True, help="Remote skill folder name.")
    parser.add_argument("--base-url", required=True, help="Remote skills base URL without the trailing skill name.")
    parser.add_argument("--local-dir", required=True, help="Local cache root directory.")
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="Required relative file paths to validate and download on demand.",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=DEFAULT_CONNECT_TIMEOUT,
        help=f"Connection timeout in seconds. Default: {DEFAULT_CONNECT_TIMEOUT}.",
    )
    parser.add_argument(
        "--read-timeout",
        type=float,
        default=DEFAULT_READ_TIMEOUT,
        help=f"Read timeout in seconds. Default: {DEFAULT_READ_TIMEOUT}.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retry count for network requests. Default: {DEFAULT_RETRIES}.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Maximum concurrent download workers. Default: {DEFAULT_MAX_WORKERS}.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = synchronize_required_files(
            skill_name=args.skill_name,
            base_url=args.base_url,
            local_dir=args.local_dir,
            required_files=args.files,
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
            retries=args.retries,
            max_workers=args.max_workers,
        )
    except SyncError as exc:
        error_payload = {"status": "error", "errors": [str(exc)]}
        json.dump(error_payload, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
        sys.stdout.write("\n")
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
