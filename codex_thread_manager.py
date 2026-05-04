#!/usr/bin/env python3
"""
Small local helper for OpenAI Codex thread titles.

It reads Codex's local state from ~/.codex and can safely rename a thread by
updating the known local title stores:

- state_5.sqlite: threads.title
- session_index.jsonl: thread_name
- rollout-*.jsonl: append a thread_name_updated event

This is intentionally conservative and creates a backup before any write.
"""

from __future__ import annotations

import argparse
from collections import deque
import datetime as dt
import json
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def manager_home(codex_home: Path) -> Path:
    return codex_home / "thread-manager"


def recent_renames_path(codex_home: Path) -> Path:
    return manager_home(codex_home) / "recent-renames.json"


def normalize_path(path: str | None) -> Path | None:
    if not path:
        return None
    # SQLite may store Windows extended paths such as \\?\C:\...
    if path.startswith("\\\\?\\"):
        path = path[4:]
    return Path(path)


def utc_timestamp() -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_writable(path: Path) -> None:
    try:
        path.chmod(0o700 if path.is_dir() else 0o600)
    except OSError:
        pass


def remove_tree(path: Path) -> None:
    def onerror(function, value, _excinfo):  # type: ignore[no-untyped-def]
        make_writable(Path(value))
        function(value)

    if path.exists():
        shutil.rmtree(path, onerror=onerror)


def _backup_matches_codex_home(backup: Path, codex_home: Path | None) -> bool:
    if codex_home is None:
        return True
    manifest = backup / "manifest.json"
    if not manifest.exists():
        # Older backups without a manifest are left alone in scoped prune mode.
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    recorded = data.get("codex_home")
    if not recorded:
        return False
    try:
        return Path(recorded).expanduser().resolve() == codex_home.expanduser().resolve()
    except OSError:
        return Path(recorded).expanduser() == codex_home.expanduser()


def prune_rename_backups(
    backup_root: Path,
    keep: int,
    *,
    codex_home: Path | None = None,
) -> list[Path]:
    if keep < 1:
        return []
    backups = [
        p
        for p in backup_root.glob("codex-thread-rename-backup-*")
        if p.is_dir() and _backup_matches_codex_home(p, codex_home)
    ]
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    removed: list[Path] = []
    for old in backups[keep:]:
        remove_tree(old)
        removed.append(old)
    return removed


def record_recent_rename(
    codex_home: Path,
    thread: dict[str, Any],
    new_title: str,
    backup: Path,
    keep: int,
) -> Path:
    path = recent_renames_path(codex_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    entry = {
        "renamed_at": utc_timestamp(),
        "id": thread["id"],
        "old_title": thread.get("title") or "",
        "new_title": new_title,
        "source": thread.get("source"),
        "cwd": thread.get("cwd"),
        "rollout_path": str(normalize_path(thread.get("rollout_path"))),
        "backup": str(backup),
    }
    data = [entry] + [
        item for item in data if isinstance(item, dict) and item.get("id") != thread["id"]
    ]
    data = data[: max(1, keep)]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_recent_renames(args: argparse.Namespace) -> int:
    codex_home = Path(args.codex_home).expanduser()
    path = recent_renames_path(codex_home)
    if not path.exists():
        print(f"No recent rename index found: {path}")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data[: args.limit]:
        print(f"{item.get('renamed_at')}  {item.get('id')}")
        print(f"    old: {item.get('old_title')}")
        print(f"    new: {item.get('new_title')}")
        print(f"    cwd: {str(item.get('cwd') or '').replace('\\\\?\\', '')}")
        print(f"    rollout: {item.get('rollout_path')}")
        print(f"    backup:  {item.get('backup')}")
    return 0


def connect_state(codex_home: Path, readonly: bool) -> sqlite3.Connection:
    db = codex_home / "state_5.sqlite"
    if not db.exists():
        raise FileNotFoundError(f"Missing Codex state DB: {db}")
    if readonly:
        return sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return sqlite3.connect(db)


def load_thread(codex_home: Path, thread_id: str) -> dict[str, Any]:
    with connect_state(codex_home, readonly=True) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "select id, title, source, cwd, rollout_path, updated_at, updated_at_ms "
            "from threads where id = ?",
            (thread_id,),
        ).fetchone()
    if row is None:
        raise SystemExit(f"Thread id not found in state_5.sqlite: {thread_id}")
    return dict(row)


