# codex-rename

本地 OpenAI Codex VS Code 对话重命名小工具。

它不是 OpenAI 官方 UI 功能，而是一个保守的本地 metadata helper：重命名前自动备份，写入失败可回滚。

## 能做什么

- 列出最近的 Codex threads，默认只看 `source = vscode`
- 重命名指定 thread/session id
- 同步更新：
  - `~/.codex/state_5.sqlite` 的 `threads.title`
  - `~/.codex/session_index.jsonl` 的 `thread_name`
  - 对应 `rollout-*.jsonl` 追加 `thread_name_updated` 事件
- 每次重命名前备份相关文件
- 默认只保留最近 3 个 rename 备份
- 记录最近 2 次重命名元数据到 `~/.codex/thread-manager/recent-renames.json`
- 支持按备份目录回滚

## 使用

先关闭或 Reload VS Code/Codex 面板会更稳；重命名后也建议执行 `Developer: Reload Window`。

```powershell
python .\codex_thread_manager.py list --limit 5 --show-cwd
python .\codex_thread_manager.py rename --id <SESSION_ID> --title "新标题"
python .\codex_thread_manager.py recent --limit 2
python .\codex_thread_manager.py rollback --backup "<BACKUP_DIR>" --dry-run
python .\codex_thread_manager.py rollback --backup "<BACKUP_DIR>"
```

如果设置了自定义 Codex home：

```powershell
python .\codex_thread_manager.py --codex-home "C:\Users\you\.codex" list --limit 5
```

## 推荐的 `/codex-rename` 工作流

1. 用户输入 `/codex-rename 新标题`。
2. 先运行：

   ```powershell
   python "<repo>\codex_thread_manager.py" list --limit 1 --show-cwd
   ```

3. 将最近更新时间最高的 `source = vscode` thread 当作当前候选。
4. 直接执行：

   ```powershell
   python "<repo>\codex_thread_manager.py" rename --id <SESSION_ID> --title "新标题"
   ```

5. 输出中保留 `Backup:`、`Recent rename index:` 和 `Rollback command:`。
6. 提醒用户 Reload Window / 重启 VS Code 刷新缓存。

复杂历史管理、标签、备注、归档建议交给 Codex History Viewer、CC Switch 等插件。

## 风险说明

这是本地 metadata hack，不是 OpenAI 官方 VS Code UI 功能。Codex 本地存储结构未来可能变化。使用前请确认脚本输出的候选 thread 是你想改的对话，并保留备份。
