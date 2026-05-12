---
name: codex-rename
description: Rename local OpenAI Codex VS Code conversations with a short MCP-first workflow. Use when the user writes "/codex-rename", "/codex rename", asks to rename the current Codex chat/thread/session, batch rename parallel Codex panels from trailing commands, inspect recent rename metadata, or rollback a previous Codex rename. Prefer codex-rename MCP tools and avoid loading long prompt context.
---

# Codex Rename Skill

Thin trigger layer only. Do not paste or reconstruct the old long prompt. The execution logic lives in the `codex-rename` MCP server and `codex_thread_manager.py`.

## Preferred path

When available, use the `codex-rename` MCP tools:

- `codex_rename_help()` for the short workflow and confirmation tokens.
- `codex_rename_list_threads(limit=1, show_cwd=true)` to identify the most recent VS Code Codex thread.
- `codex_rename_thread(thread_id, title, dry_run=true, confirm_token="")` before a single-thread write.
- `codex_rename_thread(..., confirm_token="CONFIRM_CODEX_RENAME_WRITE")` only after the user clearly wants the rename.
- `codex_rename_scan_commands(...)` and `codex_rename_preview_tail_rename(...)` for parallel panels using trailing `/codex rename <title>` commands.
- `codex_rename_apply_tail_rename(confirm_token="CONFIRM_CODEX_RENAME_WRITE")` only after confirming the batch.
- `codex_rename_recent(...)` and `codex_rename_rollback(...)` for rollback workflows.

## Fallback path

If MCP is unavailable, run `codex_thread_manager.py` directly from this skill directory. Keep the response short and preserve script output lines containing:

- `Backup:`
- `Recent rename index:`
- `Rollback command:`

## Safety

This is a local metadata helper, not an official OpenAI UI API. Renames write local Codex metadata and rollout files, so keep backups and remind the user to run `Developer: Reload Window` or restart VS Code/Codex after a successful rename.
