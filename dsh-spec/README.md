# dsh-spec

> 个人 Claude Code 插件：把 deepseek-harness（dsh）的**活文档与变更台账纪律**——
> 活文档（SPEC.md / ARCHITECTURE.md）+ 变更台账（`.agents/notes`）+ 评审/预推闸门——
> 移植进来，让 agent 在大量 commit 后仍保持 coherent、可追责、不腐烂。
> 本插件属于市场 [`z-claude-plugins`](https://github.com/zengsipei/z-claude-plugins) 的一部分。

v1 核心脊柱（已定）：活文档脚手架 + 变更台账 + 评审/预推闸门。
支柱 3（测试不变量）、5（简化发现）、6（强类型/防御式）留 v2。

## 四个命令（用户入口）

| 命令 | 作用 | 委派 skill |
| --- | --- | --- |
| `/dsh-spec-init [--root .] [--force]` | 在消费项目根脚手架化活文档与台账 | `dsh-spec-init` |
| `/dsh-spec-note "<slug>" [--class ...] [--lifecycle ...]` | 记一笔非平凡改动到变更台账 | `dsh-spec-note` |
| `/dsh-spec-review [--since <ref>] [--gate strict|warn]` | 合并前闸门：code-review + 无 note 审计 | `dsh-spec-review` |
| `/dsh-spec-rot [--check all|docs|notes|tests|adr]` | 漂移与一致性巡检 | `dsh-spec-rot` |

命令只做参数解析与委派，逻辑全在同名 skill。评审闸门复用本仓库已有的 `code-review` skill，不重造。

## 目录结构（本插件内）

```
dsh-spec/
├── .claude-plugin/
│   └── plugin.json          # 插件清单（name=dsh-spec / version / keywords）
├── commands/                # 4 个 slash 命令（薄包装，委派 skill）
│   ├── dsh-spec-init.md
│   ├── dsh-spec-note.md
│   ├── dsh-spec-review.md
│   └── dsh-spec-rot.md
├── skills/                  # 4 个同名 skill（真正逻辑）
│   ├── dsh-spec-init/SKILL.md
│   ├── dsh-spec-note/SKILL.md
│   ├── dsh-spec-review/SKILL.md
│   └── dsh-spec-rot/SKILL.md
├── hooks/
│   ├── hooks.json           # 轻量闸门占位（行为待 D3 #18 决定）
│   └── dsh-spec-gate.py     # no-op 占位实现（D3 关闭后替换）
├── LEDGER.md                # 变更台账索引种子样板（/dsh-spec-init 复制到消费项目）
├── CLAUDE.md                # 插件说明 + 纪律规则
└── README.md
```

## 消费项目落地后长这样

```
<消费项目>/
├── SPEC.md                  # 产品视角：目的/范围/非目标/术语表/当前状态快照
├── ARCHITECTURE.md          # 工程视角：改前必读 + 模块边界 + 关键不变量 + 决策索引
├── docs/adr/                # 正式、难逆转的架构决策（顺序编号 0001+）
│   └── 0000-template.md
├── .agents/
│   ├── notes/               # 变更台账：<lifecycle>/<class>/<date>-<slug>.md
│   │   ├── proposed/<class>/
│   │   ├── implemented/<class>/
│   │   └── rejected/<class>/
│   └── LEDGER.md            # 变更台账索引（六类分节，日期倒序）
└── CLAUDE.md                # 追加 dsh-spec 纪律规则块
```

## 启用插件

本插件通过市场 [`z-claude-plugins`](https://github.com/zengsipei/z-claude-plugins) 安装：

### 方式 A：本地临时加载（先验证）
```bash
claude --plugin-dir <本仓库根目录>/dsh-spec
```
仅当前会话生效，方便调试。

### 方式 B：作为常驻插件（推荐）
```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install dsh-spec@z-claude-plugins
```

## 纪律规则（/dsh-spec-init 会写入消费项目 CLAUDE.md）

- 改动前先读 `ARCHITECTURE.md`；动了结构 / 契约 / 不变量，同步 `SPEC.md` 并补 note/ADR。
- 每个非平凡改动后跑 `/dsh-spec-note` 留一笔（feature/bug-fix/simplification/architecture/process/testing）。
- 合并前跑 `/dsh-spec-review`（无 note 不合并）。
- 定期 `/dsh-spec-rot` 巡检漂移。
- 术语以 `SPEC.md` 术语表为准。

## 状态

- 脚手架与四个命令/skill 已由 T1 (#20) 落地。
- 评审/预推闸门行为（hooks）待 D3 (#18) 决定，当前 `dsh-spec-gate.py` 为 no-op 占位。
- 多项目复用、dsh-spec 自身吃狗粮、rot 具体检查项细化等见地图 Not yet specified。
