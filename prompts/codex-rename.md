帮助用户直接重命名本机 OpenAI Codex VS Code 对话；支持单会话，也支持多个并行会话从各自对话末尾解析 `/codex rename 新标题` 后批量重命名。

用户输入：$ARGUMENTS

定位策略：
- 单会话模式：如果用户在本命令参数里明确给出新标题或 session id，沿用最近更新时间最高的 `source = vscode` thread，或使用用户给出的 id。
- 并行模式：如果多个 VS Code Codex 面板同时运行，用户可以分别在各自对话末尾输入一行：`/codex rename 新标题`。本命令扫描最近的 VS Code rollouts，按每个 thread 自己末尾的命令解析新标题，避免全部误改成同一个名字。
- “运行中的对话”无法由官方 API 精确枚举；这里以 `state_5.sqlite` 里最近更新的 `source = vscode` threads + rollout 尾部用户消息作为候选。
- 不做复杂历史管理；复杂搜索、标签、备注、归档交给 Codex History Viewer / CC Switch / 其他插件。

优先使用本项目脚本：

```powershell
python "<codex-rename-repo>\codex_thread_manager.py" list --limit 1 --show-cwd
python "<codex-rename-repo>\codex_thread_manager.py" list --limit 5 --show-cwd
python "<codex-rename-repo>\codex_thread_manager.py" scan-rename-commands --limit 20 --show-cwd
python "<codex-rename-repo>\codex_thread_manager.py" tail-rename --limit 20 --apply
python "<codex-rename-repo>\codex_thread_manager.py" rename --id <SESSION_ID> --title "新标题"
python "<codex-rename-repo>\codex_thread_manager.py" rollback --backup "<BACKUP_DIR>"
python "<codex-rename-repo>\codex_thread_manager.py" rollback --backup "<BACKUP_DIR>" --dry-run
python "<codex-rename-repo>\codex_thread_manager.py" recent --limit 2
```

默认工作流：
1. 从用户输入中提取新标题或模式。
   - 单会话常见输入：`/codex-rename 新标题`
   - 并行会话推荐：在每个要重命名的对话末尾发一行 `/codex rename 新标题`，然后在任意一个对话执行 `/codex-rename` 或要求“批量处理重命名”。
2. 如果 `$ARGUMENTS` 为空、或用户说“批量/并行/扫描/处理末尾命令”，先运行 `scan-rename-commands --limit 20 --show-cwd` 展示匹配到的 id、旧标题、新标题、cwd、rollout。
3. 若扫描结果合理，默认直接运行 `tail-rename --limit 20 --apply`。该命令会批量处理所有 pending `/codex rename 新标题`，已同名的跳过。
4. 如果 `$ARGUMENTS` 明确是一个新标题，使用单会话模式：没有 session id 时先 `list --limit 1 --show-cwd`，然后 `rename --id <SESSION_ID> --title "新标题"`。
5. 真正 rename 会备份 state_5.sqlite、session_index.jsonl 和 rollout 文件，并同步更新 SQLite、session_index，再向 rollout 追加 thread_name_updated 事件。
6. 输出必须保留脚本打印的 `Backup:` 路径、`Recent rename index:` 路径和 `Rollback command:`，这是回滚与后续加载入口。
7. 默认只保留最近 3 个 rename 备份；脚本会自动清理更旧且属于同一个 CODEX_HOME 的 `codex-thread-rename-backup-*` 目录。默认只保留最近 2 次重命名元数据，位置是 `~/.codex/thread-manager/recent-renames.json`。
8. 完成后提醒：执行 `Developer: Reload Window` 或重启 VS Code / Codex 插件刷新历史缓存。
9. 如果用户说“回滚/撤销刚才改名”，使用上一轮输出的 `Backup:` 路径执行 `rollback --backup <BACKUP_DIR>`；如果不确定，先 `rollback --dry-run`。如果用户说“加载上次/前两次重命名的对话”，先运行 `recent --limit 2` 展示 id 与 rollout 路径，再按用户指定 id 加载，不要默认加载原始对话内容。
10. 不要手动删除最新 3 个备份，除非用户明确要求。

注意：这是本地 metadata hack，不是 OpenAI 官方 VS Code UI 功能。更安全但较麻烦的官方路径是 `codex resume <id>` 后在 CLI 内 `/rename 新标题`。

