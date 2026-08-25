# dsh-spec

> 一句话：这个插件帮你的项目「记笔记 + 立规矩」，让 AI 在写了几百个 commit 后还能看懂自己以前干了啥。

它是把 deepseek-harness（dsh）的**活文档与变更台账纪律**搬进 Claude Code 的插件：
- **活文档**：`SPEC.md`（这项目是啥）/ `ARCHITECTURE.md`（怎么搭的）。
- **变更台账**：每次大改动都记一笔到 `.agents/notes`。
- **评审闸门**：合并前检查「改了的东西有没有记笔记」。

本插件属于市场 [`z-claude-plugins`](https://github.com/zengsipei/z-claude-plugins)。

## 四个命令（你只要会这四个）

| 命令 | 干嘛 | 背后逻辑 |
| --- | --- | --- |
| `/dsh-spec-init [--root .] [--force]` | 在新项目里搭好活文档和台账 | skill `dsh-spec-init` |
| `/dsh-spec-note "<slug>"` | 记一笔改动（feature / bug-fix / ...） | skill `dsh-spec-note` |
| `/dsh-spec-review [--since <ref>] [--gate strict|warn]` | 合并前闸门：跑评审 + 查笔记缺口 | skill `dsh-spec-review` |
| `/dsh-spec-rot [--check all|docs|notes|tests|adr]` | 定期体检：文档漂没漂、漏没漏笔记 | skill `dsh-spec-rot` |

命令只负责「接参数、叫 skill」，真正的活都在同名 skill 里。评审复用本仓库已有的 `code-review` skill，不重造。

## 装到你的项目后，会长这样

```
<你的项目>/
├── SPEC.md              # 这项目是干嘛的、不干嘛、术语表
├── ARCHITECTURE.md      # 改之前必读：模块边界、关键不变量、决策索引
├── docs/adr/            # 正式、难回退的架构决策（0001 起编号）
├── .agents/
│   ├── notes/           # 变更台账：<生命周期>/<类别>/<日期>-<slug>.md
│   └── LEDGER.md        # 台账总索引
└── CLAUDE.md            # 追加 dsh-spec 纪律规则
```

## 怎么启用

### 方式 A：本地先试（推荐先验证）
```bash
claude --plugin-dir <本仓库根>/dsh-spec
```
仅当前会话生效，方便调试。

### 方式 B：常驻安装
```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install dsh-spec@z-claude-plugins
```

## 你要遵守的规矩（/dsh-spec-init 会写进项目 CLAUDE.md）

- 改结构 / 契约 / 不变量之前，先读 `ARCHITECTURE.md`。
- 每次大改动后跑 `/dsh-spec-note` 留一笔。
- 合并前跑 `/dsh-spec-review`（没笔记不让合）。
- 定期跑 `/dsh-spec-rot` 体检。
- 术语以 `SPEC.md` 术语表为准。

## 当前状态

- ✅ 脚手架 + 四个命令 / skill（T1 #20 落地）。
- ✅ 评审 / 预推闸门（D3 #18 落地）：**分层双闸**——
  - **权威闸口** `/dsh-spec-review --gate strict`：人触发，合并前跑，缺笔记就阻断。
  - **提醒闸口** `hooks/dsh-spec-gate.py`：会话结束（Stop）时若工作树有改动却没笔记，向 stderr 提醒，**不阻断**。
- ⏳ 留 v2：多项目复用、dsh-spec 自己吃狗粮、rot 检查项细化、测试不变量支柱。

## 目录结构（本插件内）

```
dsh-spec/
├── .claude-plugin/plugin.json
├── commands/        # 4 个命令（薄包装，调 skill）
├── skills/          # 4 个同名 skill（真正逻辑）
├── hooks/
│   ├── hooks.json   # Stop 钩子注册
│   └── dsh-spec-gate.py  # warn-only 提醒闸口（已实现）
├── LEDGER.md        # 台账索引种子（/dsh-spec-init 复制到项目）
├── CLAUDE.md
└── README.md
```
