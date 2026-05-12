from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

CONFIRM_RENAME_TOKEN = "CONFIRM_CODEX_RENAME_WRITE"
CONFIRM_ROLLBACK_TOKEN = "CONFIRM_CODEX_RENAME_ROLLBACK"
SCRIPT = Path(__file__).with_name("codex_thread_manager.py")

mcp = FastMCP("codex-rename")


def _base_args(codex_home: str | None = None) -> list[str]:
    args = [sys.executable, str(SCRIPT)]
    if codex_home:
        args.extend(["--codex-home", codex_home])
    return args


def _run(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "command": args,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _bounded(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


@mcp.tool()
def codex_rename_list_threads(
    limit: int = 5,
    cwd: str | None = None,
    source: str = "vscode",
    show_cwd: bool = True,
    codex_home: str | None = None,
) -> dict[str, Any]:
    """List recent local Codex threads. Read-only."""
    args = _base_args(codex_home) + ["list", "--limit", str(_bounded(limit, 1, 100)), "--source", source]
    if cwd:
        args.extend(["--cwd", cwd])
    if show_cwd:
        args.append("--show-cwd")
    return _run(args)


@mcp.tool()
def codex_rename_scan_commands(
    limit: int = 20,
    cwd: str | None = None,
    source: str = "vscode",
    max_lines: int = 120,
    show_cwd: bool = True,
    codex_home: str | None = None,
) -> dict[str, Any]:
    """Scan recent VS Code Codex rollouts for trailing '/codex rename <title>' commands. Read-only."""
    args = _base_args(codex_home) + [
        "scan-rename-commands",
        "--limit", str(_bounded(limit, 1, 200)),
        "--source", source,
        "--max-lines", str(_bounded(max_lines, 20, 1000)),
    ]
    if cwd:
        args.extend(["--cwd", cwd])
    if show_cwd:
        args.append("--show-cwd")
    return _run(args)


@mcp.tool()
def codex_rename_preview_tail_rename(
    limit: int = 20,
    cwd: str | None = None,
    source: str = "vscode",
    max_lines: int = 120,
    codex_home: str | None = None,
) -> dict[str, Any]:
    """Preview batch renames from trailing '/codex rename <title>' commands without writing."""
    args = _base_args(codex_home) + [
        "tail-rename",
        "--limit", str(_bounded(limit, 1, 200)),
        "--source", source,
        "--max-lines", str(_bounded(max_lines, 20, 1000)),
    ]
    if cwd:
        args.extend(["--cwd", cwd])
    return _run(args)


@mcp.tool()
def codex_rename_apply_tail_rename(
    confirm_token: str,
    limit: int = 20,
    cwd: str | None = None,
    source: str = "vscode",
    max_lines: int = 120,
    force: bool = False,
    allow_long_title: bool = False,
    keep_backups: int = 3,
    keep_recent_renames: int = 2,
    codex_home: str | None = None,
) -> dict[str, Any]:
    """Apply batch renames from trailing '/codex rename <title>' commands. Requires CONFIRM_CODEX_RENAME_WRITE."""
    if confirm_token != CONFIRM_RENAME_TOKEN:
        return {
            "ok": False,
            "permission_tier": "P3",
            "error": f"Missing confirm_token={CONFIRM_RENAME_TOKEN}. Refusing to write Codex metadata.",
        }
    args = _base_args(codex_home) + [
        "tail-rename",
        "--apply",
        "--limit", str(_bounded(limit, 1, 200)),
        "--source", source,
        "--max-lines", str(_bounded(max_lines, 20, 1000)),
        "--keep-backups", str(_bounded(keep_backups, 1, 20)),
        "--keep-recent-renames", str(_bounded(keep_recent_renames, 1, 20)),
    ]
    if cwd:
        args.extend(["--cwd", cwd])
    if force:
        args.append("--force")
    if allow_long_title:
        args.append("--allow-long-title")
    return _run(args)


@mcp.tool()
def codex_rename_thread(
    thread_id: str,
    title: str,
    confirm_token: str,
    dry_run: bool = False,
    allow_long_title: bool = False,
    keep_backups: int = 3,
    keep_recent_renames: int = 2,
    codex_home: str | None = None,
) -> dict[str, Any]:
    """Rename one local Codex thread/session title. Writes only with CONFIRM_CODEX_RENAME_WRITE unless dry_run=true."""
    if not dry_run and confirm_token != CONFIRM_RENAME_TOKEN:
        return {
            "ok": False,
            "permission_tier": "P3",
            "error": f"Missing confirm_token={CONFIRM_RENAME_TOKEN}. Refusing to write Codex metadata.",
        }
    args = _base_args(codex_home) + [
        "rename",
        "--id", thread_id,
        "--title", title,
        "--keep-backups", str(_bounded(keep_backups, 1, 20)),
        "--keep-recent-renames", str(_bounded(keep_recent_renames, 1, 20)),
    ]
    if dry_run:
        args.append("--dry-run")
    if allow_long_title:
        args.append("--allow-long-title")
    return _run(args)


@mcp.tool()
def codex_rename_recent(limit: int = 2, codex_home: str | None = None) -> dict[str, Any]:
    """Show recent Codex rename metadata. Read-only."""
    args = _base_args(codex_home) + ["recent", "--limit", str(_bounded(limit, 1, 20))]
    return _run(args)


@mcp.tool()
def codex_rename_rollback(
    backup: str,
    dry_run: bool = True,
    confirm_token: str | None = None,
    codex_home: str | None = None,
) -> dict[str, Any]:
    """Restore Codex metadata files from a rename backup. Non-dry rollback requires CONFIRM_CODEX_RENAME_ROLLBACK."""
    if not dry_run and confirm_token != CONFIRM_ROLLBACK_TOKEN:
        return {
            "ok": False,
            "permission_tier": "P3",
            "error": f"Missing confirm_token={CONFIRM_ROLLBACK_TOKEN}. Refusing rollback write.",
        }
    args = _base_args(codex_home) + ["rollback", "--backup", backup]
    if dry_run:
        args.append("--dry-run")
    return _run(args)


@mcp.tool()
def codex_rename_help() -> dict[str, Any]:
    """Return short usage and confirmation tokens for host models without loading the long prompt."""
    return {
        "purpose": "Rename local Codex VS Code thread titles through a small MCP instead of loading a long skill prompt.",
        "common_flow": [
            "codex_rename_list_threads(limit=1, show_cwd=true)",
            "codex_rename_thread(thread_id, title, dry_run=true, confirm_token='')",
            f"codex_rename_thread(thread_id, title, confirm_token='{CONFIRM_RENAME_TOKEN}')",
            "Ask the user to Reload Window / restart VS Code to refresh cached history.",
        ],
        "parallel_flow": [
            "User writes '/codex rename <new title>' at the end of each target thread.",
            "codex_rename_scan_commands(limit=20, show_cwd=true)",
            "codex_rename_preview_tail_rename(limit=20)",
            f"codex_rename_apply_tail_rename(confirm_token='{CONFIRM_RENAME_TOKEN}')",
        ],
        "rollback_flow": [
            "codex_rename_recent(limit=2)",
            "codex_rename_rollback(backup, dry_run=true)",
            f"codex_rename_rollback(backup, dry_run=false, confirm_token='{CONFIRM_ROLLBACK_TOKEN}')",
        ],
        "write_confirm_token": CONFIRM_RENAME_TOKEN,
        "rollback_confirm_token": CONFIRM_ROLLBACK_TOKEN,
        "safety": "Local metadata hack; writes are backed up by codex_thread_manager.py. Do not edit state files manually.",
    }


if __name__ == "__main__":
    mcp.run()
