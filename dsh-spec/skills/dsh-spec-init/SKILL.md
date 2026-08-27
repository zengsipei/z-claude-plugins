---
name: dsh-spec-init
description: 在项目中脚手架化 dsh-spec 的活文档与变更台账纪律——活文档（SPEC.md/ARCHITECTURE.md）、变更台账（.agents/notes）、ADR（docs/adr）、台账索引。当用户说「初始化 dsh-spec」「搭活文档骨架」「启用变更台账」「给项目加纪律」，或要在新项目落地 dsh-spec 时调用。
---

# dsh-spec-init

每个项目跑一次，让后续改动有迹可循、可追责、不腐烂。

## 参数

- `--root <path>`：目标项目根，默认当前工作目录。
- `--force`：已初始化时覆盖已存在的脚手架文件。

## 步骤

1. 解析 `--root`（默认 cwd）。若 `<root>/.agents/notes` 已存在且未传 `--force`，停下并告知 dsh-spec 已初始化，提示用 `--force` 覆盖。
   - 完成判定：目标确认为空白，或用户确认使用 `--force`。
2. 写 `<root>/.agents/RULES.md`——共享规则单一事实源的副本：把本插件 `dsh-spec/RULES.md` 母本原样复制过去（与 LEDGER.md 种子机制同构）。
   - 完成判定：副本存在且含 §1–§11 锚点小节。
3. 建目录树：`<root>/.agents/notes/<lifecycle>/<class>/`（lifecycle × class 枚举读上一步副本的 §2 三态 × §1 六类）与 `<root>/docs/adr/`。
   - 完成判定：上述每个目录均存在。
4. 写 `<root>/SPEC.md`——一页当前规格摘要（产品视角）。用下方「SPEC 模板」原样写入。
   - 完成判定：文件存在且含可扩展的项目摘要，顶部带活文档提示。
5. 写 `<root>/ARCHITECTURE.md`——改前必读文档，开头明写「⚠️ 改动前先读本文」。用下方「ARCHITECTURE 模板」原样写入。
   - 完成判定：文件存在且带「先读」强提示。
6. 写 `<root>/docs/adr/0000-template.md`——ADR 模板。用下方「ADR 模板」原样写入。
   - 完成判定：模板文件存在。
7. 写 `<root>/.agents/LEDGER.md`——变更台账索引，以本插件 `dsh-spec/LEDGER.md` 种子文件为模板（六类分节 + 顶部说明）。
   - 完成判定：索引存在并按六类分节。
8. 在 `<root>/CLAUDE.md` 追加规则块（若存在则 merge，不覆盖已有内容；不存在则新建）。规则块见下方「CLAUDE.md 规则块」。
   - 完成判定：项目 CLAUDE.md 含 dsh-spec 纪律块。

## 产出

列出所有创建/修改的文件（含 `.agents/RULES.md` 副本）；指引用户用 `/dsh-spec-note` 记录每次非平凡改动，用 `/dsh-spec-review` 合并前闸门，用 `/dsh-spec-rot` 定期巡检。

## 范围

本技能只脚手架结构与空白文档骨架。note 内容由 `/dsh-spec-note` 负责，note 模板与 LEDGER 格式由 D2 (#17) 定义，ADR 编号规则（顺序 `0001+`）由 D4 (#19) 定义。

脚手架结构清单的镜像锚点是 `RULES.md` 附录「脚手架清单」——`hooks/dsh-spec-gate.py` 的 `ADOPT_MARKERS` 亦从该清单取值。改脚手架结构须同步 RULES.md 附录与 gate.py 常量，反之亦然。

---

## SPEC 模板（写入 SPEC.md）

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

## ARCHITECTURE 模板（写入 ARCHITECTURE.md）

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

## ADR 模板（写入 docs/adr/0000-template.md）

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

## CLAUDE.md 规则块（追加到项目 CLAUDE.md）

```markdown
## 活文档与变更台账纪律（dsh-spec）
- 共享规则（分类 / lifecycle / slug / 路径 / 模板 / 阈值 / warn-only / 归档）以 `.agents/RULES.md` 为单一事实源。
- 改动前先读 `ARCHITECTURE.md`；动了结构 / 契约 / 不变量，同步 `SPEC.md` 并补 note/ADR。
- 每个非平凡改动后跑 `/dsh-spec-note` 留一笔。
- 合并前跑 `/dsh-spec-review`（无 note 不合并）。
- 定期 `/dsh-spec-rot` 巡检漂移。
- 术语以 `SPEC.md` 术语表为准。
```
