# Agent notes

## 参考代码工作流（XERJ）

本项目接入本地 XERJ 检索引擎（systemd 用户服务 `xerj.service`，节点 `http://localhost:9200`，
数据目录 `~/xerj-data`）。服务状态：`systemctl --user status xerj`。

**写代码前，先检索参考实现**——尤其是这些历史踩过坑的领域：
托盘图标、窗口生命周期、打包/分发、SSH 隧道守护、自动更新。

### 可用语料库

| 语料库 | 内容 | 典型问题 |
|---|---|---|
| `pystray` | 系统托盘库（LGPL） | 菜单动作契约、图标注册失败、任务栏重建、通知气泡 |
| `pywebview` | 窗口库（BSD） | 窗口隐藏/恢复、事件（closing/minimized）、多窗口 |
| `pyinstaller` | 打包器（GPL） | onefile/onedir、资源打包、`sys._MEIPASS`、启动失败 |
| `autossh` | SSH 隧道守护（无许可证声明） | 重连策略、保活、监控端口 |
| 本项目 | 自身源码（默认 `ax-*` 前缀） | 用 `xerj search "<词>"` / `xerj def "<符号>"` 定位 |

### 命令

```bash
xerj code pystray "menu item action requires two arguments"
xerj code pyinstaller "onedir vs onefile extraction sys._MEIPASS"
xerj code autossh "reconnect strategy keepalive"
xerj def "build_menu"                  # 本项目符号定位（file:line + 签名）
xerj search "Shell_NotifyIcon retry"   # 本项目代码语义检索
```

MCP 工具（OpenCode 会话重启后生效）：`xerj_code_search`（{corpus, query}）、`xerj_search`、`xerj_def`。

### 规则

- 引用检索结果时标注 `项目/文件:行号`（段落里会直接给出）。
- **许可**：检索输出会带许可提示；LGPL/GPL 仓库**借鉴思路、不要照抄代码**，
  只适配机制（例如"菜单动作只允许 0~2 个参数"这类契约）。
- 检索不到相关内容时明确说明，不要凭空猜测；用源码核实后再写。
- 新仓库入索引：`xerj corpus add <name> <git-url> && xerj corpus index <name>`
  （工作目录随 corpora 位于 `~/.xerj-code/`）。

## XERJ (code search)

This project uses XERJ for reference coding. Before writing code that touches
unfamiliar territory: `xerj def "<symbol>"` for go-to-definition, or
`xerj search "<plain words>"` for ranked, definition-first passages.
Index a repo with `xerj autoindex <folder>`. Cite file:line for anything you rely on.
