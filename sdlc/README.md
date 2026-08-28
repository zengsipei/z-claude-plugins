# sdlc

> 一句话：这个插件把 software-dev-process 的软件开发生命周期纪律搬进 Claude Code——文档先行、对抗性 grill 定稿、确定性阶段门禁、跨会话 AI 登记续接。

本插件是把上游 [software-dev-process](https://github.com/AtlantisYuki/prompt)（快照移植）的纪律适配为 Claude Code 插件：一条命令安装、开箱即用。属于市场 [`z-claude-plugins`](https://github.com/zengsipei/z-claude-plugins)。

## 怎么启用

```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install sdlc@z-claude-plugins
```

## 怎么用（入口词）

sdlc 没有命令面：装好后，在对话里说出入口词（或直接说要干哪个阶段的活），就会进入对应流程。

| 入口词 | 干嘛 |
| --- | --- |
| `sdlc-design-1` / `sdlc-design-2` | 分层写设计文档，对抗性 grill 到定稿 |
| `sdlc-implement` / `sdlc-test` | 按设计施工 / 测试 |
| `sdlc-solo` | 标准流程一条龙跑到测试完，自动收尾 |
| `sdlc-debug` / `sdlc-script` | 独立排查 Bug / 执行脚本（只在你显式点名时才触发） |
| `sdlc-close` | 校验关闭门禁后收口 |
| `sdlc-history` | 登记 / 查历史会话 |

大图景：

```
会话开始 ─▶ SessionStart 钩子注入 sessionId（跨会话续接的身份证）
   ▼
design-1/2：文档先行 + grill 定稿 ─▶ implement ─▶ test
   ▼
close：过门禁才收口；产物全部落在 docs/[需求目录]/
```

## 快照溯源与许可

- **upstream**: AtlantisYuki/prompt@7cdfc64588a1a8eb7d338e3f6f717f1c7dabcd81 (2026-07-22)
- 上游以 MIT 许可发布，本插件在移植时保留对其作者 **AtlantisYuki** 的署名。

## Windows-only 说明

SessionStart 钩子（`hooks/cc_session_start.ps1`）是 PowerShell 脚本，**仅在 Windows 上工作**。在非 Windows 平台，hook 注入缺失时按 [`references/registration.md`](skills/sdlc/references/registration.md) 既有的可信 sessionId 协议降级：跳过登记，并在 `status.md` 里记录原因，不影响其余流程。Python 面的跨平台核心——任务状态机（`task_state_core.py`）与登记核心（`ai_register_core.py`）——不受影响，任何平台都可用。

## 安装器勿用

`skills/sdlc/scripts/` 下的 `install_codex_hook.ps1` 与 `install_grok_hook.ps1` 是随上游快照一并留存的参考脚本，**不是本插件的安装路径**。安装本插件请只用上文的两步 marketplace 命令。

## 与 dsh-spec 共存

本插件与同市场的 [dsh-spec](https://github.com/zengsipei/z-claude-plugins/tree/main/dsh-spec) 可以装在同一个仓库里，文件面互不相交：

- dsh-spec 只写 `.agents/notes/`、`.agents/RULES.md`、`.agents/LEDGER.md`。
- sdlc 对 `.agents/` 只有一处**条件读取**（设计前读 `.agents/AGENTS.md`，不存在即跳过），其余产物全部落在 `docs/[需求目录]/`。
- 双插件仓库中，dsh-spec 的会话结束提醒闸口打「未留账」属于预期行为（sdlc 的文档产物不进台账），不阻断任何操作。
- 两个插件互不设优先级，各自按自己的纪律运行。
