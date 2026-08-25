# dsh-spec v1 · 命令与技能集合设计（PROTOTYPE — D1 #16）

> PROTOTYPE，非交付物。用于反应取舍。真正的骨架由 T1 (#20) 落地。
> 锁定后：结论写入 #16 的 resolution comment 并关闭；本文件保留为设计史（T1 可删除或并入）。

## 决策摘要（已采纳 Q1–Q4）

1. **命令 ↔ 技能 分配**：4 个 slash 命令（用户入口，平面 `commands/*.md`）+ 4 个同名 skill（逻辑，放 `skills/<name>/SKILL.md`）。命令只做参数解析与委派，逻辑全在 skill。
2. **评审闸门复用**：`dsh-spec-review` skill **包装**已有 `code-review` skill，不重造评审逻辑；在其之上叠加「无 note 不合并」审计。
3. **hooks**：1 个轻量闸门 `dsh-spec-gate`（注册于 `hooks/hooks.json`），具体规则由 D3 (#18) 决定（闸门在 Stop 层还是评审层、是否硬阻断）。
4. **agents/**：v1 **不需要**自定义 agent。`code-review` 若内部用子代理是其自己的事，dsh-spec 不引入。
5. **台账/活文档落点**：脚手架产物生成在**消费项目**根（`SPEC.md` / `ARCHITECTURE.md` / `.agents/notes/` / `docs/adr/` / `.agents/LEDGER.md`），插件内只随附 `dsh-spec/LEDGER.md` 作为索引样板。note 模板细节归 D2 (#17)。

## 目录结构（目标骨架，PROTOTYPE）

```
dsh-spec/
├── .claude-plugin/plugin.json
├── commands/
│   ├── dsh-spec-init.md
│   ├── dsh-spec-note.md
│   ├── dsh-spec-review.md
│   └── dsh-spec-rot.md
├── skills/
│   ├── dsh-spec-init/SKILL.md
│   ├── dsh-spec-note/SKILL.md
│   ├── dsh-spec-review/SKILL.md
│   └── dsh-spec-rot/SKILL.md
├── hooks/
│   └── hooks.json          # 轻量闸门，行为由 D3 定
├── dsh-spec/LEDGER.md        # 索引样板（随插件分发）
├── README.md
└── CLAUDE.md
```

## 各命令 / 技能 设计

### /dsh-spec-init
- 参数：`[--root .] [--force]`（覆盖已存在文件）
- 行为（skill）：在消费项目根脚手架化 —— 建 `SPEC.md`、`ARCHITECTURE.md`、`.agents/notes/{proposed,implemented,rejected}/<class>/`、`docs/adr/`（含 ADR 模板）、`.agents/LEDGER.md` 索引。
- 产出：列出创建的文件；写入首条 LEDGER 索引。

### /dsh-spec-note
- 参数：`"<slug>" [--class feature|bug-fix|simplification|architecture|process|testing] [--lifecycle proposed|implemented|rejected] [--no-edit]`
- 行为（skill）：在 `.agents/notes/<lifecycle>/<class>/<date>-<slug>.md` 生成 note，必含章节 `## Problem` / `## Decision|Proposal` / **必填** `## Alternatives considered` / `## Consequences`；有 `$EDITOR` 则打开补全。
- 组合：每次非平凡改动后调用；评审闸门会检查是否缺 note。

### /dsh-spec-review
- 参数：`[--since <ref>] [--gate strict|warn]`
- 行为（skill）：**委派 `code-review` skill** 做标准评审，再叠加审计：自 `<ref>`（默认上次 merge）起的每个非平凡改动是否都有对应 note/ADR；`strict` 缺 note 即报错，`warn` 仅提醒。
- 组合：合并前跑；闸门逻辑细则在 D3 (#18)。

### /dsh-spec-rot
- 参数：`[--check all|docs|notes|tests|adr]`
- 行为（skill）：漂移与一致性巡检 —— 文档漂移、无 note 的 commit、测试退化、ADR 过期。具体检查项归入地图 Not yet specified，本 prototype 仅定命令外形。
- 组合：定期（手动或 cron）跑。

## hooks/hooks.json（占位）

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/dsh-spec-gate.py\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```
> 仅占位。`Stop` 还是 `PreToolUse`、是否硬阻断、规则内容，由 D3 (#18) 决定。

## plugin.json（占位）

```json
{
  "name": "dsh-spec",
  "version": "0.1.0",
  "description": "把 deepseek-harness（dsh）的活文档与变更台账纪律（活文档 + 变更台账 + 评审/预推闸门）移植为 Claude Code 插件。",
  "author": { "name": "zsp", "url": "https://github.com/zengsipei" },
  "homepage": "https://github.com/zengsipei/z-claude-plugins/tree/main/dsh-spec",
  "repository": "https://github.com/zengsipei/z-claude-plugins",
  "license": "MIT",
  "keywords": ["living-docs", "agent-notes", "code-review", "spec", "doc-drift"]
}
```

## SKILL.md（frontmatter + 步骤，已按 /writing-for-agents 优化）

> 优化要点：description 前置触发词（上下文指针）；每步以「完成判定」收尾（清晰+有要求）；
> 范围用正向表述；删除冗余与否定式 no-op。

### skills/dsh-spec-init/SKILL.md
```
---
name: dsh-spec-init
description: 在项目中脚手架化 dsh-spec 的活文档与变更台账纪律——活文档（SPEC.md/ARCHITECTURE.md）、变更台账（.agents/notes）、ADR（docs/adr）、台账索引。当用户说「初始化 dsh-spec」「搭活文档骨架」「启用变更台账」「给项目加纪律」时调用。
---
# dsh-spec-init

每个项目跑一次，让后续改动有迹可循。

## 步骤
1. 解析 `--root`（默认 cwd）。若 `.agents/notes` 已存在，停下并告知 dsh-spec 已初始化（可加 `--force` 覆盖）。
   - 完成判定：目标目录确认为空白，或用户确认使用 `--force`。
2. 建目录树：`.agents/notes/{proposed,implemented,rejected}/<class>/` 与 `docs/adr/`。
   - 完成判定：上述每个目录均存在。
3. 写 `SPEC.md`——一页当前规格摘要（对应 dsh 的 `docs/architecture.md` 角色）。
   - 完成判定：文件存在且含可扩展的项目摘要。
4. 写 `ARCHITECTURE.md`——改前必读文档，开头明写「改动前先读本文」。
   - 完成判定：文件存在且带「先读」提示。
5. 写 `docs/adr/0000-template.md`——ADR 模板（Problem / Decision / Alternatives considered / Consequences）。
   - 完成判定：模板文件存在。
6. 写 `.agents/LEDGER.md`——链接所有 note 与 ADR 的索引，以插件内 `dsh-spec/LEDGER.md` 样板为种子。
   - 完成判定：索引存在并链接已建骨架。

## 产出
列出所有创建的文件；指引用户用 `/dsh-spec-note` 记录每次非平凡改动。

## 范围
本技能只脚手架结构与空白文档。note 内容由 `/dsh-spec-note` 负责，note 模板由 D2 (#17) 定义。
```

### skills/dsh-spec-note/SKILL.md
```
---
name: dsh-spec-note
description: 把一次非平凡改动记入变更台账，生成 .agents/notes/<lifecycle>/<class>/<date>-<slug>.md。当用户说「记一笔」「加 note」「留账」，或完成 feature/bug-fix/simplification/architecture/process/testing 改动时调用。
---
# dsh-spec-note

每个非平凡改动对应一条 note，保证项目可追责。

## 步骤
1. 解析 `<slug>`、`--class`（feature|bug-fix|simplification|architecture|process|testing）、`--lifecycle`（proposed|implemented|rejected，默认 implemented；计划阶段用 proposed）。
   - 完成判定：slug、class、lifecycle 已确定。
2. 取 `<date>` 为今天（YYYY-MM-DD），拼出路径 `.agents/notes/<lifecycle>/<class>/<date>-<slug>.md`。
   - 完成判定：目标路径已确定。
3. 写入 note，以下章节须全部填实：
   - `## Problem`——改动缘起。
   - `## Decision`（implemented/rejected）或 `## Proposal`（proposed）——改动本身。
   - `## Alternatives considered`——**必填**，至少一条被否决的备选及其落选原因。
   - `## Consequences`——收益或代价。
   - 完成判定：文件存在且每节有内容；`## Alternatives considered` 非空。
4. 若设了 `$EDITOR`，打开该文件由用户补全；否则逐节向用户索取。
   - 完成判定：用户已填实或确认内容。
5. 在 `.agents/LEDGER.md` 追加该 note 的链接。
   - 完成判定：台账已索引此 note。

## 范围
只负责记录。评审由 `/dsh-spec-review` 负责，分类法由 D2 (#17) 定义。
```

### skills/dsh-spec-review/SKILL.md
```
---
name: dsh-spec-review
description: 合并前闸门——跑 code-review skill，再审计自 --since 起的每个非平凡改动是否都有对应 note/ADR。当用户说「评审」「合并前检查」「跑闸门」或准备合并时调用。
---
# dsh-spec-review

合并闸门：标准评审 + dsh-spec「无 note 不合并」审计。复用现有 `code-review` skill，不重造评审逻辑。

## 步骤
1. 解析 `--since`（默认上次 merge base）与 `--gate`（strict|warn，默认 strict）。
   - 完成判定：两者已确定。
2. 把评审委派给 `code-review` skill，范围相同。
   - 完成判定：code-review 已产出结论。
3. 枚举 `--since` 起的每个非平凡改动，逐个确认 `.agents/notes/` 或 `docs/adr/` 中存在对应记录。
   - 完成判定：每个改动已匹配到 note/ADR，或列入缺口清单。
4. 按 `--gate` 处置缺口：
   - `strict`：报告缺口并以非零退出，阻断合并。
   - `warn`：仅列缺口提醒，零退出。
   - 完成判定：闸门结论已给出；strict 下遇缺口即停。
5. 汇总：code-review 结论 + note 审计结果。
   - 完成判定：用户拿到单一结论（通过 / 阻断）。

## 范围
只审计与闸门。闸门触发位置由 D3 (#18) 定义，评审逻辑本身不在此实现。
```

### skills/dsh-spec-rot/SKILL.md
```
---
name: dsh-spec-rot
description: 漂移与一致性巡检——发现文档漂移、无 note 的 commit、测试退化、ADR 过期。当用户说「巡检」「漂移检查」「rot 检查」或按时触发时调用。
---
# dsh-spec-rot

及早暴露腐烂，便于低成本修复。只报告，不自动修复。

## 步骤
1. 解析 `--check`（all|docs|notes|tests|adr，默认 all）。
   - 完成判定：检查集合已确定。
2. 对每个选中的检查产出发现：
   - `docs`：`ARCHITECTURE.md` 与实际结构/公开接口漂移。
   - `notes`：自上次 note 起的 commit 无对应 `.agents/notes` 条目（比对 `git log` 与台账）。
   - `tests`：测试套件退化（若存在则运行）。
   - `adr`：ADR 被推翻但未标记，或其链接代码已不符。
   - 完成判定：每个选中检查要么有发现列表，要么标记 ok。
3. 输出按严重度（高→低）排序的清单，含文件与具体漂移点。
   - 完成判定：用户拿到可处理的腐烂报告。

## 范围
只检测。修复走正常改动 + `/dsh-spec-note`。完整检查项在地图 Not yet specified，后续 ticket 扩充；本技能先交付上述 v1 集合。
```

## 状态
- D1 (#16) 已采纳 Q1–Q4：命令/技能 1:1 + 命令只委派；评审包装 `code-review`；hooks 占位待 D3；v1 不要 `agents/`。
- 上述 SKILL.md 已按 /writing-for-agents 优化（描述前置触发、步骤带完成判定、范围正向表述）。
- 本文件为原型/设计史，真实骨架由 T1 (#20) 消费落地。