def load_recent_threads(
    codex_home: Path,
    *,
    limit: int,
    source: str | None = "vscode",
    cwd: str | None = None,
) -> list[dict[str, Any]]:
    query = (
        "select id, title, source, cwd, rollout_path, updated_at, updated_at_ms "
        "from threads where 1=1"
    )
    params: list[Any] = []
    if cwd:
        query += " and cwd like ?"
        params.append(f"%{cwd}%")
    if source:
        query += " and source = ?"
        params.append(source)
    query += " order by coalesce(updated_at_ms, updated_at * 1000) desc limit ?"
    params.append(limit)

    with connect_state(codex_home, readonly=True) as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute(query, params).fetchall()]


def list_threads(args: argparse.Namespace) -> int:
    codex_home = Path(args.codex_home).expanduser()
    rows = load_recent_threads(
        codex_home,
        limit=args.limit,
        source=args.source,
        cwd=args.cwd,
    )

    for row in rows:
        updated = row["updated_at_ms"] or (row["updated_at"] * 1000)
        updated_text = "-"
        if updated:
            updated_text = dt.datetime.fromtimestamp(
                updated / 1000, tz=dt.timezone.utc
            ).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        title = (row["title"] or "").replace("\r", " ").replace("\n", " ")
        cwd = (row["cwd"] or "").replace("\\\\?\\", "")
        print(f"{updated_text}  {row['id']}  [{row['source']}]  {title}")
        if args.show_cwd:
            print(f"    cwd: {cwd}")
    return 0


def _tail_lines(path: Path, max_lines: int) -> list[str]:
    q: deque[str] = deque(maxlen=max(1, max_lines))
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            q.append(line.rstrip("\n"))
    return list(q)


def _message_text_from_user_payload(payload: dict[str, Any]) -> str:
    """Extract only user-authored text from known Codex rollout schemas."""

    if payload.get("type") == "user_message":
        return str(payload.get("message") or "")

    if payload.get("type") == "message" and payload.get("role") == "user":
        chunks: list[str] = []
        content = payload.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") in {"input_text", "text"} and item.get("text"):
                    chunks.append(str(item["text"]))
        elif isinstance(content, str):
            chunks.append(content)
        return "\n".join(chunks)

    return ""


def extract_tail_rename_title(text: str) -> str | None:
    """Parse a user command such as `/codex rename 新标题` from message text.

    Intentionally requires whitespace after `rename`, so prose like
    `/codex rename后的新名称` is not treated as a command.
    """

    patterns = [
        r"(?im)^\s*/codex\s+rename\s+(.+?)\s*$",
        r"(?im)^\s*/codex-rename\s+(.+?)\s*$",
        r"(?im)^\s*/codex重命名\s+(.+?)\s*$",
        r"(?im)^\s*codex重命名\s+(.+?)\s*$",
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, text or ""))
        if not matches:
            continue
        title = matches[-1].group(1).strip()
        title = title.strip("` \t\r\n\"'“”‘’")
        return title or None
    return None


def find_tail_rename_request(
    thread: dict[str, Any],
    *,
    max_lines: int = 120,
) -> dict[str, Any] | None:
    rollout = normalize_path(thread.get("rollout_path"))
    if not rollout or not rollout.exists():
        return None
    lines = _tail_lines(rollout, max_lines)
    for reverse_idx, line in enumerate(reversed(lines)):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = obj.get("payload")
        if not isinstance(payload, dict):
            continue
        text = _message_text_from_user_payload(payload)
        if not text:
            continue
        title = extract_tail_rename_title(text)
        if title:
            return {
                "title": title,
                "timestamp": obj.get("timestamp"),
                "rollout_path": str(rollout),
                "tail_reverse_index": reverse_idx,
            }
    return None


