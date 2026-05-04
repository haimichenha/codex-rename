帮助用户直接重命名“当前/最近的”本机 OpenAI Codex VS Code 对话。

用户输入：$ARGUMENTS

定位策略：
- 本命令默认只服务一个目标：把最近更新时间最高的 `source = vscode` Codex thread 当作“当前对话候选”。
- 不做复杂历史管理；复杂搜索、标签、备注、归档交给 Codex History Viewer / CC Switch / 其他插件。
- 如果用户明确给出 session id，则使用该 id；否则默认使用最近一条 VS Code thread。
- 如果同时开了多个 Codex 面板，最近一条可能不是当前面板；但本命令默认接受“最近对话”策略。

优先使用本项目脚本：

```powershell
python "<codex-rename-repo>\codex_thread_manager.py" list --limit 1 --show-cwd
python "<codex-rename-repo>\codex_thread_manager.py" list --limit 5 --show-cwd
python "<codex-rename-repo>\codex_thread_manager.py" rename --id <SESSION_ID> --title "新标题"
python "<codex-rename-repo>\codex_thread_manager.py" rollback --backup "<BACKUP_DIR>"
python "<codex-rename-repo>\codex_thread_manager.py" rollback --backup "<BACKUP_DIR>" --dry-run
python "<codex-rename-repo>\codex_thread_manager.py" recent --limit 2
```

默认工作流：
1. 从用户输入中提取新标题；如果 `$ARGUMENTS` 为空，先问用户要改成什么标题。
2. 如果用户没有给出明确 session id，运行 `list --limit 1 --show-cwd` 获取最近 VS Code thread 候选。
3. 默认直接执行真正 rename，不再额外确认。
4. 输出必须保留脚本打印的 `Backup:` 路径、`Recent rename index:` 路径和 `Rollback command:`。
5. 默认只保留最近 3 个 rename 备份；默认只保留最近 2 次重命名元数据。
6. 完成后提醒：执行 `Developer: Reload Window` 或重启 VS Code / Codex 插件刷新历史缓存。
7. 如果用户说“回滚/撤销刚才改名”，使用上一轮输出的 `Backup:` 路径执行 `rollback --backup <BACKUP_DIR>`；不确定时先 `--dry-run`。
8. 如果用户说“加载上次/前两次重命名的对话”，先运行 `recent --limit 2` 展示 id 与 rollout 路径，再按用户指定 id 加载，不要默认加载原始对话内容。

注意：这是本地 metadata hack，不是 OpenAI 官方 VS Code UI 功能。更安全但较麻烦的官方路径是 `codex resume <id>` 后在 CLI 内 `/rename 新标题`。
