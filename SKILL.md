---
name: codex-rename
description: Rename local OpenAI Codex VS Code conversations and safely switch Codex/cc-switch providers with a short MCP-first workflow. Use when the user writes "/codex-rename", "/codex rename", "/switch <provider>", asks to rename the current Codex chat/thread/session, batch rename parallel Codex panels, inspect recent rename metadata, rollback a previous Codex rename, verify active Codex provider, repair provider config contamination, or hot-apply provider URL/API-key settings. Prefer MCP tools and avoid loading long prompt context.
---

# Codex Rename Skill

Thin trigger layer only. Do not paste or reconstruct the old long prompt. The execution logic lives in the `codex-rename` MCP server and `codex_thread_manager.py`.
Provider switching logic lives in `codex_switch_manager.py` and `codex-switch.ps1`.

## Preferred path

When available, use the `codex-rename` MCP tools:

- `codex_rename_help()` for the short workflow and confirmation tokens.
- `codex_rename_list_threads(limit=1, show_cwd=true)` to identify the most recent VS Code Codex thread.
- `codex_rename_thread(thread_id, title, dry_run=true, confirm_token="")` before a single-thread write.
- `codex_rename_hot_thread(..., confirm_token="CONFIRM_CODEX_RENAME_WRITE")` for the currently active VS Code Codex thread: it writes immediately, then schedules a delayed same-title repair pass.
- `codex_rename_thread(..., confirm_token="CONFIRM_CODEX_RENAME_WRITE")` for inactive/older threads only after the user clearly wants the rename.
- `codex_rename_schedule_thread(..., confirm_token="CONFIRM_CODEX_RENAME_WRITE")` when only a delayed repair pass is needed.
- `codex_rename_scan_commands(...)` and `codex_rename_preview_tail_rename(...)` for parallel panels using trailing `/codex rename <title>` commands.
- `codex_rename_apply_tail_rename(confirm_token="CONFIRM_CODEX_RENAME_WRITE")` only after confirming the batch.
- `codex_rename_recent(...)` and `codex_rename_rollback(...)` for rollback workflows.

For provider switching:

- If the user message strictly matches `/switch <provider>`, do not answer as normal chat and do not use `/load`.
- Prefer `codex_switch_preview_provider(provider)` first when practical.
- Then use `codex_switch_provider(provider, confirm_token="CONFIRM_CODEX_SWITCH_WRITE")`.
- Verify with `codex_switch_diag()` that `codex_config.base_url`, `codex_config.model`, and the cc-switch current provider marker match.
- If the provider's saved URL/key is wrong, use `codex_switch_update_provider(...)` or pass `base_url` / `api_key_env` to `codex_switch_provider(...)`.
- Never print API keys. Prefer `api_key_env` over raw key arguments.

## Fallback path

If MCP is unavailable, run `codex_thread_manager.py` directly from this skill directory. Keep the response short and preserve script output lines containing:

- `Backup:`
- `Recent rename index:`
- `Rollback command:`

For the **currently active VS Code Codex thread**, preserve the hot-update
experience but add a delayed repair pass, because a direct metadata rename can
be overwritten by the still-running Codex process when it saves the current
turn. Prefer:

```powershell
python "<skill-dir>\codex_thread_manager.py" hot-rename --id <SESSION_ID> --title "新标题" --delay-seconds 10
```

This writes immediately so the title can refresh quickly, then schedules a
same-title repair pass after the assistant turn. If the user explicitly wants
only the delayed repair pass, use:

```powershell
python "<skill-dir>\codex_thread_manager.py" schedule-rename --id <SESSION_ID> --title "新标题" --delay-seconds 10
```

Then tell the user to wait for the delay and run `Developer: Reload Window` or
restart VS Code/Codex if the UI cache does not update. The scheduled command
prints a `Log:` path; inspect that log if the title still does not change.

## Safety

This is a local metadata helper, not an official OpenAI UI API. Renames write local Codex metadata and rollout files, so keep backups and remind the user to run `Developer: Reload Window` or restart VS Code/Codex after a successful rename.

Provider switching writes `~/.codex/config.toml`, `~/.codex/auth.json`, and cc-switch current-provider metadata. The switch helper creates ring backups and validates the current/target provider pair before writing. `/load <thread_id>` is only for loading sessions, not for switching providers.
