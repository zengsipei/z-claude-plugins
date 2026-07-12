# z-cc-plugin

> 仓库地址：https://github.com/zengsipei/z-cc-plugin（Public）

个人 Claude Code 插件工具箱。当前包含的第一个功能点：**飞书通知**——
Claude 触发特定 hook 时，自动通过飞书自建应用给你发私聊卡片，
让你不在电脑前也能知道「待处理 / 已完成 / 子任务完成」。

插件机制下，hooks 通过 `hooks/hooks.json` 注册，脚本用
`${CLAUDE_PLUGIN_ROOT}` 引用，启用后**对所有项目全局生效**，
无需在每个项目里重复配置。

## 目录结构

```
z-cc-plugin/
├── .claude-plugin/
│   └── plugin.json          # 插件清单（name / description / version / author）
├── hooks/
│   ├── hooks.json           # 注册的 hook 事件（Notification / Stop / SubagentStop）
│   ├── feishu_notify.py     # 通知脚本（编排 + 建卡，纯标准库，无需 pip）
│   ├── feishu_client.py     # FeishuClient 深模块（鉴权 + 传输，纯标准库）
│   ├── test_feishu_client.py# FeishuClient 零网络单测（unittest）
│   ├── feishu_config.json   # 真实配置（含密钥，已 gitignore）
│   └── feishu_config.example.json  # 配置模板（可提交）
├── docs/
│   ├── agents/              # Matt 工程 skill 仓库级配置（issue-tracker / triage-labels / domain）
│   └── adr/                 # 架构决策记录（ADR，如 0001 纯 stdlib 决策）
├── skills/                  # 未来放 skills（每个 <name>/SKILL.md）
├── commands/                # 未来放 commands（平面 markdown）
├── CLAUDE.md                # 工程 skill 配置入口 + 通用编码准则
├── .gitignore
└── README.md
```

## 通知的事件

| 事件 | 卡片标题 | 触发时机 |
| --- | --- | --- |
| `Notification` | 🔔 待处理 | 需要工具权限确认，或输入空闲 ≥60s（待确认/待输入） |
| `Stop` | ✅ 已完成 | Claude 完成一轮回复 |
| `SubagentStop` | 🧩 子任务完成 | 子代理执行结束 |

想增减事件：改 `hooks/hooks.json` 的事件键，并同步改 `feishu_config.json` 的 `enabled_events`。

## 一次性配置（飞书）

1. 飞书开放平台建自建应用，开 `im:message` 权限并发布，拿 App ID / App Secret。
2. 拿到你的 `union_id`（跨应用通用，推荐）或 `user_id` / `open_id`。
3. 复制 `hooks/feishu_config.example.json` 为 `hooks/feishu_config.json` 并填好。

自测：
```bash
echo '{"hook_event_name":"Notification","message":"测试","cwd":".","session_id":"t1"}' \
  | python "hooks/feishu_notify.py"
```
收到飞书卡片即成功；失败原因看 `hooks/feishu_notify.log`。

## 启用插件

### 方式 A：本地临时加载（先验证）
```bash
claude --plugin-dir <插件仓库根目录绝对路径>
```
仅当前会话生效，方便调试。

### 方式 B：作为常驻插件（推荐）
在 Claude Code 里：
```
/plugin marketplace add https://github.com/zengsipei/z-cc-plugin
/plugin install z-cc-plugin
```
或把它放进 `~/.claude/plugins/z-cc-plugin` 并启用。具体以 `/plugin` 命令提示为准。

## 重要：避免重复通知

如果你之前在**某个项目**里也配过相同的飞书通知（项目级 `.claude/settings.json`
+ `.claude/hooks/`），启用本插件后该事件会**触发两次**（项目 + 插件各一次）。
确认插件通知正常后，删除项目里的那份即可：
```bash
rm -f <旧项目>/.claude/settings.json
rm -rf <旧项目>/.claude/hooks
```

## 如何扩展新功能点

本插件定位是「个人工具箱」，新增功能按类型放进对应目录即可，互不干扰：

- **新的 hook 类功能** → 在 `hooks/hooks.json` 增加事件；脚本放在 `hooks/`。
- **slash command** → 在 `commands/` 放 `<name>.md`。
- **skill** → 在 `skills/<name>/SKILL.md`。
- **自定义 agent** → 在 `agents/` 放定义。

每次改完在 Claude Code 里 `/reload-plugins` 重新加载。

## 注意

- `hooks/feishu_config.json` 含密钥，已加入 `.gitignore`，切勿手动提交。
- 脚本任何异常都吞掉、永远退出码 0，通知失败也绝不阻断 Claude。
