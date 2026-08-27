# feishu-notify

> 一句话：Claude 干活时，自动通过飞书给你发消息，你不在电脑前也知道进度。

插件机制下，hooks 通过 `hooks/hooks.json` 注册，脚本用 `${CLAUDE_PLUGIN_ROOT}` 引用，启用后**对所有项目全局生效**，不用每个项目重复配。

## 什么时候会收到通知

| 事件 | 卡片标题 | 什么时候发 |
| --- | --- | --- |
| `Notification` | 🔔 待处理 | 需要你确认权限，或闲置 ≥60 秒 |
| `Stop` | ✅ 已完成 | Claude 写完一轮回复 |
| `SubagentStop` | 🧩 子任务完成 | 子代理干完活 |
| `UserPromptSubmit` | — | 你发了新指令 |
| `SessionStart` / `SessionEnd` | — | 会话开始 / 结束 |
| `PreToolUse` / `PostToolUse` | — | 每次工具调用前 / 后 |

想加减事件：改 `hooks/hooks.json` 的事件键，并同步 `hooks/feishu_config.json` 的 `enabled_events`。

## 一次性配置（飞书侧）

1. 飞书开放平台建**自建应用**，开 `im:message` 权限并发布，拿 App ID / App Secret。
2. 拿到你的 `union_id`（跨应用通用，推荐）或 `user_id` / `open_id`。
3. 复制模板填好：`cp hooks/feishu_config.example.json hooks/feishu_config.json`。

自测（收到飞书卡片即成功；失败看 `hooks/feishu_notify.log`）：
```bash
echo '{"hook_event_name":"Notification","message":"测试","cwd":".","session_id":"t1"}' \
  | python "hooks/feishu_notify.py"
```

## 怎么启用

### 方式 A：本地先试
```bash
claude --plugin-dir <本仓库根>/feishu-notify
```

### 方式 B：常驻安装
```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install feishu-notify@z-claude-plugins
```

## ⚠️ 别收重复通知

如果你以前在**某个项目**里也配过同样的飞书通知（项目级 `.claude/settings.json` + `.claude/hooks/`），启用本插件后会**收到两次**。确认插件通知正常后，删掉项目里的那份：
```bash
rm -f <旧项目>/.claude/settings.json
rm -rf <旧项目>/.claude/hooks
```

## 注意
- `hooks/feishu_config.json` 含密钥，已 gitignore，千万别提交。
- 脚本任何异常都吞掉、永远退出码 0，通知失败也绝不阻断 Claude。

## 目录结构（本插件内）

```
feishu-notify/
├── .claude-plugin/plugin.json      # 插件清单
├── hooks/
│   ├── hooks.json                  # 注册的 hook 事件
│   ├── feishu_notify.py            # 通知脚本（编排 + 建卡，纯标准库）
│   ├── feishu_client.py            # FeishuClient 深模块（鉴权 + 传输）
│   ├── throttle.py                 # 节流闸门（跨进程冷却）
│   ├── delivery_rules.py           # 投递规则
│   ├── notifiers.py                # 多通道 Notifier 注册表
│   ├── renderers.py                # 卡片渲染器
│   ├── feishu_config.py            # 配置读取
│   ├── test_*.py                   # 零网络单测（unittest）
│   ├── feishu_config.json          # 真实配置（含密钥，已 gitignore）
│   └── feishu_config.example.json # 配置模板（可提交）
├── docs/                           # ADR
├── skills/                         # 未来放 skills
├── commands/                       # 未来放 commands
├── CLAUDE.md                       # 插件说明 + 根 AGENTS.md 守则指针
└── README.md
```
