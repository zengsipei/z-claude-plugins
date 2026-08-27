# dsh-spec

> 一句话：这个插件帮你的项目「记笔记 + 立规矩」，让 AI 在写了几百个 commit 后还能看懂自己以前干了啥。

它是把 deepseek-harness（dsh）的**活文档与变更台账纪律**搬进 Claude Code 的插件：
- **活文档**：`SPEC.md`（这项目是啥）/ `ARCHITECTURE.md`（怎么搭的）。
- **变更台账**：每次大改动都记一笔到 `.agents/notes`。
- **评审闸门**：合并前检查「改了的东西有没有记笔记」。

本插件属于市场 [`z-claude-plugins`](https://github.com/zengsipei/z-claude-plugins)。

## 四个命令（你只要会这四个）

| 命令 | 干嘛 |
| --- | --- |
| `/dsh-spec-init` | 在新项目里搭好活文档和台账 |
| `/dsh-spec-note` | 记一笔改动（写进 `.agents/notes`） |
| `/dsh-spec-review` | 合并前闸门：多轴评审（code / notes / test / types） |
| `/dsh-spec-rot` | 定期体检（六查），恒 warn-only、零退出 |

命令只负责「接参数、叫 skill」：参数签名的权威说明在各命令 description 与同名 skill；全部共享规则（分类、lifecycle、slug、路径、模板、阈值、warn-only、归档）的单一事实源是 [`RULES.md`](RULES.md)，`/dsh-spec-init` 会把它复制到你的项目 `.agents/RULES.md`。

## 装到你的项目后，会长这样

```
<你的项目>/
├── SPEC.md              # 这项目是干嘛的、不干嘛、术语表
├── ARCHITECTURE.md      # 改之前必读：模块边界、关键不变量、决策索引
├── docs/adr/            # 正式、难回退的架构决策（0001 起编号）
├── .agents/
│   ├── notes/           # 变更台账：<生命周期>/<类别>/<日期>-<slug>.md
│   ├── RULES.md         # 共享规则（dsh-spec/RULES.md 的副本）
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
- 术语以 `SPEC.md` 术语表为准；共享规则以 `.agents/RULES.md` 为准。

## 当前状态

- ✅ 脚手架 + 四个命令 / skill（T1 #20 落地）。
- ✅ 评审 / 预推闸门（D3 #18 落地）：**分层双闸**——
  - **权威闸口** `/dsh-spec-review --gate strict`：人触发，合并前跑，缺笔记就阻断。
  - **提醒闸口** `hooks/dsh-spec-gate.py`：会话结束（Stop）时若工作树有改动却没笔记，向 stderr 提醒，**不阻断**。
- ✅ v2 三大支柱落地（B1 #34 / B2 #35 / B3 #36）：评审多轴（code/notes/test/types）+ rot 六查（docs/notes/tests/adr/simplify/types，自包含层 + 工具增强层双层信号）；评审准则全内化、零外部技能依赖。
- ✅ 架构深化（#38）：`RULES.md` 单一事实源 + 命令层纯接口化——共享规则只写一处，命令只做委派。
- ⏳ 留待：多项目复用、dsh-spec 自己吃狗粮（须开新项目，非本仓）。

## 目录结构（本插件内）

```
dsh-spec/
├── .claude-plugin/plugin.json
├── commands/        # 4 个命令（纯接口，调 skill）
├── skills/          # 4 个同名 skill（真正逻辑）
├── hooks/
│   ├── hooks.json   # Stop 钩子注册
│   └── dsh-spec-gate.py  # warn-only 提醒闸口（已实现）
├── RULES.md         # 共享规则单一事实源（/dsh-spec-init 复制到项目 .agents/RULES.md）
├── LEDGER.md        # 台账索引种子（/dsh-spec-init 复制到项目）
├── CLAUDE.md
└── README.md
```