def scan_rename_commands(args: argparse.Namespace) -> int:
    codex_home = Path(args.codex_home).expanduser()
    rows = load_recent_threads(
        codex_home,
        limit=args.limit,
        source=args.source,
        cwd=args.cwd,
    )
    found = 0
    for thread in rows:
        request = find_tail_rename_request(thread, max_lines=args.max_lines)
        if not request:
            continue
        found += 1
        old_title = (thread.get("title") or "").replace("\r", " ").replace("\n", " ")
        new_title = request["title"]
        status = "already-title" if old_title == new_title else "pending"
        print(f"{status}: {thread['id']}")
        print(f"    old: {old_title}")
        print(f"    new: {new_title}")
        print(f"    source: {thread.get('source')}")
        print(f"    command_at: {request.get('timestamp')}")
        if args.show_cwd:
            print(f"    cwd: {str(thread.get('cwd') or '').replace('\\\\?\\', '')}")
        print(f"    rollout: {request.get('rollout_path')}")
    if found == 0:
        print("No trailing /codex rename commands found in recent threads.")
    return 0


def backup_paths(codex_home: Path, thread: dict[str, Any]) -> Path:
    backup_root = Path(os.environ.get("TEMP", "D:\\tmp"))
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_root / f"codex-thread-rename-backup-{stamp}-{thread['id']}"
    dest.mkdir(parents=True, exist_ok=False)

    copied: list[dict[str, str]] = []
    for name in ("state_5.sqlite", "state_5.sqlite-wal", "state_5.sqlite-shm", "session_index.jsonl"):
        src = codex_home / name
        if src.exists():
            out = dest / name
            shutil.copy2(src, out)
            copied.append({"kind": "codex_home_file", "source": str(src), "backup": out.name})

    rollout = normalize_path(thread.get("rollout_path"))
    if rollout and rollout.exists():
        out = dest / rollout.name
        shutil.copy2(rollout, out)
        copied.append({"kind": "rollout", "source": str(rollout), "backup": out.name})

    manifest = {
        "created_at": utc_timestamp(),
        "operation": "codex-thread-rename",
        "thread_id": thread["id"],
        "old_title": thread.get("title") or "",
        "codex_home": str(codex_home),
        "rollout_path": str(rollout) if rollout else None,
        "files": copied,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return dest


def update_session_index(codex_home: Path, thread_id: str, new_title: str) -> bool:
    path = codex_home / "session_index.jsonl"
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    changed = False
    out: list[str] = []
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            out.append(line)
            continue
        if item.get("id") == thread_id:
            item["thread_name"] = new_title
            changed = True
            out.append(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
        else:
            out.append(line)
    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def append_rollout_event(thread: dict[str, Any], new_title: str) -> bool:
    rollout = normalize_path(thread.get("rollout_path"))
    if not rollout or not rollout.exists():
        return False
    event = {
        "timestamp": utc_timestamp(),
        "type": "event_msg",
        "payload": {
            "type": "thread_name_updated",
            "thread_id": thread["id"],
            "thread_name": new_title,
        },
    }
    with rollout.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return True


def perform_rename(
    *,
    codex_home: Path,
    thread: dict[str, Any],
    new_title: str,
    dry_run: bool,
    allow_long_title: bool,
    keep_backups: int,
    keep_recent_renames: int,
) -> int:
    new_title = new_title.strip()
    if not new_title:
        raise SystemExit("New title cannot be empty.")
    if len(new_title) > 200 and not allow_long_title:
        raise SystemExit("Title is >200 characters. Use --allow-long-title if intentional.")

    old_title = thread.get("title") or ""
    print(f"ID:        {thread['id']}")
    print(f"Old title: {old_title}")
    print(f"New title: {new_title}")
    print(f"Rollout:   {normalize_path(thread.get('rollout_path'))}")

    if dry_run:
        print("DRY_RUN: no files changed.")
        return 0

    backup = backup_paths(codex_home, thread)
    pruned = prune_rename_backups(backup.parent, keep_backups, codex_home=codex_home)
    recent_index = record_recent_rename(
        codex_home, thread, new_title, backup, keep_recent_renames
    )
    print(f"Backup:    {backup}")
    print(f"Recent rename index: {recent_index}")
    if pruned:
        print("Pruned old backups:")
        for path in pruned:
            print(f"  {path}")

    with connect_state(codex_home, readonly=False) as con:
        cur = con.execute(
            "update threads set title = ? where id = ?",
            (new_title, thread["id"]),
        )
        con.commit()
        if cur.rowcount != 1:
            raise SystemExit(f"Unexpected sqlite rowcount: {cur.rowcount}")

    index_changed = update_session_index(codex_home, thread["id"], new_title)
    rollout_changed = append_rollout_event(thread, new_title)

    print(f"Updated state_5.sqlite: yes")
    print(f"Updated session_index.jsonl: {'yes' if index_changed else 'no'}")
    print(f"Appended rollout event: {'yes' if rollout_changed else 'no'}")
    print(
        "Rollback command: "
        f"python {Path(__file__).resolve()} rollback --backup \"{backup}\""
    )
    print("Restart VS Code / Codex to refresh cached history.")
    return 0


def rename_thread(args: argparse.Namespace) -> int:
    codex_home = Path(args.codex_home).expanduser()
    thread = load_thread(codex_home, args.id)
    return perform_rename(
        codex_home=codex_home,
        thread=thread,
        new_title=args.title,
        dry_run=args.dry_run,
        allow_long_title=args.allow_long_title,
        keep_backups=args.keep_backups,
        keep_recent_renames=args.keep_recent_renames,
    )


def tail_rename_threads(args: argparse.Namespace) -> int:
    codex_home = Path(args.codex_home).expanduser()
    rows = load_recent_threads(
        codex_home,
        limit=args.limit,
        source=args.source,
        cwd=args.cwd,
    )
    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    skipped_same = 0
    for thread in rows:
        request = find_tail_rename_request(thread, max_lines=args.max_lines)
        if not request:
            continue
        if (thread.get("title") or "") == request["title"] and not args.force:
            skipped_same += 1
            continue
        pending.append((thread, request))

    if not pending:
        print("No pending /codex rename commands found.")
        if skipped_same:
            print(f"Skipped already-matching titles: {skipped_same}")
        return 0

    print(f"Pending rename commands: {len(pending)}")
    if skipped_same:
        print(f"Skipped already-matching titles: {skipped_same}")
    dry_run = not args.apply
    if dry_run:
        print("DRY_RUN: pass --apply to write changes.")

    for idx, (thread, request) in enumerate(pending, start=1):
        print("")
        print(f"== pending {idx}/{len(pending)} ==")
        print(f"Command at: {request.get('timestamp')}")
        perform_rename(
            codex_home=codex_home,
            thread=thread,
            new_title=request["title"],
            dry_run=dry_run,
            allow_long_title=args.allow_long_title,
            keep_backups=args.keep_backups,
            keep_recent_renames=args.keep_recent_renames,
        )
    return 0


def safe_backup_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise SystemExit(f"Backup directory not found: {resolved}")
    if not resolved.name.startswith("codex-thread-rename-backup-"):
        raise SystemExit(f"Refusing non rename-backup directory: {resolved}")
    return resolved


def restore_file(src: Path, dst: Path, dry_run: bool) -> bool:
    if not src.exists():
        return False
    print(f"restore: {src} -> {dst}")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return True


def rollback_thread(args: argparse.Namespace) -> int:
    backup = safe_backup_dir(Path(args.backup))
    manifest_path = backup / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(
            "Backup has no manifest.json. Only backups created by the updated "
            "script can be rolled back automatically."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    codex_home = Path(args.codex_home or manifest["codex_home"]).expanduser()
    rollout_path = normalize_path(manifest.get("rollout_path"))

    print(f"Backup:    {backup}")
    print(f"Thread:    {manifest.get('thread_id')}")
    print(f"Old title: {manifest.get('old_title')}")
    print(f"CodexHome: {codex_home}")
    if args.dry_run:
        print("DRY_RUN: no files will be restored.")
    else:
        # Snapshot current state before rollback, so a rollback can itself be undone manually.
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        safety = Path(os.environ.get("TEMP", "D:\\tmp")) / (
            f"codex-thread-rollback-current-{stamp}-{manifest.get('thread_id')}"
        )
        safety.mkdir(parents=True, exist_ok=False)
        for name in (
            "state_5.sqlite",
            "state_5.sqlite-wal",
            "state_5.sqlite-shm",
            "session_index.jsonl",
        ):
            src = codex_home / name
            if src.exists():
                shutil.copy2(src, safety / name)
        if rollout_path and rollout_path.exists():
            shutil.copy2(rollout_path, safety / rollout_path.name)
        print(f"Safety snapshot before rollback: {safety}")

    restored = 0
    for name in (
        "state_5.sqlite",
        "state_5.sqlite-wal",
        "state_5.sqlite-shm",
        "session_index.jsonl",
    ):
        if restore_file(backup / name, codex_home / name, args.dry_run):
            restored += 1

    if rollout_path:
        rollout_backup = backup / rollout_path.name
        if restore_file(rollout_backup, rollout_path, args.dry_run):
            restored += 1

    print(f"Restored files: {restored}")
    print("Restart VS Code / Codex to refresh cached history.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage local Codex thread titles.")
    parser.add_argument("--codex-home", default=str(default_codex_home()))
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List recent Codex threads.")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--cwd", help="Filter by cwd substring.")
    p_list.add_argument("--source", default="vscode", help="Filter by source, default: vscode.")
    p_list.add_argument("--show-cwd", action="store_true")
    p_list.set_defaults(func=list_threads)

    p_rename = sub.add_parser("rename", help="Rename one Codex thread.")
    p_rename.add_argument("--id", required=True, help="Thread/session UUID.")
    p_rename.add_argument("--title", required=True, help="New thread title.")
    p_rename.add_argument("--dry-run", action="store_true")
    p_rename.add_argument("--allow-long-title", action="store_true")
    p_rename.add_argument(
        "--keep-backups",
        type=int,
        default=3,
        help="Keep only the newest N rename backups in the backup root. Default: 3.",
    )
    p_rename.add_argument(
        "--keep-recent-renames",
        type=int,
        default=2,
        help="Keep only the newest N rename metadata entries. Default: 2.",
    )
    p_rename.set_defaults(func=rename_thread)

    p_recent = sub.add_parser("recent", help="Show recent rename metadata entries.")
    p_recent.add_argument("--limit", type=int, default=2)
    p_recent.set_defaults(func=print_recent_renames)

    p_scan = sub.add_parser(
        "scan-rename-commands",
        help="Scan recent VS Code rollouts for trailing /codex rename commands.",
    )
    p_scan.add_argument("--limit", type=int, default=20)
    p_scan.add_argument("--cwd", help="Filter by cwd substring.")
    p_scan.add_argument("--source", default="vscode", help="Filter by source, default: vscode.")
    p_scan.add_argument("--max-lines", type=int, default=120)
    p_scan.add_argument("--show-cwd", action="store_true")
    p_scan.set_defaults(func=scan_rename_commands)

    p_tail = sub.add_parser(
        "tail-rename",
        help="Rename recent VS Code threads from trailing /codex rename commands.",
    )
    p_tail.add_argument("--limit", type=int, default=20)
    p_tail.add_argument("--cwd", help="Filter by cwd substring.")
    p_tail.add_argument("--source", default="vscode", help="Filter by source, default: vscode.")
    p_tail.add_argument("--max-lines", type=int, default=120)
    p_tail.add_argument("--apply", action="store_true", help="Write changes. Without this, dry-run only.")
    p_tail.add_argument("--force", action="store_true", help="Rename even when current title already matches.")
    p_tail.add_argument("--allow-long-title", action="store_true")
    p_tail.add_argument(
        "--keep-backups",
        type=int,
        default=3,
        help="Keep only the newest N rename backups in the backup root. Default: 3.",
    )
    p_tail.add_argument(
        "--keep-recent-renames",
        type=int,
        default=2,
        help="Keep only the newest N rename metadata entries. Default: 2.",
    )
    p_tail.set_defaults(func=tail_rename_threads)

    p_rollback = sub.add_parser("rollback", help="Restore files from a rename backup.")
    p_rollback.add_argument("--backup", required=True, help="Backup directory from rename output.")
    p_rollback.add_argument("--dry-run", action="store_true")
    p_rollback.set_defaults(func=rollback_thread)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
