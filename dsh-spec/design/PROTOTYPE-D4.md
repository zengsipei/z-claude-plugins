# dsh-spec v1 · 活文档脚手架内容（PROTOTYPE — D4 #19）

> PROTOTYPE，非交付物。用于反应取舍。真实模板由 T1 (#20) 落地到 `/dsh-spec-init` 脚手架逻辑，D2 (#17) 已锁定 note 模板，本文件只定「init 生成的活文档」四件套内容骨架。
> 锁定后：结论写入 #19 的 resolution comment 并关闭；本文件保留为设计史（T1 可删除或并入）。

## 背景约束

- D1 (#16) 已定：`/dsh-spec-init` 在**消费项目根**生成 `SPEC.md` / `ARCHITECTURE.md` / `.agents/notes/...` / `docs/adr/` / `.agents/LEDGER.md`；插件内随附 `dsh-spec/LEDGER.md` 样板。
- D2 (#17) 已定 note 五段：Status frontmatter + `## Problem` / `## Decision|Proposal` / **必填** `## Alternatives considered` / `## Consequences`；六类；slug kebab-case ASCII≤40；目录 `.agents/notes/<lifecycle>/<class>/<date>-<slug>.md`。
- 本 ticket 只定 SPEC / ARCHITECTURE / ADR 模板 + CLAUDE.md 追加规则块的内容骨架与取舍。

---

## 1. SPEC.md 模板（项目一页规格摘要）

```markdown
# SPEC — <项目名>

> 活文档：随项目演进，每次相关改动后更新。改结构/契约前先读 ARCHITECTURE.md。

## 目的（Why）
<一句话定位 + 一段：解决谁、什么痛点>

## 范围（In scope）
- <能力/模块清单>

## 非目标（Out of scope）
- <明确排除，防范围蠕变>

## 术语表（Glossary）
| 术语 | 含义 |
|---|---|
| <term> | <def> |

## 当前状态
- 里程碑：v<x.y>
- 最近更新：YYYY-MM-DD（关联 note/ADR 链接）
```

## 2. ARCHITECTURE.md 模板（改前必读）

```markdown
# ARCHITECTURE — <项目名>

> ⚠️ 改动前先读本文。动了结构 / 跨模块契约 / 关键不变量，同步 SPEC.md 并补 note/ADR。

## 读到这里（Read-before-change）
凡触及以下任一项，先读完本文并同步更新：
- 新增 / 删除模块，或重划模块边界
- 改动跨模块契约（函数 / 事件 / 数据 schema）
- 修改下方关键不变量

## 模块边界（Module boundaries）
| 模块 | 职责 | 不依赖谁 | 被谁依赖 |
|---|---|---|---|
| <m> | <resp> | <forbidden deps> | <depended by> |

（依赖方向表达边界，禁止环依赖）

## 关键不变量（Invariants）
- I1：<不变量 + 为何不可破>
- I2：...

## 数据流 / 控制流（可选）
<一句话或 ASCII 图>

## 决策索引
- ADR：`docs/adr/`
- 变更台账：`.agents/notes/`（索引 `.agents/LEDGER.md`）
```

## 3. ADR 模板（docs/adr/0000-template.md）

```markdown
# ADR-0000 — <标题>

Status: <proposed|accepted|superseded-by ADR-00XX|rejected>

## Context（背景）
<什么力量 / 约束 / 需求促使决策；可引用 SPEC / ARCHITECTURE>

## Decision（决策）
<我们决定做什么，为何是当下最优>

## Alternatives considered
- <备选 A>：<为何不选>
- <备选 B>：<为何不选>

## Consequences（后果）
<正向 / 负向 / 需后续跟进项>

## 关联
- note：<link>
- 相关 ADR：<link>
```

## 4. CLAUDE.md 追加规则块

```markdown
## 活文档与变更台账纪律（dsh-spec）
- 改动前先读 `ARCHITECTURE.md`；动了结构 / 契约 / 不变量，同步 `SPEC.md` 并补 note/ADR。
- 每个非平凡改动后跑 `/dsh-spec-note` 留一笔（feature/bug-fix/simplification/architecture/process/testing）。
- 合并前跑 `/dsh-spec-review`（无 note 不合并）。
- 定期 `/dsh-spec-rot` 巡检漂移。
- 术语以 `SPEC.md` 术语表为准。
```

---

## 已锁定取舍（D4 #19 结论 — Q1–Q6 全部采纳推荐，2026-08-25）

> 以下为可争议点，已全部拍板锁入 #19 结论，供 T1 (#20) 落地。

- **Q1 · SPEC.md 与 ARCHITECTURE.md 分工**：推荐如上——SPEC 管「做什么/边界/术语」（产品视角），ARCHITECTURE 管「怎么分/不变量/改前必读」（工程视角），二者正交不重叠。备选：合并为单一 `ARCHITECTURE.md`（更贴近 dsh 原貌，少一个文件），但会混进产品描述。→ 推荐**拆分**。
- **Q2 · ADR 编号**：推荐 `0001`/`0002` 顺序递增（与 note 的 `<date>-<slug>` 区分：ADR=正式决策态、note=过程态）。备选：ADR 也用 `<date>-<slug>`。→ 推荐**顺序编号**（决策态，数量少、需稳定引用）。
- **Q3 · ARCHITECTURE「读到这里」约束强度**：推荐**强提示**（直接写「⚠️ 改动前先读」，并列为 review 闸门检查项），而非轻注释。备选：仅放文末约定。→ 推荐**强提示**（与「无 note 不合并」同调性）。
- **Q4 · CLAUDE.md 落地方式**：推荐 init 时**追加规则块**到项目已有 `CLAUDE.md`（若不存在则新建），并保留「若已有则不覆盖、只 merge」语义（同 D1 的 `--force` 覆盖约定）。备选：独立 `DSH-SPEC.md` 不碰 CLAUDE.md。→ 推荐**追加 CLAUDE.md**（让 agent 在每次会话自动读到纪律）。
- **Q5 · 模板内是否带示例内容**：推荐**纯骨架 + 一行占位注释**（强制填，避免过期示例误导），比内置伪示例更不易腐烂。备选：内置「示例项目」演示。→ 推荐**纯骨架**。
- **Q6 · SPEC 与 note/ADR 的信息重叠**：推荐 SPEC 只放「当前事实快照」，决策来龙去脉进 ADR/note，SPEC 用「最近更新 + 链接」指向，不重复叙述。→ 规则写入 ARCHITECTURE「读到这里」与 CLAUDE.md 块。

## 状态
- D4 (#19) 原型已起；**2026-08-25 用户确认 Q1–Q6 全部采纳推荐 → 结论锁定，#19 关闭，由 T1 (#20) 落地。**
- 锁定结论：
  - Q1 拆分 SPEC.md / ARCHITECTURE.md（产品视角正交工程视角）
  - Q2 ADR 顺序编号 `0001+`（决策态稳定引用）
  - Q3 ARCHITECTURE「读到这里」强提示（与「无 note 不合并」同调性）
  - Q4 CLAUDE.md 追加规则块（不覆盖、merge 语义，同 D1 `--force` 约定）
  - Q5 纯骨架 + 一行占位（防过期示例误导）
  - Q6 SPEC 仅快照+链接，来龙去脉进 ADR/note
